/**
 * calendar-init.js
 * Inicializador principal del calendario híbrido
 *
 * Orquesta:
 * - Setup de inputs y filtros
 * - Inicialización de FullCalendar
 * - Carga inicial de datos
 * - Configuración de event listeners
 * - Exportación de funciones a window (para onclick)
 */

import {
  getTodayDate,
  getCalendarObj,
  setCalendarObj,
  getEventsUrl,
  getSelectedStatuses,
  getCurrentUserId,
  setCurrentUserId,
  setSelectedStatuses,
} from './calendar-state.js';

import {
  sendLeaveRequest,
  submitAbsenceRequest,
  showEventModal,
  prepareAttachmentSection,
  showUploadZone,
  uploadAttachment,
  prepareEditLeaveModal,
  saveEditLeaveRequest,
  editLeaveRequest,
} from './calendar-leaves.js';

import {
  loadPendingRequests,
  approveLeave,
  openRejectModal,
  openApproveVacationModal,
  submitReview,
} from './calendar-pending.js';

import {
  loadResolvedRequests,
  toggleResolved,
  toggleReviewNote,
} from './calendar-resolved.js';

// ════════════════════════════════════════════════════════════════════════════
// 🔥 PUNTO DE ENTRADA PRINCIPAL
// ════════════════════════════════════════════════════════════════════════════

/**
 * Inicializa todos los módulos del calendario
 * Llamada cuando el DOM está listo
 */
export async function initCalendar() {
  try {
    console.log('[CALENDAR] Inicializando calendario...');
    // 1. Configurar min dates de inputs
    setupMinDates();

    // 2. Configurar filtros de estado
    setupStatusFilters();

    // 3. Inicializar FullCalendar
    setupFullCalendar();

    // 4. Configurar selector de equipo
    setupTeamSelector();

    // 5. Cargar datos iniciales
    await setupInitialData();

    // 6. Configurar listeners de botones
    setupButtonListeners();

    // 7. Configurar listener de confirmación de rechazo
    setupRejectListener();

    // 7.5. Configurar listener de confirmación de aprobación de vacaciones
    setupApproveVacationListener();

    // 8. Configurar listener de cambio de razón de ausencia
    setupAbsenceReasonListener();

    // 9. Exportar funciones a window (para onclick)
    exportFunctionsToWindow();

  } catch (error) {
    console.error('[CALENDAR] Error during initialization:', error);
  }
}

// ════════════════════════════════════════════════════════════════════════════
// 📅 Setup de Inputs
// ════════════════════════════════════════════════════════════════════════════

/**
 * Configura las fechas mínimas para inputs de fecha
 * (no pueden seleccionar fechas pasadas)
 */
function setupMinDates() {
  const today = getTodayDate();

  document.getElementById('vacationStart').min = today;
  document.getElementById('vacationEnd').min = today;
  document.getElementById('absenceStart').min = today;
  document.getElementById('absenceEnd').min = today;
}

// ════════════════════════════════════════════════════════════════════════════
// 🎛️ Setup de Filtros de Estado
// ════════════════════════════════════════════════════════════════════════════

/**
 * Configura los checkboxes de filtrado de estado
 */
function setupStatusFilters() {
  document.querySelectorAll('[id^="filter"]').forEach(checkbox => {
    checkbox.addEventListener('change', function () {
      const selectedStatuses = [];
      if (document.getElementById('filterPending').checked) selectedStatuses.push('pending');
      if (document.getElementById('filterApproved').checked) selectedStatuses.push('approved');
      if (document.getElementById('filterRejected').checked) selectedStatuses.push('rejected');

      setSelectedStatuses(selectedStatuses);
      const calendarObj = getCalendarObj();
      if (calendarObj) calendarObj.refetchEvents();
    });
  });
}

// ════════════════════════════════════════════════════════════════════════════
// 📆 Setup de FullCalendar
// ════════════════════════════════════════════════════════════════════════════

/**
 * Inicializa la instancia de FullCalendar
 * Se mantiene en este módulo por su complejidad
 */
