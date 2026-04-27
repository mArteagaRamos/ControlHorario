/**
 * Workday Modal Module
 * Maneja el modal de solicitud/edición de correcciones
 *
 * Características:
 * - Preparación del modal según acción (crear vs editar)
 * - Llenado de campos según datos del button
 * - Limpieza de feedback anterior
 * - Manejo de respuestas HTMX
 */

/**
 * Inicializa el evento del modal
 */
function initModalListener() {
    const modal = document.getElementById('modalCorreccion');
    if (!modal) return;

    modal.addEventListener('show.bs.modal', function (event) {
        const button = event.relatedTarget;
        const action = button.getAttribute('data-action') || 'request_correction';

        document.getElementById('form_action').value = action;

        // Limpiar feedback anterior al abrir el modal
        const feedback = document.getElementById('correctionFeedback');
        feedback.textContent = '';
        feedback.classList.add('d-none');

        if (action === 'edit_correction') {
            // MODO EDICIÓN
            document.getElementById('request_id').value = button.getAttribute('data-request-id') || '';
            document.getElementById('entry_id').value = ''; // Limpiamos por si acaso
            document.querySelector('input[name="new_clock_in"]').value = button.getAttribute('data-in') || '';
            document.querySelector('input[name="new_clock_out"]').value = button.getAttribute('data-out') || '';
            document.querySelector('textarea[name="reason"]').value = button.getAttribute('data-reason') || '';
            document.querySelector('.modal-title').textContent = 'Editar Solicitud de Corrección';
        } else {
            // MODO CREACIÓN NUEVA
            document.getElementById('entry_id').value = button.getAttribute('data-entry-id') || '';
            document.getElementById('request_id').value = ''; // Limpiamos por si acaso
            document.querySelector('input[name="new_clock_in"]').value = '';
            document.querySelector('input[name="new_clock_out"]').value = '';
            document.querySelector('textarea[name="reason"]').value = '';
            document.querySelector('.modal-title').textContent = 'Nueva Solicitud de Corrección';
        }
    });
}

/**
 * Inicializa el handler HTMX
 */
function initHTMXHandler() {
    const form = document.getElementById('correctionForm');
    if (!form) return;

    form.addEventListener('htmx:afterRequest', function (evt) {
        const status   = evt.detail.xhr.status;
        const feedback = document.getElementById('correctionFeedback');

        // Asumimos que la vista de Django devuelve un código 204 (No Content) o 200 en caso de éxito
        if (status === 204 || status === 200) {
            const modal = bootstrap.Modal.getInstance(document.getElementById('modalCorreccion'));
            modal.hide();
            window.location.reload();
        } else {
            // Si hay un error (ej. 400), mostramos el mensaje del servidor
            feedback.textContent = evt.detail.xhr.responseText || 'Error al enviar la solicitud.';
            feedback.classList.remove('d-none');
        }
    });
}

/**
 * Inicializa todo el módulo del modal
 */
export function initWorkdayModal() {
    initModalListener();
    initHTMXHandler();
}
