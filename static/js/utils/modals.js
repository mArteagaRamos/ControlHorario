/**
 * Generic Modals Utilities
 * Funciones reutilizables para manejo de modals y forms
 *
 * FASE 1: Extraer helpers comunes
 * FASE 2: Agregar inicializador genérico de modals simples
 */

/**
 * Rellena campos de un formulario desde dataset de un elemento
 * Mapea dataset attributes a campos del formulario
 *
 * @param {Object} mapping - { formFieldId: 'datasetKey', ... }
 * @param {HTMLElement} sourceElement - elemento con los datos en dataset
 * @example
 * fillFormFromDataset({
 *   'editNombre': 'nombre',
 *   'editEmail': 'email'
 * }, button);
 */
export function fillFormFromDataset(mapping, sourceElement) {
    Object.entries(mapping).forEach(([fieldId, datasetKey]) => {
        const field = document.getElementById(fieldId);
        if (field) {
            const value = sourceElement.dataset[datasetKey] || '';
            // Si es un input, asigna el valor
            if (field.tagName === 'INPUT' || field.tagName === 'SELECT' || field.tagName === 'TEXTAREA') {
                field.value = value;
            } else {
                // Si es otro elemento (span, strong, div, etc.), asigna como texto
                field.textContent = value;
            }
        }
    });
}

/**
 * Modal de Editar Trabajador
 * Rellena los campos del formulario cuando se abre el modal
 * Funciona en cualquier contexto (admin, staff, etc.)
 * - admin_dashboard: solo campos globales del usuario
 * - staff: incluye role (membresía en la empresa)
 */
export function initializeEditWorkerModal() {
    const editarModal = document.getElementById('modalEditarTrabajador');
    if (!editarModal) return;

    editarModal.addEventListener('show.bs.modal', function(event) {
        const button = event.relatedTarget;
        if (!button) return;

        // Mapeo de campos para editar trabajador
        const mapping = {
            editUserId: 'id',
            editNombre: 'nombre',
            editApellidos: 'apellidos',
            editEmail: 'email',
            editEstado: 'estado'
        };

        fillFormFromDataset(mapping, button);

        // editDni es opcional (puede no existir en admin_dashboard)
        const editDniField = document.getElementById('editDni');
        if (editDniField) {
            editDniField.value = button.dataset.dni || '';
        }

        // editRol es opcional (solo existe en staff.html, no en admin_dashboard)
        const editRolField = document.getElementById('editRol');
        if (editRolField) {
            editRolField.value = button.dataset.rol || 'employee';
        }
    });

    console.log('[Modals] Edit worker modal initialized');
}

/**
 * Inicializador genérico para modals simples
 * Maneja el patrón común: mostrar modal → obtener datos del button → rellenar campos
 *
 * @param {Object} options - Configuración del modal
 * @param {string} options.modalId - ID del modal elemento
 * @param {Object} options.mapping - Mapeo de campos { fieldId: 'dataAttribute' }
 * @param {string} options.buttonSelector - Selector para el button dentro del relatedTarget (opcional)
 * @param {Function} options.onShow - Callback para lógica adicional al mostrar (opcional)
 * @param {string} options.logName - Nombre para logs (ej: "[Modals]") (opcional)
 *
 * @example
 * // Caso simple: solo rellenar campos
 * initializeSimpleModal({
 *   modalId: 'modalEliminar',
 *   buttonSelector: '.js-delete-btn',
 *   mapping: {
 *     deleteUserId: 'id',
 *     deleteNombre: 'nombrecompleto'
 *   }
 * });
 *
 * @example
 * // Con callback para lógica adicional
 * initializeSimpleModal({
 *   modalId: 'modalEliminarEmpresa',
 *   mapping: {
 *     deleteCompanyId: 'companyId',
 *     deleteCompanyName: 'companyName'
 *   },
 *   onShow: async (button, modal) => {
 *     const companyId = button.getAttribute('data-company-id');
 *     const response = await fetch(`/api/company/${companyId}`);
 *     const data = await response.json();
 *     document.getElementById('memberCount').textContent = data.member_count;
 *   }
 * });
 */
export function initializeSimpleModal(options) {
    const {
        modalId,
        mapping = {},
        buttonSelector = undefined,
        onShow = null,
        logName = '[Modals]'
    } = options;

    const modal = document.getElementById(modalId);
    if (!modal) return;

    modal.addEventListener('show.bs.modal', async function(event) {
        // Obtener el button que disparó el modal
        let button;
        if (buttonSelector) {
            button = event.relatedTarget?.closest(buttonSelector);
        } else {
            button = event.relatedTarget;
        }

        if (!button) return;

        // Rellenar campos simples
        fillFormFromDataset(mapping, button);

        // Ejecutar callback si existe
        if (onShow) {
            try {
                await onShow(button, modal);
            } catch (error) {
                console.error(`${logName} Error in onShow callback:`, error);
            }
        }
    });

    console.log(`${logName} Simple modal '${modalId}' initialized`);
}