function setupFullCalendar() {
  const calEl = document.getElementById('calendar');
  if (!calEl) {
    throw new Error('No se encontró elemento #calendar en el DOM');
  }

  const calendarObj = new FullCalendar.Calendar(calEl, {
    locale: 'es',
    initialView: 'dayGridMonth',
    headerToolbar: { left: 'prev,next today', center: 'title', right: 'dayGridMonth,listWeek' },
    height: 'auto',
    firstDay: 1,
    locales: [{
      code: 'es',
      buttonText: {
        today: 'hoy',
        month: 'mes',
        list: 'lista'
      },
      allDayText: 'todo el día'
    }],
    events: function (info, successCb, failureCb) {
      const params = new URLSearchParams({
        start: info.startStr.slice(0, 10),
        end: info.endStr.slice(0, 10),
      });
      if (getCurrentUserId()) params.set('user_id', getCurrentUserId());
      const statuses = getSelectedStatuses();
      if (statuses && statuses.length > 0) {
        params.set('statuses', statuses.join(','));
      }
      const url = `${getEventsUrl()}?${params}`;
      fetch(url).then(r => r.json()).then(successCb).catch(failureCb);
    },
    eventClick: function (info) {
      showEventModal(info.event);
    }
  });

  calendarObj.render();
  setCalendarObj(calendarObj);
}

// ════════════════════════════════════════════════════════════════════════════
// 👥 Setup de Selector de Equipo
// ════════════════════════════════════════════════════════════════════════════

/**
 * Configura el selector de empleados (solo para managers)
 */
function setupTeamSelector() {
  const teamSelector = document.getElementById('teamSelector');
  if (teamSelector) {
    teamSelector.addEventListener('change', async function () {
      setCurrentUserId(this.value || null);
      const calendarObj = getCalendarObj();
      if (calendarObj) calendarObj.refetchEvents();
      await loadResolvedRequests(getCurrentUserId());
    });
  }
}

// ════════════════════════════════════════════════════════════════════════════
// 📦 Cargar Datos Iniciales
// ════════════════════════════════════════════════════════════════════════════

/**
 * Carga las solicitudes pendientes y resueltas inicialmente
 */
async function setupInitialData() {
  // Cargar solicitudes pendientes si es manager
  if (document.getElementById('pendingContainer')) {
    await loadPendingRequests();
  }

  // Cargar solicitudes resueltas para el usuario
  await loadResolvedRequests(null);
}

// ════════════════════════════════════════════════════════════════════════════
// 🔘 Setup de Listeners de Botones
// ════════════════════════════════════════════════════════════════════════════

/**
 * Configura los listeners de los botones de envío
 */
function setupButtonListeners() {
  // Botón: Solicitar vacaciones
  const btnVacation = document.getElementById('btnSendVacation');
  if (btnVacation) {
    btnVacation.addEventListener('click', function () {
      sendLeaveRequest({
        leave_type: 'vacation',
        leave_reason: document.getElementById('vacationReason').value,
        start_date: document.getElementById('vacationStart').value,
        end_date: document.getElementById('vacationEnd').value,
        reason_note: document.getElementById('vacationNote').value,
      }, 'vacationMsg');
    });
  }

  // Botón: Guardar cambios de edición de solicitud
  const saveEditBtn = document.getElementById('btnSaveEditLeave');
  if (saveEditBtn) {
    saveEditBtn.addEventListener('click', saveEditLeaveRequest);
  }
}

// ════════════════════════════════════════════════════════════════════════════
// 🔧 Setup de Listener para Razón de Ausencia
// ════════════════════════════════════════════════════════════════════════════

/**
 * Configura el listener de cambio de razón de ausencia
 * Muestra/oculta campos de hora y gestiona fecha única
 */
