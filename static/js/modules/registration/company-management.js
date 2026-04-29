/**
 * company-management.js
 * Company-specific management (mode toggle, search, form handling)
 *
 * Functions:
 * - setCompanyMode(mode)
 * - initCompanyManagement(lookupUrl)
 * - setupCompanyModeToggle()
 * - setupCompanySearchByTaxId(lookupUrl)
 * - setupCompanySearchByName(lookupUrl)
 * - setupCompanySearchModeTabs()
 */

import {
  handleCompanyExactSearch,
  handleCompanyAutocompleteSearch,
  setupClickOutsideListener,
  setFeedback as setSearchFeedback,
  clearFeedback,
} from './search-handler.js';

import { fillCompanyForm, clearFormBlock } from './form-utils.js';

/**
 * Toggle company mode between 'create' and 'select'
 * @param {string} mode - 'create' or 'select'
 */
export function setCompanyMode(mode) {
  const companyModeInput = document.getElementById('company_mode_input');
  const btnCompanyCreate = document.getElementById('btn-company-create');
  const btnCompanySelect = document.getElementById('btn-company-select');
  const companyLookupBlock = document.getElementById('company-lookup-block');
  const companyFormBlock = document.getElementById('company-form-block');
  const workerToggleGroup = document.getElementById('worker-toggle-group');
  const companyIdInput = document.getElementById('company_id_input');
  const companyLookupFeedback = document.getElementById('company-lookup-feedback');
  const workerLookupFeedback = document.getElementById('worker-lookup-feedback');

  if (!companyModeInput) return;

  companyModeInput.value = mode;
  const isCreate = mode === 'create';

  // Update button styles
  btnCompanyCreate?.classList.toggle('btn-primary', isCreate);
  btnCompanyCreate?.classList.toggle('btn-outline-primary', !isCreate);
  btnCompanySelect?.classList.toggle('btn-primary', !isCreate);
  btnCompanySelect?.classList.toggle('btn-outline-primary', isCreate);

  // Toggle visibility of blocks
  companyLookupBlock?.classList.toggle('d-none', isCreate);
  companyFormBlock?.classList.toggle('d-none', !isCreate);

  // In 'create' mode, hide worker toggles (direct form)
  workerToggleGroup?.classList.toggle('d-none', isCreate);

  // Clean up forms and lookups
  clearFormBlock('company-form-block');
  clearFormBlock('worker-form-block');
  clearFormBlock('worker-lookup-block');

  // Clear search inputs
  const cifInput = document.getElementById('cif-lookup-input');
  const companyNameInput = document.getElementById('company-lookup-name');
  const companySuggestions = document.getElementById('company-name-suggestions');

  if (cifInput) cifInput.value = '';
  if (companyNameInput) companyNameInput.value = '';
  if (companySuggestions) companySuggestions.innerHTML = '';

  // Clear feedback and hidden inputs
  clearFeedback(companyLookupFeedback);
  clearFeedback(workerLookupFeedback);
  if (companyIdInput) companyIdInput.value = '';

  // Hide suggestions
  companySuggestions?.classList.add('d-none');
}

/**
 * Setup company mode toggle buttons
 */
export function setupCompanyModeToggle() {
  const btnCompanyCreate = document.getElementById('btn-company-create');
  const btnCompanySelect = document.getElementById('btn-company-select');

  if (btnCompanyCreate) {
    btnCompanyCreate.addEventListener('click', () => setCompanyMode('create'));
  }

  if (btnCompanySelect) {
    btnCompanySelect.addEventListener('click', () => setCompanyMode('select'));
  }
}

/**
 * Setup company search by Tax ID (CIF/NIF)
 * @param {string} lookupUrl - Company lookup URL
 */
