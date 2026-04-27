/**
 * Mode Toggle Module
 * Maneja el toggle entre modo empresa y modo trabajador
 *
 * FASE 5: Extraer UI (Toggles)
 */

/**
 * Estado global del modo actual
 */
let currentTipo = 'empresa';

/**
 * Obtiene referencias del DOM
 */
function getDOMReferences() {
    return {
        btnTipoEmpresa: document.getElementById('btn-tipo-empresa'),
        btnTipoTrabajador: document.getElementById('btn-tipo-trabajador'),
        sectionEmpresa: document.getElementById('section-empresa'),
        sectionTrabajador: document.getElementById('section-trabajador')
    };
}

/**
 * Limpia resultados (delegado a otro módulo)
 */
function clearResultsWrapper() {
    const sectionResultados = document.getElementById('section-resultados');
    if (sectionResultados) {
        sectionResultados.classList.add('d-none');
    }
}

/**
 * Cambia al modo empresa
 */
function switchToCompanyMode(refs) {
    currentTipo = 'empresa';
    refs.btnTipoEmpresa.classList.add('btn-primary');
    refs.btnTipoEmpresa.classList.remove('btn-outline-primary');
    refs.btnTipoTrabajador.classList.add('btn-outline-primary');
    refs.btnTipoTrabajador.classList.remove('btn-primary');

    refs.sectionEmpresa.classList.remove('d-none');
    refs.sectionTrabajador.classList.add('d-none');
    clearResultsWrapper();
}

/**
 * Cambia al modo trabajador
 */
function switchToWorkerMode(refs) {
    currentTipo = 'trabajador';
    refs.btnTipoTrabajador.classList.add('btn-primary');
    refs.btnTipoTrabajador.classList.remove('btn-outline-primary');
    refs.btnTipoEmpresa.classList.add('btn-outline-primary');
    refs.btnTipoEmpresa.classList.remove('btn-primary');

    refs.sectionEmpresa.classList.add('d-none');
    refs.sectionTrabajador.classList.remove('d-none');
    clearResultsWrapper();
}

/**
 * Inicializa el estado por defecto
 */
function initializeState(refs) {
    refs.btnTipoEmpresa.classList.add('btn-primary');
    refs.btnTipoEmpresa.classList.remove('btn-outline-primary');
    refs.btnTipoTrabajador.classList.add('btn-outline-primary');
    refs.btnTipoTrabajador.classList.remove('btn-primary');
}

/**
 * Inicializa los event listeners para el toggle
 */
export function initializeModeToggle() {
    const refs = getDOMReferences();

    if (!refs.btnTipoEmpresa || !refs.btnTipoTrabajador) {
        console.warn('[ModeToggle] Toggle buttons not found in DOM');
        return;
    }

    // Event listeners para los botones de toggle
    refs.btnTipoEmpresa.addEventListener('click', () => switchToCompanyMode(refs));
    refs.btnTipoTrabajador.addEventListener('click', () => switchToWorkerMode(refs));

    // Inicializar estado por defecto
    initializeState(refs);

    console.log('[ModeToggle] Initialized');
}

/**
 * Getter para el estado actual
 */
export function getCurrentMode() {
    return currentTipo;
}

/**
 * Setter para el estado (si es necesario desde otro módulo)
 */
export function setCurrentMode(mode) {
    if (mode === 'empresa' || mode === 'trabajador') {
        currentTipo = mode;
    }
}
