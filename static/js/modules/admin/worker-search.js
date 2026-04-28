/**
 * Worker Search Module
 * Maneja la búsqueda de trabajadores por Email, DNI y autocomplete por nombre
 * REFACTORIZADO: Usa search-utils y ui-utils para reducir duplicación
 */

import { getAdminConfig } from '../../utils/config.js';
import { createDebouncedSearch, renderSuggestions, setupClickOutsideListener, clearSuggestions } from '../../utils/search-utils.js';
import { setFeedback, hideElement } from '../../utils/ui-utils.js';

// DOM References
let trabajadorEmailInput = null;
let trabajadorDniInput = null;
let trabajadorNombreInput = null;
let trabajadorNombreSuggestions = null;

/**
 * Inicializa las referencias del DOM
 */
function initializeDOMReferences() {
    trabajadorEmailInput = document.getElementById('trabajador-email-input');
    trabajadorDniInput = document.getElementById('trabajador-dni-input');
    trabajadorNombreInput = document.getElementById('trabajador-nombre-input');
    trabajadorNombreSuggestions = document.getElementById('trabajador-nombre-suggestions');
}

/**
 * Limpia los resultados
 */
export function clearResults() {
    hideElement(document.getElementById('section-resultados'));
}

/**
 * Busca trabajador por Email
 */
async function searchWorkerByEmail() {
    const email = trabajadorEmailInput.value.trim();
    const feedback = document.getElementById('trabajador-feedback');

    if (!email) {
        setFeedback(feedback, 'Introduce un email.', 'danger');
        return;
    }

    try {
        const LOOKUP_USER_URL = getAdminConfig('LOOKUP_USER_URL');
        const url = new URL(LOOKUP_USER_URL, window.location.origin);
        url.searchParams.set('email', email);
        url.searchParams.set('include_companies', 'true');

        const res = await fetch(url.toString());
        const data = await res.json();

        if (data.found) {
            const { displayWorkerResults } = await import('./result-display.js');
            displayWorkerResults([data]);
            setFeedback(feedback, 'Trabajador encontrado.', 'success');
        } else {
            clearResults();
            setFeedback(feedback, 'No existe ningún trabajador con ese email.', 'danger');
        }
    } catch (error) {
        console.error('Error searching worker by email:', error);
        setFeedback(feedback, 'Error al buscar el trabajador.', 'danger');
    }
}

/**
 * Busca trabajador por DNI
 */
async function searchWorkerByDni() {
    const dni = trabajadorDniInput.value.trim();
    const feedback = document.getElementById('trabajador-feedback');

    if (!dni) {
        setFeedback(feedback, 'Introduce un DNI.', 'danger');
        return;
    }

    try {
        const LOOKUP_USER_URL = getAdminConfig('LOOKUP_USER_URL');
        const url = new URL(LOOKUP_USER_URL, window.location.origin);
        url.searchParams.set('dni', dni);
        url.searchParams.set('include_companies', 'true');

        const res = await fetch(url.toString());
        const data = await res.json();

        if (data.found) {
            const { displayWorkerResults } = await import('./result-display.js');
            displayWorkerResults([data]);
            setFeedback(feedback, 'Trabajador encontrado.', 'success');
        } else {
            clearResults();
            setFeedback(feedback, 'No existe ningún trabajador con ese DNI.', 'danger');
        }
    } catch (error) {
        console.error('Error searching worker by DNI:', error);
        setFeedback(feedback, 'Error al buscar el trabajador.', 'danger');
    }
}

/**
 * Formatea item de trabajador para sugerencias
 */
function formatWorkerItem(user) {
    return `<strong>${user.username} ${user.surname}</strong>`;
}

/**
 * Inicializa los event listeners
 */
export function initializeWorkerSearch() {
    initializeDOMReferences();

    const LOOKUP_USER_URL = getAdminConfig('LOOKUP_USER_URL');
    const feedback = document.getElementById('trabajador-feedback');

    // Búsqueda por Email
    document.getElementById('btn-buscar-trabajador-email')?.addEventListener('click', searchWorkerByEmail);

    // Búsqueda por DNI
    document.getElementById('btn-buscar-trabajador-dni')?.addEventListener('click', searchWorkerByDni);

    // Búsqueda por nombre (autocomplete con debounce reutilizable)
    const performSearch = createDebouncedSearch(
        LOOKUP_USER_URL,
        async (data) => {
            const results = data.results || [];

            if (results.length === 0) {
                clearSuggestions(trabajadorNombreSuggestions);
                setFeedback(feedback, 'Sin resultados para esa búsqueda.', 'warning');
                return;
            }

            setFeedback(feedback, '', '');
            renderSuggestions(results, trabajadorNombreSuggestions, formatWorkerItem, async (user) => {
                const { displayWorkerResults } = await import('./result-display.js');
                displayWorkerResults([user]);
                trabajadorNombreInput.value = `${user.username} ${user.surname}`;
                setFeedback(feedback, 'Trabajador seleccionado.', 'success');
            });
        },
        (error) => {
            console.error('Error searching worker by name:', error);
            clearSuggestions(trabajadorNombreSuggestions);
            setFeedback(feedback, 'Error al buscar trabajadores.', 'danger');
        },
        300
    );

    trabajadorNombreInput?.addEventListener('input', () => {
        const query = trabajadorNombreInput.value.trim();
        if (!query || query.length < 2) {
            clearSuggestions(trabajadorNombreSuggestions);
            setFeedback(feedback, '', '');
            return;
        }
        performSearch(query);
    });

    // Cerrar sugerencias al hacer click fuera (usa función compartida)
    setupClickOutsideListener(trabajadorNombreInput, trabajadorNombreSuggestions, () => {
        trabajadorNombreSuggestions.innerHTML = '';
    });

    console.log('[WorkerSearch] Initialized');
}

