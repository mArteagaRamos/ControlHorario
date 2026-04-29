/**
 * Manager Logs Filters Module
 * Maneja el filtrado de datos y actualización de tabla
 *
 * Características:
 * - Fetch asincrónico de datos filtrados
 * - TomSelect para dropdown de empleados
 * - Listeners para filtros dinámicos (fecha, horas, incidencias)
 */

import { initializePaginationState, updatePaginationView, attachShowMoreListener, initPaginationRechazadas } from './manager-logs-pagination.js';
import { reattachModalListeners } from './manager-logs-modals.js';
import { actualizarBotonExportar, actualizarBotonExportarRechazadas } from './manager-logs-export.js';

/**
 * Función principal: Obtiene datos filtrados del servidor
 * Se llama cuando cambian los filtros
 */
export function fetchResultados(page = 1) {
    const filterForm = document.getElementById('filterForm');
    const contenedor = document.getElementById('resultados-actualizables');

    if (!filterForm || !contenedor) return;

    // Efecto visual de carga
    const tabla = contenedor.querySelector('.table-scroll-container');
    if(tabla) tabla.style.opacity = '0.4';
    contenedor.style.pointerEvents = 'none';

    // Recopilar datos del formulario de filtros
    const formData = new FormData(filterForm);
    const params = new URLSearchParams(formData);
    params.set('page', page);

    // Hacer fetch silencioso al servidor
    fetch(`${window.location.pathname}?${params.toString()}`, {
        headers: { 'X-Requested-With': 'XMLHttpRequest' }
    })
    .then(response => response.text())
    .then(html => {
        // Extraer solo la tabla y paginación del HTML devuelto
        const parser = new DOMParser();
        const doc = parser.parseFromString(html, 'text/html');
        const nuevoContenido = doc.getElementById('resultados-actualizables');

        if (nuevoContenido) {
            contenedor.innerHTML = nuevoContenido.innerHTML;

            // Reinicializar paginación después de actualizar contenido
            initializePaginationState();

            // Re-atar listeners de modals
            reattachModalListeners();

            // Re-atar listener del botón "Ver Más"
            attachShowMoreListener();
        }

        // Remover efecto visual de carga
        contenedor.style.pointerEvents = 'auto';
        if(tabla) tabla.style.opacity = '1';

        // Actualizar botones de exportar
        actualizarBotonExportar();
    })
    .catch(error => {
        console.error('[Filters] Error fetching results:', error);
        if(tabla) tabla.style.opacity = '1';
        contenedor.style.pointerEvents = 'auto';
    });
}

/**
 * Inicializa el selector de empleados con TomSelect
 */
function initTomSelect() {
    let tomSelectInit = false;

    if (typeof TomSelect !== 'undefined') {
        new TomSelect("#empleado-select", {
            placeholder: "Todos los empleados",
            allowEmptyOption: true,
            plugins: ['clear_button'],
            onChange: function() {
                if (tomSelectInit) fetchResultados(1);
            }
        });
        tomSelectInit = true;
        console.log('[Filters] TomSelect initialized');
    }
}

/**
 * Ata listeners para los campos de filtro dinámico
 * Se llama cuando cambia: fecha, hora_desde, hora_hasta, solo_incidencias
 */
function attachFilterListeners() {
    document.querySelectorAll('.js-filter').forEach(input => {
        input.addEventListener('change', () => fetchResultados(1));
    });
    console.log('[Filters] Filter listeners attached');
}

/**
 * Inicializa todo el módulo de filtros
 */
export function initFilters() {
    initTomSelect();
    attachFilterListeners();
    console.log('[Filters] Filters initialized');
}
