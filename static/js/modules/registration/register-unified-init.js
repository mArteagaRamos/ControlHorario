/**
 * register-unified-init.js
 *
 * Main entry point for register_unified.html
 * Orchestrates initialization of all registration modules (FASE 2, 3, 4)
 *
 * Modules imported and orchestrated:
 * - FASE 2: form-utils, password-generator, validation
 * - FASE 3: search-handler, company-management, worker-management
 * - FASE 4: auditor-toggle, search-tabs, enter-key-handler
 */

// ═══════════════════════════════════════════════════════════════════════════
// IMPORTS - All registration modules
// ═══════════════════════════════════════════════════════════════════════════

// FASE 2: Base utilities
import { fillWorkerForm, fillCompanyForm, clearFormBlock } from './form-utils.js';
import { generatePassword } from './password-generator.js';

// FASE 3: Search and management
import { initCompanyManagement, setCompanyMode } from './company-management.js';
import { initWorkerManagement, setWorkerAction } from './worker-management.js';

// FASE 4: UI modules
import { initAuditorToggle, hideAuditorOptions, showAuditorOptions } from './auditor-toggle.js';
import { initSearchModeTabs } from './search-tabs.js';
import { initEnterKeyHandling } from './enter-key-handler.js';

// ═══════════════════════════════════════════════════════════════════════════
// UTILITY FUNCTIONS - Shared across modules
// ═══════════════════════════════════════════════════════════════════════════

/**
 * Hide worker name suggestions dropdown
 */
function hideSuggestions() {
  const suggestionsList = document.getElementById('name-suggestions');
  if (suggestionsList) {
    suggestionsList.classList.add('d-none');
    suggestionsList.innerHTML = '';
  }
}

/**
 * Hide company name suggestions dropdown
 */
function hideCompanySuggestions() {
  const companySuggestions = document.getElementById('company-name-suggestions');
  if (companySuggestions) {
    companySuggestions.classList.add('d-none');
    companySuggestions.innerHTML = '';
  }
}

/**
 * Setup password generator button and auto-generate on load
 */
function setupPasswordGenerator() {
  const btnGenPassword = document.getElementById('btn-gen-password');
  const passwordInput = document.getElementById('id_password');

  // Button click handler
  if (btnGenPassword) {
    btnGenPassword.addEventListener('click', () => {
      if (passwordInput) {
        passwordInput.value = generatePassword();
      }
    });
  }

  // Auto-generate on page load if in 'create' mode
  if (passwordInput && !passwordInput.value) {
    passwordInput.value = generatePassword();
  }
}

/**
 * Storage for exported functions from modules
 * Used by setupInitialState to access functions
 */
const initModuleExports = {};

// ═══════════════════════════════════════════════════════════════════════════
// MAIN INITIALIZATION FUNCTION
// ═══════════════════════════════════════════════════════════════════════════

/**
 * Initialize all registration modules
 * Called from register_unified.html on DOMContentLoaded
 *
 * This function:
 * 1. Gets URLs from window (defined in template)
 * 2. Initializes all module systems in proper order
 * 3. Sets up utility functions
 */
export function initRegisterUnified() {
  // Get URLs from template (defined as window variables)
  const LOOKUP_COMPANY_URL = window.LOOKUP_COMPANY_URL;
  const LOOKUP_USER_URL = window.LOOKUP_USER_URL;
  const CHECK_LAST_MANAGER_URL = window.CHECK_LAST_MANAGER_URL;

  // Validate URLs exist
  if (!LOOKUP_COMPANY_URL || !LOOKUP_USER_URL || !CHECK_LAST_MANAGER_URL) {
    console.error('Missing required URLs in window scope', {
      LOOKUP_COMPANY_URL,
      LOOKUP_USER_URL,
      CHECK_LAST_MANAGER_URL,
    });
    return;
  }

  // ─────────────────────────────────────────────────────────────────────────
  // PHASE 1: Initialize password generator (no dependencies)
  // ─────────────────────────────────────────────────────────────────────────
  setupPasswordGenerator();

  // ─────────────────────────────────────────────────────────────────────────
  // PHASE 2: Initialize ENTER key handling (no dependencies)
  // ─────────────────────────────────────────────────────────────────────────
  initEnterKeyHandling();

  // ─────────────────────────────────────────────────────────────────────────
  // PHASE 3: Initialize search mode tabs with callbacks
  // ─────────────────────────────────────────────────────────────────────────
  initSearchModeTabs({
    onWorkerSuggestionsHide: hideSuggestions,
    onCompanySuggestionsHide: hideCompanySuggestions,
  });

  // ─────────────────────────────────────────────────────────────────────────
  // PHASE 4: Initialize auditor toggle
  // ─────────────────────────────────────────────────────────────────────────
  initAuditorToggle();

  // ─────────────────────────────────────────────────────────────────────────
  // PHASE 5: Initialize company management with lookup URL
  // ─────────────────────────────────────────────────────────────────────────
  initCompanyManagement(LOOKUP_COMPANY_URL);

  // ─────────────────────────────────────────────────────────────────────────
  // PHASE 6: Initialize worker management with lookup URLs
  // ─────────────────────────────────────────────────────────────────────────
  initWorkerManagement(LOOKUP_USER_URL, CHECK_LAST_MANAGER_URL);

  // ─────────────────────────────────────────────────────────────────────────
  // PHASE 7: Apply initial styles from form values
  // ─────────────────────────────────────────────────────────────────────────
  const companyModeInput = document.getElementById('company_mode_input');
  const workerActionInput = document.getElementById('worker_action_input');

  if (companyModeInput) {
    setCompanyMode(companyModeInput.value || 'create');
  }

  if (workerActionInput) {
    setWorkerAction(workerActionInput.value || 'create');
  }

  // ─────────────────────────────────────────────────────────────────────────
  // Log success
  // ─────────────────────────────────────────────────────────────────────────
  console.log('✅ Register Unified: All modules initialized successfully');
}

// ═══════════════════════════════════════════════════════════════════════════
// AUTO-EXECUTE ON DOMContentLoaded
// ═══════════════════════════════════════════════════════════════════════════

/**
 * Check if DOM is ready and initialize
 * If already loaded, initialize immediately
 * Otherwise, wait for DOMContentLoaded
 */
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    console.log('📋 DOMContentLoaded triggered - initializing register unified...');
    initRegisterUnified();
  });
} else {
  // DOM is already ready (e.g., if this script is loaded after DOM is ready)
  console.log('📋 DOM already ready - initializing register unified...');
  initRegisterUnified();
}

// ═══════════════════════════════════════════════════════════════════════════
// EXPORTS for template
// ═══════════════════════════════════════════════════════════════════════════

// Export utility functions that might be needed in template
export { hideSuggestions, hideCompanySuggestions };
