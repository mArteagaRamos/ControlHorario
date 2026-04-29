/**
 * calendar-state.js
 * Gestión centralizada de estado compartido del calendario
 *
 * Proporciona getters/setters para variables globales y URLs
 * Evita acceso directo a window para mayor control
 */

// ════════════════════════════════════════════════════════════════════════════
// 📌 VARIABLES DE ESTADO - Getters y Setters
// ════════════════════════════════════════════════════════════════════════════

/**
 * Obtiene la instancia actual de FullCalendar
 * @returns {FullCalendar.Calendar|null}
 */
export function getCalendarObj() {
  return window.calendarObj || null;
}

/**
 * Establece la instancia de FullCalendar
 * @param {FullCalendar.Calendar} obj
 */
export function setCalendarObj(obj) {
  window.calendarObj = obj;
}

/**
 * Obtiene el ID del usuario actualmente seleccionado en filtros
 * @returns {string|null}
 */
export function getCurrentUserId() {
  return window.currentUserId || null;
}

/**
 * Establece el ID del usuario seleccionado
 * @param {string|null} id
 */
export function setCurrentUserId(id) {
  window.currentUserId = id;
}

/**
 * Obtiene el ID de la solicitud siendo rechazada
 * @returns {string|null}
 */
export function getPendingRejectId() {
  return window._pendingRejectId || null;
}

/**
 * Establece el ID de la solicitud siendo rechazada
 * @param {string|null} id
 */
export function setPendingRejectId(id) {
  window._pendingRejectId = id;
}

/**
 * Obtiene el ID de la solicitud actualmente en el modal
 * @returns {string|null}
 */
export function getCurrentLeaveId() {
  return window.currentLeaveId || null;
}

/**
 * Establece el ID de la solicitud actualmente en el modal
 * @param {string|null} id
 */
export function setCurrentLeaveId(id) {
  window.currentLeaveId = id;
}

/**
 * Obtiene los estados actualmente filtrados
 * @returns {string[]}
 */
export function getSelectedStatuses() {
  return window.selectedStatuses || ['pending', 'approved'];
}

/**
 * Establece los estados filtrados
 * @param {string[]} statuses
 */
export function setSelectedStatuses(statuses) {
  window.selectedStatuses = statuses;
}

/**
 * Obtiene los datos de una solicitud desde el mapa compartido
 * @param {string} id - ID de la solicitud
 * @returns {Object|undefined}
 */
export function getLeaveData(id) {
  if (!window._leaveDataMap) window._leaveDataMap = {};
  return window._leaveDataMap[id];
}

/**
 * Establece los datos de una solicitud en el mapa compartido
 * @param {string} id - ID de la solicitud
 * @param {Object} data - Datos de la solicitud
 */
export function setLeaveData(id, data) {
  if (!window._leaveDataMap) window._leaveDataMap = {};
  window._leaveDataMap[id] = data;
}

/**
 * Inicializa el mapa de datos de solicitudes
 */
export function initLeaveDataMap() {
  window._leaveDataMap = {};
}

/**
 * Obtiene toda la data del mapa de solicitudes
 * @returns {Object}
 */
export function getAllLeaveData() {
  if (!window._leaveDataMap) window._leaveDataMap = {};
  return window._leaveDataMap;
}

// ════════════════════════════════════════════════════════════════════════════
// 🔗 URLS Y CONFIGURACIÓN - Helpers
// ════════════════════════════════════════════════════════════════════════════

/**
 * Obtiene URL para cargar eventos del calendario
 * @returns {string}
 */
export function getEventsUrl() {
  return window.AEPTIC_CALENDAR?.EVENTS_URL || '';
}

/**
 * Obtiene URL para crear solicitud
 * @returns {string}
 */
export function getLeaveCreateUrl() {
  return window.AEPTIC_CALENDAR?.LEAVE_CREATE_URL || '';
}

/**
 * Obtiene URL para cargar solicitudes pendientes
 * @returns {string}
 */
export function getLeavePendingUrl() {
  return window.AEPTIC_CALENDAR?.LEAVE_PENDING_URL || '';
}

/**
 * Obtiene URL para cargar solicitudes resueltas
 * @returns {string}
 */
export function getLeaveResolvedUrl() {
  return window.AEPTIC_CALENDAR?.LEAVE_RESOLVED_URL || '';
}

/**
 * Obtiene URL base para construcción dinámica de endpoints
 * @returns {string}
 */
export function getLeaveBaseUrl() {
  return window.AEPTIC_CALENDAR?.LEAVE_BASE_URL || '/leave/';
}

/**
 * Obtiene el token CSRF
 * @returns {string}
 */
export function getCsrfToken() {
  return window.AEPTIC_CALENDAR?.CSRF_TOKEN || '';
}

/**
 * Obtiene toda la configuración global
 * @returns {Object}
 */
export function getCalendarConfig() {
  return window.AEPTIC_CALENDAR || {};
}

// ════════════════════════════════════════════════════════════════════════════
// 🛠️ UTILIDADES
// ════════════════════════════════════════════════════════════════════════════

/**
 * Valida que la configuración esté completa
 * @returns {boolean}
 */
export function isConfigValid() {
  const config = getCalendarConfig();
  return !!(
    config.EVENTS_URL &&
    config.LEAVE_CREATE_URL &&
    config.LEAVE_PENDING_URL &&
    config.LEAVE_RESOLVED_URL &&
    config.CSRF_TOKEN
  );
}

/**
 * Obtiene la fecha actual en formato YYYY-MM-DD
 * @returns {string}
 */
export function getTodayDate() {
  return new Date().toISOString().split('T')[0];
}

/**
 * Log de debug (solo en desarrollo)
 * @param {string} message
 * @param {*} data
 */
export function logDebug(message, data = null) {
  if (process.env.NODE_ENV === 'development' || localStorage.getItem('debug_calendar')) {
    console.log(`[CALENDAR-STATE] ${message}`, data || '');
  }
}
