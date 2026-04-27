/**
 * Worker Search Module
 * Maneja la búsqueda de trabajadores por Email, DNI y autocomplete por nombre
 *
 * FASE 4: Extraer búsqueda de trabajadores
 */

import { getAdminConfig } from '../../utils/config.js';

// DOM References
let trabajadorEmailInput = null;
let trabajadorDniInput = null;
let trabajadorNombreInput = null;
let trabajadorNombreSuggestions = null;
let trabajadorNombreDebounceTimer = null;

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
    const sectionResultados = document.getElementById('section-resultados');
    if (sectionResultados) {
        sectionResultados.classList.add('d-none');
    }
}

/**
 * Busca trabajador por Email
 */
async function searchWorkerByEmail() {
    const email = trabajadorEmailInput.value.trim();
    const feedback = document.getElementById('trabajador-feedback');

    if (!email) {
        feedback.textContent = 'Introduce un email.';
        feedback.className = 'form-text text-danger';
        return;
    }

    try {
        const LOOKUP_USER_URL = getAdminConfig('LOOKUP_USER_URL');
        const res = await fetch(`${LOOKUP_USER_URL}?email=${encodeURIComponent(email)}&include_companies=true`);
        const data = await res.json();

        if (data.found) {
            // Importar dinámicamente para evitar dependencia circular
            const { displayWorkerResults } = await import('./result-display.js');
            displayWorkerResults([data]);
            feedback.textContent = 'Trabajador encontrado.';
            feedback.className = 'form-text text-success';
        } else {
            clearResults();
            feedback.textContent = 'No existe ningún trabajador con ese email.';
            feedback.className = 'form-text text-danger';
        }
    } catch (error) {
        console.error('Error searching worker by email:', error);
        feedback.textContent = 'Error al buscar el trabajador.';
        feedback.className = 'form-text text-danger';
    }
}

/**
 * Busca trabajador por DNI
 */
async function searchWorkerByDni() {
    const dni = trabajadorDniInput.value.trim();
    const feedback = document.getElementById('trabajador-feedback');

    if (!dni) {
        feedback.textContent = 'Introduce un DNI.';
        feedback.className = 'form-text text-danger';
        return;
    }

    try {
        const LOOKUP_USER_URL = getAdminConfig('LOOKUP_USER_URL');
        const res = await fetch(`${LOOKUP_USER_URL}?dni=${encodeURIComponent(dni)}&include_companies=true`);
        const data = await res.json();

        if (data.found) {
            const { displayWorkerResults } = await import('./result-display.js');
            displayWorkerResults([data]);
            feedback.textContent = 'Trabajador encontrado.';
            feedback.className = 'form-text text-success';
        } else {
            clearResults();
            feedback.textContent = 'No existe ningún trabajador con ese DNI.';
            feedback.className = 'form-text text-danger';
        }
    } catch (error) {
        console.error('Error searching worker by DNI:', error);
        feedback.textContent = 'Error al buscar el trabajador.';
        feedback.className = 'form-text text-danger';
    }
}

/**
 * Busca trabajadores por nombre (autocomplete)
 */
async function searchWorkerByName(query) {
    if (!query || query.length < 2) {
        trabajadorNombreSuggestions.classList.add('d-none');
        document.getElementById('trabajador-feedback').textContent = '';
        return;
    }

    try {
        const LOOKUP_USER_URL = getAdminConfig('LOOKUP_USER_URL');
        const res = await fetch(`${LOOKUP_USER_URL}?name=${encodeURIComponent(query)}&include_companies=true`);
        const data = await res.json();
        const results = data.results || [];

        trabajadorNombreSuggestions.innerHTML = '';

        if (results.length === 0) {
            trabajadorNombreSuggestions.classList.add('d-none');
            document.getElementById('trabajador-feedback').textContent = 'Sin resultados para esa búsqueda.';
            document.getElementById('trabajador-feedback').className = 'form-text text-warning';
            return;
        }

        document.getElementById('trabajador-feedback').textContent = '';
        results.forEach(user => {
            const li = document.createElement('li');
            li.className = 'list-group-item list-group-item-action d-flex justify-content-between align-items-center';
            li.style.cursor = 'pointer';
            li.innerHTML = `<strong>${user.username} ${user.surname}</strong>`;
            li.addEventListener('click', async () => {
                const { displayWorkerResults } = await import('./result-display.js');
                displayWorkerResults([user]);
                trabajadorNombreInput.value = `${user.username} ${user.surname}`;
                trabajadorNombreSuggestions.classList.add('d-none');
                document.getElementById('trabajador-feedback').textContent = 'Trabajador seleccionado.';
                document.getElementById('trabajador-feedback').className = 'form-text text-success';
            });
            trabajadorNombreSuggestions.appendChild(li);
        });

        trabajadorNombreSuggestions.classList.remove('d-none');
    } catch (error) {
        console.error('Error searching worker by name:', error);
        trabajadorNombreSuggestions.classList.add('d-none');
        document.getElementById('trabajador-feedback').textContent = 'Error al buscar trabajadores.';
        document.getElementById('trabajador-feedback').className = 'form-text text-danger';
    }
}

/**
 * Inicializa los event listeners
 */
export function initializeWorkerSearch() {
    initializeDOMReferences();

    // Búsqueda por Email
    document.getElementById('btn-buscar-trabajador-email')?.addEventListener('click', searchWorkerByEmail);

    // Búsqueda por DNI
    document.getElementById('btn-buscar-trabajador-dni')?.addEventListener('click', searchWorkerByDni);

    // Búsqueda por nombre (autocomplete con debounce)
    trabajadorNombreInput?.addEventListener('input', () => {
        clearTimeout(trabajadorNombreDebounceTimer);
        const query = trabajadorNombreInput.value.trim();
        trabajadorNombreDebounceTimer = setTimeout(() => {
            searchWorkerByName(query);
        }, 300);
    });

    // Cerrar sugerencias al hacer click fuera
    document.addEventListener('click', (e) => {
        if (!trabajadorNombreInput?.contains(e.target) && !trabajadorNombreSuggestions?.contains(e.target)) {
            trabajadorNombreSuggestions?.classList.add('d-none');
        }
    });

    console.log('[WorkerSearch] Initialized');
}
