/**
 * Pagination Height Calculator Module
 * Calcula la altura fija basada en 5 filas visibles para todas las tablas
 *
 * Uso:
 * initPaginationHeights({
 *   'tableId': {
 *     rowSelector: '.row-class',
 *     containerSelector: '#containerId',
 *     fixedHeight: '280px' (opcional - si no se proporciona, se calcula automáticamente)
 *   }
 * })
 */

/**
 * Calcula la altura fija para mostrar 5 filas
 * @param {HTMLElement} container - El contenedor de la tabla
 * @param {NodeList} rows - Las filas de la tabla
 * @returns {string} Altura en píxeles (ej: "250px")
 */
function calculateTableHeight(container, rows) {
    if (!container || !rows || rows.length === 0) {
        return null;
    }

    // Guardar el estado actual de display
    const originalDisplays = Array.from(rows).map(row => row.style.display);

    // Mostrar todas las filas temporalmente para calcular
    rows.forEach(row => row.style.display = '');

    // Calcular la altura basada en 5 filas visibles
    const firstFiveRows = Array.from(rows).slice(0, 5);
    let totalHeight = 0;

    firstFiveRows.forEach(row => {
        totalHeight += row.offsetHeight;
    });

    // Restaurar el estado de display
    rows.forEach((row, index) => {
        row.style.display = originalDisplays[index];
    });

    return totalHeight > 0 ? totalHeight + 'px' : null;
}

/**
 * Aplica la altura fija a un contenedor
 * @param {string} containerSelector - Selector del contenedor
 * @param {string} height - Altura a aplicar
 */
function applyFixedHeight(containerSelector, height) {
    const container = document.querySelector(containerSelector);
    if (!container) {
        console.warn(`[Pagination] Contenedor no encontrado: ${containerSelector}`);
        return;
    }

    if (height) {
        container.style.setProperty('--table-fixed-height', height);
        container.classList.add('has-fixed-height');
    } else {
        container.classList.remove('has-fixed-height');
        container.style.removeProperty('--table-fixed-height');
    }
}

/**
 * Inicializa la altura fija para múltiples tablas
 * @param {Object} tablesConfig - Objeto con configuración de tablas
 * Ejemplo:
 * {
 *   '#tablaEmpresas': {
 *     rowSelector: 'tbody tr.empresa-row',
 *     containerSelector: '#tablaEmpresasContainer',
 *     fixedHeight: '280px' (opcional)
 *   }
 * }
 */
function initPaginationHeights(tablesConfig) {
    Object.entries(tablesConfig).forEach(([tableSelector, config]) => {
        const table = document.querySelector(tableSelector);
        if (!table) {
            console.warn(`[Pagination] Tabla no encontrada: ${tableSelector}`);
            return;
        }

        const rows = table.querySelectorAll(config.rowSelector);
        if (!rows || rows.length === 0) {
            console.warn(`[Pagination] No se encontraron filas en: ${tableSelector}`);
            return;
        }

        // Calcular altura fija
        const container = document.querySelector(config.containerSelector);
        if (!container) {
            console.warn(`[Pagination] Contenedor no encontrado: ${config.containerSelector}`);
            return;
        }

        const fixedHeight = config.fixedHeight || calculateTableHeight(container, rows);

        if (fixedHeight) {
            applyFixedHeight(config.containerSelector, fixedHeight);
        }
    });
}

/**
 * Recalcula la altura fija (útil cuando cambia el contenido dinámicamente)
 * @param {string} tableSelector - Selector de la tabla
 * @param {string} rowSelector - Selector de las filas
 * @param {string} containerSelector - Selector del contenedor
 */
function recalculatePaginationHeight(tableSelector, rowSelector, containerSelector) {
    const table = document.querySelector(tableSelector);
    if (!table) return;

    const rows = table.querySelectorAll(rowSelector);
    const container = document.querySelector(containerSelector);

    if (!container || !rows.length) return;

    const fixedHeight = calculateTableHeight(container, rows);
    applyFixedHeight(containerSelector, fixedHeight);
}

// Exportar para uso como módulo
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        initPaginationHeights,
        recalculatePaginationHeight,
        calculateTableHeight,
        applyFixedHeight
    };
}
