/**
 * calendar-leaves.js
 * Gestión de solicitudes de vacaciones y ausencia
 *
 * Funciones para:
 * - Enviar solicitudes de vacaciones/ausencia
 * - Cargar y mostrar justificantes
 * - Subir adjuntos a las solicitudes
 */

import {
  getCalendarObj,
  getLeaveCreateUrl,
  getCsrfToken,
  getCurrentLeaveId,
  setCurrentLeaveId,
} from './calendar-state.js';

// ════════════════════════════════════════════════════════════════════════════
// 📤 Enviar Solicitud de Vacaciones/Ausencia
// ════════════════════════════════════════════════════════════════════════════

/**
 * Envía una solicitud de vacaciones o ausencia
 * @param {Object|FormData} payload - Datos de la solicitud
 * @param {string} msgElementId - ID del elemento para mostrar mensajes
 * @param {boolean} isFormData - Si payload es FormData (para adjuntos)
 * @returns {Promise<void>}
 */
export async function sendLeaveRequest(payload, msgElementId, isFormData = false) {
  const msgEl = document.getElementById(msgElementId);
  msgEl.textContent = '';

  const start_date = isFormData
    ? payload.get('start_date')
    : payload.start_date;
  const end_date = isFormData
    ? payload.get('end_date')
    : payload.end_date;

  // VALIDACION: Verificar solapamientos antes de enviar
  if (start_date && end_date) {
    try {
      const validationRes = await fetch('/api/leave/validate-overlap/', {
        method: 'POST',
        headers: {
          'X-CSRFToken': getCsrfToken(),
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ start_date, end_date })
      });
      const validationData = await validationRes.json();

      if (!validationRes.ok) {
        msgEl.className = 'mt-2 small text-danger';
        msgEl.innerHTML = '⚠️ ' + validationData.message;
        return;
      }

      if (validationData.conflicts && validationData.conflicts.length > 0) {
        msgEl.className = 'mt-2 small text-warning';
        msgEl.innerHTML = '⚠️ Conflicto detectado: ya tienes ' + validationData.conflicts[0].leave_type + ' en este periodo';
        return;
      }
    } catch (err) {
      console.error('Error validating:', err);
    }
  }

  const fetchOptions = {
    method: 'POST',
    headers: { 'X-CSRFToken': getCsrfToken() },
    body: isFormData ? payload : JSON.stringify(payload)
  };

  if (!isFormData) {
    fetchOptions.headers['Content-Type'] = 'application/json';
  }

  try {
    const response = await fetch(getLeaveCreateUrl(), fetchOptions);
    
    let data;
    try {
      data = await response.json();
    } catch (jsonErr) {
      // Si no es JSON válido, es un error del servidor
      console.error('Server error response (non-JSON):', response.status, response.statusText);
      msgEl.className = 'mt-2 small text-danger';
      msgEl.textContent = `Error del servidor (${response.status}). Contacta con soporte.`;
      return;
    }

    if (response.ok) {
      msgEl.className = 'mt-2 small text-success';
      msgEl.textContent = data.message || 'Solicitud enviada correctamente.';

      // Actualizar calendario
      const calendarObj = getCalendarObj();
      if (calendarObj) calendarObj.refetchEvents();

      // Actualizar solicitudes pendientes si existen
      if (document.getElementById('pendingContainer')) {
        const { loadPendingRequests } = await import('./calendar-pending.js');
        loadPendingRequests();
      }

      // Limpiar formularios
      clearLeaveFormInputs();
    } else {
      msgEl.className = 'mt-2 small text-danger';
      msgEl.textContent = data.error || 'Error al enviar la solicitud.';
    }
  } catch (err) {
    msgEl.className = 'mt-2 small text-danger';
    msgEl.textContent = 'Error de red. Inténtalo de nuevo.';
    console.error('Send leave request error:', err);
  }
}

/**
 * Limpia todos los inputs de formularios de solicitud
 * @returns {void}
 */
function clearLeaveFormInputs() {
  // Limpiar file input si existe
  const fileInput = document.getElementById('absenceAttachment');
  if (fileInput) fileInput.value = '';

  // Limpiar formularios de vacaciones
  const vacationReason = document.getElementById('vacationReason');
  if (vacationReason) {
    document.getElementById('vacationReason').value = vacationReason.options[0].value;
  }
  document.getElementById('vacationStart').value = '';
  document.getElementById('vacationEnd').value = '';
  document.getElementById('vacationNote').value = '';

  // Limpiar formularios de ausencia
  const absenceReason = document.getElementById('absenceReason');
  if (absenceReason) {
    document.getElementById('absenceReason').value = absenceReason.options[0].value;
  }
  document.getElementById('absenceStart').value = '';
  document.getElementById('absenceEnd').value = '';
  document.getElementById('absenceNote').value = '';
}

