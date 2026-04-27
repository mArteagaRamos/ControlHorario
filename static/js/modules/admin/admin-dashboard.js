/**
 * Admin Dashboard - Entry point
 * Coordina la inicialización de todos los módulos del admin
 *
 * Este archivo será el central que importa y ejecuta todos los módulos
 * de administración en el orden correcto.
 *
 * FASE 3: Incluye company-search
 * FASE 4: Incluye worker-search
 * FASE 5: Incluye mode-toggle y search-tabs
 * FASE 6: Incluye pagination
 * FASE 7: Incluye modals
 */

import { initializeCompanySearch } from './company-search.js';
import { initializeWorkerSearch } from './worker-search.js';
import { initializeModeToggle } from './mode-toggle.js';
import { initializeSearchTabs } from './search-tabs.js';
import { initializePagination } from './pagination.js';
import { initializeModals } from './modals.js';

console.log('[AdminDashboard] Ready to load modules');

/**
 * Inicializa todos los módulos
 * Nota: Se ejecuta directamente sin DOMContentLoaded porque main.js
 * se carga como módulo al final del HTML (DOMContentLoaded ya ocurrió)
 */
export function initializeAdminDashboard() {
    console.log('[AdminDashboard] Initializing...');

    // FASE 5: Inicializar UI (debe ser primero para establecer estado inicial)
    try {
        initializeModeToggle();
    } catch (error) {
        console.error('[AdminDashboard] Error initializing mode toggle:', error);
    }

    try {
        initializeSearchTabs();
    } catch (error) {
        console.error('[AdminDashboard] Error initializing search tabs:', error);
    }

    // FASE 6: Inicializar paginación
    try {
        initializePagination();
    } catch (error) {
        console.error('[AdminDashboard] Error initializing pagination:', error);
    }

    // FASE 7: Inicializar modals
    try {
        initializeModals();
    } catch (error) {
        console.error('[AdminDashboard] Error initializing modals:', error);
    }

    // FASE 3: Inicializar búsqueda de empresas
    try {
        initializeCompanySearch();
    } catch (error) {
        console.error('[AdminDashboard] Error initializing company search:', error);
    }

    // FASE 4: Inicializar búsqueda de trabajadores
    try {
        initializeWorkerSearch();
    } catch (error) {
        console.error('[AdminDashboard] Error initializing worker search:', error);
    }

    // Los módulos posteriores irán aquí en fases siguientes
    console.log('[AdminDashboard] All modules initialized');
}

// FASE 8: La inicialización ahora es controlada por main.js
// (Se removió la auto-inicialización para evitar inicialización doble)

