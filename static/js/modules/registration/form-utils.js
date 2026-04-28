/**
 * form-utils.js
 * Utilities for form manipulation and clearing
 *
 * Functions:
 * - fillWorkerForm(data)
 * - fillCompanyForm(data)
 * - clearFormBlock(blockId)
 */

/**
 * Fill worker form fields with data
 * @param {Object} data - Worker data (id, email, username, surname, dni, status)
 */
export function fillWorkerForm(data) {
  const fields = {
    'id_email':    data.email    || '',
    'id_username': data.username || '',
    'id_surname':  data.surname  || '',
    'id_dni':      data.dni      || '',
    'id_status':   data.status   || '',
  };

  for (const [id, value] of Object.entries(fields)) {
    const el = document.getElementById(id);
    if (el) el.value = value;
  }
}

/**
 * Fill company form fields with data
 * @param {Object} data - Company data (id, tax_id, name, legal_name)
 */
export function fillCompanyForm(data) {
  document.getElementById('id_tax_id').value     = data.tax_id    || '';
  document.getElementById('id_name').value       = data.name      || '';
  document.getElementById('id_legal_name').value = data.legal_name || '';

  // Set company_id in hidden input
  const companyIdInput = document.getElementById('company_id_input');
  if (companyIdInput) {
    companyIdInput.value = data.id;
  }

  // Show company form block
  const companyFormBlock = document.getElementById('company-form-block');
  if (companyFormBlock) {
    companyFormBlock.classList.remove('d-none');
  }
}

/**
 * Clear all form fields within a block
 * @param {string} blockId - ID of the block to clear
 * @param {Function} onClearCallback - Optional callback after clearing
 */
export function clearFormBlock(blockId, onClearCallback) {
  const block = document.getElementById(blockId);
  if (!block) return;

  // Clear form inputs
  block.querySelectorAll('input:not([type="hidden"]), select, textarea').forEach(el => {
    if (el.type === 'checkbox' || el.type === 'radio') {
      el.checked = false;
    } else {
      el.value = '';
    }
  });

  // Special handling for worker-form-block
  if (blockId === 'worker-form-block') {
    const warningDiv = document.getElementById('last-manager-warning');
    const roleSelect = document.getElementById('id_role');

    if (warningDiv) {
      warningDiv.classList.add('d-none');
    }
    if (roleSelect) {
      roleSelect.disabled = false;
      roleSelect.classList.remove('is-invalid');
    }
  }

  // Execute callback if provided
  if (typeof onClearCallback === 'function') {
    onClearCallback();
  }
}
