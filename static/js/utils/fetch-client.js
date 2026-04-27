/**
 * Cliente HTTP wrapper para fetch con soporte automático de CSRF token
 * Uso:
 *   apiClient.get(url)
 *   apiClient.post(url, data)
 *   apiClient.put(url, data)
 *   apiClient.delete(url)
 */

import { getAdminConfig, getCalendarConfig } from './config.js';

class ApiClient {
    constructor(configNamespace = 'AEPTIC_ADMIN') {
        this.configNamespace = configNamespace;
    }

    /**
     * Obtiene el CSRF token de la configuración
     */
    getCsrfToken() {
        let csrfToken = null;

        // Intenta desde la configuración global
        if (this.configNamespace === 'AEPTIC_ADMIN') {
            csrfToken = getAdminConfig('CSRF_TOKEN');
        } else if (this.configNamespace === 'AEPTIC_CALENDAR') {
            csrfToken = getCalendarConfig('CSRF_TOKEN');
        } else if (this.configNamespace === 'AEPTIC_TIMETRACKING') {
            // Para timetracking, intenta obtener del DOM directamente
            const csrfElement = document.getElementById('csrfToken');
            csrfToken = csrfElement?.value;
        }

        // Si no encuentra, busca en el DOM
        if (!csrfToken) {
            const csrfElement = document.querySelector('[name="csrfmiddlewaretoken"]');
            csrfToken = csrfElement?.value;
        }

        return csrfToken;
    }

    /**
     * Construye los headers por defecto
     */
    getDefaultHeaders(customHeaders = {}) {
        const headers = {
            'Content-Type': 'application/json',
            ...customHeaders
        };

        // Agrega CSRF token para requests POST, PUT, DELETE
        const csrfToken = this.getCsrfToken();
        if (csrfToken) {
            headers['X-CSRFToken'] = csrfToken;
        }

        return headers;
    }

    /**
     * GET request
     */
    async get(url, options = {}) {
        return fetch(url, {
            method: 'GET',
            headers: this.getDefaultHeaders(options.headers),
            ...options
        });
    }

    /**
     * POST request
     */
    async post(url, data = null, options = {}) {
        const body = data instanceof FormData ? data : JSON.stringify(data);

        // No establecer Content-Type para FormData (el navegador lo hace automáticamente)
        const headers = data instanceof FormData
            ? { 'X-CSRFToken': this.getCsrfToken(), ...options.headers }
            : this.getDefaultHeaders(options.headers);

        return fetch(url, {
            method: 'POST',
            headers,
            body,
            ...options
        });
    }

    /**
     * PUT request
     */
    async put(url, data = null, options = {}) {
        return fetch(url, {
            method: 'PUT',
            headers: this.getDefaultHeaders(options.headers),
            body: JSON.stringify(data),
            ...options
        });
    }

    /**
     * DELETE request
     */
    async delete(url, options = {}) {
        return fetch(url, {
            method: 'DELETE',
            headers: this.getDefaultHeaders(options.headers),
            ...options
        });
    }

    /**
     * PATCH request
     */
    async patch(url, data = null, options = {}) {
        return fetch(url, {
            method: 'PATCH',
            headers: this.getDefaultHeaders(options.headers),
            body: JSON.stringify(data),
            ...options
        });
    }
}

// Crear instancias para cada página
export const adminApiClient = new ApiClient('AEPTIC_ADMIN');
export const calendarApiClient = new ApiClient('AEPTIC_CALENDAR');
export const timetrackingApiClient = new ApiClient('AEPTIC_TIMETRACKING');

// Export por defecto es el admin client
export default adminApiClient;
