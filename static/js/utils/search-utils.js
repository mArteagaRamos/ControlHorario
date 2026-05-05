/**
 * search-utils.js
 * Utilidades compartidas para búsqueda (autocomplete, renderizado, validación)
 * Centraliza lógica de búsqueda usada en admin y registration modules
 */

import { debounce } from './debounce.js';
import { setFeedback, clearFeedback, hideElement, showElement } from './ui-utils.js';

/**
 * Renderizar lista de sugerencias
 * Patrón común en búsquedas autocomplete
 *
 * @param {Array} results - Resultados de búsqueda
 * @param {HTMLElement} container - Contenedor <ul> para sugerencias
 * @param {Function} formatter - Función que retorna HTML para cada item
 * @param {Function} onItemClick - Callback cuando se clickea una sugerencia
 */
export function renderSuggestions(results, container, formatter, onItemClick) {
  if (!container) return;

  container.innerHTML = '';

  results.forEach(item => {
    const li = document.createElement('li');
    li.className = 'list-group-item list-group-item-action d-flex justify-content-between align-items-center';
    li.style.cursor = 'pointer';
    li.innerHTML = formatter(item);

    li.addEventListener('click', () => {
      if (onItemClick) onItemClick(item);
      hideElement(container);
    });

    container.appendChild(li);
  });

  showElement(container);
}

/**
 * Limpiar sugerencias (vaciar y esconder)
 * @param {HTMLElement} container - Contenedor a limpiar
 */
export function clearSuggestions(container) {
  if (!container) return;
  container.innerHTML = '';
  hideElement(container);
}

/**
 * Configurar listener de click-outside para cerrar sugerencias
 * Útil para autocomplete que debe cerrarse al clickear afuera
 *
 * @param {HTMLElement} triggerEl - Input o elemento que triggerigera sugerencias
 * @param {HTMLElement} dropdownEl - Contenedor de sugerencias
 * @param {Function} onHide - Callback opcional cuando se cierra
 */
export function setupClickOutsideListener(triggerEl, dropdownEl, onHide) {
  if (!triggerEl || !dropdownEl) return;

  document.addEventListener('click', (e) => {
    if (!triggerEl.contains(e.target) && !dropdownEl.contains(e.target)) {
      hideElement(dropdownEl);
      if (typeof onHide === 'function') {
        onHide();
      }
    }
  });
}

/**
 * Crear función de búsqueda con debounce automático
 * Wrapper alrededor de la lógica de búsqueda
 *
 * @param {string} url - URL del endpoint de búsqueda
 * @param {Function} onSuccess - Callback con resultados
 * @param {Function} onError - Callback de error
 * @param {number} delayMs - Delay del debounce (default: 300ms)
 * @param {Object} extraParams - Parámetros adicionales a agregar a la URL (default: {})
 * @returns {Function} Función debouncified que ejecuta la búsqueda
 */
export function createDebouncedSearch(url, onSuccess, onError, delayMs = 300, extraParams = {}) {
  const performSearch = debounce(async (query) => {
    try {
      const searchUrl = new URL(url, window.location.origin);
      searchUrl.searchParams.set('name', query);

      // Agregar parámetros adicionales
      Object.entries(extraParams).forEach(([key, value]) => {
        searchUrl.searchParams.set(key, value);
      });

      const res = await fetch(searchUrl.toString());
      if (!res.ok) throw new Error(`HTTP ${res.status}`);

      const data = await res.json();
      if (onSuccess) onSuccess(data);
    } catch (error) {
      console.error('Search error:', error);
      if (onError) onError(error);
    }
  }, delayMs);

  return performSearch;
}

/**
 * Validar consulta de búsqueda
 * Retorna true si es válida, false si no
 * También limpia feedback si es inválida
 *
 * @param {string} query - Texto a validar
 * @param {HTMLElement} feedbackEl - Elemento para mostrar feedback
 * @param {number} minLength - Longitud mínima (default: 2)
 * @returns {boolean}
 */
export function isValidSearchQuery(query, feedbackEl = null, minLength = 2) {
  if (!query || query.length < minLength) {
    if (feedbackEl) {
      clearFeedback(feedbackEl);
    }
    return false;
  }
  return true;
}

/**
 * Limpiar inputs de búsqueda
 * Útil cuando se cambia de modo de búsqueda o se resetea
 *
 * @param {Array<string>} inputIds - IDs de inputs a limpiar
 */
export function clearSearchInputs(inputIds = []) {
  inputIds.forEach(id => {
    const input = document.getElementById(id);
    if (input) input.value = '';
  });
}

/**
 * Configurar entrada de búsqueda con autocomplete
 * Patrón completo: input → debounce → fetch → renderizar sugerencias
 *
 * @param {Object} options - Configuración
 * @param {string} options.inputId - ID del input
 * @param {string} options.suggestionsId - ID del contenedor de sugerencias
 * @param {string} options.feedbackId - ID del feedback
 * @param {string} options.url - URL del endpoint
 * @param {Function} options.formatter - Función para formatear items
 * @param {Function} options.onSelect - Callback cuando selecciona item
 * @param {number} options.minLength - Longitud mínima (default: 2)
 * @param {number} options.debounceMs - Delay debounce (default: 300)
 */
export function setupAutocompleteSearch(options = {}) {
  const {
    inputId,
    suggestionsId,
    feedbackId,
    url,
    formatter,
    onSelect,
    minLength = 2,
    debounceMs = 300,
  } = options;

  const input = document.getElementById(inputId);
  const suggestions = document.getElementById(suggestionsId);
  const feedback = document.getElementById(feedbackId);

  if (!input || !suggestions) return;

  const performSearch = debounce(async (query) => {
    if (!isValidSearchQuery(query, feedback, minLength)) {
      clearSuggestions(suggestions);
      return;
    }

    try {
      const searchUrl = new URL(url, window.location.origin);
      searchUrl.searchParams.set('name', query);

      const res = await fetch(searchUrl.toString());
      if (!res.ok) throw new Error(`HTTP ${res.status}`);

      const data = await res.json();
      const results = data.results || [];

      if (results.length === 0) {
        clearSuggestions(suggestions);
        setFeedback(feedback, 'Sin resultados', 'warning');
        return;
      }

      setFeedback(feedback, '', '');
      renderSuggestions(results, suggestions, formatter, (item) => {
        if (onSelect) onSelect(item);
        setFeedback(feedback, 'Seleccionado', 'success');
      });
    } catch (error) {
      console.error('Autocomplete error:', error);
      clearSuggestions(suggestions);
      setFeedback(feedback, 'Error al buscar', 'danger');
    }
  }, debounceMs);

  input.addEventListener('input', () => {
    const query = input.value.trim();
    performSearch(query);
  });

  // Click-outside listener
  setupClickOutsideListener(input, suggestions, () => {
    suggestions.innerHTML = '';
  });
}
