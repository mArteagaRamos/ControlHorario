/**
 * DOM Utilities
 * Funciones genéricas para manipulación del DOM
 *
 * FASE 2: Extraer helpers de DOM comunes
 */

/**
 * Muestra u oculta un elemento agregando/removiendo clase 'd-none'
 * @param {HTMLElement|string} element - Elemento o ID del elemento
 * @param {boolean} show - true para mostrar, false para ocultar
 * @example
 * toggleVisibility('myElement', true);  // muestra
 * toggleVisibility(document.getElementById('section'), false); // oculta
 */
export function toggleVisibility(element, show) {
    const el = typeof element === 'string' ? document.getElementById(element) : element;
    if (!el) return;

    if (show) {
        el.classList.remove('d-none');
    } else {
        el.classList.add('d-none');
    }
}

/**
 * Alias convenientes
 */
export function showElement(element) {
    toggleVisibility(element, true);
}

export function hideElement(element) {
    toggleVisibility(element, false);
}

/**
 * Marca/desmarca todos los checkboxes visibles (no ocultos)
 * Útil para filtros: solo selecciona filas que no estén ocultas
 *
 * @param {string} checkboxSelector - CSS selector para los checkboxes
 * @param {string} rowSelector - CSS selector para las filas (para detectar visibility)
 * @param {boolean} checked - true para marcar, false para desmarcar
 * @example
 * toggleAllVisibleCheckboxes('.select-row-empleados', 'tr', true);
 */
export function toggleAllVisibleCheckboxes(checkboxSelector, rowSelector, checked) {
    const checkboxes = document.querySelectorAll(checkboxSelector);

    checkboxes.forEach(checkbox => {
        const row = checkbox.closest(rowSelector);
        if (row) {
            const isVisible = !row.classList.contains('d-none');
            if (isVisible) {
                checkbox.checked = checked;
            }
        }
    });
}

/**
 * Cuenta los checkboxes marcados (opcionalmente solo visibles)
 * @param {string} checkboxSelector - CSS selector para los checkboxes
 * @param {boolean} onlyVisible - Si true, solo cuenta visibles
 * @returns {number} Cantidad de checkboxes marcados
 */
export function countCheckedCheckboxes(checkboxSelector, onlyVisible = false) {
    const checkboxes = document.querySelectorAll(`${checkboxSelector}:checked`);

    if (!onlyVisible) {
        return checkboxes.length;
    }

    return Array.from(checkboxes).filter(checkbox => {
        const row = checkbox.closest('tr');
        return row && !row.classList.contains('d-none');
    }).length;
}

/**
 * Actualiza el estado de un botón basado en cantidad de selecciones
 * Útil para botones de acciones en lotes (exportar, eliminar, etc.)
 *
 * @param {Object} options - Configuración
 * @param {HTMLElement|string} options.button - Elemento botón o su ID
 * @param {string} options.checkboxSelector - CSS selector para los checkboxes
 * @param {Object} options.activeState - Estado cuando hay selecciones
 * @param {string} options.activeState.text - Texto HTML activo (puede incluir {count})
 * @param {boolean} options.activeState.enabled - Debe estar habilitado (default: true)
 * @param {Object} options.inactiveState - Estado cuando NO hay selecciones
 * @param {string} options.inactiveState.text - Texto HTML inactivo
 * @param {boolean} options.inactiveState.enabled - Debe estar deshabilitado (default: false)
 * @param {boolean} options.countOnlyVisible - Solo contar checkboxes en filas visibles (default: false)
 * @returns {number} Cantidad de elementos seleccionados
 *
 * @example
 * // Caso simple: Exportar botón
 * updateButtonState({
 *   button: 'btnExportar',
 *   checkboxSelector: '.select-row-empleados',
 *   activeState: {
 *     text: '<i class="bi bi-file-excel"></i> Exportar ({count})',
 *     enabled: true
 *   },
 *   inactiveState: {
 *     text: '<i class="bi bi-file-excel"></i> Exportar seleccionados',
 *     enabled: false
 *   },
 *   countOnlyVisible: true
 * });
 */
export function updateButtonState(options) {
    const {
        button,
        checkboxSelector,
        activeState = {},
        inactiveState = {},
        countOnlyVisible = false
    } = options;

    // Obtener elemento del botón
    const btn = typeof button === 'string' ? document.getElementById(button) : button;
    if (!btn) return 0;

    // Contar selecciones
    const count = countCheckedCheckboxes(checkboxSelector, countOnlyVisible);

    // Defaults para estados
    const active = {
        text: activeState.text || 'Action ({count})',
        enabled: activeState.enabled !== false
    };

    const inactive = {
        text: inactiveState.text || 'Select items',
        enabled: inactiveState.enabled ?? false
    };

    // Aplicar estado
    if (count > 0) {
        // Estado activo
        btn.innerHTML = active.text.replace('{count}', count);
        btn.disabled = !active.enabled;
    } else {
        // Estado inactivo
        btn.innerHTML = inactive.text;
        btn.disabled = !inactive.enabled;
    }

    return count;
}
