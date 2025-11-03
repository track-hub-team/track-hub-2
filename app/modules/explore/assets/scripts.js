let currentPage = 1;
const perPage = 20;

document.addEventListener('DOMContentLoaded', () => {
    // Inicializar búsqueda al cargar la página
    let urlParams = new URLSearchParams(window.location.search);
    let queryParam = urlParams.get('query');

    if (queryParam && queryParam.trim() !== '') {
        const queryInput = document.getElementById('query');
        queryInput.value = queryParam;
    }
    
    // Configurar listeners de filtros
    setupFilters();
    
    // Realizar búsqueda inicial
    performSearch(1);
});

function setupFilters() {
    const filters = document.querySelectorAll('#filters input, #filters select, #filters [type="radio"]');

    filters.forEach(filter => {
        filter.addEventListener('input', () => {
            currentPage = 1;
            performSearch(1);
        });
    });
    
    // Clear filters button
    document.getElementById('clear-filters').addEventListener('click', clearFilters);
}

function performSearch(page) {
    const csrfToken = document.getElementById('csrf_token').value;

    const searchCriteria = {
        csrf_token: csrfToken,
        query: document.querySelector('#query').value,
        publication_type: document.querySelector('#publication_type').value,
        sorting: document.querySelector('[name="sorting"]:checked').value,
        dataset_type: document.querySelector('#dataset_type').value,
        gpx_difficulty: document.querySelector('#gpx_difficulty').value,
        page: page,
        per_page: perPage,
    };

    console.log("Searching with criteria:", searchCriteria);

    // Limpiar resultados solo en la primera página
    if (page === 1) {
        document.getElementById('results').innerHTML = '';
        document.getElementById("results_not_found").style.display = "none";
    }

    fetch('/explore', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(searchCriteria),
    })
        .then(response => response.json())
        .then(data => {

            console.log("Response from server:", data);

            // Verificar que data.datasets existe
            if (!data.datasets) {
                console.error("Error: data.datasets is undefined", data);
                document.getElementById("results_not_found").style.display = "block";
                return;
            }

            // Results counter
            const resultText = data.total === 1 ? 'dataset' : 'datasets';
            document.getElementById('results_number').textContent = `${data.total} ${resultText} found`;

            if (data.total === 0) {
                document.getElementById("results_not_found").style.display = "block";
                return;
            } else {
                document.getElementById("results_not_found").style.display = "none";
            }

            // Renderizar datasets
            data.datasets.forEach(dataset => {
                let card = document.createElement('div');
                card.className = 'col-12';
                
                if (dataset.dataset_type === 'gpx') {
                    card.innerHTML = renderGPXCard(dataset);
                } else {
                    card.innerHTML = renderUVLCard(dataset);
                }

                document.getElementById('results').appendChild(card);
            });

            // Añadir botón "Load more" si hay más páginas
            if (page < data.total_pages) {
                let loadMoreBtn = document.createElement('div');
                loadMoreBtn.className = 'col-12 text-center mt-3';
                loadMoreBtn.innerHTML = `
                    <button class="btn btn-primary" onclick="loadMore(${page + 1})">
                        Load more datasets (${data.total - (page * perPage)} remaining)
                    </button>
                `;
                document.getElementById('results').appendChild(loadMoreBtn);
            }
        })
        .catch(error => {
            console.error("Error fetching data:", error);
            document.getElementById("results_not_found").style.display = "block";
        });
}

function renderGPXCard(dataset) {
    // ✅ CONSTRUIR URL CORRECTA
    const datasetUrl = `/gpx/${dataset.id}`;
    const downloadUrl = `/gpx/${dataset.id}/download`;
    
    // ✅ FORMATEAR MÉTRICAS
    const distance = dataset.length_3d ? `${(dataset.length_3d / 1000).toFixed(1)} km` : 'N/A';
    const elevation = dataset.uphill ? `${Math.round(dataset.uphill)} m` : 'N/A';
    const duration = dataset.moving_time ? formatDuration(dataset.moving_time) : 'N/A';
    
    return `
        <div class="card">
            <div class="card-body">
                <div class="d-flex align-items-center justify-content-between">
                    <h3><a href="${datasetUrl}">${escapeHtml(dataset.title)}</a></h3>
                    <div>
                        <span class="badge bg-success">Hiking Track</span>
                        ${dataset.difficulty ? `<span class="badge bg-warning text-dark">${dataset.difficulty}</span>` : ''}
                    </div>
                </div>
                <p class="text-secondary">${formatDate(dataset.created_at)}</p>

                <div class="row mb-2">
                    <div class="col-md-4 col-12">
                        <span class="text-secondary">Metrics</span>
                    </div>
                    <div class="col-md-8 col-12">
                        <p class="p-0 m-0">📏 Distance: ${distance}</p>
                        <p class="p-0 m-0">⛰️ Elevation gain: ${elevation}</p>
                        <p class="p-0 m-0">⏱️ Duration: ${duration}</p>
                    </div>
                </div>

                ${dataset.hikr_user ? `
                <div class="row mb-2">
                    <div class="col-md-4 col-12">
                        <span class="text-secondary">Author</span>
                    </div>
                    <div class="col-md-8 col-12">
                        <p class="p-0 m-0">${escapeHtml(dataset.hikr_user)} (hikr.org)</p>
                    </div>
                </div>
                ` : ''}

                <div class="row">
                    <div class="col-md-4 col-12"></div>
                    <div class="col-md-8 col-12">
                        <a href="${datasetUrl}" class="btn btn-outline-primary btn-sm" style="border-radius: 5px;">
                            View track
                        </a>
                        <a href="${downloadUrl}" class="btn btn-outline-success btn-sm" style="border-radius: 5px;">
                            Download GPX
                        </a>
                    </div>
                </div>
            </div>
        </div>
    `;
}

