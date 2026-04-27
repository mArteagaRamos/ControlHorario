/**
 * Staff Filters Module
 * Maneja el filtrado client-side de la tabla de empleados
 */

import { toggleVisibility } from '../../utils/dom.js';

export function initializeFilters() {
    const inputBusqueda = document.getElementById('filtroBusqueda');
    const selectRol = document.getElementById('filtroRol');
    const selectEstado = document.getElementById('filtroEstado');
    const filas = document.querySelectorAll('.empleado-row');
    const noResultsJs = document.getElementById('no-results-js');

    if (!inputBusqueda || !selectRol || !selectEstado) return;

    const filtrarTabla = () => {
        const textoBuscado = inputBusqueda.value.toLowerCase().trim();
        const rolBuscado = selectRol.value;
        const estadoBuscado = selectEstado.value;
        let filasVisibles = 0;

        filas.forEach(fila => {
            const nombre = fila.querySelector('.nombre-empleado')?.textContent.toLowerCase() || '';
            const email = fila.querySelector('.email-empleado')?.textContent.toLowerCase() || '';
            const rol = fila.dataset.rol || '';
            const estado = fila.dataset.estado || '';

            const coincideTexto = nombre.includes(textoBuscado) || email.includes(textoBuscado);
            const coincideRol = rolBuscado === "" || rol === rolBuscado;
            const coincideEstado = estadoBuscado === "" || estado === estadoBuscado;

            if (coincideTexto && coincideRol && coincideEstado) {
                toggleVisibility(fila, true);
                filasVisibles++;
            } else {
                toggleVisibility(fila, false);
            }
        });

        if (noResultsJs) {
            toggleVisibility(noResultsJs, filasVisibles === 0 && filas.length > 0);
        }
    };

    inputBusqueda.addEventListener('input', filtrarTabla);
    selectRol.addEventListener('change', filtrarTabla);
    selectEstado.addEventListener('change', filtrarTabla);

    console.log('[Filters] Staff table filters initialized');
}

