/**
 * Manager Logs Export Module
 * Maneja la lógica de checkboxes y botones de exportación
 *
 * Características:
 * - Checkboxes individuales y "Seleccionar Todo"
 * - Actualización dinámica de botones de exportar
 * - Soporte para dos tablas independientes (registros y rechazadas)
 * - Event delegation para elementos dinámicos
 */

/**
 * Actualiza estado del botón de exportar para tabla de registros
 * Se llama cada vez que cambia un checkbox
 */
export function actualizarBotonExportar() {
    const seleccionados = document.querySelectorAll('.select-row:checked').length;
    const btnExportar = document.getElementById('btnExportar');
    if (!btnExportar) return;

    if (seleccionados > 0) {
        btnExportar.innerHTML = `<i class="bi bi-file-earmark-excel"></i> Exportar (${seleccionados})`;
        btnExportar.disabled = false;
    } else {
        btnExportar.innerHTML = `<i class="bi bi-file-earmark-excel"></i> Exportar seleccionados`;
        btnExportar.disabled = true;
    }
}

/**
 * Actualiza estado del botón de exportar para tabla de rechazadas
 * Se llama cada vez que cambia un checkbox
 */
export function actualizarBotonExportarRechazadas() {
    const seleccionados = document.querySelectorAll('.select-row-rechazadas:checked').length;
    const btnExportar = document.getElementById('btnExportarRechazadas');
    if (!btnExportar) return;

    if (seleccionados > 0) {
        btnExportar.innerHTML = `<i class="bi bi-file-earmark-excel"></i> Exportar (${seleccionados})`;
        btnExportar.disabled = false;
    } else {
        btnExportar.innerHTML = `<i class="bi bi-file-earmark-excel"></i> Exportar seleccionados`;
        btnExportar.disabled = true;
    }
}

/**
 * Inicializa toda la lógica de exportación
 * Event delegation para checkboxes dinámicos
 */
export function initExportLogic() {
    // ===== TABLA DE REGISTROS =====
    // Listener para checkbox "Seleccionar Todo"
    document.addEventListener('change', function(e) {
        if (e.target.id === 'selectAll') {
            document.querySelectorAll('.select-row').forEach(cb => cb.checked = e.target.checked);
            actualizarBotonExportar();
        }
        // Listener para checkboxes individuales
        else if (e.target.classList.contains('select-row')) {
            actualizarBotonExportar();
            const selectAllCheckbox = document.getElementById('selectAll');
            if (!e.target.checked && selectAllCheckbox) {
                selectAllCheckbox.checked = false;
            }
        }

        // ===== TABLA DE RECHAZADAS =====
        // Listener para checkbox "Seleccionar Todo" (rechazadas)
        if (e.target.id === 'selectAllRechazadas') {
            document.querySelectorAll('.select-row-rechazadas').forEach(cb => cb.checked = e.target.checked);
            actualizarBotonExportarRechazadas();
        }
        // Listener para checkboxes individuales (rechazadas)
        else if (e.target.classList.contains('select-row-rechazadas')) {
            actualizarBotonExportarRechazadas();
            const selectAllCheckbox = document.getElementById('selectAllRechazadas');
            if (!e.target.checked && selectAllCheckbox) {
                selectAllCheckbox.checked = false;
            }
        }
    });

    console.log('[Export] Export logic initialized');
}
