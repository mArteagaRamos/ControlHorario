/**
 * Manager Logs Init Module
 * Orquestador principal que inicializa todos los módulos
 *
 * Se ejecuta una sola vez al cargar la página
 */

import { initializePaginationState, attachShowMoreListener, initPaginationRechazadas } from './manager-logs-pagination.js';
import { initExportLogic } from './manager-logs-export.js';
import { initModals } from './manager-logs-modals.js';
import { initFilters } from './manager-logs-filters.js';

/**
 * Inicializa todos los módulos de manager logs
 * Se llama una sola vez desde el template
 */
export function initManagerLogs() {
    console.log('[ManagerLogs] Initializing all modules...');

    // 1. Paginación
    initializePaginationState();
    attachShowMoreListener();
    initPaginationRechazadas();

    // 2. Export logic (checkboxes)
    initExportLogic();

    // 3. Modals
    initModals();

    // 4. Filters (TomSelect, listeners)
    initFilters();

    console.log('[ManagerLogs] All modules initialized successfully ✓');
}
