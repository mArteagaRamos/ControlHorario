/**
 * Search Tabs Module
 * Maneja el tab switching para búsqueda de empresas y trabajadores
 * REFACTORIZADO: Usa ui-utils para reducir duplicación
 */

import { toggleTabBlocks, setFeedback, hideElement } from '../../utils/ui-utils.js';

/**
 * Limpia resultados
 */
function clearResultsWrapper() {
    const sectionResultados = document.getElementById('section-resultados');
    hideElement(sectionResultados);
}

/**
 * Inicializa los tabs de búsqueda de empresas
 */
function initializeCompanySearchTabs() {
    const modeGroup = document.getElementById('empresa-search-mode-group');
    if (!modeGroup) return;

    modeGroup.querySelectorAll('[data-cmode]').forEach(btn => {
        btn.addEventListener('click', () => {
            const mode = btn.dataset.cmode;

            // Usar utilidad compartida para toggle de tabs
            toggleTabBlocks(modeGroup, 'data-cmode', mode, '.empresa-search-block');

            // Limpiar feedback y resultados
            const feedback = document.getElementById('empresa-feedback');
            setFeedback(feedback, '', '');
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
            const mode = btn.dataset.tmode;

            // Usar utilidad compartida para toggle de tabs
            toggleTabBlocks(modeGroup, 'data-tmode', mode, '.trabajador-search-block');

            // Limpiar feedback y resultados
            const feedback = document.getElementById('trabajador-feedback');
            setFeedback(feedback, '', '');
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

