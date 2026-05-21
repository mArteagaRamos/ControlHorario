/**
 * calendar-pending.js
 * Gestión de solicitudes pendientes de revisión
 *
 * Funciones para:
 * - Cargar solicitudes pendientes
 * - Aprobar/rechazar solicitudes
 * - Mostrar modal de rechazo con nota
 */

import {
  getCalendarObj,
  getLeavePendingUrl,
  getLeaveBaseUrl,
  getCsrfToken,
  getPendingRejectId,
  setPendingRejectId,
  getLeaveData,
  setLeaveData,
  initLeaveDataMap,
  getAllLeaveData,
} from './calendar-state.js';

import { loadVacationStatus } from './calendar-init.js';

// ════════════════════════════════════════════════════════════════════════════
// 📋 Cargar Solicitudes Pendientes
// ════════════════════════════════════════════════════════════════════════════

/**
 * Carga todas las solicitudes pendientes de revisión
 * Solo accesible para managers
 * @returns {Promise<void>}
 */
export async function loadPendingRequests() {
  const container = document.getElementById('pendingContainer');
  if (!container) return; // No es un manager, skip

  const badge = document.getElementById('pendingBadge');

  try {
    const res = await fetch(getLeavePendingUrl());
    const data = await res.json();
    const list = data.requests;
    console.log('[PENDING] Loaded requests:', list.length, list);
    badge.textContent = list.length;

    if (list.length === 0) {
      container.innerHTML = '<small class="text-muted ps-3 py-2">Sin solicitudes pendientes.</small>';
      return;
    }

    // Guardamos los datos en un mapa para acceder desde el modal sin tocar el DOM
    initLeaveDataMap();
    list.forEach(l => {
      console.log('[PENDING] Storing leave data:', l.id, l);
      setLeaveData(l.id, l);
    });
    console.log('[PENDING] Stored data map:', window._leaveDataMap);

    container.innerHTML = list.map(l => `
      <div class="pending-item" id="pending-${l.id}">
        <div class="pending-item__header">
          <div class="pending-item__header-left">
            <div class="pending-item__name">${l.user}</div>
            <div class="pending-item__badge-group">
              <span class="pending-badge badge-${l.leave_type_raw === 'vacation' ? 'vacation' : 'absence'}">${l.leave_type}</span>
              <span class="pending-badge" style="background:#ede9fe;color:#5b21b6;">${l.leave_reason}</span>
            </div>
          </div>
          <div class="pending-item__dates">${l.start_date} → ${l.end_date}</div>
        </div>
        ${l.reason_note ? `<div class="pending-item__reason">${l.reason_note}</div>` : '<div class="pending-item__reason text-muted">Sin motivo especificado</div>'}
        <div class="pending-item__actions">
          <button class="pcard-btn pcard-btn--approve" onclick="approveLeave('${l.id}')">Aprobar</button>
          <button class="pcard-btn pcard-btn--reject"  onclick="openRejectModal('${l.id}')">Rechazar</button>
        </div>
      </div>
    `).join('');
  } catch (e) {
    container.innerHTML = '<small class="text-danger ps-3 py-2">Error al cargar.</small>';
    console.error('Load pending requests error:', e);
  }
}

// ════════════════════════════════════════════════════════════════════════════
// ✅ Aprobar Solicitud
// ════════════════════════════════════════════════════════════════════════════

/**
 * Aprueba una solicitud de vacaciones/ausencia
 * Para vacaciones: carga datos sugeridos y muestra modal
 * Para ausencias: aprueba directamente
 * @param {string} leaveId - ID de la solicitud
 * @returns {Promise<void>}
 */
export async function approveLeave(leaveId) {
  const l = getLeaveData(leaveId);
  if (!l) {
    console.warn('[DEBUG] Leave data not found for:', leaveId);
    return;
  }

  // Si es vacaciones, mostrar modal con unidad de vacación
  if (l.leave_type_raw === 'vacation') {
    await openApproveVacationModal(leaveId);
  } else {
    // Para ausencias, aprobar directamente
    await submitReview(leaveId, 'approve', null);
  }
}

// ════════════════════════════════════════════════════════════════════════════
// ❌ Rechazar Solicitud
// ════════════════════════════════════════════════════════════════════════════

/**
 * Abre el modal para rechazar una solicitud
 * @param {string} leaveId - ID de la solicitud
 * @returns {void}
 */
