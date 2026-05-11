/**
 * Modals Module - Admin
 * Maneja los modals de Bootstrap para editar/eliminar empresas y trabajadores
 * Reutiliza helpers genéricos de utils/modals.js y utils/dom.js
 *
 * FASE 7: Extraer Modals
 * FASE 9: Refactorizar con helpers genéricos
 * FASE 10: Usar initializeSimpleModal para casos simples
 */

import { getAdminConfig } from '../../utils/config.js';
import { initializeEditWorkerModal, initializeSimpleModal } from '../../utils/modals.js';
import { toggleVisibility } from '../../utils/dom.js';

/**
 * Inicializa todos los modals
 */
export function initializeModals() {
    console.log('[Modals] Initializing...');

    // Usar helper genérico de utils
    initializeEditWorkerModal();

    // Funciones específicas de admin
    initializeDeleteWorkerModal();
    initializeDeleteCompanyModal();

    console.log('[Modals] All modals initialized');
}

/**
 * Modal de Eliminar Trabajador
 * Maneja la lógica compleja de mostrar checkboxes dinámicos según empresas
 */
function initializeDeleteWorkerModal() {
    const eliminarModal = document.getElementById('modalEliminarTrabajador');
    if (!eliminarModal) return;

    // Event listener para mostrar el modal
    eliminarModal.addEventListener('show.bs.modal', function(event) {
        const button = event.relatedTarget;
        if (!button) return;

        const userId = button.getAttribute('data-id');
        const nombre = button.getAttribute('data-nombrecompleto');
        const companiesJson = button.getAttribute('data-companies');
        let companies = [];

        // Parsear JSON de empresas
        try {
            companies = companiesJson ? JSON.parse(companiesJson) : [];
        } catch (e) {
            console.error('[Modals] Error parsing companies:', e);
        }

        // Asignar valores básicos
        document.getElementById('deleteUserId').value = userId;
        document.getElementById('deleteNombre').textContent = nombre;

        // Manejar secciones de empresas (una vs múltiples)
        const singleCompanySection = document.getElementById('singleCompanySection');
        const multipleCompaniesSection = document.getElementById('multipleCompaniesSection');
        const companiesCheckboxes = document.getElementById('companiesCheckboxes');

        if (companies.length === 1) {
            // Una empresa: mostrar directamente
            toggleVisibility(singleCompanySection, true);
            toggleVisibility(multipleCompaniesSection, false);
            document.getElementById('singleCompanyName').textContent = companies[0].name;
            document.getElementById('singleCompanyId').name = 'company_ids';
            document.getElementById('singleCompanyId').value = companies[0].id;
        } else if (companies.length > 1) {
            // Múltiples empresas: mostrar checkboxes
            toggleVisibility(singleCompanySection, false);
            toggleVisibility(multipleCompaniesSection, true);
            companiesCheckboxes.innerHTML = '';

            companies.forEach((company, index) => {
                const checkboxDiv = document.createElement('div');
                checkboxDiv.className = 'form-check';
                checkboxDiv.innerHTML = `
                    <input class="form-check-input company-checkbox" type="checkbox"
                           id="company_${company.id}" value="${company.id}"
                           data-company-name="${company.name}">
                    <label class="form-check-label" for="company_${company.id}">
                        ${company.name}
                    </label>
                `;
                companiesCheckboxes.appendChild(checkboxDiv);

                // Auto-check la primera empresa
                if (index === 0) {
                    checkboxDiv.querySelector('.form-check-input').checked = true;
                }
            });

            // Crear/actualizar input hidden de company_ids
            updateCompanyIdsInput();
        } else {
            // Ninguna empresa
            toggleVisibility(singleCompanySection, false);
            toggleVisibility(multipleCompaniesSection, false);
        }
    });

    // Event listener para cambios en checkboxes (delegado)
    document.addEventListener('change', function(e) {
        if (e.target.classList.contains('company-checkbox')) {
            updateCompanyIdsInput();
        }
    });

    // Event listener para validar al enviar el formulario
    const form = eliminarModal.querySelector('form');
    if (form) {
        form.addEventListener('submit', function(e) {
            const checkboxes = document.querySelectorAll('.company-checkbox');
            if (checkboxes.length > 0) {
                const anyChecked = Array.from(checkboxes).some(cb => cb.checked);
                if (!anyChecked) {
                    e.preventDefault();
                    alert('Por favor selecciona al menos una empresa');
                }
            }
        });
    }

    console.log('[Modals] Delete worker modal initialized');
}

/**
 * Actualiza el input hidden company_ids con los valores seleccionados
 */
function updateCompanyIdsInput() {
    const eliminarModal = document.getElementById('modalEliminarTrabajador');
    if (!eliminarModal) return;

    const multipleCompaniesSection = document.getElementById('multipleCompaniesSection');
    if (!multipleCompaniesSection || multipleCompaniesSection.classList.contains('d-none')) return;

    const checkboxes = document.querySelectorAll('.company-checkbox:checked');
    const form = eliminarModal.querySelector('form');
    if (!form) return;

    let companyIdsInput = form.querySelector('input[name="company_ids"]:not(#singleCompanyId)');

    if (!companyIdsInput) {
        companyIdsInput = document.createElement('input');
        companyIdsInput.type = 'hidden';
        companyIdsInput.name = 'company_ids';
        form.querySelector('.modal-body').appendChild(companyIdsInput);
    }

    const selectedIds = Array.from(checkboxes).map(cb => cb.value).join(',');
    companyIdsInput.value = selectedIds;
}

/**
 * Modal de Eliminar Empresa
 * Muestra información de la empresa y cantidad de empleados
 * Usa initializeSimpleModal con callback para obtener datos del backend
 */
function initializeDeleteCompanyModal() {
    initializeSimpleModal({
        modalId: 'modalEliminarEmpresa',
        mapping: {
            deleteCompanyId: 'companyId'
        },
        onShow: async (button) => {
            const companyId = button.getAttribute('data-company-id');
            const companyName = button.getAttribute('data-company-name');

            // Rellenar el nombre (es un elemento de texto, no input)
            document.getElementById('deleteCompanyName').textContent = companyName;

            // Obtener el count de miembros desde el backend
            try {
                const LOOKUP_COMPANY_URL = getAdminConfig('LOOKUP_COMPANY_URL');
                const response = await fetch(`${LOOKUP_COMPANY_URL}?company_id=${companyId}`);
                const data = await response.json();
                const memberCount = data.member_count || 0;
                document.getElementById('memberCountWarning').textContent = memberCount;
            } catch (e) {
                console.error('[Modals] Error fetching member count:', e);
                document.getElementById('memberCountWarning').textContent = '?';
            }
        },
        logName: '[Modals]'
    });

    console.log('[Modals] Delete company modal initialized');
}
