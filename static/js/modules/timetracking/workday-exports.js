/**
 * Workday Exports Module
 * Maneja la selección y exportación de entradas y solicitudes
 *
 * Reutiliza función factory de exports-helper.js para parametrizar selectores
 */

import { initializeExportModules } from '../../utils/exports-helper.js';

/**
 * Inicializa ambas exportaciones (entries y requests)
 */
export function initWorkdayExports() {
    initializeExportModules([
        {
            selectAllId: 'selectAllEntries',
            buttonId: 'btnExportarEntries',
            checkboxClass: 'select-row-entries',
            buttonText: '<i class="bi bi-file-earmark-excel"></i> Exportar ({count})',
            countOnlyVisible: false
        },
        {
            selectAllId: 'selectAllRequests',
            buttonId: 'btnExportarRequests',
            checkboxClass: 'select-row-requests',
            buttonText: '<i class="bi bi-file-earmark-excel"></i> Exportar ({count})',
            countOnlyVisible: false
        }
    ]);

    console.log('[Workday Exports] Initialized');
}
