/**
 * Tests para funciones de DOM utilities
 * Ejecutar con: npm test
 */

import { toggleVisibility, showElement, hideElement, toggleAllVisibleCheckboxes, countCheckedCheckboxes } from './dom.js';

describe('DOM Utilities', () => {
    let testElement;

    beforeEach(() => {
        // Crear elemento de prueba
        testElement = document.createElement('div');
        testElement.id = 'test-element';
        document.body.appendChild(testElement);
    });

    afterEach(() => {
        // Limpiar
        document.body.removeChild(testElement);
    });

    describe('toggleVisibility', () => {
        test('debe agregar d-none cuando show=false', () => {
            testElement.className = '';
            toggleVisibility(testElement, false);
            expect(testElement.classList.contains('d-none')).toBe(true);
        });

        test('debe remover d-none cuando show=true', () => {
            testElement.className = 'd-none';
            toggleVisibility(testElement, true);
            expect(testElement.classList.contains('d-none')).toBe(false);
        });

        test('debe funcionar con ID string', () => {
            toggleVisibility('test-element', false);
            expect(testElement.classList.contains('d-none')).toBe(true);
        });

        test('debe retornar silenciosamente si elemento no existe', () => {
            expect(() => toggleVisibility('no-existe', true)).not.toThrow();
        });
    });

    describe('showElement / hideElement', () => {
        test('showElement debe mostrar elemento', () => {
            testElement.className = 'd-none';
            showElement(testElement);
            expect(testElement.classList.contains('d-none')).toBe(false);
        });

        test('hideElement debe ocultar elemento', () => {
            testElement.className = '';
            hideElement(testElement);
            expect(testElement.classList.contains('d-none')).toBe(true);
        });
    });

    describe('toggleAllVisibleCheckboxes', () => {
        let container, row1, row2, row3;

        beforeEach(() => {
            container = document.createElement('div');

            // Crear 3 filas con checkboxes
            row1 = document.createElement('tr');
            row1.innerHTML = '<td><input type="checkbox" class="select-row"></td></td>';

            row2 = document.createElement('tr');
            row2.innerHTML = '<td><input type="checkbox" class="select-row"></td></td>';
            row2.className = 'd-none'; // Esta está oculta

            row3 = document.createElement('tr');
            row3.innerHTML = '<td><input type="checkbox" class="select-row"></td></td>';

            container.appendChild(row1);
            container.appendChild(row2);
            container.appendChild(row3);
            document.body.appendChild(container);
        });

        afterEach(() => {
            document.body.removeChild(container);
        });

        test('debe marcar solo checkboxes visibles', () => {
            toggleAllVisibleCheckboxes('.select-row', 'tr', true);

            const checkboxes = container.querySelectorAll('.select-row');
            expect(checkboxes[0].checked).toBe(true);  // visible
            expect(checkboxes[1].checked).toBe(false); // oculta
            expect(checkboxes[2].checked).toBe(true);  // visible
        });

        test('debe desmarcar solo checkboxes visibles', () => {
            // Marcar todos primero
            container.querySelectorAll('.select-row').forEach(cb => cb.checked = true);

            // Desmarcar solo visibles
            toggleAllVisibleCheckboxes('.select-row', 'tr', false);

            const checkboxes = container.querySelectorAll('.select-row');
            expect(checkboxes[0].checked).toBe(false);
            expect(checkboxes[1].checked).toBe(true);  // oculta, debería mantenerse
            expect(checkboxes[2].checked).toBe(false);
        });
    });

    describe('countCheckedCheckboxes', () => {
        let container;

        beforeEach(() => {
            container = document.createElement('div');

            const row1 = document.createElement('tr');
            row1.innerHTML = '<td><input type="checkbox" class="select-row" checked></td></td>';

            const row2 = document.createElement('tr');
            row2.className = 'd-none';
            row2.innerHTML = '<td><input type="checkbox" class="select-row" checked></td></td>';

            const row3 = document.createElement('tr');
            row3.innerHTML = '<td><input type="checkbox" class="select-row"></td></td>';

            container.appendChild(row1);
            container.appendChild(row2);
            container.appendChild(row3);
            document.body.appendChild(container);
        });

        afterEach(() => {
            document.body.removeChild(container);
        });

        test('debe contar todos los checkboxes marcados', () => {
            const count = countCheckedCheckboxes('.select-row', false);
            expect(count).toBe(2); // Dos marcados
        });

        test('debe contar solo visibles cuando onlyVisible=true', () => {
            const count = countCheckedCheckboxes('.select-row', true);
            expect(count).toBe(1); // Una visible marcada (la segunda está oculta)
        });
    });
});
