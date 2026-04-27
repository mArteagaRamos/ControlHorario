/**
 * Staff Exports Module
 * Maneja la lógica de selección y exportación de empleados
 * Reutiliza función factory de exports-helper.js
 */

import { initializeExportConfig } from '../../utils/exports-helper.js';

export function initializeExports() {
    initializeExportConfig({
        selectAllId: 'selectAllEmpleados',
        buttonId: 'btnExportarEmpleados',
        checkboxClass: 'select-row-empleados',
        buttonText: '<i class="bi bi-file-earmark-excel"></i> Exportar ({count})',
        countOnlyVisible: true
    });

    console.log('[Exports] Staff exports initialized');
}


