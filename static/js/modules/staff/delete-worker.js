/**
 * Staff Delete Worker Modal
 * Maneja la eliminación de trabajadores desde la tabla de staff
 * Versión simple - elimina solo de la empresa actual
 *
 * Usa initializeSimpleModal para el patrón común de modal simple
 */

import { initializeSimpleModal } from '../../utils/modals.js';

export function initializeDeleteWorkerModalStaff() {
    initializeSimpleModal({
        modalId: 'modalEliminar',
        buttonSelector: '.js-delete-btn',
        mapping: {
            deleteUserId: 'id',
            deleteNombre: 'nombrecompleto'
        },
        logName: '[Staff]'
    });

    console.log('[Staff] Delete worker modal initialized');
}

