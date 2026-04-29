/**
 * search-tabs.js
 *
 * Handles search mode tab switching for both worker and company searches.
 * - Worker search: Email / DNI / Nombre (3 tabs)
 * - Company search: CIF/NIF / Nombre (2 tabs)
 *
 * Template references:
 * - search-mode-group: worker search tabs container (línea 153)
 * - company-search-mode-group: company search tabs container (línea 61)
 * - search-block-email, search-block-dni, search-block-name: worker search blocks
 * - company-search-block-tax_id, company-search-block-name: company search blocks
 * - [data-mode]: worker search tab buttons
 * - [data-cmode]: company search tab buttons
 */

/**
 * Setup worker search mode tabs
 * @param {Function} onHideSuggestions - Callback to hide suggestions when switching tabs
 */
export function setupWorkerSearchModeTabs(onHideSuggestions) {
  const searchModeGroup = document.getElementById('search-mode-group');
  if (!searchModeGroup) return;

  searchModeGroup.querySelectorAll('[data-mode]').forEach(btn => {
    btn.addEventListener('click', () => {
      const mode = btn.dataset.mode;

      // Toggle active button styling
      searchModeGroup.querySelectorAll('[data-mode]').forEach(b => {
        b.classList.toggle('active', b === btn);
        b.classList.toggle('btn-secondary', b === btn);
        b.classList.toggle('btn-outline-secondary', b !== btn);
      });

      // Show/hide search blocks
      document.querySelectorAll('.search-block').forEach(block => {
        block.classList.add('d-none');
      });
      document.getElementById(`search-block-${mode}`)?.classList.remove('d-none');

      // Clear feedback and suggestions
      const workerLookupFeedback = document.getElementById('worker-lookup-feedback');
      if (workerLookupFeedback) {
        workerLookupFeedback.textContent = '';
      }

      if (onHideSuggestions) {
        onHideSuggestions();
      }
    });
  });
}

/**
 * Setup company search mode tabs
 * @param {Function} onHideSuggestions - Callback to hide company suggestions when switching tabs
 */
export function setupCompanySearchModeTabs(onHideSuggestions) {
  const companySearchModeGroup = document.getElementById('company-search-mode-group');
  if (!companySearchModeGroup) return;

  companySearchModeGroup.querySelectorAll('[data-cmode]').forEach(btn => {
    btn.addEventListener('click', () => {
      const mode = btn.dataset.cmode;

      // Toggle active button styling
      companySearchModeGroup.querySelectorAll('[data-cmode]').forEach(b => {
        b.classList.toggle('active', b === btn);
        b.classList.toggle('btn-secondary', b === btn);
        b.classList.toggle('btn-outline-secondary', b !== btn);
      });

      // Show/hide search blocks
      document.querySelectorAll('.company-search-block').forEach(block => {
        block.classList.add('d-none');
      });
      document.getElementById(`company-search-block-${mode}`)?.classList.remove('d-none');

      // Clear feedback and suggestions
      const companyLookupFeedback = document.getElementById('company-lookup-feedback');
      if (companyLookupFeedback) {
        companyLookupFeedback.textContent = '';
      }

      if (onHideSuggestions) {
        onHideSuggestions();
      }
    });
  });
}

/**
 * Initialize all search mode tabs
 * @param {Object} options - Configuration options
 * @param {Function} options.onWorkerSuggestionsHide - Callback when hiding worker suggestions
 * @param {Function} options.onCompanySuggestionsHide - Callback when hiding company suggestions
 */
export function initSearchModeTabs(options = {}) {
  const {
    onWorkerSuggestionsHide = null,
    onCompanySuggestionsHide = null
  } = options;

  setupWorkerSearchModeTabs(onWorkerSuggestionsHide);
  setupCompanySearchModeTabs(onCompanySuggestionsHide);
}
