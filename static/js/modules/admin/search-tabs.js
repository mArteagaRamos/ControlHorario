/**
 * Search Tabs Module
 * Maneja el tab switching para búsqueda de empresas y trabajadores
 *
 * FASE 5: Extraer UI (Tabs)
 */

/**
 * Limpia resultados
 */
function clearResultsWrapper() {
    const sectionResultados = document.getElementById('section-resultados');
    if (sectionResultados) {
        sectionResultados.classList.add('d-none');
    }
}

/**
 * Inicializa los tabs de búsqueda de empresas
 */
function initializeCompanySearchTabs() {
    const modeGroup = document.getElementById('empresa-search-mode-group');
    if (!modeGroup) return;

    modeGroup.querySelectorAll('[data-cmode]').forEach(btn => {
        btn.addEventListener('click', () => {
            // Actualizar estado visual de los botones
            modeGroup.querySelectorAll('[data-cmode]').forEach(b => {
                b.classList.toggle('active', b === btn);
                b.classList.toggle('btn-secondary', b === btn);
                b.classList.toggle('btn-outline-secondary', b !== btn);
            });

            // Ocultar todos los bloques y mostrar el seleccionado
            document.querySelectorAll('.empresa-search-block').forEach(b => {
                b.classList.add('d-none');
            });
            document.getElementById(`empresa-search-block-${btn.dataset.cmode}`)?.classList.remove('d-none');

            // Limpiar feedback y resultados
            document.getElementById('empresa-feedback').textContent = '';
            clearResultsWrapper();
        });
    });

    console.log('[SearchTabs] Company search tabs initialized');
}

/**
 * Inicializa los tabs de búsqueda de trabajadores
 */
function initializeWorkerSearchTabs() {
    const modeGroup = document.getElementById('trabajador-search-mode-group');
    if (!modeGroup) return;

    modeGroup.querySelectorAll('[data-tmode]').forEach(btn => {
        btn.addEventListener('click', () => {
            // Actualizar estado visual de los botones
            modeGroup.querySelectorAll('[data-tmode]').forEach(b => {
                b.classList.toggle('active', b === btn);
                b.classList.toggle('btn-secondary', b === btn);
                b.classList.toggle('btn-outline-secondary', b !== btn);
            });

            // Ocultar todos los bloques y mostrar el seleccionado
            document.querySelectorAll('.trabajador-search-block').forEach(b => {
                b.classList.add('d-none');
            });
            document.getElementById(`trabajador-search-block-${btn.dataset.tmode}`)?.classList.remove('d-none');

            // Limpiar feedback y resultados
            document.getElementById('trabajador-feedback').textContent = '';
            clearResultsWrapper();
        });
    });

    console.log('[SearchTabs] Worker search tabs initialized');
}

/**
 * Inicializa todos los tabs de búsqueda
 */
export function initializeSearchTabs() {
    initializeCompanySearchTabs();
    initializeWorkerSearchTabs();
    console.log('[SearchTabs] All search tabs initialized');
}
