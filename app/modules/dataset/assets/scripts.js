var currentId = 0;
var amount_authors = 0;

function show_upload_dataset() {
    document.getElementById('upload_dataset').style.display = 'block';
}

function generateIncrementalId() {
    return currentId++;
}

function addField(newAuthor, name, text, className = 'col-lg-6 col-12 mb-3') {
    let fieldWrapper = document.createElement('div');
    fieldWrapper.className = className;

    let label = document.createElement('label');
    label.className = 'form-label';
    label.for = name;
    label.textContent = text;

    let field = document.createElement('input');
    field.name = name;
    field.className = 'form-control';

    fieldWrapper.appendChild(label);
    fieldWrapper.appendChild(field);
    newAuthor.appendChild(fieldWrapper);
}

function addRemoveButton(newAuthor) {
    let buttonWrapper = document.createElement('div');
    buttonWrapper.className = 'col-12 mb-2';

    let button = document.createElement('button');
    button.textContent = 'Remove author';
    button.className = 'btn btn-danger btn-sm';
    button.type = 'button';
    button.addEventListener('click', function (event) {
        event.preventDefault();
        newAuthor.remove();
    });

    buttonWrapper.appendChild(button);
    newAuthor.appendChild(buttonWrapper);
}

function createAuthorBlock(idx, suffix = "") {
    let newAuthor = document.createElement('div');
    newAuthor.className = 'author-block row mb-3';

    // Campo Name
    let nameCol = document.createElement('div');
    nameCol.className = 'col-md-4';
    nameCol.innerHTML = `
        <label class="form-label">Name *</label>
        <input type="text" name="${suffix}authors-${idx}-name" class="form-control" required>
    `;
    newAuthor.appendChild(nameCol);

    // Campo Affiliation
    let affiliationCol = document.createElement('div');
    affiliationCol.className = 'col-md-4';
    affiliationCol.innerHTML = `
        <label class="form-label">Affiliation</label>
        <input type="text" name="${suffix}authors-${idx}-affiliation" class="form-control">
    `;
    newAuthor.appendChild(affiliationCol);

    // Campo ORCID
    let orcidCol = document.createElement('div');
    orcidCol.className = 'col-md-3';
    orcidCol.innerHTML = `
        <label class="form-label">ORCID</label>
        <input type="text" name="${suffix}authors-${idx}-orcid" class="form-control" placeholder="0000-0000-0000-0000">
    `;
    newAuthor.appendChild(orcidCol);

    // Botón de eliminar
    let removeCol = document.createElement('div');
    removeCol.className = 'col-md-1 d-flex align-items-end';
    let removeBtn = document.createElement('button');
    removeBtn.type = 'button';
    removeBtn.className = 'btn btn-danger btn-sm remove-author';
    removeBtn.innerHTML = '<i data-feather="trash-2"></i>';
    removeBtn.addEventListener('click', function () {
        newAuthor.remove();
    });
    removeCol.appendChild(removeBtn);
    newAuthor.appendChild(removeCol);

    return newAuthor;
}

// Evento para añadir autores
document.addEventListener('DOMContentLoaded', function() {
    const addAuthorBtn = document.getElementById('add_author');
    if (addAuthorBtn) {
        addAuthorBtn.addEventListener('click', function () {
            let authorsList = document.getElementById('authors_list');
            let currentAuthors = authorsList.querySelectorAll('.author-block').length;
            let newAuthor = createAuthorBlock(currentAuthors, "");
            authorsList.appendChild(newAuthor);

            // Actualizar íconos de Feather
            if (typeof feather !== 'undefined') {
                feather.replace();
            }
        });
    }

    // Evento para eliminar autores (delegación de eventos)
    const authorsList = document.getElementById('authors_list');
    if (authorsList) {
        authorsList.addEventListener('click', function(e) {
            if (e.target.closest('.remove-author')) {
                const authorBlock = e.target.closest('.author-block');
                if (authorBlock) {
                    authorBlock.remove();
                }
            }
        });
    }
});

function check_title_and_description() {
    let titleInput = document.querySelector('input[name="title"]');
    let descriptionTextarea = document.querySelector('textarea[name="desc"]');

    if (!titleInput || !descriptionTextarea) {
        return false;
    }

    titleInput.classList.remove("error");
    descriptionTextarea.classList.remove("error");
    clean_upload_errors();

    let titleLength = titleInput.value.trim().length;
    let descriptionLength = descriptionTextarea.value.trim().length;

    if (titleLength < 3) {
        write_upload_error("Title must be at least 3 characters long");
        titleInput.classList.add("error");
        return false;
    }

    if (descriptionLength < 3) {
        write_upload_error("Description must be at least 3 characters long");
        descriptionTextarea.classList.add("error");
        return false;
    }

    return true;
}

