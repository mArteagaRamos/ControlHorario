/**
 * Calendar - Entry point
 * Coordina la inicialización de todos los módulos del calendario
 *
 * Este archivo será el central que importa y ejecuta todos los módulos
 * de calendario en el orden correcto.
 */

// Este archivo actuará como entry point
// En las fases posteriores, se cargará aquí la inicialización de todos los módulos

console.log('[Calendar] Ready to load modules');

/**
 * Inicializa todos los módulos cuando el DOM esté listo
 */
export function initializeCalendar() {
    console.log('[Calendar] Initializing...');

    // Los módulos serán importados aquí en las fases posteriores
    // Por ahora, este es solo un placeholder

    document.addEventListener('DOMContentLoaded', () => {
        console.log('[Calendar] DOM ready');
        // Aquí irán las inicializaciones de módulos
    });
}

// Auto-initialize if this is the main script
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeCalendar);
} else {
    initializeCalendar();
}
