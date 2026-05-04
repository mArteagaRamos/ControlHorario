/**
 * Mode Toggle Module
 * Maneja el toggle entre modo empresa y modo trabajador
 * REFACTORIZADO: Usa ui-utils para reducir duplicación
 */

import { toggleExclusiveButtons, hideElement, showElement } from '../../utils/ui-utils.js';

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
 * Limpia resultados
 */
function clearResultsWrapper() {
    hideElement(document.getElementById('section-resultados'));
}

/**
 * Cambia al modo empresa
 */
function switchToCompanyMode(refs) {
    currentTipo = 'empresa';

    // Usar utilidad compartida para toggle de botones
    toggleExclusiveButtons(refs.btnTipoEmpresa, refs.btnTipoTrabajador, true);

    showElement(refs.sectionEmpresa);
    hideElement(refs.sectionTrabajador);
    clearResultsWrapper();
}

/**
 * Cambia al modo trabajador
 */
function switchToWorkerMode(refs) {
    currentTipo = 'trabajador';

    // Usar utilidad compartida para toggle de botones
    toggleExclusiveButtons(refs.btnTipoEmpresa, refs.btnTipoTrabajador, false);

    hideElement(refs.sectionEmpresa);
    showElement(refs.sectionTrabajador);
    clearResultsWrapper();
}

/**
 * Inicializa el estado por defecto
 */
function initializeState(refs) {
    // Usar utilidad compartida para establecer estado inicial
    toggleExclusiveButtons(refs.btnTipoEmpresa, refs.btnTipoTrabajador, true);
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
