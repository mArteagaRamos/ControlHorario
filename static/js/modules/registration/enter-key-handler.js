/**
 * enter-key-handler.js
 *
 * Handles ENTER key behavior in search and form inputs.
 * - search-input: executes search when ENTER is pressed
 * - form-input: submits form when ENTER is pressed
 * - autocomplete inputs: prevents ENTER from closing dropdown
 *
 * Template references (líneas 813-905):
 * - .search-input: inputs with data-search-action attribute
 * - .form-input: regular form inputs
 * - #worker-lookup-name, #company-lookup-name: autocomplete inputs
 * - #name-suggestions, #company-name-suggestions: autocomplete dropdowns
 */

/**
 * Checks if input is within an active autocomplete dropdown
 * @param {HTMLElement} inputEl - The input element to check
 * @returns {boolean} - True if dropdown is open
 */
export function isWithinActiveAutocomplete(inputEl) {
  const autocompletes = [
    { input: '#worker-lookup-name', dropdown: '#name-suggestions' },
    { input: '#company-lookup-name', dropdown: '#company-name-suggestions' },
  ];

  for (const { input, dropdown } of autocompletes) {
    const inputEl2 = document.querySelector(input);
    const dropdownEl = document.querySelector(dropdown);

    if (inputEl === inputEl2 && dropdownEl && !dropdownEl.classList.contains('d-none')) {
      return true; // Dropdown is open
    }
  }

  return false;
}

/**
 * Executes the appropriate search based on data-search-action
 * @param {HTMLElement} inputEl - The input element that triggered search
 */
export function executeSearch(inputEl) {
  const actionTarget = inputEl.dataset.searchAction;

  if (!actionTarget) return; // No action defined

  // Find associated button and click it
  const button = document.getElementById(actionTarget)
              || inputEl.closest('.input-group')?.querySelector('[data-field]');

  if (button) {
    button.click();
  }
}

/**
 * Setup ENTER key handlers for search inputs
 * Attaches keydown listener to all search inputs
 */
export function setupSearchInputs() {
  document.querySelectorAll('.search-input').forEach(input => {
    input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        executeSearch(input);
      }
    });
  });
}

/**
 * Initialize global ENTER key handling
 * - Prevents ENTER in search inputs from bubbling
 * - Prevents ENTER in form inputs from unwanted form submission
 * - Does nothing if within active autocomplete
 */
export function initEnterKeyHandling() {
  // Global ENTER key listener for all inputs
  document.addEventListener('keydown', (e) => {
    // Only act on ENTER key
    if (e.key !== 'Enter') return;

    const input = e.target;

    // If input is within an active autocomplete, ignore
    if (isWithinActiveAutocomplete(input)) return;

    // ── SEARCH INPUT: execute search ──
    if (input.classList.contains('search-input')) {
      e.preventDefault();
      executeSearch(input);
      return;
    }

    // ── FORM INPUT: execute submit
    if (input.classList.contains('form-input')) {
      e.preventDefault();
      const form = input.closest('form');
      if (form) form.querySelector('button[type="submit"]')?.click();
      return;
    }
  });

  // Setup individual search input handlers (redundant with global, but explicit)
  setupSearchInputs();
}
