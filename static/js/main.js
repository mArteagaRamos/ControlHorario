/**
 * Main Entry Point - Control Horario
 * Carga los módulos correspondientes según la página actual
 *
 * FASE 8: Consolidar inicialización
 */

console.log('[Main] Initializing application...');

/**
 * Detecta qué página estamos visitando y carga los módulos correspondientes
 */
async function initializePageModules() {
    // Detectar página por URL o por elemento específico del DOM

    // Admin Dashboard
    if (document.getElementById('section-empresa') || document.getElementById('btn-tipo-empresa')) {
        console.log('[Main] Detected Admin Dashboard page');
        await loadAdminDashboard();
        return;
    }

    // Calendar (futuro)
    if (document.getElementById('calendarContainer')) {
        console.log('[Main] Detected Calendar page');
        await loadCalendar();
        return;
    }

    // Otras páginas
    console.log('[Main] No specific page modules detected');
}

/**
 * Carga los módulos del Admin Dashboard
 */
async function loadAdminDashboard() {
    try {
        // Usar dynamic import para cargar el módulo
        const { initializeAdminDashboard } = await import('./modules/admin/admin-dashboard.js');
        console.log('[Main] Loading Admin Dashboard module...');
        initializeAdminDashboard();
    } catch (error) {
        console.error('[Main] Error loading Admin Dashboard:', error);
    }
}

/**
 * Carga los módulos del Calendar (futuro)
 */
async function loadCalendar() {
    try {
        const { initializeCalendar } = await import('./modules/calendar/calendar.js');
        console.log('[Main] Loading Calendar module...');
        initializeCalendar();
    } catch (error) {
        console.error('[Main] Error loading Calendar:', error);
    }
}

/**
 * Inicializa la aplicación cuando el DOM está listo
 */
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializePageModules);
} else {
    // Si el DOM ya está cargado (lo normal para scripts de módulo)
    // Ejecutar directamente
    initializePageModules().catch(error => {
        console.error('[Main] Error during initialization:', error);
    });
}

console.log('[Main] Setup complete - waiting for page modules...');

