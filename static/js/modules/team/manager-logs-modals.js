/**
 * Manager Logs Modals Module
 * Maneja los event listeners de 5 modals diferentes
 *
 * Modals:
 * 1. modalResolver - Resolver incidencias
 * 2. modalEditar - Editar entrada de registros
 * 3. modalAnular - Anular entrada
 * 4. modalEditarRechazada - Editar incidencia rechazada
 * 5. modalEliminarRechazada - Eliminar incidencia rechazada
 */

/**
 * Inicializa todos los modals con sus listeners
 */
export function initModals() {
    attachReopenModalListeners();
    console.log('[Modals] All modals initialized');
}

/**
 * Configura los event listeners para todos los modals
 * Usa event delegation con 'show.bs.modal' de Bootstrap
 */
function attachReopenModalListeners() {
    // ===== MODAL 1: RESOLVER INCIDENCIA =====
    const resolverModal = document.getElementById('modalResolver');
    if (resolverModal) {
        resolverModal.addEventListener('show.bs.modal', function(event) {
            let button = event.relatedTarget;
            document.getElementById('incidenciaIdInput').value = button.getAttribute('data-id');
            document.getElementById('modalEmpleado').textContent = button.getAttribute('data-empleado');
            document.getElementById('modalMotivo').textContent = button.getAttribute('data-motivo') || "No se especificó un motivo.";
            document.getElementById('modalOldIn').textContent = button.getAttribute('data-old-in');
            document.getElementById('modalOldOut').textContent = button.getAttribute('data-old-out');
            document.getElementById('modalNewIn').textContent = button.getAttribute('data-new-in');
            document.getElementById('modalNewOut').textContent = button.getAttribute('data-new-out');
        });
    }

    // ===== MODAL 2: EDITAR ENTRADA =====
    const editarModal = document.getElementById('modalEditar');
    if (editarModal) {
        editarModal.addEventListener('show.bs.modal', function(event) {
            let button = event.relatedTarget.closest('button');
            document.getElementById('editRegistroId').value = button.getAttribute('data-entry-id');
            document.getElementById('editClockIn').value = button.getAttribute('data-in');
            document.getElementById('editClockOut').value = button.getAttribute('data-out') || '';
        });
    }

    // ===== MODAL 3: ANULAR ENTRADA =====
    const modalAnular = document.getElementById('modalAnular');
    if (modalAnular) {
        modalAnular.addEventListener('show.bs.modal', function(event) {
            const button = event.relatedTarget;
            const entryId = button.getAttribute('data-entry-id');
            const inputId = modalAnular.querySelector('#anularRegistroId');
            inputId.value = entryId;
        });
    }

    // ===== MODAL 4: EDITAR INCIDENCIA RECHAZADA =====
    const modalEditarRechazada = document.getElementById('modalEditarRechazada');
    if (modalEditarRechazada) {
        modalEditarRechazada.addEventListener('show.bs.modal', function(event) {
            const button = event.relatedTarget;
            document.getElementById('editarRechazadaId').value = button.getAttribute('data-incidencia-id');
            document.getElementById('editarRechazadaIn').value = button.getAttribute('data-new-in') || '';
            document.getElementById('editarRechazadaOut').value = button.getAttribute('data-new-out') || '';
            document.getElementById('editarRechazadaReason').value = button.getAttribute('data-reason') || '';
        });
    }

    // ===== MODAL 5: ELIMINAR INCIDENCIA RECHAZADA =====
    const modalEliminarRechazada = document.getElementById('modalEliminarRechazada');
    if (modalEliminarRechazada) {
        modalEliminarRechazada.addEventListener('show.bs.modal', function(event) {
            const button = event.relatedTarget;
            document.getElementById('eliminarRechazadaId').value = button.getAttribute('data-incidencia-id');
        });
    }

    console.log('[Modals] Modal listeners attached');
}

/**
 * Re-ata listeners de modals después de que el contenido se actualiza dinámicamente
 * Se llama después de fetchResultados() cuando la tabla cambia
 */
export function reattachModalListeners() {
    attachReopenModalListeners();
    console.log('[Modals] Modal listeners re-attached after content update');
}