function setupAbsenceReasonListener() {
  const absenceReasonSelect = document.getElementById('absenceReason');
  const absenceStart = document.getElementById('absenceStart');
  const absenceEnd = document.getElementById('absenceEnd');
  const absenceStartTime = document.getElementById('absenceStartTime');
  const absenceEndTime = document.getElementById('absenceEndTime');
  const timeFields = document.getElementById('absenceTimeFields');
  const hourlyReasons = ['medical_appointment', 'legal_duty'];

  if (absenceReasonSelect) {
    absenceReasonSelect.addEventListener('change', function() {
      const isHourly = hourlyReasons.includes(this.value);
      
      if (isHourly) {
        // Mostrar campos de hora y bloquear fecha única
        timeFields.style.display = 'block';
        absenceEnd.disabled = true;
        absenceEnd.style.opacity = '0.6';
        absenceEnd.style.cursor = 'not-allowed';
        // Igualar fechas si la de inicio existe
        if (absenceStart.value) {
          absenceEnd.value = absenceStart.value;
        }
      } else {
        // Ocultar campos de hora y desbloquear fecha
        timeFields.style.display = 'none';
        absenceEnd.disabled = false;
        absenceEnd.style.opacity = '1';
        absenceEnd.style.cursor = 'auto';
        // Limpiar campos de hora
        absenceStartTime.value = '';
        absenceEndTime.value = '';
        absenceEndTime.min = '';
      }
    });

    // Listener para sincronizar fecha de fin cuando es cita médica/deber público
    if (absenceStart) {
      absenceStart.addEventListener('change', function() {
        const isHourly = hourlyReasons.includes(absenceReasonSelect.value);
        if (isHourly && this.value) {
          absenceEnd.value = this.value;
        }
      });
    }

    // Listener para validar que hora fin >= hora inicio
    if (absenceStartTime) {
      absenceStartTime.addEventListener('change', function() {
        if (this.value && absenceEndTime) {
          // Establecer el mínimo de hora fin igual a la hora inicio
          absenceEndTime.min = this.value;
          // Si la hora fin es menor que inicio, igualarla
          if (absenceEndTime.value && absenceEndTime.value < this.value) {
            absenceEndTime.value = this.value;
          }
        }
      });
    }
  }
}

// ════════════════════════════════════════════════════════════════════════════
// ❌ Setup de Listener de Rechazo
// ════════════════════════════════════════════════════════════════════════════

/**
 * Configura el listener del botón de confirmación de rechazo
 */
function setupRejectListener() {
  document.getElementById('btnConfirmReject').addEventListener('click', async function () {
    const note = document.getElementById('rejectNoteInput').value.trim() || null;
    bootstrap.Modal.getInstance(document.getElementById('rejectModal')).hide();
    // Usar _pendingRejectId desde window (se establece en openRejectModal)
    if (window._pendingRejectId) {
      await submitReview(window._pendingRejectId, 'reject', note);
    }
  });
}

/**
 * Configura el listener del botón de confirmación de aprobación de vacaciones
 */
function setupApproveVacationListener() {
  const btn = document.getElementById('btnConfirmApproveVacation');
  if (!btn) return;

  btn.addEventListener('click', async function () {
    const leaveId = this.dataset.leaveId;
    if (!leaveId) return;

    const multiplier = parseFloat(document.getElementById('vacApproveMultiplier').value);
    const note = document.getElementById('vacApproveNote').value.trim() || null;

    // Validar multiplicador
    if (isNaN(multiplier) || multiplier < 0.1 || multiplier > 2.0) {
      alert('El multiplicador debe estar entre 0.1 y 2.0');
      return;
    }

    // Cerrar modal y enviar revisión
    bootstrap.Modal.getInstance(document.getElementById('approveVacationModal')).hide();
    await submitReview(leaveId, 'approve', note, multiplier);
  });
}

// ════════════════════════════════════════════════════════════════════════════
// 🪟 Exportar Funciones a Window (para onclick handlers)
// ════════════════════════════════════════════════════════════════════════════

/**
 * Exporta todas las funciones usadas en onclick handlers
 * al objeto window para que sean accesibles desde HTML dinámico
 */
function exportFunctionsToWindow() {
  // Funciones de leave requests
  window.sendLeaveRequest = sendLeaveRequest;
  window.submitAbsenceRequest = submitAbsenceRequest;
  window.showEventModal = showEventModal;
  window.prepareAttachmentSection = prepareAttachmentSection;
  window.showUploadZone = showUploadZone;
  window.uploadAttachment = uploadAttachment;

  // Funciones de edición de solicitudes
  window.editLeaveRequest = editLeaveRequest;
  window.prepareEditLeaveModal = prepareEditLeaveModal;
  window.saveEditLeaveRequest = saveEditLeaveRequest;

  // Funciones de pending requests
  window.loadPendingRequests = loadPendingRequests;
  window.approveLeave = approveLeave;
  window.openRejectModal = openRejectModal;
  window.openApproveVacationModal = openApproveVacationModal;
  window.submitReview = submitReview;

  // Funciones de resolved requests
  window.loadResolvedRequests = loadResolvedRequests;
  window.toggleResolved = toggleResolved;
  window.toggleReviewNote = toggleReviewNote;
}

// ════════════════════════════════════════════════════════════════════════════
// Nota: La inicialización se llama desde el template cuando el DOM está listo
// Este listener se removió para evitar doble inicialización
// ════════════════════════════════════════════════════════════════════════════