function show_loading() {
    const uploadBtn = document.getElementById("upload_dataset_btn");
    if (uploadBtn) {
        uploadBtn.disabled = true;
        uploadBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Uploading...';
    }
}

function hide_loading() {
    const uploadBtn = document.getElementById("upload_dataset_btn");
    if (uploadBtn) {
        uploadBtn.disabled = false;
        uploadBtn.innerHTML = '<i data-feather="upload"></i> Upload dataset';
        if (typeof feather !== 'undefined') {
            feather.replace();
        }
    }
}

function clean_upload_errors() {
    const errorContainer = document.getElementById('upload_errors');
    if (errorContainer) {
        errorContainer.innerHTML = '';
        errorContainer.style.display = 'none';
    }
}

function write_upload_error(error_message) {
    const errorContainer = document.getElementById('upload_errors');
    if (errorContainer) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'alert alert-danger alert-dismissible fade show';
        errorDiv.innerHTML = `
            ${error_message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        errorContainer.appendChild(errorDiv);
        errorContainer.style.display = 'block';
    } else {
        alert('Upload error: ' + error_message);
    }
    console.error('Upload error:', error_message);
}

function isValidOrcid(orcid) {
    let orcidRegex = /^\d{4}-\d{4}-\d{4}-\d{4}$/;
    return orcidRegex.test(orcid);
}

// ========================================
// DROPZONE PARA UVL
// ========================================
Dropzone.options.uvlDropzone = {
    paramName: "file",
    maxFilesize: 20,
    acceptedFiles: ".uvl",
    dictDefaultMessage: "Drop UVL files here or click to browse",
    dictFileTooBig: "File is too big ({{filesize}}MB). Max: {{maxFilesize}}MB",
    dictInvalidFileType: "Invalid file type. Only .uvl files allowed",

    init: function () {
        const dz = this;

        dz.on("success", function (file, response) {
            if (typeof show_upload_dataset === "function") show_upload_dataset();

            const fileList = document.getElementById("uvl-file-list");
            const li = document.createElement("li");
            li.className = "file-item mb-3 p-3 border rounded";

            const h4 = document.createElement("h4");
            h4.className = "h6 mb-2";
            h4.innerHTML = `<i data-feather="file-text"></i> ${response.filename}`;
            li.appendChild(h4);

            const id = generateIncrementalId();

            // Botones
            const btnInfo = document.createElement("button");
            btnInfo.type = "button";
            btnInfo.textContent = "Show info";
            btnInfo.className = "btn btn-outline-secondary btn-sm me-2";

            const btnDel = document.createElement("button");
            btnDel.type = "button";
            btnDel.textContent = "Delete";
            btnDel.className = "btn btn-outline-danger btn-sm";

            li.appendChild(btnInfo);
            li.appendChild(btnDel);

            // ✅ Formulario específico para UVL
            const form = document.createElement("div");
            form.className = "uvl_form mt-3";
            form.style.display = "none";
            form.innerHTML = `
                <div class="row">
                    <input type="hidden" name="feature_models-${id}-filename" value="${response.filename}">

                    <div class="col-12 mb-3">
                        <label class="form-label">Title *</label>
                        <input type="text" class="form-control" name="feature_models-${id}-title" required>
                    </div>

                    <div class="col-12 mb-3">
                        <label class="form-label">Description</label>
                        <textarea rows="3" class="form-control" name="feature_models-${id}-desc"></textarea>
                    </div>

                    <div class="col-md-6 mb-3">
                        <label class="form-label">UVL Version</label>
                        <input type="text" class="form-control" name="feature_models-${id}-file_version" value="1.0">
                    </div>

                    <div class="col-md-6 mb-3">
                        <label class="form-label">Publication type</label>
                        <select class="form-control" name="feature_models-${id}-publication_type">
                            <option value="none">None</option>
                            <option value="conference_paper">Conference paper</option>
                            <option value="journal_article">Journal article</option>
                            <option value="technical_note">Technical note</option>
                            <option value="other">Other</option>
                        </select>
                    </div>

                    <div class="col-md-6 mb-3">
                        <label class="form-label">Publication DOI</label>
                        <input type="text" class="form-control" name="feature_models-${id}-publication_doi" placeholder="10.1234/example.doi">
                    </div>

                    <div class="col-md-6 mb-3">
                        <label class="form-label">Tags (separated by commas)</label>
                        <input type="text" class="form-control" name="feature_models-${id}-tags" placeholder="feature-model, spl, variability">
                    </div>
                </div>
            `;

            // Event listeners
            btnInfo.addEventListener("click", function () {
                const visible = form.style.display !== "none";
                form.style.display = visible ? "none" : "block";
                btnInfo.textContent = visible ? "Show info" : "Hide info";
            });

            btnDel.addEventListener("click", function () {
                fileList.removeChild(li);
                dz.removeFile(file);
                fetch("/dataset/file/delete", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ file: response.filename }),
                }).catch(() => {});
            });

            li.appendChild(form);
            fileList.appendChild(li);

            if (typeof feather !== 'undefined') {
                feather.replace();
            }
        });

        dz.on("error", function (file, errorMessage) {
            console.error("UVL Upload error:", errorMessage);
            const alerts = document.getElementById("uvl-alerts");
            if (alerts) {
                alerts.innerHTML = `<div class="alert alert-danger alert-dismissible fade show">
                    ${errorMessage}
                    <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                </div>`;
            }
            dz.removeFile(file);
        });
    }
};

// ========================================
// DROPZONE PARA GPX
// ========================================
Dropzone.options.gpxDropzone = {
    paramName: "file",
    maxFilesize: 20,
    acceptedFiles: ".gpx",
    dictDefaultMessage: "Drop GPX files here or click to browse",
    dictFileTooBig: "File is too big ({{filesize}}MB). Max: {{maxFilesize}}MB",
    dictInvalidFileType: "Invalid file type. Only .gpx files allowed",

    init: function () {
        const dz = this;

        dz.on("success", function (file, response) {
            if (typeof show_upload_dataset === "function") show_upload_dataset();

            const fileList = document.getElementById("gpx-file-list");
            const li = document.createElement("li");
            li.className = "file-item mb-3 p-3 border rounded";

            const h4 = document.createElement("h4");
            h4.className = "h6 mb-2";
            h4.innerHTML = `<i data-feather="map-pin"></i> ${response.filename}`;
            li.appendChild(h4);

            const id = generateIncrementalId();

            // Botones
            const btnInfo = document.createElement("button");
            btnInfo.type = "button";
            btnInfo.textContent = "Show info";
            btnInfo.className = "btn btn-outline-secondary btn-sm me-2";

            const btnDel = document.createElement("button");
            btnDel.type = "button";
            btnDel.textContent = "Delete";
            btnDel.className = "btn btn-outline-danger btn-sm";

            li.appendChild(btnInfo);
            li.appendChild(btnDel);

            // ✅ Formulario específico para GPX con publication_type
            const form = document.createElement("div");
            form.className = "gpx_form mt-3";
            form.style.display = "none";
            form.innerHTML = `
                <div class="row">
                    <input type="hidden" name="feature_models-${id}-filename" value="${response.filename}">

                    <div class="col-12 mb-3">
                        <label class="form-label">Track Name *</label>
                        <input type="text" class="form-control" name="feature_models-${id}-title" required>
                    </div>

                    <div class="col-12 mb-3">
                        <label class="form-label">Description</label>
                        <textarea rows="3" class="form-control" name="feature_models-${id}-desc" placeholder="Describe your track..."></textarea>
                    </div>

                    <div class="col-md-6 mb-3">
                        <label class="form-label">GPX Version</label>
                        <input type="text" class="form-control" name="feature_models-${id}-file_version" value="1.1" readonly>
                    </div>

                    <div class="col-md-6 mb-3">
                        <label class="form-label">Track Type</label>
                        <select class="form-control" name="feature_models-${id}-gpx_type">
                            <option value="run">Running</option>
                            <option value="bike">Cycling</option>
                            <option value="hike">Hiking</option>
                            <option value="walk">Walking</option>
                            <option value="other">Other</option>
                        </select>
                    </div>

                    <div class="col-md-6 mb-3">
                        <label class="form-label">Publication type</label>
                        <select class="form-control" name="feature_models-${id}-publication_type">
                            <option value="none">None</option>
                            <option value="conference_paper">Conference paper</option>
                            <option value="journal_article">Journal article</option>
                            <option value="technical_note">Technical note</option>
                            <option value="other">Other</option>
                        </select>
                    </div>

                    <div class="col-md-6 mb-3">
                        <label class="form-label">Publication DOI</label>
                        <input type="text" class="form-control" name="feature_models-${id}-publication_doi" placeholder="10.1234/example.doi">
                    </div>

                    <div class="col-12 mb-3">
                        <label class="form-label">Tags (separated by commas)</label>
                        <input type="text" class="form-control" name="feature_models-${id}-tags" placeholder="outdoor, gps, trail">
                    </div>
                </div>
            `;

            // Event listeners
            btnInfo.addEventListener("click", function () {
                const visible = form.style.display !== "none";
                form.style.display = visible ? "none" : "block";
                btnInfo.textContent = visible ? "Show info" : "Hide info";
            });

            btnDel.addEventListener("click", function () {
                fileList.removeChild(li);
                dz.removeFile(file);
                fetch("/dataset/file/delete", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ file: response.filename }),
                }).catch(() => {});
            });

            li.appendChild(form);
            fileList.appendChild(li);

            if (typeof feather !== 'undefined') {
                feather.replace();
            }
        });

        dz.on("error", function (file, errorMessage) {
            console.error("GPX Upload error:", errorMessage);
            const alerts = document.getElementById("gpx-alerts");
            if (alerts) {
                alerts.innerHTML = `<div class="alert alert-danger alert-dismissible fade show">
                    ${errorMessage}
                    <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                </div>`;
            }
            dz.removeFile(file);
        });
    }
};

// ========================================
// SUBMIT DEL FORMULARIO
// ========================================
document.addEventListener('DOMContentLoaded', function() {
    const uploadBtn = document.getElementById('upload_dataset_btn');
    if (uploadBtn) {
        uploadBtn.addEventListener('click', function(e) {
            e.preventDefault();

            // Validar que hay al menos 1 archivo UVL o GPX
            const uvlFiles = document.querySelectorAll('#uvl-file-list .file-item').length;
            const gpxFiles = document.querySelectorAll('#gpx-file-list .file-item').length;

            if (uvlFiles === 0 && gpxFiles === 0) {
                write_upload_error('Please upload at least one file (UVL or GPX)');
                return;
            }

            // Validar título y descripción
            if (!check_title_and_description()) {
                return;
            }

            // Validar autores
            const authors = document.querySelectorAll('.author-block');
            let validAuthors = true;

            authors.forEach((author) => {
                const nameInput = author.querySelector('input[name*="-name"]');
                const orcidInput = author.querySelector('input[name*="-orcid"]');

                if (nameInput && nameInput.value.trim() === '') {
                    write_upload_error("Author's name cannot be empty");
                    validAuthors = false;
                    return;
                }

                if (orcidInput && orcidInput.value.trim() !== '' && !isValidOrcid(orcidInput.value.trim())) {
                    write_upload_error("ORCID value does not conform to valid format: " + orcidInput.value);
                    validAuthors = false;
                    return;
                }
            });

            if (!validAuthors) {
                return;
            }

            clean_upload_errors();
            show_loading();

            // Recopilar datos del formulario
            const formData = new FormData();

            // CSRF Token
            const csrfToken = document.querySelector('input[name="csrf_token"]');
            if (csrfToken) {
                formData.append('csrf_token', csrfToken.value);
            }

            // Información básica
            const basicForm = document.getElementById('basic_info_form');
            if (basicForm) {
                const inputs = basicForm.querySelectorAll('input, select, textarea');
                inputs.forEach(input => {
                    if (input.name && input.name !== 'csrf_token') {
                        formData.append(input.name, input.value);
                    }
                });
            }

            // Añadir feature models de UVL
            document.querySelectorAll('.uvl_form').forEach(form => {
                const inputs = form.querySelectorAll('input, select, textarea');
                inputs.forEach(input => {
                    if (input.name) {
                        formData.append(input.name, input.value);
                    }
                });
            });

            // Añadir feature models de GPX
            document.querySelectorAll('.gpx_form').forEach(form => {
                const inputs = form.querySelectorAll('input, select, textarea');
                inputs.forEach(input => {
                    if (input.name) {
                        formData.append(input.name, input.value);
                    }
                });
            });

            // Añadir autores
            authors.forEach((author) => {
                const inputs = author.querySelectorAll('input');
                inputs.forEach(input => {
                    if (input.name) {
                        formData.append(input.name, input.value);
                    }
                });
            });

            // Debug: mostrar datos que se van a enviar
            console.log('FormData contents:');
            for (let pair of formData.entries()) {
                console.log(pair[0] + ': ' + pair[1]);
            }

            // Enviar formulario
            fetch('/dataset/upload', {
                method: 'POST',
                body: formData
            })
            .then(response => {
                console.log('Response status:', response.status);
                return response.json().then(data => {
                    return { status: response.status, data: data };
                });
            })
            .then(result => {
                hide_loading();
                console.log('Response data:', result.data);

                if (result.status === 200) {
                    window.location.href = '/dataset/list';
                } else {
                    const errorMessage = result.data.message || 'Unknown error';
                    const errors = result.data.errors || [];

                    let fullError = errorMessage;
                    if (errors.length > 0) {
                        fullError += '\n\nDetails:\n' + errors.join('\n');
                    }

                    write_upload_error(fullError);
                }
            })
            .catch(error => {
                hide_loading();
                console.error('Fetch error:', error);
                write_upload_error('Network error: ' + error.message);
            });
        });
    }
});

// ========================================
// TEST ZENODO CONNECTION (si existe)
// ========================================
window.addEventListener('load', function() {
    if (typeof test_zenodo_connection === "function") {
        test_zenodo_connection();
    }
});
