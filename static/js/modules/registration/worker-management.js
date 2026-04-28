/**
 * worker-management.js
 * Worker-specific management (action toggle, search, form handling)
 *
 * Functions:
 * - setWorkerAction(action)
 * - initWorkerManagement(lookupUrl)
 * - setupWorkerActionToggle()
 * - setupWorkerExactSearchListeners(lookupUrl)
 * - setupWorkerAutocompleteSearch(lookupUrl)
 * - setupWorkerSearchModeTabs()
 */

import {
  handleWorkerExactSearch,
  handleWorkerAutocompleteSearch,
  setupClickOutsideListener,
  buildLookupUrl,
  setFeedback as setSearchFeedback,
  clearFeedback,
} from './search-handler.js';

import { fillWorkerForm, clearFormBlock } from './form-utils.js';
import { checkAndHandleLastManager, requireCompany } from './validation.js';

/**
 * Toggle worker action between 'create' and 'select'
 * @param {string} action - 'create' or 'select'
 */
export function setWorkerAction(action) {
  const workerActionInput = document.getElementById('worker_action_input');
  const btnWorkerCreate = document.getElementById('btn-worker-create');
  const btnWorkerSelect = document.getElementById('btn-worker-select');
  const workerLookupBlock = document.getElementById('worker-lookup-block');
  const workerLookupFeedback = document.getElementById('worker-lookup-feedback');

  if (!workerActionInput) return;

  workerActionInput.value = action;
  const isCreate = action === 'create';

  // Update button styles
  btnWorkerCreate?.classList.toggle('btn-primary', isCreate);
  btnWorkerCreate?.classList.toggle('btn-outline-primary', !isCreate);
  btnWorkerSelect?.classList.toggle('btn-primary', !isCreate);
  btnWorkerSelect?.classList.toggle('btn-outline-primary', isCreate);

  // Toggle lookup block visibility
  workerLookupBlock?.classList.toggle('d-none', isCreate);

  // Clean worker form and lookup
  clearFormBlock('worker-form-block');
  clearFormBlock('worker-lookup-block');

  // Clear search inputs
  const emailInput = document.getElementById('worker-lookup-email');
  const dniInput = document.getElementById('worker-lookup-dni');
  const nameInput = document.getElementById('worker-lookup-name');
  const nameSuggestions = document.getElementById('name-suggestions');

  if (emailInput) emailInput.value = '';
  if (dniInput) dniInput.value = '';
  if (nameInput) nameInput.value = '';

  // Clear feedback
  clearFeedback(workerLookupFeedback);

  // Hide suggestions
  if (nameSuggestions) {
    nameSuggestions.innerHTML = '';
    nameSuggestions.classList.add('d-none');
  }

  // Reset manager warning and role select
  const warningDiv = document.getElementById('last-manager-warning');
  const roleSelect = document.getElementById('id_role');

  if (warningDiv) warningDiv.classList.add('d-none');
  if (roleSelect) {
    roleSelect.disabled = false;
    roleSelect.classList.remove('is-invalid');
  }

  // Hide auditor checkbox when switching to 'select' mode
  const auditorCheckboxBlock = document.getElementById('auditor-checkbox-block');
  const auditorCheckbox = document.getElementById('id_is_auditor');
  const btnToggleAuditor = document.getElementById('btn-toggle-auditor');

  if (auditorCheckboxBlock) {
    if (action === 'select') {
      auditorCheckboxBlock.classList.add('d-none');
      btnToggleAuditor?.classList.add('d-none');
      if (auditorCheckbox) {
        auditorCheckbox.checked = false;
      }
    } else {
      btnToggleAuditor?.classList.remove('d-none');
    }
  }
}

/**
 * Setup worker action toggle buttons
 */
export function setupWorkerActionToggle() {
  const btnWorkerCreate = document.getElementById('btn-worker-create');
  const btnWorkerSelect = document.getElementById('btn-worker-select');

  if (btnWorkerCreate) {
    btnWorkerCreate.addEventListener('click', () => setWorkerAction('create'));
  }

  if (btnWorkerSelect) {
    btnWorkerSelect.addEventListener('click', () => setWorkerAction('select'));
  }
}

/**
 * Setup exact worker search (email/dni)
 * @param {string} lookupUrl - Worker lookup URL
 * @param {string} checkLastManagerUrl - URL to check last manager status
 */
