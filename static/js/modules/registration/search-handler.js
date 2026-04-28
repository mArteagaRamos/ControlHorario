/**
 * search-handler.js
 * Centralized search handling for company and worker lookups
 *
 * Functions:
 * - handleCompanyExactSearch(taxId, lookupUrl, callbacks)
 * - handleCompanyAutocompleteSearch(query, lookupUrl, callbacks)
 * - handleWorkerExactSearch(field, value, lookupUrl, callbacks)
 * - handleWorkerAutocompleteSearch(query, lookupUrl, callbacks)
 * - setupClickOutsideListener(triggerEl, dropdownEl, callback)
 */

import { debounce } from '../../utils/debounce.js';

/**
 * Handle exact company search by Tax ID
 * @param {string} taxId - Company tax ID/CIF
 * @param {string} lookupUrl - URL for lookup endpoint
 * @param {Object} callbacks - { onSuccess, onError, setFeedback }
 */
export async function handleCompanyExactSearch(taxId, lookupUrl, callbacks) {
  const { onSuccess, onError, setFeedback } = callbacks;

  if (!taxId) {
    setFeedback('Introduce un CIF / NIF.', 'danger');
    return;
  }

  try {
    const res = await fetch(`${lookupUrl}?tax_id=${encodeURIComponent(taxId)}`);
    const data = await res.json();

    if (data.found) {
      setFeedback('Empresa encontrada. Puedes editar sus datos.', 'success');
      if (onSuccess) onSuccess(data);
    } else {
      setFeedback('No existe ninguna empresa con ese CIF.', 'danger');
      if (onError) onError();
    }
  } catch (error) {
    console.error('Error searching company:', error);
    setFeedback('Error al buscar la empresa.', 'danger');
    if (onError) onError();
  }
}

/**
 * Handle company autocomplete search by name
 * @param {string} query - Search query
 * @param {string} lookupUrl - URL for lookup endpoint
 * @param {Object} callbacks - { onSuccess, onError, setFeedback, suggestionsElement, onSuggestionClick }
 * @returns {Function} Debounced search function
 */
export function handleCompanyAutocompleteSearch(query, lookupUrl, callbacks) {
  const { onSuccess, onError, setFeedback, suggestionsElement, onSuggestionClick } = callbacks;

  if (query.length < 2) {
    suggestionsElement?.classList.add('d-none');
    setFeedback('', '');
    return;
  }

  const performSearch = debounce(async () => {
    try {
      const res = await fetch(`${lookupUrl}?name=${encodeURIComponent(query)}`);
      const data = await res.json();
      const results = data.results || [];

      suggestionsElement.innerHTML = '';

      if (results.length === 0) {
        suggestionsElement.classList.add('d-none');
        setFeedback('Sin resultados para esa búsqueda.', 'warning');
        return;
      }

      setFeedback('', '');
      results.forEach(company => {
        const li = document.createElement('li');
        li.className = 'list-group-item list-group-item-action d-flex justify-content-between align-items-center';
        li.style.cursor = 'pointer';
        li.innerHTML = `
          <span>
            <strong>${company.name.title || company.name}</strong>
            <small class="text-muted ms-2">${company.legal_name || ''}</small>
          </span>
        `;

        li.addEventListener('click', () => {
          if (onSuggestionClick) {
            onSuggestionClick(company);
          }
          suggestionsElement.classList.add('d-none');
          setFeedback('Empresa seleccionada. Puedes editar sus datos.', 'success');
        });

        suggestionsElement.appendChild(li);
      });

      suggestionsElement.classList.remove('d-none');
      if (onSuccess) onSuccess(results);
    } catch (error) {
      console.error('Error searching companies:', error);
      suggestionsElement.classList.add('d-none');
      setFeedback('Error al buscar empresas.', 'danger');
      if (onError) onError();
    }
  }, 300);

  performSearch();
}

/**
 * Handle exact worker search by email or DNI
 * @param {string} field - 'email' or 'dni'
 * @param {string} value - Field value to search
 * @param {string} lookupUrl - URL for lookup endpoint
 * @param {Object} callbacks - { onSuccess, onError, setFeedback }
 */
export async function handleWorkerExactSearch(field, value, lookupUrl, callbacks) {
  const { onSuccess, onError, setFeedback } = callbacks;
  const fieldLabel = field === 'email' ? 'email' : 'DNI';

  if (!value) {
    setFeedback(`Introduce un ${fieldLabel}.`, 'danger');
    return;
  }

  try {
    const url = new URL(lookupUrl, window.location.origin);
    url.searchParams.set(field, value);
    const res = await fetch(url.toString());
    const data = await res.json();

    if (data.found) {
      setFeedback('Trabajador encontrado.', 'success');
      if (onSuccess) onSuccess(data);
    } else {
      setFeedback(`No existe ningún trabajador con ese ${fieldLabel} en esta empresa.`, 'danger');
      if (onError) onError();
    }
  } catch (error) {
    console.error(`Error searching worker by ${field}:`, error);
    setFeedback('Error al buscar el trabajador.', 'danger');
    if (onError) onError();
  }
}

