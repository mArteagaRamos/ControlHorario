/**
 * Timetracking Timer Module
 * Maneja la lógica del cronómetro y acciones de time tracking
 *
 * Exports:
 * - formatTime(seconds): Formatea segundos a HH:MM:SS
 * - postAction(action): Envía acciones de time tracking
 * - initializeTimer(): Inicializa el timer
 */

import { timetrackingApiClient } from '../../utils/fetch-client.js';

console.log('[Timer] Module loaded');

/**
 * Formatea segundos a formato HH:MM:SS
 * @param {number} seconds - Segundos a formatear
 * @returns {string} Tiempo formateado
 */
export function formatTime(seconds) {
    const h = String(Math.floor(seconds / 3600)).padStart(2, '0');
    const m = String(Math.floor((seconds % 3600) / 60)).padStart(2, '0');
    const s = String(seconds % 60).padStart(2, '0');
    return `${h}:${m}:${s}`;
}

/**
 * Envía una acción de time tracking al servidor
 * @param {string} action - Acción a enviar (clock_in, clock_out, pause_start, pause_end)
 */
export async function postAction(action) {
    try {
        const csrfToken = timetrackingApiClient.getCsrfToken();

        if (!csrfToken) {
            console.error('[Timer] CSRF token not found');
            return;
        }

        const res = await fetch(window.location.href, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-CSRFToken': csrfToken,
            },
            body: new URLSearchParams({ action }).toString(),
        });

        if (res.ok) {
            window.location.reload();
        } else {
            console.error('[Timer] Error posting action:', res.status);
        }
    } catch (error) {
        console.error('[Timer] Error in postAction:', error);
    }
}

/**
 * Inicializa el timer y la lógica de actualización
 */
export function initializeTimer() {
    const timerDisplay = document.getElementById('timerDisplay');
    const dataEl = document.getElementById('active-data');

    if (!timerDisplay || !dataEl) {
        console.warn('[Timer] Timer elements not found');
        return;
    }

    // Constantes desde data attributes
    const hasActive = dataEl.dataset.hasActive === 'true';
    const isPaused = dataEl.dataset.isPaused === 'true';
    const startTimeStr = dataEl.dataset.startTime;
    const pauseSecs = parseInt(dataEl.dataset.pauseSeconds || '0');
    const pausedElapsed = parseInt(dataEl.dataset.pausedElapsed || '0');

    if (hasActive) {
        if (isPaused) {
            // Si está pausada, mostrar el tiempo pausado
            timerDisplay.textContent = formatTime(pausedElapsed);
        } else {
            // Si no está pausada, actualizar cada segundo
            const start = new Date(startTimeStr).getTime();
            const update = () => {
                const elapsed = Math.floor((Date.now() - start) / 1000) - pauseSecs;
                timerDisplay.textContent = formatTime(elapsed);
            };
            update();
            setInterval(update, 1000);
        }
    }

    console.log('[Timer] Timer initialized');
}

// Auto-inicializar cuando el módulo se carga
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeTimer);
} else {
    // Si el DOM ya está cargado (lo normal para scripts de módulo)
    initializeTimer();
}

// Exponer postAction en window para que sea accesible desde el HTML (onclick)
window.postAction = postAction;
