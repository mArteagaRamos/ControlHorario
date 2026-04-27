/**
 * Módulo de configuración global
 * Lee configuración desde window.AEPTIC_ADMIN, window.AEPTIC_CALENDAR, etc.
 * o desde data attributes del HTML
 */

export const getConfig = (key, namespace = 'AEPTIC_ADMIN', defaultValue = null) => {
    try {
        // Primero intenta desde window global
        if (window[namespace] && window[namespace][key]) {
            return window[namespace][key];
        }

        // Si no encuentra, retorna el valor por defecto
        return defaultValue;
    } catch (error) {
        console.warn(`Config key ${key} not found in ${namespace}:`, error);
        return defaultValue;
    }
};

export const getAdminConfig = (key, defaultValue = null) => {
    return getConfig(key, 'AEPTIC_ADMIN', defaultValue);
};

export const getCalendarConfig = (key, defaultValue = null) => {
    return getConfig(key, 'AEPTIC_CALENDAR', defaultValue);
};

export const getAllConfig = (namespace = 'AEPTIC_ADMIN') => {
    try {
        return window[namespace] || {};
    } catch (error) {
        console.warn(`Could not retrieve config namespace ${namespace}:`, error);
        return {};
    }
};
