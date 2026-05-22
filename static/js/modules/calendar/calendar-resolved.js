/**
 * calendar-resolved.js
 * Gestión de solicitudes resueltas (aprobadas/rechazadas)
 *
 * Funciones para:
 * - Cargar solicitudes resueltas
 * - Toggle de visibilidad de tabla
 * - Expandir/contraer notas de resolución
 * - Eliminar solicitudes
 */

import {
  getLeaveResolvedUrl,
  getCurrentUserId,
  setLeaveData,
} from './calendar-state.js';

// ════════════════════════════════════════════════════════════════════════════
// Estado de Visibilidad (Local)
// ════════════════════════════════════════════════════════════════════════════

let _resolvedVisible = true;

// ════════════════════════════════════════════════════════════════════════════
// Cargar Solicitudes Resueltas
// ════════════════════════════════════════════════════════════════════════════

/**
 * Carga las solicitudes resueltas (aprobadas/rechazadas)
 * Accesible para todos los usuarios
 * @param {string|null} userId - null (mis solicitudes), 'all', o ID específico
 * @returns {Promise<void>}
 */
export async function loadResolvedRequests(userId) {
  const container = document.getElementById('resolvedContainer');
  const titleEl = document.getElementById('resolvedTitle');

  if (!container) return;

  // Título dinámico según filtro
  if (titleEl) {
    if (!userId) {
      titleEl.textContent = 'Mis Solicitudes';
    } else if (userId === 'all') {
      titleEl.textContent = 'Solicitudes — Todos los empleados';
    } else {
      const sel = document.getElementById('teamSelector');
      const selectedText = sel ? sel.options[sel.selectedIndex].text : 'Empleado';
      titleEl.textContent = `Solicitudes — ${selectedText}`;
    }
  }

  container.innerHTML = '<small class="text-muted ps-2">Cargando…</small>';

  try {
    const params = new URLSearchParams();
    if (userId) params.set('user_id', userId);

    const res = await fetch(`${getLeaveResolvedUrl()}?${params}`);
    const data = await res.json();
    const list = data.requests;
    const showUserCol = data.show_user_col;

    if (!list || list.length === 0) {
      container.innerHTML = '<small class="text-muted ps-2">No hay solicitudes resueltas.</small>';
      return;
    }

    const STATUS_STYLE = {
      pending: { bg: '#fef3c7', border: '#fde68a', color: '#92400e', icon: '⏱' },
      approved: { bg: '#f0fdf4', border: '#bbf7d0', color: '#166534', icon: '✓' },
      rejected: { bg: '#fff1f2', border: '#fecaca', color: '#991b1b', icon: '✗' },
      canceled: { bg: '#f1f5f9', border: '#cbd5e1', color: '#475569', icon: '⊘' }
    };

    const rows = list.map(l => {
      // Guardar datos en el mapa para acceso posterior
      setLeaveData(l.id, {
        start_date: l.start_date,
        end_date: l.end_date,
        leave_type: l.leave_type,
        leave_reason: l.leave_reason,
        reason_note: l.reason_note,
        status: l.status,
        attachment_path: l.attachment_path,
      });

      const validStatuses = ['pending', 'approved', 'rejected', 'canceled'];
      const currentStatus = validStatuses.includes(l.status) ? l.status : 'canceled';

      const s = STATUS_STYLE[currentStatus];
      const badge = `<span style="display:inline-flex;align-items:center;gap:.25rem;font-size:.72rem;font-weight:700;padding:.18rem .55rem;border-radius:999px;background:${s.bg};border:1px solid ${s.border};color:${s.color};">${s.icon} ${l.status_display}</span>`;

      let attachCell = '<span style="color:#94a3b8;font-size:.78rem;">—</span>';
      if (l.attachment_path) {
        attachCell = `<a href="/media/${l.attachment_path}" target="_blank"
          style="display:inline-flex;align-items:center;gap:.3rem;font-size:.78rem;font-weight:600;text-decoration:none;"
          title="Ver justificante"><i class="bi bi-file-earmark-text"></i> Ver</a>`;
      }

      const reviewNote = l.review_note
        ? `<span onclick="toggleReviewNote(this, '${l.review_note.replace(/'/g, "\\'")}')"
                style="cursor:pointer; margin-left:0.5rem; font-size:0.7rem;"
                title="Ver motivo">
              <i class="bi-chat-dots"></i>
          </span>`
        : '';

      let editIcon = '';
      if (l.status === 'pending') {
        editIcon = `<button onclick="editLeaveRequest('leave-${l.id}')"
                  style="background:none;border:none;cursor:pointer;padding:0 .25rem;margin-left:.5rem;font-size:0.75rem;color:#6366f1;"
                  title="Editar solicitud"
                  class="btn-edit-leave">
            <i class="bi bi-pencil"></i>
          </button>`;
      }

      const userCell = showUserCol
        ? `<td style="padding:.5rem .6rem;white-space:nowrap;font-weight:500;">${l.user_name}</td>`
        : '';

      // Botón universal de eliminación (Papelera)
      const deleteButtonHtml = `
        <button onclick="deleteLeaveRequest('${l.id}')"
                style="background:none;border:none;cursor:pointer;padding:0 .25rem;color:#dc2626;font-size:1rem;transition:color 0.2s;"
                title="Eliminar esta solicitud"
                class="btn-delete-leave"
                onmouseover="this.style.color='#991b1b'"
                onmouseout="this.style.color='#dc2626'">
          <i class="bi bi-trash"></i>
        </button>
      `;

      return `<tr style="font-size:.82rem;border-bottom:1px solid #f1f5f9;">
        ${userCell}
        <td style="padding:.5rem .6rem;white-space:nowrap;">${l.start_date}</td>
        <td style="padding:.5rem .6rem;white-space:nowrap;">${l.end_date}</td>
        <td style="padding:.5rem .6rem;">${l.leave_type}</td>
        <td style="padding:.5rem .6rem;">${l.leave_reason}</td>
        <td style="padding:.5rem .6rem;">${badge}${reviewNote}${editIcon}</td>
        <td style="padding:.5rem .6rem;text-align:center;">${attachCell}</td>
        <td style="padding:.5rem .6rem;text-align:center;">${deleteButtonHtml}</td>
      </tr>`;
    }).join('');

    const userHeader = showUserCol
      ? `<th style="padding:.4rem .6rem;font-weight:600;">Empleado</th>`
      : '';

    container.innerHTML = `
      <table style="width:100%;border-collapse:collapse;">
        <thead>
          <tr style="font-size:.72rem;text-transform:uppercase;letter-spacing:.04em;color:#94a3b8;border-bottom:2px solid #e2e8f0;">
            ${userHeader}
            <th style="padding:.4rem .6rem;font-weight:600;">Desde</th>
            <th style="padding:.4rem .6rem;font-weight:600;">Hasta</th>
            <th style="padding:.4rem .6rem;font-weight:600;">Tipo</th>
            <th style="padding:.4rem .6rem;font-weight:600;">Motivo</th>
            <th style="padding:.4rem .6rem;font-weight:600;">Estado</th>
            <th style="padding:.4rem .6rem;font-weight:600;text-align:center;">Justificante</th>
            <th style="padding:.4rem .6rem;font-weight:600;text-align:center;">Acciones</th>
          </tr>
        </thead>
        <tbody>${rows}</tbody>
      </table>`;
  } catch (e) {
    container.innerHTML = '<small class="text-danger ps-2">Error al cargar.</small>';
    console.error('Load resolved requests error:', e);
  }
}

