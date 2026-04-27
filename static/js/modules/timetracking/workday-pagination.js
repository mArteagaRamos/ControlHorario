/**
 * Workday Pagination Module
 * Maneja la paginación de tablas con altura fija dinámica
 *
 * Características:
 * - Calcula altura basada en 5 filas visibles
 * - Aplica altura fija como variable CSS
 * - Usa clases CSS para mostrar/ocultar botón
 * - Respeta filas filtradas
 */

/**
 * Pagination state manager - almacena estado de paginación por tabla
 */
const pagination = {};

/**
 * Calcula la altura fija basada en 5 filas visibles
 */
function calculateFixedHeight(stateKey) {
    const state = pagination[stateKey];
    const visibleRows = state.rows.filter(r => !r.classList.contains('table-row-hidden'));

    if (visibleRows.length <= state.ROWS_PER_PAGE) {
        return null; // No se necesita altura fija
    }

    // Mostrar solo 5 filas temporalmente para calcular la altura
    let visibleCount = 0;
    state.rows.forEach((row) => {
        if (!row.classList.contains('table-row-hidden')) {
            visibleCount++;
            row.style.display = visibleCount <= state.ROWS_PER_PAGE ? '' : 'none';
        }
    });

    // Calcular la altura del contenedor con 5 filas
    const height = state.container.scrollHeight;
    return height + 'px';
}

/**
 * Renderiza la vista actual de la tabla
 */
function updateTableView(stateKey) {
    const state = pagination[stateKey];
    const visibleRows = state.rows.filter(r => !r.classList.contains('table-row-hidden'));
    const maxRows = state.ROWS_PER_PAGE * state.currentPage;

    let visibleCount = 0;
    state.rows.forEach((row) => {
        if (!row.classList.contains('table-row-hidden')) {
            visibleCount++;
            row.style.display = visibleCount <= maxRows ? '' : 'none';
        }
    });

    // Mostrar botón solo si hay más de 5 registros totales
    if (visibleRows.length > state.ROWS_PER_PAGE) {
        // Calcular y aplicar altura fija
        if (!state.fixedHeight) {
            state.fixedHeight = calculateFixedHeight(stateKey);
        }

        if (state.fixedHeight) {
            state.container.style.setProperty('--table-fixed-height', state.fixedHeight);
            state.container.classList.add('has-fixed-height');
        }

        // Si aún hay más registros por mostrar en esta página
        if (maxRows < visibleRows.length) {
            state.button.classList.add('visible');
        } else {
            state.button.classList.remove('visible');
        }
    } else {
        // Si hay 5 o menos registros, remover altura fija
        state.container.classList.remove('has-fixed-height');
        state.container.style.removeProperty('--table-fixed-height');
        state.button.classList.remove('visible');
    }
}

/**
 * Inicializa la paginación para una tabla
 */
function initTablePagination(tableSelector, rowSelector, buttonSelector, containerSelector) {
    const table = document.querySelector(tableSelector);
    if (!table) return;

    const tbody = table.querySelector('tbody');
    const rows = Array.from(tbody.querySelectorAll(rowSelector));
    const button = document.querySelector(buttonSelector);
    const container = document.querySelector(containerSelector);

    // Validación: si no encuentra el botón, salir
    if (!button) {
        console.warn(`[${buttonSelector}] Botón no encontrado en el DOM`);
        return;
    }

    const ROWS_PER_PAGE = 5;
    const stateKey = buttonSelector;

    pagination[stateKey] = {
        currentPage: 1,
        rows: rows,
        container: container,
        button: button,
        ROWS_PER_PAGE: ROWS_PER_PAGE,
        fixedHeight: null // Se calculará en la primera actualización
    };

    button.addEventListener('click', function(e) {
        e.preventDefault();
        pagination[stateKey].currentPage++;
        updateTableView(stateKey);
    });

    updateTableView(stateKey);
}

/**
 * Resetea la paginación de una tabla (útil cuando se filtran resultados)
 */
function resetPagination(buttonSelector) {
    const state = pagination[buttonSelector];
    if (!state) return;

    state.currentPage = 1;
    state.fixedHeight = null; // Recalcular altura
    updateTableView(buttonSelector);
}

/**
 * Obtiene el estado de paginación de una tabla
 */
function getPaginationState(buttonSelector) {
    return pagination[buttonSelector];
}

/**
 * Inicializa ambas tablas de workday
 */
export function initWorkdayPagination() {
    initTablePagination('#entryTable', '.entry-row', '#entryShowMore', '#entryTableContainer');
    initTablePagination('#requestTable', '.request-row', '#requestShowMore', '#requestTableContainer');
}

/**
 * Exporta funciones para uso desde otros módulos
 */
export function resetAllPagination() {
    resetPagination('#entryShowMore');
    resetPagination('#requestShowMore');
}

export function updateEntryPagination() {
    updateTableView('#entryShowMore');
}

export function updateRequestPagination() {
    updateTableView('#requestShowMore');
}

export function getPagination() {
    return pagination;
}

export { calculateFixedHeight, updateTableView };
