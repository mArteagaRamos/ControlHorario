/**
 * Company Search Module
 * Maneja la búsqueda de empresas por CIF y autocomplete por nombre
 *
 * FASE 3: Extraer búsqueda de empresas
 */

import { getAdminConfig } from '../../utils/config.js';
import { debounce } from '../../utils/debounce.js';

// DOM References
let empresaCifInput = null;
let empresaNombreInput = null;
let empresaNombreSuggestions = null;
let empresaNombreDebounceTimer = null;

/**
 * Inicializa las referencias del DOM
 */
function initializeDOMReferences() {
    empresaCifInput = document.getElementById('empresa-cif-input');
    empresaNombreInput = document.getElementById('empresa-nombre-input');
    empresaNombreSuggestions = document.getElementById('empresa-nombre-suggestions');
}

/**
 * Busca empresa por CIF
 */
async function searchCompanyByCif() {
    const taxId = empresaCifInput.value.trim();
    const feedback = document.getElementById('empresa-feedback');

    if (!taxId) {
        feedback.textContent = 'Introduce un CIF / NIF.';
        feedback.className = 'form-text text-danger';
        return;
    }

    try {
        const LOOKUP_COMPANY_URL = getAdminConfig('LOOKUP_COMPANY_URL');
        const res = await fetch(`${LOOKUP_COMPANY_URL}?tax_id=${encodeURIComponent(taxId)}&include_created=true`);
        const data = await res.json();

        if (data.found) {
            // Importar dinámicamente para evitar dependencia circular
            const { displayCompanyResults } = await import('./result-display.js');
            displayCompanyResults([data]);
            feedback.textContent = 'Empresa encontrada.';
            feedback.className = 'form-text text-success';
        } else {
            clearResults();
            feedback.textContent = 'No existe ninguna empresa con ese CIF.';
            feedback.className = 'form-text text-danger';
        }
    } catch (error) {
        console.error('Error searching company by CIF:', error);
        feedback.textContent = 'Error al buscar la empresa.';
        feedback.className = 'form-text text-danger';
    }
}

/**
 * Busca empresas por nombre (autocomplete)
 */
async function searchCompanyByName(query) {
    if (!query || query.length < 2) {
        empresaNombreSuggestions.classList.add('d-none');
        document.getElementById('empresa-feedback').textContent = '';
        return;
    }

    try {
        const LOOKUP_COMPANY_URL = getAdminConfig('LOOKUP_COMPANY_URL');
        const res = await fetch(`${LOOKUP_COMPANY_URL}?name=${encodeURIComponent(query)}&include_created=true`);
        const data = await res.json();
        const results = data.results || [];

        empresaNombreSuggestions.innerHTML = '';

        if (results.length === 0) {
            empresaNombreSuggestions.classList.add('d-none');
            document.getElementById('empresa-feedback').textContent = 'Sin resultados para esa búsqueda.';
            document.getElementById('empresa-feedback').className = 'form-text text-warning';
            return;
        }

        document.getElementById('empresa-feedback').textContent = '';
        results.forEach(company => {
            const li = document.createElement('li');
            li.className = 'list-group-item list-group-item-action d-flex justify-content-between align-items-center';
            li.style.cursor = 'pointer';
            li.innerHTML = `
                <span>
                    <strong>${company.name}</strong>
                    <small class="text-muted ms-2">${company.legal_name}</small>
                </span>
            `;
            li.addEventListener('click', async () => {
                const { displayCompanyResults } = await import('./result-display.js');
                displayCompanyResults([company]);
                empresaNombreInput.value = company.name;
                empresaNombreSuggestions.classList.add('d-none');
                document.getElementById('empresa-feedback').textContent = 'Empresa seleccionada.';
                document.getElementById('empresa-feedback').className = 'form-text text-success';
            });
            empresaNombreSuggestions.appendChild(li);
        });

        empresaNombreSuggestions.classList.remove('d-none');
    } catch (error) {
        console.error('Error searching company by name:', error);
        empresaNombreSuggestions.classList.add('d-none');
        document.getElementById('empresa-feedback').textContent = 'Error al buscar empresas.';
        document.getElementById('empresa-feedback').className = 'form-text text-danger';
    }
}

/**
 * Limpia los resultados
 */
export function clearResults() {
    const sectionResultados = document.getElementById('section-resultados');
    if (sectionResultados) {
        sectionResultados.classList.add('d-none');
    }
}

/**
 * Inicializa los event listeners
 */
export function initializeCompanySearch() {
    initializeDOMReferences();

    // Búsqueda por CIF
    document.getElementById('btn-buscar-empresa-cif')?.addEventListener('click', searchCompanyByCif);

    // Búsqueda por nombre (autocomplete con debounce)
    empresaNombreInput?.addEventListener('input', () => {
        clearTimeout(empresaNombreDebounceTimer);
        const query = empresaNombreInput.value.trim();
        empresaNombreDebounceTimer = setTimeout(() => {
            searchCompanyByName(query);
        }, 300);
    });

    // Cerrar sugerencias al hacer click fuera
    document.addEventListener('click', (e) => {
        if (!empresaNombreInput?.contains(e.target) && !empresaNombreSuggestions?.contains(e.target)) {
            empresaNombreSuggestions?.classList.add('d-none');
        }
    });

    console.log('[CompanySearch] Initialized');
}
