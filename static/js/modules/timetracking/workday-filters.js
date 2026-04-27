/**
 * Workday Filters Module
 * Maneja el filtrado por rango de fechas
 *
 * Características:
 * - Filtra entries y requests por fecha
 * - Resetea paginación al filtrar
 * - Recalcula altura fija de tablas
 * - Actualiza visibilidad de botones "Ver Más"
 */

import { getPagination, calculateFixedHeight, updateTableView } from './workday-pagination.js';

/**
 * Aplica el filtro a un conjunto de filas
 */
function applyFilter(rows, fromDate, toDate) {
    rows.forEach(row => {
        const rowDate = row.getAttribute('data-entry-date');
        let shouldShow = true;

        if (fromDate && rowDate < fromDate) shouldShow = false;
        if (toDate && rowDate > toDate) shouldShow = false;

        if (shouldShow) {
            row.classList.remove('table-row-hidden');
        } else {
            row.classList.add('table-row-hidden');
        }
    });
}

/**
 * Refresh completo después del filtrado
 * Replicar la lógica exacta del original
 */
function refreshAfterFilter() {
    const pagination = getPagination();

    // Reset pagination
    pagination['#entryShowMore'].currentPage = 1;
    pagination['#requestShowMore'].currentPage = 1;
    pagination['#entryShowMore'].fixedHeight = null; // Recalcular altura
    pagination['#requestShowMore'].fixedHeight = null;

    // Trigger manual refresh
    ['#entryShowMore', '#requestShowMore'].forEach(key => {
        const state = pagination[key];
        if (!state) {
            return;
        }

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
                // Mostrar solo 5 filas temporalmente para calcular la altura
                let tempCount = 0;
                state.rows.forEach((row) => {
                    if (!row.classList.contains('table-row-hidden')) {
                        tempCount++;
                        row.style.display = tempCount <= state.ROWS_PER_PAGE ? '' : 'none';
                    }
                });
                state.fixedHeight = state.container.scrollHeight + 'px';

                // Restaurar display
                visibleCount = 0;
                state.rows.forEach((row) => {
                    if (!row.classList.contains('table-row-hidden')) {
                        visibleCount++;
                        row.style.display = visibleCount <= maxRows ? '' : 'none';
                    }
                });
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
    });
}

/**
 * Inicializa el módulo de filtros
 */
export function initWorkdayFilters() {
    const filterButton = document.getElementById('filterButton');
    const filterFromDate = document.getElementById('filterFromDate');
    const filterToDate = document.getElementById('filterToDate');

    if (!filterButton || !filterFromDate || !filterToDate) return;

    filterButton.addEventListener('click', function(e) {
        e.preventDefault();
        const fromDate = filterFromDate.value;
        const toDate = filterToDate.value;

        const entryRows = document.querySelectorAll('.entry-row');
        const requestRows = document.querySelectorAll('.request-row');

        applyFilter(entryRows, fromDate, toDate);
        applyFilter(requestRows, fromDate, toDate);

        // Refrescar paginación después del filtrado
        refreshAfterFilter();
    });
}