export function openRejectModal(leaveId) {
  const l = getLeaveData(leaveId);
  if (!l) return;

  setPendingRejectId(leaveId);
  document.getElementById('rejectNoteInput').value = '';
  document.getElementById('rejectModalUser').textContent = l.user;
  document.getElementById('rejectModalType').textContent = l.leave_type + ' · ' + l.leave_reason;
  document.getElementById('rejectModalDates').textContent = '' + l.start_date + ' → ' + l.end_date;
  document.getElementById('rejectModalNote').textContent = l.reason_note ? '"' + l.reason_note + '"' : '';

  bootstrap.Modal.getOrCreateInstance(document.getElementById('rejectModal')).show();
}

/**
 * Abre el modal para aprobar una solicitud de vacaciones con unidad de vacación
 * @param {string} leaveId - ID de la solicitud
 * @returns {Promise<void>}
 */
export async function openApproveVacationModal(leaveId) {
  try {
    // Cargar datos sugeridos desde la API
    const res = await fetch(`/leave/${leaveId}/for-review/`, {
      headers: { 'Accept': 'application/json' }
    });

    if (!res.ok) {
      alert('Error al cargar los datos de la solicitud');
      return;
    }

    const data = await res.json();

    // Llenar campos del modal
    document.getElementById('vacApproveUser').textContent = data.user;
    document.getElementById('vacApproveDates').textContent = `${data.start_date} → ${data.end_date}`;
    document.getElementById('vacApproveReason').textContent = data.leave_reason_display;

    // Llenar campos de vacaciones
    document.getElementById('vacApproveMultiplier').value = data.suggested_multiplier || 1.0;
    document.getElementById('vacApproveRequest').textContent = data.request_days || 0;
    document.getElementById('vacApproveRemaining').textContent = data.remaining_days_after || 0;
    document.getElementById('vacApproveLimit').textContent = data.available_days || 23;
    document.getElementById('vacApproveBarText').textContent = `${data.consumed_days || 0}/${data.available_days || 23} días`;
    document.getElementById('vacApproveNote').value = '';

    // Actualizar barra de progreso
    const percentage = Math.min(100, ((data.consumed_days || 0) / (data.available_days || 23)) * 100);
    const bar = document.getElementById('vacApproveBar');
    bar.style.width = percentage + '%';
    bar.classList.remove('bg-success', 'bg-danger');
    bar.classList.add(data.exceeds_limit ? 'bg-danger' : 'bg-success');

    // Mostrar alerta si excede
    const alert = document.getElementById('vacApproveAlert');
    if (data.exceeds_limit) {
      alert.classList.remove('d-none');
    } else {
      alert.classList.add('d-none');
    }

    // Guardar leaveId en un atributo para usar después
    document.getElementById('btnConfirmApproveVacation').dataset.leaveId = leaveId;

    // Mostrar modal
    console.log('[DEBUG] Showing approval modal');
    bootstrap.Modal.getOrCreateInstance(document.getElementById('approveVacationModal')).show();

  } catch (e) {
    console.error('Error opening approve vacation modal:', e);
    alert('Error al cargar los datos de la solicitud');
  }
}

// ════════════════════════════════════════════════════════════════════════════
// 🔄 Procesar Revisión (Aprobar/Rechazar)
// ════════════════════════════════════════════════════════════════════════════

/**
 * Envía la revisión (aprobación o rechazo) a la API
 * @param {string} leaveId - ID de la solicitud
 * @param {string} action - 'approve' o 'reject'
 * @param {string|null} note - Nota opcional para el rechazo
 * @param {number|null} hourMultiplier - Unidad de Vacación (solo para vacaciones aprobadas)
 * @returns {Promise<void>}
 */
export async function submitReview(leaveId, action, note, hourMultiplier = null) {
  try {
    const body = { action, note };

    // Agregar unidad de vacación si es aprobación de vacaciones
    if (action === 'approve' && hourMultiplier !== null) {
      body.hour_multiplier = hourMultiplier;
    }

    const res = await fetch(getLeaveBaseUrl() + leaveId + '/review/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCsrfToken()
      },
      body: JSON.stringify(body),
    });
    const data = await res.json();

    if (res.ok) {
      // Recargar solicitudes pendientes
      if (document.getElementById('pendingContainer')) {
        await loadPendingRequests();
      }

      // Recargar eventos del calendario
      const calendarObj = getCalendarObj();
      if (calendarObj) calendarObj.refetchEvents();

      // Recargar estado de vacaciones
      await loadVacationStatus();
    } else {
      alert(data.error || 'Error al procesar la solicitud.');
    }
  } catch (e) {
    console.error('Error en submitReview:', e);
    alert('Error de conexión con el servidor.');
  }
}
