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

    // 8. Exportar funciones a window (para onclick)
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
  document.getElementById('btnSendVacation').addEventListener('click', function () {
    sendLeaveRequest({
      leave_type: 'vacation',
      leave_reason: document.getElementById('vacationReason').value,
      start_date: document.getElementById('vacationStart').value,
      end_date: document.getElementById('vacationEnd').value,
      reason_note: document.getElementById('vacationNote').value,
    }, 'vacationMsg');
  });

  // Botón: Solicitar ausencia
  document.getElementById('btnSendAbsence').addEventListener('click', function () {
    const fileInput = document.getElementById('absenceAttachment');
    const formData = new FormData();

    formData.append('leave_type', 'absence');
    formData.append('leave_reason', document.getElementById('absenceReason').value);
    formData.append('start_date', document.getElementById('absenceStart').value);
    formData.append('end_date', document.getElementById('absenceEnd').value);
    formData.append('reason_note', document.getElementById('absenceNote').value);

    if (fileInput && fileInput.files[0]) {
      formData.append('attachment', fileInput.files[0]);
    }

    sendLeaveRequest(formData, 'absenceMsg', true); // true indica que es FormData
  });

  // Botón: Guardar cambios de edición de solicitud
  const saveEditBtn = document.getElementById('btnSaveEditLeave');
  if (saveEditBtn) {
    saveEditBtn.addEventListener('click', saveEditLeaveRequest);
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