export function setupWorkerExactSearchListeners(lookupUrl, checkLastManagerUrl) {
  const buttons = document.querySelectorAll('.btn-lookup-exact');
  const feedback = document.getElementById('worker-lookup-feedback');

  buttons.forEach(btn => {
    btn.addEventListener('click', async () => {
      const field = btn.dataset.field; // 'email' or 'dni'
      const inputEl = document.getElementById(`worker-lookup-${field}`);
      const value = inputEl?.value.trim() || '';

      const fieldLabel = field === 'email' ? 'email' : 'DNI';

      // Validate company first
      if (!requireCompany((text, type) => setSearchFeedback(feedback, text, type))) {
        return;
      }

      if (!value) {
        setSearchFeedback(feedback, `Introduce un ${fieldLabel}.`, 'danger');
        return;
      }

      const searchUrl = buildLookupUrl(lookupUrl);
      const callbacks = {
        onSuccess: async (data) => {
          fillWorkerForm(data);
          // Check if user is last manager
          if (data.id) {
            await checkAndHandleLastManager(data.id, checkLastManagerUrl);
          }
        },
        onError: () => {
          clearFormBlock('worker-form-block');
        },
        setFeedback: (text, type) => setSearchFeedback(feedback, text, type),
      };

      await handleWorkerExactSearch(field, value, searchUrl, callbacks);
    });
  });

  // Clear feedback when typing
  const emailInput = document.getElementById('worker-lookup-email');
  const dniInput = document.getElementById('worker-lookup-dni');

  if (emailInput) {
    emailInput.addEventListener('input', () => {
      clearFeedback(feedback);
      clearFormBlock('worker-form-block');
    });
  }

  if (dniInput) {
    dniInput.addEventListener('input', () => {
      clearFeedback(feedback);
      clearFormBlock('worker-form-block');
    });
  }
}

/**
 * Setup worker autocomplete search by name
 * @param {string} lookupUrl - Worker lookup URL
 * @param {string} checkLastManagerUrl - URL to check last manager status
 */
export function setupWorkerAutocompleteSearch(lookupUrl, checkLastManagerUrl) {
  const input = document.getElementById('worker-lookup-name');
  const suggestions = document.getElementById('name-suggestions');
  const feedback = document.getElementById('worker-lookup-feedback');

  if (!input || !suggestions) return;

  input.addEventListener('input', () => {
    const query = input.value.trim();

    // Validate company first
    if (!requireCompany((text, type) => setSearchFeedback(feedback, text, type))) {
      return;
    }

    const searchUrl = buildLookupUrl(lookupUrl);

    const callbacks = {
      onSuccess: () => {
        // Results rendered in handler
      },
      onError: () => {
        // Error handled in handler
      },
      setFeedback: (text, type) => setSearchFeedback(feedback, text, type),
      suggestionsElement: suggestions,
      onSuggestionClick: async (user) => {
        fillWorkerForm(user);
        input.value = `${user.username} ${user.surname}`;
        // Check if user is last manager
        if (user.id) {
          await checkAndHandleLastManager(user.id, checkLastManagerUrl);
        }
      },
    };

    handleWorkerAutocompleteSearch(query, searchUrl, callbacks);
  });

  // Setup click-outside listener
  setupClickOutsideListener(input, suggestions, () => {
    suggestions.innerHTML = '';
  });
}

/**
 * Setup worker search mode tabs (Email / DNI / Name)
 */
export function setupWorkerSearchModeTabs() {
  const modeGroup = document.getElementById('search-mode-group');

  if (!modeGroup) return;

  modeGroup.querySelectorAll('[data-mode]').forEach(btn => {
    btn.addEventListener('click', () => {
      const mode = btn.dataset.mode;

      // Update active button
      modeGroup.querySelectorAll('[data-mode]').forEach(b => {
        b.classList.toggle('active', b === btn);
        b.classList.toggle('btn-secondary', b === btn);
        b.classList.toggle('btn-outline-secondary', b !== btn);
      });

      // Show/hide search blocks
      document.querySelectorAll('.search-block').forEach(block => {
        block.classList.add('d-none');
      });
      const activeBlock = document.getElementById(`search-block-${mode}`);
      if (activeBlock) {
        activeBlock.classList.remove('d-none');
      }

      // Clear feedback and suggestions
      const feedback = document.getElementById('worker-lookup-feedback');
      const suggestions = document.getElementById('name-suggestions');

      clearFeedback(feedback);
      if (suggestions) {
        suggestions.innerHTML = '';
        suggestions.classList.add('d-none');
      }
    });
  });
}

/**
 * Initialize all worker management features
 * @param {string} lookupUrl - Worker lookup URL from Django template
 * @param {string} checkLastManagerUrl - Check last manager URL
 */
export function initWorkerManagement(lookupUrl, checkLastManagerUrl) {
  setupWorkerActionToggle();
  setupWorkerExactSearchListeners(lookupUrl, checkLastManagerUrl);
  setupWorkerAutocompleteSearch(lookupUrl, checkLastManagerUrl);
  setupWorkerSearchModeTabs();
}
