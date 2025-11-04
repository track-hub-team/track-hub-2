#!/usr/bin/env bash

# ---------------------------------------------------------------------------
# Sync "uploads" folder with a Git repository
# ---------------------------------------------------------------------------

set -euo pipefail

# --- Config ---
UPLOADS_DIR="${WORKING_DIR%/}/uploads"
GIT_REPO_URL="${UPLOADS_GIT_REPO_URL:?Error: UPLOADS_GIT_REPO_URL is not set}"
GIT_BRANCH="${UPLOADS_GIT_BRANCH:-main}"
GIT_USER_NAME="${UPLOADS_GIT_USER_NAME:-UVLHub Bot}"
GIT_USER_EMAIL="${UPLOADS_GIT_USER_EMAIL:-bot@uvlhub.io}"
GITHUB_TOKEN="${UPLOADS_GITHUB_TOKEN:?Error: UPLOADS_GITHUB_TOKEN is not set}"

echo "Starting uploads synchronization..."

# --- Dependencies ---
command -v git >/dev/null 2>&1          || { echo "Error: git not installed"; exit 1; }
command -v inotifywait >/dev/null 2>&1  || { echo "Error: inotifywait (inotify-tools) not installed"; exit 1; }

# --- Git identity & safe dir ---
git config --global user.name  "$GIT_USER_NAME"
git config --global user.email "$GIT_USER_EMAIL"
mkdir -p "$UPLOADS_DIR"
git config --global --add safe.directory "$UPLOADS_DIR" || true

# Build an authenticated URL ONLY for clone/fetch (no persist)
# Preserve host/path; inject token after scheme
AUTH_CLONE_URL="$(echo "$GIT_REPO_URL" | sed -E 's#^https?://#&'"${GITHUB_TOKEN}"':x-oauth-basic@#')"

# --- Clone or update repo ---
if [ ! -d "$UPLOADS_DIR/.git" ]; then
    echo "Cloning uploads repository..."
    rm -rf "$UPLOADS_DIR"
    git clone --depth 1 --branch "$GIT_BRANCH" --single-branch "$AUTH_CLONE_URL" "$UPLOADS_DIR"
    git -C "$UPLOADS_DIR" remote set-url origin "$GIT_REPO_URL"   # remove token from saved config
else
    echo "Pulling latest changes from uploads repository..."
    git -C "$UPLOADS_DIR" remote set-url origin "$GIT_REPO_URL"   # ensure clean remote
    # Use askpass for auth without persisting token
    GIT_TERMINAL_PROMPT=0 GIT_ASKPASS=/bin/echo \
    git -C "$UPLOADS_DIR" fetch origin "$GIT_BRANCH"
    git -C "$UPLOADS_DIR" checkout "$GIT_BRANCH" 2>/dev/null || git -C "$UPLOADS_DIR" checkout -b "$GIT_BRANCH"
    GIT_TERMINAL_PROMPT=0 GIT_ASKPASS=/bin/echo \
    git -C "$UPLOADS_DIR" pull --rebase --autostash origin "$GIT_BRANCH"
fi

echo "Uploads folder synchronized successfully!"

# --- Prepare GIT_ASKPASS script (used by background watcher for push) ---
GIT_ASKPASS_SCRIPT="/tmp/git-askpass-uploads.sh"
cat > "$GIT_ASKPASS_SCRIPT" <<'EOF'
#!/usr/bin/env bash
case "$1" in
  *Username*) echo "x-access-token" ;;
  *Password*) echo "${UPLOADS_GITHUB_TOKEN}" ;;
  *) echo "" ;;
esac
EOF
chmod +x "$GIT_ASKPASS_SCRIPT"

# --- Start monitoring changes in background ---
# Note: we export only what's needed; remote stays clean (no token)
export UPLOADS_GITHUB_TOKEN="$GITHUB_TOKEN"
export GIT_ASKPASS="$GIT_ASKPASS_SCRIPT"
export GIT_TERMINAL_PROMPT=0

nohup bash -c '
set -euo pipefail
UPLOADS_DIR="'"$UPLOADS_DIR"'"
GIT_BRANCH="'"$GIT_BRANCH"'"

cd "$UPLOADS_DIR"

inotifywait -m -r -e modify,create,delete,move --exclude "^\./?\.git(/|$)" "$UPLOADS_DIR" | \
while read -r directory events filename; do
    echo "Change detected: $events $directory$filename"
    # Debounce a bit to batch multiple writes
    sleep 5

    git add -A

    if ! git diff --staged --quiet; then
        TIMESTAMP=$(date "+%Y-%m-%d %H:%M:%S")
        git commit -m "Auto-sync uploads: $TIMESTAMP" || true

        # Retry push with exponential backoff (handles brief network/auth hiccups)
        for i in 1 2 3 4 5; do
            if git push origin "$GIT_BRANCH"; then
                echo "Changes synchronized successfully at $TIMESTAMP"
                break
            fi
            echo "Push failed (attempt $i). Retrying..."
            sleep $((i*i))
        done
    fi
done
' > /tmp/uploads-sync.log 2>&1 &

echo "Background sync process started (PID: $!)"