/**
 * Handle worker autocomplete search by name
 * @param {string} query - Search query (name/surname)
 * @param {string} lookupUrl - URL for lookup endpoint (already includes company_id if needed)
 * @param {Object} callbacks - { onSuccess, onError, setFeedback, suggestionsElement, onSuggestionClick }
 * @returns {Function} Debounced search function
 */
export function handleWorkerAutocompleteSearch(query, lookupUrl, callbacks) {
  const { onSuccess, onError, setFeedback, suggestionsElement, onSuggestionClick } = callbacks;

  if (query.length < 2) {
    suggestionsElement?.classList.add('d-none');
    setFeedback('', '');
    return;
  }

  const performSearch = debounce(async () => {
    try {
      const res = await fetch(`${lookupUrl}&name=${encodeURIComponent(query)}`);
      const data = await res.json();
      const results = data.results || [];

      suggestionsElement.innerHTML = '';

      if (results.length === 0) {
        suggestionsElement.classList.add('d-none');
        setFeedback('Sin resultados para esa búsqueda.', 'warning');
        return;
      }

      setFeedback('', '');
      results.forEach(user => {
        const li = document.createElement('li');
        li.className = 'list-group-item list-group-item-action d-flex justify-content-between align-items-center';
        li.style.cursor = 'pointer';
        li.innerHTML = `
          <span>
            <strong>${(user.username || '').charAt(0).toUpperCase() + (user.username || '').slice(1).toLowerCase()}
                    ${(user.surname || '').charAt(0).toUpperCase() + (user.surname || '').slice(1).toLowerCase()}</strong>
          </span>
        `;

        li.addEventListener('click', () => {
          if (onSuggestionClick) {
            onSuggestionClick(user);
          }
          suggestionsElement.classList.add('d-none');
          setFeedback('Trabajador seleccionado.', 'success');
        });

        suggestionsElement.appendChild(li);
      });

      suggestionsElement.classList.remove('d-none');
      if (onSuccess) onSuccess(results);
    } catch (error) {
      console.error('Error searching workers:', error);
      suggestionsElement.classList.add('d-none');
      setFeedback('Error al buscar trabajadores.', 'danger');
      if (onError) onError();
    }
  }, 300);

  performSearch();
}

/**
 * Setup click-outside listener to hide dropdown
 * Useful for closing autocomplete suggestions when clicking outside
 *
 * @param {HTMLElement} triggerEl - Element that triggers suggestions (input field)
 * @param {HTMLElement} dropdownEl - Dropdown element to hide
 * @param {Function} onHide - Optional callback when hiding
 */
export function setupClickOutsideListener(triggerEl, dropdownEl, onHide) {
  if (!triggerEl || !dropdownEl) return;

  document.addEventListener('click', (e) => {
    if (!triggerEl.contains(e.target) && !dropdownEl.contains(e.target)) {
      dropdownEl.classList.add('d-none');
      if (typeof onHide === 'function') {
        onHide();
      }
    }
  });
}

/**
 * Build URL with company_id parameter if present
 * Used for worker lookups that require company context
 *
 * @param {string} baseUrl - Base lookup URL
 * @param {Object} params - Query parameters
 * @returns {string} Full URL with parameters
 */
export function buildLookupUrl(baseUrl, params = {}) {
  const companyId = document.getElementById('company_id_input')?.value.trim();
  const url = new URL(baseUrl, window.location.origin);

  for (const [k, v] of Object.entries(params)) {
    url.searchParams.set(k, v);
  }

  if (companyId) {
    url.searchParams.set('company_id', companyId);
  }

  return url.toString();
}

/**
 * Clear feedback message
 * @param {HTMLElement} feedbackEl - Feedback element to clear
 */
export function clearFeedback(feedbackEl) {
  if (feedbackEl) {
    feedbackEl.textContent = '';
    feedbackEl.className = '';
  }
}

/**
 * Set feedback message with color
 * @param {HTMLElement} feedbackEl - Feedback element
 * @param {string} text - Feedback message
 * @param {string} type - 'success', 'danger', 'warning'
 */
export function setFeedback(feedbackEl, text, type) {
  if (feedbackEl) {
    feedbackEl.textContent = text;
    feedbackEl.className = `form-text text-${type}`;
  }
}
