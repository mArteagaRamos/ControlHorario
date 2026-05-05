/**
 * Company Search Module
 * Maneja la búsqueda de empresas por CIF y autocomplete por nombre
 * REFACTORIZADO: Usa search-utils y ui-utils para reducir duplicación
 */

import { getAdminConfig } from '../../utils/config.js';
import { createDebouncedSearch, renderSuggestions, setupClickOutsideListener, clearSuggestions } from '../../utils/search-utils.js';
import { setFeedback, hideElement } from '../../utils/ui-utils.js';

// DOM References
let empresaCifInput = null;
let empresaNombreInput = null;
let empresaNombreSuggestions = null;

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
        setFeedback(feedback, 'Introduce un CIF / NIF.', 'danger');
        return;
    }

    try {
        const LOOKUP_COMPANY_URL = getAdminConfig('LOOKUP_COMPANY_URL');
        const url = new URL(LOOKUP_COMPANY_URL, window.location.origin);
        url.searchParams.set('tax_id', taxId);
        url.searchParams.set('include_created', 'true');

        const res = await fetch(url.toString());
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();

        if (data.found) {
            const { displayCompanyResults } = await import('./result-display.js');
            displayCompanyResults([data]);
            setFeedback(feedback, 'Empresa encontrada.', 'success');
        } else {
            clearResults();
            setFeedback(feedback, 'No existe ninguna empresa con ese CIF.', 'danger');
        }
    } catch (error) {
        console.error('Error searching company by CIF:', error);
        setFeedback(feedback, 'Error al buscar la empresa.', 'danger');
    }
}

/**
 * Formatea item de empresa para sugerencias
 */
function formatCompanyItem(company) {
    return `
        <span>
            <strong>${company.name}</strong>
            <small class="text-muted ms-2">${company.legal_name}</small>
        </span>
    `;
}

/**
 * Limpia los resultados
 */
export function clearResults() {
    hideElement(document.getElementById('section-resultados'));
}

/**
 * Inicializa los event listeners
 */
export function initializeCompanySearch() {
    initializeDOMReferences();

    const LOOKUP_COMPANY_URL = getAdminConfig('LOOKUP_COMPANY_URL');
    const feedback = document.getElementById('empresa-feedback');

    // Búsqueda por CIF
    document.getElementById('btn-buscar-empresa-cif')?.addEventListener('click', searchCompanyByCif);

    // Búsqueda por nombre (autocomplete con debounce reutilizable)
    const performSearch = createDebouncedSearch(
        LOOKUP_COMPANY_URL,
        async (data) => {
            const results = data.results || [];

            if (results.length === 0) {
                clearSuggestions(empresaNombreSuggestions);
                setFeedback(feedback, 'Sin resultados para esa búsqueda.', 'warning');
                return;
            }

            setFeedback(feedback, '', '');
            renderSuggestions(results, empresaNombreSuggestions, formatCompanyItem, async (company) => {
                const { displayCompanyResults } = await import('./result-display.js');
                displayCompanyResults([company]);
                empresaNombreInput.value = company.name;
                setFeedback(feedback, 'Empresa seleccionada.', 'success');
            });
        },
        (error) => {
            console.error('Error searching company by name:', error);
            clearSuggestions(empresaNombreSuggestions);
            setFeedback(feedback, 'Error al buscar empresas.', 'danger');
        },
        300,
        { include_created: 'true' }
    );

    empresaNombreInput?.addEventListener('input', () => {
        const query = empresaNombreInput.value.trim();
        if (!query || query.length < 2) {
            clearSuggestions(empresaNombreSuggestions);
            setFeedback(feedback, '', '');
            return;
        }
        performSearch(query);
    });

    // Cerrar sugerencias al hacer click fuera (usa función compartida)
    setupClickOutsideListener(empresaNombreInput, empresaNombreSuggestions, () => {
        empresaNombreSuggestions.innerHTML = '';
    });

    console.log('[CompanySearch] Initialized');
}