export function setupCompanySearchByTaxId(lookupUrl) {
  const btn = document.getElementById('btn-lookup-company');
  const input = document.getElementById('cif-lookup-input');
  const feedback = document.getElementById('company-lookup-feedback');

  if (!btn || !input) return;

  btn.addEventListener('click', async () => {
    const taxId = input.value.trim();

    const callbacks = {
      onSuccess: (data) => {
        fillCompanyForm(data);
      },
      onError: () => {
        const companyFormBlock = document.getElementById('company-form-block');
        const companyIdInput = document.getElementById('company_id_input');
        if (companyFormBlock) companyFormBlock.classList.add('d-none');
        if (companyIdInput) companyIdInput.value = '';
        clearFormBlock('company-form-block');
      },
      setFeedback: (text, type) => setSearchFeedback(feedback, text, type),
    };

    await handleCompanyExactSearch(taxId, lookupUrl, callbacks);
  });

  // Clear feedback when typing
  input.addEventListener('input', () => {
    clearFeedback(feedback);
    const companyIdInput = document.getElementById('company_id_input');
    const companyFormBlock = document.getElementById('company-form-block');
    if (companyIdInput) companyIdInput.value = '';
    if (companyFormBlock) companyFormBlock.classList.add('d-none');
    clearFormBlock('company-form-block');
    clearFormBlock('worker-form-block');
    clearFormBlock('worker-lookup-block');
  });
}

/**
 * Setup company search by name (autocomplete)
 * @param {string} lookupUrl - Company lookup URL
 */
export function setupCompanySearchByName(lookupUrl) {
  const input = document.getElementById('company-lookup-name');
  const suggestions = document.getElementById('company-name-suggestions');
  const feedback = document.getElementById('company-lookup-feedback');

  if (!input || !suggestions) return;

  input.addEventListener('input', () => {
    const query = input.value.trim();

    const callbacks = {
      onSuccess: () => {
        // Results rendered in handler
      },
      onError: () => {
        // Error handled in handler
      },
      setFeedback: (text, type) => setSearchFeedback(feedback, text, type),
      suggestionsElement: suggestions,
      onSuggestionClick: (company) => {
        fillCompanyForm(company);
        input.value = company.name;
      },
    };

    handleCompanyAutocompleteSearch(query, lookupUrl, callbacks);
  });

  // Setup click-outside listener
  setupClickOutsideListener(input, suggestions, () => {
    suggestions.innerHTML = '';
  });
}

/**
 * Setup company search mode tabs (CIF vs Name)
 */
export function setupCompanySearchModeTabs() {
  const modeGroup = document.getElementById('company-search-mode-group');

  if (!modeGroup) return;

  modeGroup.querySelectorAll('[data-cmode]').forEach(btn => {
    btn.addEventListener('click', () => {
      const mode = btn.dataset.cmode;

      // Update active button
      modeGroup.querySelectorAll('[data-cmode]').forEach(b => {
        b.classList.toggle('active', b === btn);
        b.classList.toggle('btn-secondary', b === btn);
        b.classList.toggle('btn-outline-secondary', b !== btn);
      });

      // Show/hide search blocks
      document.querySelectorAll('.company-search-block').forEach(block => {
        block.classList.add('d-none');
      });
      const activeBlock = document.getElementById(`company-search-block-${mode}`);
      if (activeBlock) {
        activeBlock.classList.remove('d-none');
      }

      // Clear feedback and suggestions
      const feedback = document.getElementById('company-lookup-feedback');
      const suggestions = document.getElementById('company-name-suggestions');

      clearFeedback(feedback);
      if (suggestions) {
        suggestions.innerHTML = '';
        suggestions.classList.add('d-none');
      }
    });
  });
}

/**
 * Initialize all company management features
 * @param {string} lookupUrl - Company lookup URL from Django template
 */
export function initCompanyManagement(lookupUrl) {
  setupCompanyModeToggle();
  setupCompanySearchByTaxId(lookupUrl);
  setupCompanySearchByName(lookupUrl);
  setupCompanySearchModeTabs();
}
