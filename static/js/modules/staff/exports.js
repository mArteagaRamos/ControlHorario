/**
 * Staff Exports Module
 * Maneja la lógica de selección y exportación de empleados
 * Reutiliza helpers de dom.js para estado de botones
 */

import { toggleAllVisibleCheckboxes, updateButtonState } from '../../utils/dom.js';

export function initializeExports() {
    const tableBody = document.querySelector('tbody');
    const selectAllCheckbox = document.getElementById('selectAllEmpleados');
    const btnExportar = document.getElementById('btnExportarEmpleados');

    if (!tableBody || !selectAllCheckbox || !btnExportar) return;

    // Configuración del botón exportar
    const buttonConfig = {
        button: btnExportar,
        checkboxSelector: '.select-row-empleados',
        activeState: {
            text: '<i class="bi bi-file-earmark-excel"></i> Exportar ({count})',
            enabled: true
        },
        inactiveState: {
            text: '<i class="bi bi-file-earmark-excel"></i> Exportar seleccionados',
            enabled: false
        },
        countOnlyVisible: true
    };

    // Función para actualizar el botón
    const actualizarBotonExportar = () => {
        updateButtonState(buttonConfig);
    };

    // Delegación de eventos para el tbody
    tableBody.addEventListener('change', (e) => {
        if (e.target.classList.contains('select-row-empleados')) {
            actualizarBotonExportar();
            if (!e.target.checked) selectAllCheckbox.checked = false;
        }
    });

    // Evento para el checkbox "Seleccionar todos"
    selectAllCheckbox.addEventListener('change', (e) => {
        toggleAllVisibleCheckboxes('.select-row-empleados', 'tr', e.target.checked);
        actualizarBotonExportar();
    });

    console.log('[Exports] Staff exports initialized');
}