function renderUVLCard(dataset) {
    // ✅ CONSTRUIR URL CORRECTA
    const datasetUrl = `/dataset/view/${dataset.id}`;
    const downloadUrl = `/dataset/download/${dataset.id}`;
    
    return `
        <div class="card">
            <div class="card-body">
                <div class="d-flex align-items-center justify-content-between">
                    <h3><a href="${datasetUrl}">${escapeHtml(dataset.title)}</a></h3>
                    <div>
                        <span class="badge bg-primary" style="cursor: pointer;" onclick="set_publication_type_as_query('${dataset.publication_type}')">${dataset.publication_type || 'dataset'}</span>
                    </div>
                </div>
                <p class="text-secondary">${formatDate(dataset.created_at)}</p>

                ${dataset.description ? `
                <div class="row mb-2">
                    <div class="col-md-4 col-12">
                        <span class="text-secondary">Description</span>
                    </div>
                    <div class="col-md-8 col-12">
                        <p class="card-text">${escapeHtml(dataset.description)}</p>
                    </div>
                </div>
                ` : ''}

                ${dataset.authors && dataset.authors.length > 0 ? `
                <div class="row mb-2">
                    <div class="col-md-4 col-12">
                        <span class="text-secondary">Authors</span>
                    </div>
                    <div class="col-md-8 col-12">
                        ${dataset.authors.map(author => `
                            <p class="p-0 m-0">${escapeHtml(author.name)}${author.affiliation ? ` (${escapeHtml(author.affiliation)})` : ''}${author.orcid ? ` (${author.orcid})` : ''}</p>
                        `).join('')}
                    </div>
                </div>
                ` : ''}

                ${dataset.tags ? `
                <div class="row mb-2">
                    <div class="col-md-4 col-12">
                        <span class="text-secondary">Tags</span>
                    </div>
                    <div class="col-md-8 col-12">
                        ${dataset.tags.split(',').map(tag => `<span class="badge bg-primary me-1" style="cursor: pointer;" onclick="set_tag_as_query('${escapeHtml(tag.trim())}')">${escapeHtml(tag.trim())}</span>`).join('')}
                    </div>
                </div>
                ` : ''}

                <div class="row">
                    <div class="col-md-4 col-12"></div>
                    <div class="col-md-8 col-12">
                        <a href="${datasetUrl}" class="btn btn-outline-primary btn-sm" style="border-radius: 5px;">
                            View dataset
                        </a>
                        <a href="${downloadUrl}" class="btn btn-outline-primary btn-sm" style="border-radius: 5px;">
                            Download${dataset.total_size_in_human_format ? ` (${dataset.total_size_in_human_format})` : ''}
                        </a>
                    </div>
                </div>
            </div>
        </div>
    `;
}

function loadMore(page) {
    currentPage = page;
    
    // Remover botón "Load more" anterior
    const loadMoreBtns = document.querySelectorAll('.btn-primary');
    loadMoreBtns.forEach(btn => {
        if (btn.textContent.includes('Load more')) {
            btn.parentElement.remove();
        }
    });
    
    performSearch(page);
}

function formatDate(dateString) {
    const options = {day: 'numeric', month: 'long', year: 'numeric', hour: 'numeric', minute: 'numeric'};
    const date = new Date(dateString);
    return date.toLocaleString('en-US', options);
}

function formatDuration(seconds) {
    if (!seconds) return 'N/A';
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    return `${hours}h ${minutes}m`;
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function set_tag_as_query(tagName) {
    const queryInput = document.getElementById('query');
    queryInput.value = tagName.trim();
    queryInput.dispatchEvent(new Event('input', {bubbles: true}));
}

function set_publication_type_as_query(publicationType) {
    const publicationTypeSelect = document.getElementById('publication_type');
    for (let i = 0; i < publicationTypeSelect.options.length; i++) {
        if (publicationTypeSelect.options[i].text === publicationType.trim()) {
            publicationTypeSelect.value = publicationTypeSelect.options[i].value;
            break;
        }
    }
    publicationTypeSelect.dispatchEvent(new Event('input', {bubbles: true}));
}

function clearFilters() {
    document.querySelector('#query').value = "";
    document.querySelector('#publication_type').value = "any";
    document.querySelector('#dataset_type').value = "any";
    document.querySelector('#gpx_difficulty').value = "any";
    
    document.querySelectorAll('[name="sorting"]').forEach(option => {
        option.checked = option.value == "newest";
    });

    currentPage = 1;
    performSearch(1);
}