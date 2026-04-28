# 📦 Plan de Modularización: manager_logs.html

## 🎯 Objetivo
Extraer todo el JavaScript del template `manager_logs.html` (excepto `clearDelegation()`) en módulos reutilizables bajo `/static/js/modules/team/`.

---

## 📋 Tareas por Completar

### FASE 1: Crear Módulos Base

- [ ] **1.1** Crear `manager-logs-pagination.js`
  - Funciones: `initializePaginationState()`, `updatePaginationView()`
  - Manejar estado de paginación para "registros" y "rechazadas"
  - Exportar: `initPaginationRegistros()`, `initPaginationRechazadas()`

- [ ] **1.2** Crear `manager-logs-filters.js`
  - Función: `fetchResultados(page)`
  - Función: Inicializar TomSelect
  - Función: Setup de listeners de filtros (.js-filter)
  - Exportar: `initFilters()`

- [ ] **1.3** Crear `manager-logs-export.js`
  - Función: `actualizarBotonExportar()` - para "registros"
  - Función: `actualizarBotonExportarRechazadas()` - para "rechazadas"
  - Manejar event delegation para checkboxes
  - Exportar: `initExportLogic()`

- [ ] **1.4** Crear `manager-logs-modals.js`
  - Función: `attachReopenModalListeners()` - todos los 4 modals
  - Manejar: modalResolver, modalEditar, modalAnular, modalEditarRechazada, modalEliminarRechazada
  - Exportar: `initModals()`

### FASE 2: Crear Inicializador Principal

- [ ] **2.1** Crear `manager-logs-init.js`
  - Importar todas las funciones de los módulos anteriores
  - Ejecutar setup dentro de `DOMContentLoaded`
  - Exportar: `initManagerLogs()`

### FASE 3: Verificar Funciones Comunes

- [ ] **3.1** Revisar si `modals.js` (utils) puede reutilizarse
  - Comparar con `attachReopenModalListeners()`
  - Si no aplica, mantener lógica custom en `manager-logs-modals.js`

- [ ] **3.2** Revisar si `fetch-client.js` puede simplificar `fetchResultados()`
  - Considerar usar `apiClient` en lugar de `fetch` directo

### FASE 4: Actualizar Template

- [ ] **4.1** Reemplazar script inline en `manager_logs.html`
  - Agregar imports de los módulos
  - Mantener SOLO `clearDelegation()` y su setup
  - Eliminar 250+ líneas de código JS

### FASE 5: Testing & Validación

- [ ] **5.1** Verificar que los filtros funcionan ✅
- [ ] **5.2** Verificar que la paginación funciona (ambas tablas) ✅
- [ ] **5.3** Verificar que los modals se abren y rellenan correctamente ✅
- [ ] **5.4** Verificar que el export de checkboxes funciona (ambas tablas) ✅
- [ ] **5.5** Verificar que clearDelegation() aún funciona ✅
- [ ] **5.6** Revisar consola de browser (sin errores) ✅

---

## 🔍 Detalles por Módulo

### `manager-logs-pagination.js`
**Responsabilidad:** Manejo de estado y vista de paginación

```javascript
// Estado para "registros"
paginationState = {
  currentPage: 1,
  ROWS_PER_PAGE: 5,
  allRows: []
}

// Estado para "rechazadas"  
rechazadasPaginationState = {
  currentPage: 1,
  ROWS_PER_PAGE: 5,
  allRows: []
}

// Exportar:
export function initPaginationRegistros()
export function initPaginationRechazadas()
export function updatePaginationView(state, container)
```

### `manager-logs-filters.js`
**Responsabilidad:** Filtrado de datos y actualización de tabla

```javascript
// Función principal que hace fetch y renderiza
function fetchResultados(page = 1) { ... }

// Setup de TomSelect
function initTomSelect() { ... }

// Setup de event listeners
function attachFilterListeners() { ... }

// Exportar:
export function initFilters()
```

### `manager-logs-export.js`
**Responsabilidad:** Lógica de selección de checkboxes y botones de export

```javascript
// Para tabla de registros
function actualizarBotonExportar() { ... }
function setupExportRegistros() { ... }

// Para tabla de rechazadas
function actualizarBotonExportarRechazadas() { ... }
function setupExportRechazadas() { ... }

// Exportar:
export function initExportLogic()
```

### `manager-logs-modals.js`
**Responsabilidad:** Listeners de modals y rellenado de campos

```javascript
// 5 modals diferentes
function setupModalResolver() { ... }
function setupModalEditar() { ... }
function setupModalAnular() { ... }
function setupModalEditarRechazada() { ... }
function setupModalEliminarRechazada() { ... }

// Exportar:
export function initModals()
```

### `manager-logs-init.js`
**Responsabilidad:** Orquestación y entry point

```javascript
import { initPaginationRegistros, initPaginationRechazadas } from './manager-logs-pagination.js';
import { initFilters } from './manager-logs-filters.js';
import { initExportLogic } from './manager-logs-export.js';
import { initModals } from './manager-logs-modals.js';

export function initManagerLogs() {
  // Ejecuta todo el setup
}
```

---

## 📍 Cambios en Template

**Template: `templates/team/manager_logs.html`**

```html
<!-- ANTES: ~250 líneas de <script> inline -->

<!-- DESPUÉS: -->
<script type="module">
  import { initManagerLogs } from '{% static "js/modules/team/manager-logs-init.js" %}';
  
  document.addEventListener('DOMContentLoaded', () => {
    initManagerLogs();
  });
</script>

<!-- MANTENER: -->
<script>
  async function clearDelegation() {
    const response = await fetch("{% url 'clear_delegated_worker' %}", {
      method: 'POST',
      headers: {'X-CSRFToken': '{{ csrf_token }}'}
    });
    if (response.ok) {
      location.reload();
    }
  }
</script>
```

---

## ⚠️ Puntos Críticos a Validar

1. **CSRF Token** - `fetchResultados()` lo obtiene del header XML-Requested-With ✅
2. **DOM Elements** - Todos los IDs deben existir en el template ✅
3. **Event Delegation** - Checkboxes se reemplazan al filtrar, usar `document.addEventListener` ✅
4. **Modal Data Attributes** - Los botones tienen data-* que rellenan el modal ✅
5. **TomSelect** - Depende de librería externa (ya cargada) ✅

---

## 🚀 Orden de Implementación Recomendado

1. **Primero: `manager-logs-pagination.js`** (más simple, sin dependencias)
2. **Segundo: `manager-logs-export.js`** (simple, independiente)
3. **Tercero: `manager-logs-modals.js`** (independiente)
4. **Cuarto: `manager-logs-filters.js`** (usa paginación, refuerza el estado)
5. **Quinto: `manager-logs-init.js`** (orquesta todo)
6. **Sexto: Actualizar template** (cuando todo esté listo)

---

## ✅ Señal de Completitud

El proyecto estará completo cuando:
- ✅ Todos los módulos existan en `/static/js/modules/team/`
- ✅ El template importa y ejecuta `initManagerLogs()`
- ✅ Consola sin errores 🔴 → 🟢
- ✅ Todas las 5 validaciones funcionales pasan