/**
 * Envía una petición POST al servidor para eliminar una solicitud (Soft-Delete)
 * @param {string} leaveId - ID único de la solicitud
 */
export async function deleteLeaveRequest(leaveId) {
  if (!confirm('¿Estás seguro de que quieres eliminar esta solicitud? Esta acción no se puede deshacer.')) {
    return;
  }

  try {
    const csrfToken = window.AEPTIC_CALENDAR?.CSRF_TOKEN || '';

    const res = await fetch(`/leave/${leaveId}/delete/`, {
      method: 'POST',
      headers: {
        'X-CSRFToken': csrfToken,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({})
    });

    const data = await res.json();
    if (data.ok) {
      const selector = document.getElementById('teamSelector');
      const userId = selector?.value || null;
      
      await loadResolvedRequests(userId);
      alert('Solicitud eliminada correctamente');
    } else {
      alert(`Error: ${data.error || 'No se pudo eliminar la solicitud'}`);
    }
  } catch (err) {
    console.error('[DELETE_LEAVE] Error:', err);
    alert('Error de conexión al intentar eliminar la solicitud');
  }
}

// ════════════════════════════════════════════════════════════════════════════
// Toggle Visibilidad de la Sección
// ════════════════════════════════════════════════════════════════════════════
export function toggleResolved() {
  const container = document.getElementById('resolvedContainer');
  const icon = document.getElementById('resolvedToggleIcon');
  if (!container) return;

  _resolvedVisible = !_resolvedVisible;
  container.style.display = _resolvedVisible ? '' : 'none';
  if (icon) {
    icon.textContent = _resolvedVisible ? '▲ ocultar' : '▼ mostrar';
  }
}

// ════════════════════════════════════════════════════════════════════════════
// Notas de Resolución (Fila Desplegable)
// ════════════════════════════════════════════════════════════════════════════
export function toggleReviewNote(element, note) {
  const mainRow = element.closest('tr');
  const nextRow = mainRow.nextElementSibling;

  if (nextRow && nextRow.classList.contains('review-note-row')) {
    nextRow.remove();
    return;
  }

  const colCount = mainRow.cells.length;

  const noteRow = document.createElement('tr');
  noteRow.classList.add('review-note-row');
  noteRow.style.background = '#fffbeb';

  noteRow.innerHTML = `
    <td colspan="${colCount}" style="padding: 0.8rem; border-bottom: 1px solid #fef3c7;">
      <div style="display: flex; align-items: flex-start; gap: 10px;">
        <i class="bi bi-info-circle-fill" style="color: #d97706;"></i>
        <div>
          <strong style="font-size: 0.75rem; color: #92400e; text-transform: uppercase;">Motivo de la resolución:</strong>
          <p style="margin: 3px 0 0 0; color: #451a03; font-style: italic;">${note}</p>
        </div>
        <button onclick="this.closest('tr').remove()" class="btn-close" style="font-size: 0.6rem; margin-left: auto;"></button>
      </div>
    </td>
  `;

  mainRow.parentNode.insertBefore(noteRow, mainRow.nextSibling);
}

// Exportar al objeto Window para soportar los handlers onclick inline del HTML dinámico
window.deleteLeaveRequest = deleteLeaveRequest;
window.toggleResolved = toggleResolved;
window.toggleReviewNote = toggleReviewNote;