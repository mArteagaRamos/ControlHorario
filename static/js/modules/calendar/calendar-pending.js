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
    badge.textContent = list.length;

    if (list.length === 0) {
      container.innerHTML = '<small class="text-muted ps-3 py-2">Sin solicitudes pendientes.</small>';
      return;
    }

    // Guardamos los datos en un mapa para acceder desde el modal sin tocar el DOM
    initLeaveDataMap();
    list.forEach(l => {
      setLeaveData(l.id, l);
    });

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
 * @param {string} leaveId - ID de la solicitud
 * @returns {Promise<void>}
 */
export async function approveLeave(leaveId) {
  await submitReview(leaveId, 'approve', null);
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

// ════════════════════════════════════════════════════════════════════════════
// 🔄 Procesar Revisión (Aprobar/Rechazar)
// ════════════════════════════════════════════════════════════════════════════

/**
 * Envía la revisión (aprobación o rechazo) a la API
 * @param {string} leaveId - ID de la solicitud
 * @param {string} action - 'approve' o 'reject'
 * @param {string|null} note - Nota opcional para el rechazo
 * @returns {Promise<void>}
 */
export async function submitReview(leaveId, action, note) {
  try {
    const res = await fetch(getLeaveBaseUrl() + leaveId + '/review/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCsrfToken()
      },
      body: JSON.stringify({ action, note }),
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
    } else {
      alert(data.error || 'Error al procesar la solicitud.');
    }
  } catch (e) {
    console.error('Error en submitReview:', e);
    alert('Error de conexión con el servidor.');
  }
}
