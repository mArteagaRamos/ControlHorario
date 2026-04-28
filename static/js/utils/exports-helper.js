/**
 * Exports Helper Module
 * Función factory genérica para inicializar módulos de exportación
 * Parametriza selectores para reutilización entre módulos
 */

import { updateButtonState, toggleAllVisibleCheckboxes } from './dom.js';

/**
 * Inicializa la lógica de exportación para una tabla
 * @param {Object} config - Configuración de la tabla
 * @param {string} config.selectAllId - ID del checkbox "Seleccionar todos"
 * @param {string} config.buttonId - ID del botón exportar
 * @param {string} config.checkboxClass - Clase CSS de los checkboxes individuales
 * @param {string} config.buttonText - Texto del botón (puede incluir {count})
 * @param {boolean} config.countOnlyVisible - Contar solo checkboxes visibles (default: false)
 * @example
 * initializeExportConfig({
 *   selectAllId: 'selectAllEmpleados',
 *   buttonId: 'btnExportarEmpleados',
 *   checkboxClass: 'select-row-empleados',
 *   buttonText: '<i class="bi bi-file-earmark-excel"></i> Exportar ({count})',
 *   countOnlyVisible: true
 * });
 */
export function initializeExportConfig(config) {
    const {
        selectAllId,
        buttonId,
        checkboxClass,
        buttonText,
        countOnlyVisible = false
    } = config;

    const selectAllCheckbox = document.getElementById(selectAllId);
    const btnExportar = document.getElementById(buttonId);

    if (!selectAllCheckbox || !btnExportar) {
        console.warn(`[Exports] Missing elements for config:`, config);
        return;
    }

    // Configuración del botón exportar
    const buttonConfig = {
        button: btnExportar,
        checkboxSelector: `.${checkboxClass}`,
        activeState: {
            text: buttonText,
            enabled: true
        },
        inactiveState: {
            text: buttonText.replace('{count}', '0').replace(/\s*\d+\s*/, 'seleccionados'),
            enabled: false
        },
        countOnlyVisible: countOnlyVisible
    };

    // Actualizar botón
    const actualizarBoton = () => updateButtonState(buttonConfig);

    // Event listener para select all
    selectAllCheckbox.addEventListener('change', (e) => {
        toggleAllVisibleCheckboxes(`.${checkboxClass}`, 'tr', e.target.checked);
        actualizarBoton();
    });

    // Event listener para checkboxes individuales
    document.addEventListener('change', (e) => {
        if (e.target.classList.contains(checkboxClass)) {
            actualizarBoton();
            // Desmarcar "select all" si se deselecciona un checkbox
            if (!e.target.checked) {
                selectAllCheckbox.checked = false;
            }
        }
    });
}

/**
 * Inicializa múltiples tablas de exportación
 * @param {Array<Object>} configs - Array de configuraciones
 * @example
 * initializeExportModules([
 *   { selectAllId: 'selectAll1', buttonId: 'btn1', checkboxClass: 'check1', ... },
 *   { selectAllId: 'selectAll2', buttonId: 'btn2', checkboxClass: 'check2', ... }
 * ]);
 */
export function initializeExportModules(configs) {
    configs.forEach(config => initializeExportConfig(config));
}
