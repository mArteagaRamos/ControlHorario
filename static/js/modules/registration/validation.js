/**
 * validation.js
 * Validation functions for registration form
 *
 * Functions:
 * - requireCompany()
 * - checkAndHandleLastManager(userId, checkLastManagerUrl)
 */

/**
 * Validate that a company is selected
 * Shows feedback if no company found
 *
 * @param {Function} setFeedback - Feedback display function
 * @returns {boolean} True if company_id exists, false otherwise
 */
export function requireCompany(setFeedback) {
  const companyId = document.getElementById('company_id_input')?.value.trim();

  if (!companyId) {
    if (typeof setFeedback === 'function') {
      setFeedback('Primero busca y selecciona una empresa.', 'warning');
    }
    return false;
  }

  return true;
}

/**
 * Check if user is the last manager in the company
 * Shows warning and disables role selection if true
 *
 * @param {number} userId - User ID to check
 * @param {string} checkLastManagerUrl - URL for validation endpoint
 * @returns {Promise<boolean>} True if user is last manager
 */
export async function checkAndHandleLastManager(userId, checkLastManagerUrl) {
  const companyId = document.getElementById('company_id_input')?.value.trim();
  const roleSelect = document.getElementById('id_role');
  const warningDiv = document.getElementById('last-manager-warning');

  if (!companyId || !roleSelect || !warningDiv) {
    return false;
  }

  try {
    const checkUrl = new URL(checkLastManagerUrl, window.location.origin);
    checkUrl.searchParams.set('user_id', userId);
    checkUrl.searchParams.set('company_id', companyId);

    const res = await fetch(checkUrl.toString());
    const data = await res.json();

    if (data.is_last_manager) {
      // Show warning and disable role change
      warningDiv.classList.remove('d-none');
      roleSelect.disabled = true;
      roleSelect.classList.add('is-invalid');
      roleSelect.value = 'manager';  // Force value to manager
      return true;
    } else {
      // Hide warning and allow role change
      warningDiv.classList.add('d-none');
      roleSelect.disabled = false;
      roleSelect.classList.remove('is-invalid');
      return false;
    }
  } catch (error) {
    console.error('Error checking last manager status:', error);

    // On error: hide warning and allow role change
    warningDiv.classList.add('d-none');
    roleSelect.disabled = false;
    roleSelect.classList.remove('is-invalid');

    return false;
  }
}
