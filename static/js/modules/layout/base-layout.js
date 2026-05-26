/**
 * Base Layout Module
 * Maneja la lógica común de layout: sidebar, mensajes y notificaciones
 *
 * Exports:
 * - initializeBaseLayout(): Inicializa todos los componentes
 * - showToast(message): Muestra una notificación
 */

import { toggleClass, addClass, removeClass, hasClass } from '../../utils/dom-utils.js';

console.log('[BaseLayout] Module loaded');

/**
 * Inicializa los tooltips de Bootstrap
 */
function initializeTooltips() {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    console.log('[BaseLayout] Tooltips initialized');
}

/**
 * Inicializa la lógica del sidebar en mobile
 */
function initializeSidebarToggle() {
    const toggleBtn = document.getElementById('menu-toggle');
    const sidebar = document.getElementById('sidebar');
    const closeBtn = document.getElementById('close-sidebar-btn');

    if (!sidebar) {
        console.warn('[BaseLayout] Sidebar element not found');
        return;
    }

    // Abrir menú
    toggleBtn?.addEventListener('click', () => {
        toggleClass(sidebar, 'active');
    });

    // Cerrar menú con la X
    closeBtn?.addEventListener('click', () => {
        removeClass(sidebar, 'active');
    });

    // Cerrar sidebar cuando se hace click en un link en mobile
    const navLinks = document.querySelectorAll('.sidebar .nav-link:not(.collapse-toggle)');
    navLinks.forEach(link => {
        link.addEventListener('click', () => {
            if (window.innerWidth < 768) {
                removeClass(sidebar, 'active');
            }
        });
    });

    // Cerrar sidebar al hacer clic fuera
    document.addEventListener('click', (e) => {
        if (window.innerWidth < 768 && hasClass(sidebar, 'active')) {
            if (!sidebar.contains(e.target) && !toggleBtn?.contains(e.target)) {
                removeClass(sidebar, 'active');
            }
        }
    });

    console.log('[BaseLayout] Sidebar toggle initialized');
}

/**
 * Inicializa la lógica de menús colapsables
 */
function initializeCollapsibleMenus() {
    const collapseLinks = document.querySelectorAll('.collapse-toggle');

    collapseLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const submenu = link.nextElementSibling;
            const chevron = link.querySelector('.chevron');

            if (submenu) {
                toggleClass(submenu, 'active');
            }
            if (chevron) {
                toggleClass(chevron, 'rotated');
            }
        });
    });

    console.log('[BaseLayout] Collapsible menus initialized');
}

/**
 * Inicializa el auto-cierre de mensajes de Django
 */
function initializeMessageAutoClose() {
    const container = document.getElementById('django-messages-container');

    if (!container) {
        return; // No hay mensajes en esta página
    }

    setTimeout(function() {
        if (container && container.parentElement) {
            addClass(container, 'closing');
            setTimeout(function() {
                container.remove();
            }, 300);
        }
    }, 5000);

    console.log('[BaseLayout] Message auto-close initialized');
}

/**
 * Muestra un toast/notificación
 * @param {string} message - Mensaje a mostrar
 */
export function showToast(message) {
    const toast = document.getElementById("toast");

    if (!toast) {
        console.warn('[BaseLayout] Toast element not found');
        return;
    }

    toast.innerText = message;
    removeClass(toast, "hidden");
    addClass(toast, "show");

    setTimeout(() => {
        removeClass(toast, "show");
        setTimeout(() => addClass(toast, "hidden"), 300);
    }, 3000);
}

/**
 * Inicializa todos los componentes de layout base
 */
export function initializeBaseLayout() {
    console.log('[BaseLayout] Initializing base layout...');

    try {
        initializeSidebarToggle();
    } catch (error) {
        console.error('[BaseLayout] Error initializing sidebar toggle:', error);
    }

    try {
        initializeCollapsibleMenus();
    } catch (error) {
        console.error('[BaseLayout] Error initializing collapsible menus:', error);
    }

    try {
        initializeMessageAutoClose();
    } catch (error) {
        console.error('[BaseLayout] Error initializing message auto-close:', error);
    }

    try {
        initializeTooltips();
    } catch (error) {
        console.error('[BaseLayout] Error initializing tooltips:', error);
    }

    console.log('[BaseLayout] All components initialized');
}

// Ejecutar automáticamente cuando el módulo se carga
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeBaseLayout);
} else {
    // Si el DOM ya está cargado (lo normal para scripts de módulo)
    initializeBaseLayout();
}
