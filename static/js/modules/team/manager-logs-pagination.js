/**
 * Manager Logs Pagination Module
 * Maneja la paginación de dos tablas independientes: "registros" y "rechazadas"
 *
 * Características:
 * - Estado de paginación para cada tabla
 * - Botones "Ver Más" independientes
 * - Actualización de vista sin recargar página
 */

// Estado para tabla de "registros" (historial general)
let paginationState = {
    currentPage: 1,
    ROWS_PER_PAGE: 5,
    allRows: []
};

// Estado para tabla de "rechazadas"
let rechazadasPaginationState = {
    currentPage: 1,
    ROWS_PER_PAGE: 5,
    allRows: []
};

/**
 * Inicializa estado de paginación para tabla de registros
 * Se llama después de cada filtrado/fetch
 */
export function initializePaginationState() {
    paginationState.allRows = Array.from(document.querySelectorAll('.registro-row'));
    paginationState.currentPage = 1;
    updatePaginationView();
}

/**
 * Actualiza la vista de la tabla de registros basado en página actual
 */
export function updatePaginationView() {
    const maxRows = paginationState.ROWS_PER_PAGE * paginationState.currentPage;
    paginationState.allRows.forEach((row, index) => {
        row.style.display = (index < maxRows) ? '' : 'none';
    });

    // Mostrar/ocultar botón "Ver Más"
    const button = document.getElementById('registrosShowMore');
    if (button) {
        if (maxRows >= paginationState.allRows.length) {
            button.style.display = 'none';
        } else {
            button.style.display = 'block';
        }
    }
}

/**
 * Inicializa el botón "Ver Más" para tabla de registros
 */
export function attachShowMoreListener() {
    const showMoreBtn = document.getElementById('registrosShowMore');
    if (showMoreBtn) {
        showMoreBtn.addEventListener('click', function(e) {
            e.preventDefault();
            paginationState.currentPage++;
            updatePaginationView();
        });
    }
}

/**
 * Inicializa paginación para tabla de "rechazadas"
 */
export function initPaginationRechazadas() {
    const rechazadasRows = Array.from(document.querySelectorAll('.rechazada-row'));
    const rechazadasShowMoreBtn = document.getElementById('rechazadasShowMore');

    if (!rechazadasShowMoreBtn || rechazadasRows.length === 0) return;

    // Almacenar estado en el mismo objeto para consistencia
    rechazadasPaginationState.allRows = rechazadasRows;
    rechazadasPaginationState.currentPage = 1;

    // Event listener para botón "Ver Más" de rechazadas
    rechazadasShowMoreBtn.addEventListener('click', function(e) {
        e.preventDefault();
        rechazadasPaginationState.currentPage++;
        updatePaginationViewRechazadas();
    });
}

/**
 * Actualiza la vista de la tabla de rechazadas basado en página actual
 */
function updatePaginationViewRechazadas() {
    const maxRows = rechazadasPaginationState.ROWS_PER_PAGE * rechazadasPaginationState.currentPage;

    let visibleCount = 0;
    rechazadasPaginationState.allRows.forEach((row) => {
        visibleCount++;
        row.style.display = (visibleCount <= maxRows) ? '' : 'none';
    });

    const button = document.getElementById('rechazadasShowMore');
    if (button) {
        if (maxRows >= rechazadasPaginationState.allRows.length) {
            button.style.display = 'none';
        }
    }
}
