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
  getLeaveData,
  getCurrentUserId,
} from './calendar-state.js';

import { loadResolvedRequests } from './calendar-resolved.js';

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

  export function submitAbsenceRequest() {
    const reason = document.getElementById('absenceReason').value;
    // Solo capturamos horas si el motivo es Cita Médica o Deber Inexcusable
    const isHourly = (reason === 'medical_appointment' || reason === 'legal_duty');

    const startTime = isHourly ? document.getElementById('absenceStartTime').value : null;
    const endTime = isHourly ? document.getElementById('absenceEndTime').value : null;

    const payload = {
      start_date: document.getElementById('absenceStart').value,
      end_date: document.getElementById('absenceEnd').value,
      leave_type: 'absence',
      leave_reason: reason,
      reason_note: document.getElementById('absenceNote').value,
      start_time: startTime,
      end_time: endTime,
    };

    if (!payload.start_date || !payload.end_date) {
      const msgEl = document.getElementById('absenceMsg');
      if (msgEl) {
        msgEl.className = 'mt-2 small text-danger';
        msgEl.textContent = 'Las fechas son obligatorias.';
      }
      return;
    }

    // Validar horas si es cita médica o deber público
    if (isHourly) {
      if (!startTime || !endTime) {
        const msgEl = document.getElementById('absenceMsg');
        if (msgEl) {
          msgEl.className = 'mt-2 small text-danger';
          msgEl.textContent = 'Las horas de inicio y fin son obligatorias para este tipo de ausencia.';
        }
        return;
      }
      if (endTime < startTime) {
        const msgEl = document.getElementById('absenceMsg');
        if (msgEl) {
          msgEl.className = 'mt-2 small text-danger';
          msgEl.textContent = 'La hora de fin no puede ser menor a la hora de inicio.';
        }
        return;
      }
    }

    sendLeaveRequest(payload, 'absenceMsg');
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
  const absenceEnd = document.getElementById('absenceEnd');
  if (absenceReason) {
    document.getElementById('absenceReason').value = absenceReason.options[0].value;
  }
  document.getElementById('absenceStart').value = '';
  document.getElementById('absenceEnd').value = '';
  document.getElementById('absenceNote').value = '';
  document.getElementById('absenceStartTime').value = '';
  document.getElementById('absenceEndTime').value = '';
  
  // Desbloquear y mostrar campo de fecha "Hasta"
  if (absenceEnd) {
    absenceEnd.disabled = false;
    absenceEnd.style.opacity = '1';
    absenceEnd.style.cursor = 'auto';
  }
  
  // Ocultar campos de hora
  const timeFields = document.getElementById('absenceTimeFields');
  if (timeFields) {
    timeFields.style.display = 'none';
  }
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

  console.log('Event clicked:', {
    id: event.id,
    title: event.title,
    status: props.status,
    is_owner: props.is_owner,
    leave_type: props.leave_type,
    start_time: props.start_time,
    end_time: props.end_time
  });

  document.getElementById('eventModalTitle').textContent = event.title;

  let bodyHTML =
    '<p class="mb-1"><strong>Estado:</strong> ' + (props.status || 'N/A') + '</p>' +
    '<p class="mb-1"><strong>Motivo:</strong> ' + (props.reason || 'No especificado') + '</p>' +
    '<p class="mb-0 text-muted small">' + event.startStr + ' – ' + (event.endStr || '') + '</p>';

  // Mostrar horas si existen
  if (props.start_time || props.end_time) {
    const startTime = props.start_time ? props.start_time.substring(0, 5) : 'N/A';
    const endTime = props.end_time ? props.end_time.substring(0, 5) : 'N/A';
    bodyHTML += `<p class="mb-1"><strong>Horario:</strong> ${startTime} - ${endTime}</p>`;
  }
  
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

  // Llenar el footer con el botón de edición si aplica
  const footerEl = document.getElementById('eventModalFooter');
  footerEl.innerHTML = '';

  console.log('Checking edit button conditions:', {
    status: props.status,
    is_pending: props.status === 'Pendiente' || props.status === 'pending',
    is_owner: props.is_owner
  });

  if ((props.status === 'Pendiente' || props.status === 'pending') && props.is_owner) {
    footerEl.innerHTML = `
      <button class="std-btn" onclick="editLeaveRequest('${event.id}')">
        <i class="bi bi-pencil"></i> Editar Solicitud
      </button>
    `;
  }

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
  const attachmentSection = document.getElementById('attachmentSection');
  const container = document.getElementById('attachStatus');
  const uploadZone = document.getElementById('uploadZone');
  const msg = document.getElementById('uploadMsg');

  msg.textContent = '';
  document.getElementById('fileInput').value = '';

  // Solo mostrar sección de justificantes para ausencias
  if (event.extendedProps.leave_type === 'absence') {
    attachmentSection.style.display = 'block';

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
  } else {
    // Ocultar sección para vacaciones
    attachmentSection.style.display = 'none';
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
 * @returns {Promise<void>}
 */
export async function uploadAttachment() {
  const leaveId = getCurrentLeaveId();
  const fileInput = document.getElementById('fileInput');
  const msgEl = document.getElementById('uploadMsg');

  if (!leaveId) {
    msgEl.className = 'mt-1 small text-danger';
    msgEl.textContent = 'Error: ID de solicitud no encontrado.';
    return;
  }

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
    const res = await fetch(`/leave/${cleanId}/upload/`, {
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

      setTimeout(() => location.reload(), 1000);
    } else {
      msgEl.className = 'mt-1 small text-danger';
      msgEl.textContent = data.message || 'Error en el servidor';
    }
  } catch (err) {
    msgEl.className = 'mt-1 small text-danger';
    msgEl.textContent = 'Error de conexión: ' + err.message;
    console.error('Upload attachment error:', err);
  }
}

// ════════════════════════════════════════════════════════════════════════════
// ✏️ Edición de Solicitudes de Ausencia
// ════════════════════════════════════════════════════════════════════════════

/**
 * Prepara y abre el modal de edición de solicitud
 * @param {string} leaveId - ID de la solicitud a editar
 * @param {Object} leaveData - Datos actuales de la solicitud
 * @returns {void}
 */
export function prepareEditLeaveModal(leaveId, leaveData) {
  const msgEl = document.getElementById('editLeaveMessage');
  msgEl.classList.add('d-none');
  msgEl.textContent = '';

  document.getElementById('editLeaveId').value = leaveId;
  document.getElementById('editStartDate').value = leaveData.start_date || '';
  document.getElementById('editEndDate').value = leaveData.end_date || '';
  document.getElementById('editLeaveReason').value = leaveData.leave_reason || '';
  document.getElementById('editReasonNote').value = leaveData.reason_note || '';
  
  // Llenar horas si existen
  if (leaveData.start_time) {
    document.getElementById('editStartTime').value = leaveData.start_time.substring(0, 5);
  } else {
    document.getElementById('editStartTime').value = '';
  }
  
  if (leaveData.end_time) {
    document.getElementById('editEndTime').value = leaveData.end_time.substring(0, 5);
  } else {
    document.getElementById('editEndTime').value = '';
  }

  // Copiar opciones de motivos del formulario de ausencia
  const absenceReasonSelect = document.getElementById('absenceReason');
  const editReasonSelect = document.getElementById('editLeaveReason');
  
  if (absenceReasonSelect && editReasonSelect) {
    // Limpiar opciones excepto la primera (placeholder)
    while (editReasonSelect.options.length > 1) {
      editReasonSelect.remove(1);
    }
    
    // Copiar opciones
    for (let i = 1; i < absenceReasonSelect.options.length; i++) {
      const option = document.createElement('option');
      option.value = absenceReasonSelect.options[i].value;
      option.textContent = absenceReasonSelect.options[i].textContent;
      editReasonSelect.appendChild(option);
    }
  }

  // Mostrar/ocultar campos de hora según el motivo
  const hourlyReasons = ['medical_appointment', 'legal_duty'];
  const timeFields = document.getElementById('editTimeFields');
  const editStartTime = document.getElementById('editStartTime');
  const editEndTime = document.getElementById('editEndTime');
  const editStartDate = document.getElementById('editStartDate');
  const editEndDate = document.getElementById('editEndDate');
  
  const updateTimeFieldsVisibility = () => {
    const reason = editReasonSelect.value;
    if (hourlyReasons.includes(reason)) {
      timeFields.style.display = 'block';
      editEndDate.disabled = true;
      editEndDate.style.opacity = '0.6';
      editEndDate.style.cursor = 'not-allowed';
      // Sincronizar fecha fin con fecha inicio
      if (editStartDate.value) {
        editEndDate.value = editStartDate.value;
      }
    } else {
      timeFields.style.display = 'none';
      editEndDate.disabled = false;
      editEndDate.style.opacity = '1';
      editEndDate.style.cursor = 'auto';
      // Limpiar campos de hora
      editStartTime.value = '';
      editEndTime.value = '';
      editEndTime.min = '';
    }
  };

  // Mostrar/ocultar inicialmente
  updateTimeFieldsVisibility();

  // Remover listeners anteriores (si existen)
  editReasonSelect.removeEventListener('change', editReasonSelect._updateTimeFieldsHandler);
  editStartDate.removeEventListener('change', editStartDate._syncDateHandler);
  editStartTime.removeEventListener('change', editStartTime._validateTimeHandler);

  // Guardar referencias a las funciones para poder removerlas después
  editReasonSelect._updateTimeFieldsHandler = updateTimeFieldsVisibility;
  editStartDate._syncDateHandler = function() {
    const reason = editReasonSelect.value;
    if (hourlyReasons.includes(reason) && this.value) {
      editEndDate.value = this.value;
    }
  };
  editStartTime._validateTimeHandler = function() {
    if (this.value && editEndTime) {
      editEndTime.min = this.value;
      if (editEndTime.value && editEndTime.value < this.value) {
        editEndTime.value = this.value;
      }
    }
  };

  // Agregar listeners
  editReasonSelect.addEventListener('change', editReasonSelect._updateTimeFieldsHandler);
  editStartDate.addEventListener('change', editStartDate._syncDateHandler);
  editStartTime.addEventListener('change', editStartTime._validateTimeHandler);

  // Establecer fecha mínima como hoy
  const today = new Date().toISOString().split('T')[0];
  document.getElementById('editStartDate').min = today;
  document.getElementById('editEndDate').min = today;

  new bootstrap.Modal(document.getElementById('editLeaveModal')).show();
}

/**
 * Guarda los cambios de la solicitud de edición
 * @returns {Promise<void>}
 */
export async function saveEditLeaveRequest() {
  const leaveId = document.getElementById('editLeaveId').value;
  const startDate = document.getElementById('editStartDate').value;
  const endDate = document.getElementById('editEndDate').value;
  const leaveReason = document.getElementById('editLeaveReason').value;
  const reasonNote = document.getElementById('editReasonNote').value;
  const startTime = document.getElementById('editStartTime').value || null;
  const endTime = document.getElementById('editEndTime').value || null;
  const msgEl = document.getElementById('editLeaveMessage');

  msgEl.classList.add('d-none');
  msgEl.textContent = '';

  // Validación frontal
  if (!leaveId) {
    msgEl.className = 'alert alert-danger d-block';
    msgEl.textContent = '⚠️ Error: ID de solicitud no encontrado.';
    return;
  }

  if (!startDate || !endDate) {
    msgEl.className = 'alert alert-danger d-block';
    msgEl.textContent = '⚠️ Las fechas son obligatorias.';
    return;
  }

  if (!leaveReason) {
    msgEl.className = 'alert alert-danger d-block';
    msgEl.textContent = '⚠️ El motivo es obligatorio.';
    return;
  }

  const today = new Date().toISOString().split('T')[0];
  if (startDate < today) {
    msgEl.className = 'alert alert-danger d-block';
    msgEl.textContent = '⚠️ No puedes solicitar días anteriores a hoy.';
    return;
  }

  if (endDate < startDate) {
    msgEl.className = 'alert alert-danger d-block';
    msgEl.textContent = '⚠️ La fecha fin no puede ser anterior a la fecha inicio.';
    return;
  }

  // Validar horas si es cita médica o deber público
  const hourlyReasons = ['medical_appointment', 'legal_duty'];
  if (hourlyReasons.includes(leaveReason)) {
    if (!startTime || !endTime) {
      msgEl.className = 'alert alert-danger d-block';
      msgEl.textContent = '⚠️ Las horas de inicio y fin son obligatorias para este tipo de ausencia.';
      return;
    }
    if (endTime < startTime) {
      msgEl.className = 'alert alert-danger d-block';
      msgEl.textContent = '⚠️ La hora de fin no puede ser menor a la hora de inicio.';
      return;
    }
  }

  // Deshabilitar botón mientras se procesa
  const btnSave = document.getElementById('btnSaveEditLeave');
  const btnSaveHTML = btnSave.innerHTML;
  btnSave.disabled = true;
  btnSave.innerHTML = '<i class="bi bi-hourglass-split"></i> Guardando…';

  try {
    const cleanId = leaveId.replace('leave-', '');
    const response = await fetch(`/leave/${cleanId}/edit/`, {
      method: 'POST',
      headers: {
        'X-CSRFToken': getCsrfToken(),
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        start_date: startDate,
        end_date: endDate,
        leave_reason: leaveReason,
        reason_note: reasonNote,
        start_time: startTime,
        end_time: endTime
      })
    });

    const data = await response.json();

    if (response.ok) {
      msgEl.className = 'alert alert-success d-block';
      msgEl.textContent = '✓ ' + (data.message || 'Solicitud actualizada correctamente.');

      // Cerrar modal después de 1 segundo
      setTimeout(() => {
        bootstrap.Modal.getInstance(document.getElementById('editLeaveModal')).hide();

        // Refrescar calendario
        const calendarObj = getCalendarObj();
        if (calendarObj) calendarObj.refetchEvents();

        // Refrescar tabla de solicitudes resueltas
        const userId = getCurrentUserId();
        loadResolvedRequests(userId);

        // Refrescar modal de evento
        setTimeout(() => {
          const eventModal = bootstrap.Modal.getOrCreateInstance(document.getElementById('eventModal'));
          if (eventModal._isShown) {
            eventModal.hide();
          }
        }, 300);
      }, 1000);
    } else {
      msgEl.className = 'alert alert-danger d-block';
      if (data.error) {
        msgEl.textContent = '✗ ' + data.error;
      } else if (data.conflicts) {
        msgEl.innerHTML = '✗ Solapamiento detectado:<br>' +
          data.conflicts.map(c => `${c.leave_type} (${c.start_date} - ${c.end_date})`).join('<br>');
      } else {
        msgEl.textContent = '✗ Error al actualizar la solicitud.';
      }
    }
  } catch (err) {
    msgEl.className = 'alert alert-danger d-block';
    msgEl.textContent = '✗ Error de conexión: ' + err.message;
    console.error('Save edit leave error:', err);
  } finally {
    btnSave.disabled = false;
    btnSave.innerHTML = btnSaveHTML;
  }
}

/**
 * Obtiene datos de la solicitud y abre el modal de edición
 * @param {string} leaveId - ID de la solicitud a editar
 * @returns {Promise<void>}
 */
export async function editLeaveRequest(leaveId) {
  try {
    // Cerrar modal de evento primero (si está abierto)
    const eventModal = document.getElementById('eventModal');
    if (eventModal) {
      const modalInstance = bootstrap.Modal.getInstance(eventModal);
      if (modalInstance) {
        modalInstance.hide();
      }
    }

    const cleanId = leaveId.replace('leave-', '');

    // 1. Intentar obtener datos del mapa primero
    let leaveData = getLeaveData(cleanId);

    // 2. Si no está en el mapa, intentar obtener del calendario
    if (!leaveData) {
      const calendarObj = getCalendarObj();
      if (calendarObj) {
        const event = calendarObj.getEventById(leaveId);
        if (event) {
          const props = event.extendedProps;
          const startDate = new Date(event.startStr);
          const endDate = new Date(event.endStr);
          endDate.setDate(endDate.getDate() - 1);

          leaveData = {
            start_date: startDate.toISOString().split('T')[0],
            end_date: endDate.toISOString().split('T')[0],
            leave_reason: props.leave_reason || '',
            reason_note: props.reason_note || ''
          };
        }
      }
    }

    // 3. Si aún no tenemos datos, mostrar error
    if (!leaveData) {
      console.error('No data found for leave:', cleanId);
      alert('Error: No se encontraron los datos de la solicitud');
      return;
    }

    prepareEditLeaveModal(cleanId, leaveData);
  } catch (err) {
    console.error('Edit leave request error:', err);
    alert('Error al abrir el formulario de edición');
  }
}