// ════════════════════════════════════════════════════════════════════════════
// 🎯 Modal de Evento
// ════════════════════════════════════════════════════════════════════════════

/**
 * Muestra el modal de detalle de un evento del calendario
 * @param {FullCalendar.Event} event - Evento del calendario
 * @returns {void}
 */
export function showEventModal(event) {
  const props = event.extendedProps;
  setCurrentLeaveId(event.id);

  document.getElementById('eventModalTitle').textContent = event.title;

  let bodyHTML =
    '<p class="mb-1"><strong>Estado:</strong> ' + (props.status || 'N/A') + '</p>' +
    '<p class="mb-1"><strong>Motivo:</strong> ' + (props.reason || 'No especificado') + '</p>' +
    '<p class="mb-0 text-muted small">' + event.startStr + ' – ' + (event.endStr || '') + '</p>';

  // Agregar indicador de conflicto
  if (props.has_conflict) {
    bodyHTML += `
      <div class="conflict-warning">
        <strong>Conflicto detectado</strong><br>
        Este período se solapa con otra solicitud.
      </div>
    `;
  }

  document.getElementById('eventModalBody').innerHTML = bodyHTML;

  prepareAttachmentSection(event);

  new bootstrap.Modal(document.getElementById('eventModal')).show();
}

// ════════════════════════════════════════════════════════════════════════════
// 📎 Gestión de Justificantes
// ════════════════════════════════════════════════════════════════════════════

/**
 * Prepara la sección de justificantes en el modal de evento
 * @param {FullCalendar.Event} event - Evento con datos de adjuntos
 * @returns {void}
 */
export function prepareAttachmentSection(event) {
  setCurrentLeaveId(event.id);
  const container = document.getElementById('attachStatus');
  const uploadZone = document.getElementById('uploadZone');
  const msg = document.getElementById('uploadMsg');

  msg.textContent = '';
  document.getElementById('fileInput').value = '';

  if (event.extendedProps.attachment_path) {
    uploadZone.classList.add('d-none');
    container.classList.remove('d-none');
    container.innerHTML = `
      <div class="d-flex align-items-center gap-2 mb-2" style="font-size:.82rem; background:#f0fdf4; border:1px solid #bbf7d0; border-radius:.45rem; padding:.45rem .7rem; color:#166534;">
        <i class="bi bi-check-circle-fill"></i> Justificante adjunto
        <a href="/media/${event.extendedProps.attachment_path}" target="_blank" class="ms-2 fw-bold">Ver archivo</a>
        <button onclick="showUploadZone()" class="ms-auto btn btn-link btn-sm p-0 text-muted" style="font-size:.7rem; text-decoration:none;">Reemplazar</button>
      </div>`;
  } else {
    uploadZone.classList.remove('d-none');
    container.classList.add('d-none');
  }
}

/**
 * Muestra la zona de upload de justificantes
 * @returns {void}
 */
export function showUploadZone() {
  document.getElementById('uploadZone').classList.remove('d-none');
  document.getElementById('attachStatus').classList.add('d-none');
}

/**
 * Sube un adjunto a una solicitud
 * @param {string} leaveId - ID de la solicitud (puede tener prefijo "leave-")
 * @returns {Promise<void>}
 */
export async function uploadAttachment(leaveId) {
  const fileInput = document.getElementById('fileInput');
  const msgEl = document.getElementById('uploadMsg');

  if (!fileInput.files[0]) {
    msgEl.className = 'mt-1 small text-danger';
    msgEl.textContent = 'Selecciona un archivo primero.';
    return;
  }

  // LIMPIEZA DEL ID: Esto quita "leave-" si existe
  const cleanId = leaveId.replace('leave-', '');

  const formData = new FormData();
  formData.append('attachment', fileInput.files[0]);

  msgEl.className = 'mt-1 small text-muted';
  msgEl.textContent = 'Subiendo…';

  try {
    // Usamos el cleanId aquí
    const res = await fetch(`/api/leave/${cleanId}/upload/`, {
      method: 'POST',
      headers: { 'X-CSRFToken': getCsrfToken() },
      body: formData,
    });

    const data = await res.json();

    if (res.ok) {
      msgEl.className = 'mt-1 small text-success';
      msgEl.textContent = '¡Subido con éxito!';

      // Refrescar calendario para ver cambios
      const calendarObj = getCalendarObj();
      if (calendarObj) calendarObj.refetchEvents();

      setTimeout(() => location.reload(), 1000); // Recarga para actualizar el modal
    } else {
      msgEl.className = 'mt-1 small text-danger';
      msgEl.textContent = data.message || 'Error en el servidor';
    }
  } catch (err) {
    msgEl.className = 'mt-1 small text-danger';
    msgEl.textContent = 'Error de conexión.';
    console.error('Upload attachment error:', err);
  }
}
