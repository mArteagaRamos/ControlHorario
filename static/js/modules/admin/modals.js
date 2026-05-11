/**
 * Modals Module - Admin
 * Maneja los modals de Bootstrap para editar/eliminar empresas y trabajadores
 * Reutiliza helpers genéricos de utils/modals.js
 *
 * FASE 7: Extraer Modals
 * FASE 9: Refactorizar con helpers genéricos
 * FASE 10: Usar initializeSimpleModal para casos simples
 */

import { getAdminConfig } from '../../utils/config.js';
import { initializeEditWorkerModal, initializeSimpleModal } from '../../utils/modals.js';

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
 * Modal de Eliminar Trabajador (Admin Dashboard)
 * Muestra información del trabajador y cantidad de empresas
 * Usa helper genérico con callback para obtener datos del backend
 */
function initializeDeleteWorkerModal() {
    initializeSimpleModal({
        modalId: 'modalEliminarTrabajador',
        mapping: {
            deleteUserId: 'id'
        },
        onShow: async (button) => {
            const userId = button.getAttribute('data-id');
            const nombre = button.getAttribute('data-nombrecompleto');

            // Rellenar nombre
            document.getElementById('deleteNombre').textContent = nombre;

            // Obtener cantidad de empresas desde el backend
            try {
                const response = await fetch(`/api/user-companies-count/?user_id=${userId}`);
                const data = await response.json();
                const companyCount = data.company_count || 0;
                document.getElementById('memberCountWarning').textContent = companyCount;
            } catch (e) {
                console.error('[Modals] Error fetching company count:', e);
                document.getElementById('memberCountWarning').textContent = '?';
            }
        },
        logName: '[Modals]'
    });

    console.log('[Modals] Delete worker modal initialized');
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
