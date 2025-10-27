
function pretty(obj) {
  try { return JSON.stringify(obj, null, 2); } catch(e) { return String(obj); }
}

function rowHTML(step, idx) {
  const ok = step.ok ? "🟢 OK" : "🔴 FAIL";
  const status = step.status ? "[" + step.status + "]" : "";
  const req = (step.method || "?") + " " + (step.url || "n/a");

  // intenta extraer DOI si existe
  let doiHtml = "";
  try {
    const p = step.payload && (typeof step.payload === "string" ? JSON.parse(step.payload) : step.payload);
    const doi = p && p.doi;
    if (doi) {
      doiHtml = `<div style="margin:0.25rem 0;">
        <span style="display:inline-block;background:#eef6ff;border:1px solid #cfe3ff;padding:2px 6px;border-radius:6px;font-family:monospace;">
          DOI: ${doi}
        </span>
      </div>`;
    }
  } catch(e) { /* ignore JSON parse errors */ }

  const payload = step.payload
    ? "<pre style='background:#f6f8fa;padding:0.5rem;border-radius:6px;overflow:auto;'>" +
        (typeof step.payload === "string" ? step.payload : JSON.stringify(step.payload, null, 2)) +
      "</pre>"
    : "";

  const error = step.error ? "<div style='color:#b71c1c;font-weight:600'>Error: " + step.error + "</div>" : "";

  return `
    <li style="margin:0.75rem 0;">
      <div><strong>${idx+1}. ${step.name}</strong> ${ok} ${status}</div>
      <div style="font-family:monospace;font-size:0.95em;margin:0.25rem 0 0.5rem;">${req}</div>
      ${doiHtml}
      ${payload}
      ${error}
    </li>`;
}


function clearOutput() {
  const steps = document.getElementById("steps");
  const status = document.getElementById("status");
  if (steps) steps.innerHTML = "";
  if (status) status.textContent = "";
}

async function runZenodoDemo() {
  clearOutput();
  const status = document.getElementById("status");
  const stepsEl = document.getElementById("steps");
  if (status) status.textContent = "⏳ Ejecutando demo...";
  try {
    const resp = await fetch("/zenodo/demo");
    if (!resp.ok) throw new Error("HTTP " + resp.status);
    const data = await resp.json();
    const steps = Array.isArray(data.steps) ? data.steps : [];
    steps.forEach((s, i) => stepsEl.insertAdjacentHTML("beforeend", rowHTML(s, i)));
    if (status) status.textContent = data.success ? "✅ Demo finalizada correctamente" : "⚠️ Demo finalizada con errores";
  } catch (e) {
    if (status) status.textContent = "❌ Error al ejecutar la demo: " + e;
  }
}

// (deja solo UNA definición)
function test_zenodo_connection() {
  var xhr = new XMLHttpRequest();
  xhr.open('GET', '/zenodo/test', true);
  xhr.setRequestHeader('Content-Type', 'application/json');
  xhr.onreadystatechange = function () {
    if (xhr.readyState === 4 && xhr.status === 200) {
      var response = JSON.parse(xhr.responseText);
      if (response.success) {
        document.getElementById("test_zenodo_connection_success").style.display = "block";
        document.getElementById("test_zenodo_connection_error").style.display = "none";
      } else {
        document.getElementById("test_zenodo_connection_error").style.display = "block";
        document.getElementById("test_zenodo_connection_success").style.display = "none";
        console.warn(response.messages);
      }
    } else if (xhr.readyState === 4 && xhr.status !== 200) {
      document.getElementById("test_zenodo_connection_error").style.display = "block";
      document.getElementById("test_zenodo_connection_success").style.display = "none";
      console.error('Error:', xhr.status);
    }
  };
  xhr.send();
}
