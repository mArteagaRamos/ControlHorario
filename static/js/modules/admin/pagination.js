/**
 * Pagination Module
 * Maneja la paginación de tablas en el panel de administración
 *
 * FASE 6: Extraer paginación
 */

/**
 * Configuración de paginación
 */
const ROWS_PER_PAGE = 5;

/**
 * Clase para manejar paginación de una tabla
 */
class TablePaginator {
    constructor(rowSelector, showMoreButtonId) {
        this.rows = Array.from(document.querySelectorAll(rowSelector));
        this.showMoreBtn = document.getElementById(showMoreButtonId);
        this.currentPage = 1;
        this.rowsPerPage = ROWS_PER_PAGE;

        if (this.showMoreBtn && this.rows.length > 0) {
            this.initialize();
        }
    }

    /**
     * Inicializa los event listeners
     */
    initialize() {
        this.showMoreBtn.addEventListener('click', (e) => {
            e.preventDefault();
            this.loadNextPage();
        });

        // Mostrar las primeras filas
        this.renderCurrentPage();
    }

    /**
     * Carga la siguiente página
     */
    loadNextPage() {
        this.currentPage++;
        this.renderCurrentPage();
    }

    /**
     * Renderiza la página actual
     */
    renderCurrentPage() {
        const maxRows = this.rowsPerPage * this.currentPage;
        let visibleCount = 0;

        this.rows.forEach((row) => {
            visibleCount++;
            row.style.display = (visibleCount <= maxRows) ? '' : 'none';
        });

        // Ocultar botón si ya se muestran todas las filas
        if (maxRows >= this.rows.length) {
            this.showMoreBtn.style.display = 'none';
        }
    }

    /**
     * Reset de paginación (útil cuando se filtran resultados)
     */
    reset() {
        this.currentPage = 1;
        if (this.showMoreBtn) {
            this.showMoreBtn.style.display = '';
        }
        this.renderCurrentPage();
    }

    /**
     * Obtiene el número total de filas
     */
    getTotalRows() {
        return this.rows.length;
    }

    /**
     * Obtiene el número de página actual
     */
    getCurrentPage() {
        return this.currentPage;
    }
}

// Instancias globales de paginadores
let empresasPaginator = null;
let trabajadoresPaginator = null;

/**
 * Inicializa la paginación para ambas tablas
 */
export function initializePagination() {
    // Inicializar paginador de empresas
    empresasPaginator = new TablePaginator('.empresa-row', 'empresasShowMore');

    // Inicializar paginador de trabajadores
    trabajadoresPaginator = new TablePaginator('.worker-row', 'trabajadoresShowMore');

    console.log('[Pagination] Initialized');
}

/**
 * Reset de paginación (para cuando se filtran resultados)
 */
export function resetPagination() {
    if (empresasPaginator) {
        empresasPaginator.reset();
    }
    if (trabajadoresPaginator) {
        trabajadoresPaginator.reset();
    }
}

/**
 * Getter para el paginador de empresas (si se necesita acceso desde otro módulo)
 */
export function getEmpresasPaginator() {
    return empresasPaginator;
}

/**
 * Getter para el paginador de trabajadores
 */
export function getTrabajadoresPaginator() {
    return trabajadoresPaginator;
}
