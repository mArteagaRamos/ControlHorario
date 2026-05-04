/**
 * auditor-toggle.js
 *
 * Handles auditor checkbox toggle and role field visibility.
 * - Toggle 'Opciones avanzadas' button to show/hide auditor checkbox
 * - When auditor is checked: disable role field and set to 'employee'
 * - When auditor is unchecked: enable role field
 *
 * Template references (líneas 217-239):
 * - btn-toggle-auditor: button to toggle auditor options
 * - auditor-checkbox-block: container for auditor checkbox
 * - id_is_auditor: auditor checkbox input
 * - id_role: role select field
 */

/**
 * Initialize auditor toggle functionality
 */
export function initAuditorToggle() {
  const btnToggleAuditor = document.getElementById('btn-toggle-auditor');
  const auditorCheckboxBlock = document.getElementById('auditor-checkbox-block');
  const auditorCheckbox = document.getElementById('id_is_auditor');
  const roleSelect = document.getElementById('id_role');

  // Toggle button: show/hide auditor checkbox block
  if (btnToggleAuditor) {
    btnToggleAuditor.addEventListener('click', (e) => {
      e.preventDefault();
      auditorCheckboxBlock?.classList.toggle('d-none');
    });
  }

  // Auditor checkbox: manage role field visibility/disable
  if (auditorCheckbox) {
    auditorCheckbox.addEventListener('change', () => {
      if (auditorCheckbox.checked) {
        // Auditor checked: hide role field and set to employee
        if (roleSelect) {
          roleSelect.disabled = true;
          roleSelect.value = 'employee';
          roleSelect.closest('.mb-3')?.classList.add('d-none');
        }
      } else {
        // Auditor unchecked: show and enable role field
        if (roleSelect) {
          roleSelect.disabled = false;
          roleSelect.closest('.mb-3')?.classList.remove('d-none');
        }
      }
    });
  }
}

/**
 * Hide auditor block and uncheck auditor checkbox
 * Called from worker-management.js when toggling to 'select' mode
 */
export function hideAuditorOptions() {
  const auditorCheckboxBlock = document.getElementById('auditor-checkbox-block');
  const auditorCheckbox = document.getElementById('id_is_auditor');
  const btnToggleAuditor = document.getElementById('btn-toggle-auditor');

  if (auditorCheckboxBlock) {
    auditorCheckboxBlock.classList.add('d-none');
    btnToggleAuditor?.classList.add('d-none');
  }

  if (auditorCheckbox) {
    auditorCheckbox.checked = false;
  }
}

/**
 * Show auditor block and toggle button (called in 'create' mode)
 */
export function showAuditorOptions() {
  const btnToggleAuditor = document.getElementById('btn-toggle-auditor');

  if (btnToggleAuditor) {
    btnToggleAuditor.classList.remove('d-none');
  }
}
