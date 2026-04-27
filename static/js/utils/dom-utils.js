/**
 * Utilidades para manipulación del DOM
 * Simplifica operaciones comunes del DOM
 */

/**
 * Agrega una clase a un elemento
 */
export function addClass(element, className) {
    if (element) {
        element.classList.add(className);
    }
}

/**
 * Remueve una clase de un elemento
 */
export function removeClass(element, className) {
    if (element) {
        element.classList.remove(className);
    }
}

/**
 * Toggle una clase en un elemento
 */
export function toggleClass(element, className, force) {
    if (element) {
        element.classList.toggle(className, force);
    }
}

/**
 * Verifica si un elemento tiene una clase
 */
export function hasClass(element, className) {
    return element?.classList.contains(className) ?? false;
}

/**
 * Oculta un elemento (display: none)
 */
export function hide(element) {
    if (element) {
        element.style.display = 'none';
    }
}

/**
 * Muestra un elemento (remove display: none)
 */
export function show(element) {
    if (element) {
        element.style.display = '';
    }
}

/**
 * Toggle visibility de un elemento
 */
export function toggleVisibility(element, show = null) {
    if (!element) return;

    if (show === null) {
        // Toggle automático
        element.style.display = element.style.display === 'none' ? '' : 'none';
    } else if (show) {
        show(element);
    } else {
        hide(element);
    }
}

/**
 * Establece atributo de un elemento
 */
export function setAttribute(element, name, value) {
    if (element) {
        element.setAttribute(name, value);
    }
}

/**
 * Obtiene atributo de un elemento
 */
export function getAttribute(element, name) {
    return element?.getAttribute(name) ?? null;
}

/**
 * Establece múltiples atributos
 */
export function setAttributes(element, attrs) {
    if (element) {
        Object.entries(attrs).forEach(([key, value]) => {
            element.setAttribute(key, value);
        });
    }
}

/**
 * Limpia el HTML de un elemento
 */
export function clear(element) {
    if (element) {
        element.innerHTML = '';
    }
}

/**
 * Establece el HTML de un elemento
 */
export function setHtml(element, html) {
    if (element) {
        element.innerHTML = html;
    }
}

/**
 * Establece el texto de un elemento
 */
export function setText(element, text) {
    if (element) {
        element.textContent = text;
    }
}

/**
 * Obtiene el valor de un input
 */
export function getValue(element) {
    return element?.value ?? '';
}

/**
 * Establece el valor de un input
 */
export function setValue(element, value) {
    if (element) {
        element.value = value;
    }
}

/**
 * Enfoca un elemento
 */
export function focus(element) {
    if (element) {
        element.focus();
    }
}

/**
 * Verifica si un elemento está en el viewport
 */
export function isInViewport(element) {
    const rect = element?.getBoundingClientRect();
    if (!rect) return false;

    return (
        rect.top >= 0 &&
        rect.left >= 0 &&
        rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) &&
        rect.right <= (window.innerWidth || document.documentElement.clientWidth)
    );
}

/**
 * Scrollea a un elemento
 */
export function scrollToElement(element, behavior = 'smooth') {
    element?.scrollIntoView({ behavior });
}

/**
 * Event delegation - maneja eventos en elementos dinámicos
 * Uso: onEvent(document, 'click', '.my-class', (event, element) => {})
 */
export function onEvent(parent, eventType, selector, callback) {
    parent.addEventListener(eventType, (event) => {
        if (event.target.closest(selector)) {
            callback(event, event.target.closest(selector));
        }
    });
}

/**
 * Crea un elemento HTML
 */
export function createElement(tag, className = '', html = '') {
    const element = document.createElement(tag);
    if (className) {
        element.className = className;
    }
    if (html) {
        element.innerHTML = html;
    }
    return element;
}

/**
 * Agrega un elemento hijo
 */
export function appendChild(parent, child) {
    if (parent && child) {
        parent.appendChild(child);
    }
}

/**
 * Remueve un elemento
 */
export function removeElement(element) {
    element?.remove();
}
