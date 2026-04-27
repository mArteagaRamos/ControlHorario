/**
 * Función de debounce para evitar ejecutar una función múltiples veces
 * mientras se está escribiendo, moviendo el mouse, etc.
 *
 * Uso:
 *   const debouncedSearch = debounce((query) => {
 *       console.log('Buscando:', query);
 *   }, 300);
 *
 *   input.addEventListener('input', (e) => {
 *       debouncedSearch(e.target.value);
 *   });
 */

export function debounce(func, wait = 300) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

/**
 * Función de throttle para ejecutar una función máximo una vez cada X milisegundos
 *
 * Uso:
 *   const throttledResize = throttle(() => {
 *       console.log('Window resized');
 *   }, 200);
 *
 *   window.addEventListener('resize', throttledResize);
 */
export function throttle(func, limit = 300) {
    let inThrottle;
    return function(...args) {
        if (!inThrottle) {
            func.apply(this, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}

/**
 * Debounce con leading execution (ejecuta inmediatamente en la primera llamada)
 */
export function debounceLeading(func, wait = 300) {
    let timeout;
    let executed = false;

    return function(...args) {
        if (!executed) {
            func.apply(this, args);
            executed = true;
        }

        clearTimeout(timeout);
        timeout = setTimeout(() => {
            executed = false;
        }, wait);
    };
}
