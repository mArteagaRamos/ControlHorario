/**
 * ui-utils.js
 * Utilidades compartidas para UI (tabs, botones, feedback)
 * Centraliza patrones repetidos en admin y registration modules
 */

/**
 * Toggle botones exclusivos (solo uno activo)
 * Útil para: create/select, registrar/seleccionar empresa/trabajador
 *
 * @param {HTMLElement} btnPrimary - Botón "activo"
 * @param {HTMLElement} btnSecondary - Botón "inactivo"
 * @param {boolean} isPrimary - Si true, activa btnPrimary; si false, activa btnSecondary
 */
export function toggleExclusiveButtons(btnPrimary, btnSecondary, isPrimary) {
  if (btnPrimary) {
    btnPrimary.classList.toggle('btn-primary', isPrimary);
    btnPrimary.classList.toggle('btn-outline-primary', !isPrimary);
  }

  if (btnSecondary) {
    btnSecondary.classList.toggle('btn-primary', !isPrimary);
    btnSecondary.classList.toggle('btn-outline-primary', isPrimary);
  }
}

/**
 * Toggle botones con estilos secondary (usado en tabs de búsqueda)
 * @param {HTMLElement} btn - Botón a actualizar
 * @param {boolean} isActive - Si true, aplica btn-secondary; si false, btn-outline-secondary
 */
export function toggleSecondaryButton(btn, isActive) {
  if (!btn) return;
  btn.classList.toggle('active', isActive);
  btn.classList.toggle('btn-secondary', isActive);
  btn.classList.toggle('btn-outline-secondary', !isActive);
}

/**
 * Toggle visibilidad de bloques basado en tabs
 * Patrón: mostrar un bloque, esconder los demás
 *
 * @param {HTMLElement} tabsContainer - Contenedor de botones de tabs
 * @param {string} tabAttribute - Atributo del botón (ej: 'data-cmode', 'data-mode')
 * @param {string} selectedValue - Valor del tab seleccionado
 * @param {string} blockSelector - Selector CSS para los bloques (ej: '.company-search-block')
 */
export function toggleTabBlocks(tabsContainer, tabAttribute, selectedValue, blockSelector) {
  if (!tabsContainer) return;

  // Actualizar estilos de botones
  tabsContainer.querySelectorAll(`[${tabAttribute}]`).forEach(btn => {
    const isActive = btn.dataset[tabAttribute.replace('data-', '')] === selectedValue;
    toggleSecondaryButton(btn, isActive);
  });

  // Mostrar/esconder bloques
  document.querySelectorAll(blockSelector).forEach(block => {
    block.classList.add('d-none');
  });

  const activeBlock = document.getElementById(`${blockSelector.slice(1)}-${selectedValue}`);
  if (activeBlock) {
    activeBlock.classList.remove('d-none');
  }
}

/**
 * Establecer mensaje de feedback (error, éxito, advertencia)
 *
 * @param {HTMLElement} element - Elemento donde mostrar el feedback
 * @param {string} text - Texto del mensaje
 * @param {string} type - Tipo: 'success', 'danger', 'warning', '' (limpia)
 */
export function setFeedback(element, text, type = '') {
  if (!element) return;

  element.textContent = text;
  element.className = text ? `form-text text-${type}` : '';
}

/**
 * Limpiar feedback
 * @param {HTMLElement} element - Elemento a limpiar
 */
export function clearFeedback(element) {
  setFeedback(element, '', '');
}

/**
 * Validar que input tenga longitud mínima
 * Típicamente para búsquedas con autocomplete
 *
 * @param {string} query - Texto a validar
 * @param {number} minLength - Longitud mínima (default: 2)
 * @returns {boolean}
 */
export function isValidSearchQuery(query, minLength = 2) {
  return query && query.length >= minLength;
}

/**
 * Limpiar/esconder elemento con clase d-none
 * @param {HTMLElement} element - Elemento a esconder
 */
export function hideElement(element) {
  element?.classList.add('d-none');
}

/**
 * Mostrar/revelar elemento removiendo clase d-none
 * @param {HTMLElement} element - Elemento a mostrar
 */
export function showElement(element) {
  element?.classList.remove('d-none');
}

/**
 * Toggle visibilidad de elemento
 * @param {HTMLElement} element - Elemento a toggle
 * @param {boolean} show - Si true muestra, si false esconde. Si undefined, toggle.
 */
export function toggleElement(element, show = undefined) {
  if (!element) return;

  if (show === undefined) {
    element.classList.toggle('d-none');
  } else {
    element.classList.toggle('d-none', !show);
  }
}
