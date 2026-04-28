# 📅 Plan de Modularización Híbrida: calendar.html

## 🎯 Objetivo
Refactorizar `templates/dashboard/calendar.html` de manera **híbrida**: manteniendo la inicialización crítica de FullCalendar en el template mientras se extraen funciones reutilizables a módulos especializados.

---

## ⚠️ ¿Por qué es HÍBRIDA y no completa?

### Razones Técnicas

**Manager Logs (✅ Modularización Completa):**
- Funciones independientes
- Sin librerías externas complejas
- Estado simple y local

**Calendar (⚠️ Modularización Híbrida):**
- FullCalendar requiere referencia global `calendarObj` que múltiples funciones usan
- Muchas funciones generan HTML dinámico que invoca `onclick="functionName()"`
- Estado compartido complejo (currentUserId, _leaveDataMap, selectedStatuses)
- Inicialización crítica que debe ocurrir en DOMContentLoaded antes que cualquier función

**Solución:** Mantener lo crítico en template, extraer lo modulable a funciones.

---

## 📁 Estructura Final

```
templates/dashboard/
└── calendar.html
    ├── <head> (sin cambios)
    ├── <body> (sin cambios)
    └── {% block extra_scripts %}
        ├── <script> window.AEPTIC_CALENDAR = { ... }  ← MANTENER
        ├── <script> let currentUserId, calendarObj, etc ← MANTENER
        ├── <script type="module"> import calendar-init ← NUEVO
        └── <!-- Funciones que se mueven a módulos → eliminadas →

static/js/modules/calendar/
├── calendar-state.js            (STATE - Manage estado compartido)
├── calendar-leaves.js           (Solicitudes de vacaciones/ausencia)
├── calendar-pending.js          (Solicitudes pendientes)
├── calendar-resolved.js         (Solicitudes resueltas)
└── calendar-init.js             (Inicializador principal)
```

---

## 📋 Tareas por Completar

### FASE 1: Análisis y Preparación

- [ ] **1.1** Identificar todas las funciones a extraer
  - `sendLeaveRequest()` - 79 líneas
  - `loadPendingRequests()` - 41 líneas
  - `loadResolvedRequests()` - 96 líneas
  - `approveLeave()` - 3 líneas
  - `submitReview()` - 19 líneas
  - `showEventModal()` - 27 líneas
  - `openRejectModal()` - 11 líneas
  - `uploadAttachment()` - 44 líneas
  - `prepareAttachmentSection()` - 23 líneas
  - `toggleResolved()` - 7 líneas
  - `toggleReviewNote()` - 31 líneas
  - **Total: ~380 líneas** para extraer

- [ ] **1.2** Documentar dependencias
  - ✅ Variables globales: `currentUserId`, `currentLeaveId`, `_pendingRejectId`, `calendarObj`, `window._leaveDataMap`, `window.selectedStatuses`
  - ✅ IDs de DOM: `vacationReason`, `vacationStart`, `vacationEnd`, `vacationNote`, `absenceReason`, etc.
  - ✅ URLs: Desde `window.AEPTIC_CALENDAR`
  - ✅ Librerías externas: Bootstrap Modal, FullCalendar

### FASE 2: Crear Módulo de Estado

- [ ] **2.1** Crear `calendar-state.js`
  - Exportar getters/setters para variables compartidas
  - Exportar funciones para acceder a `calendarObj`
  - Centralizar acceso a `window.AEPTIC_CALENDAR`

**Contenido:**
```javascript
// Gestionar estado compartido
export function getCalendarObj() { return window.calendarObj; }
export function setCalendarObj(obj) { window.calendarObj = obj; }
export function getCurrentUserId() { return window.currentUserId; }
export function setCurrentUserId(id) { window.currentUserId = id; }
// ... más getters/setters

// Helpers para URLs
export function getEventsUrl() { return window.AEPTIC_CALENDAR.EVENTS_URL; }
export function getLeaveCreateUrl() { return window.AEPTIC_CALENDAR.LEAVE_CREATE_URL; }
// ... más URLs

// Helpers para datos
export function getLeaveData(id) { return window._leaveDataMap[id]; }
export function setLeaveData(id, data) { window._leaveDataMap[id] = data; }
```

### FASE 3: Extraer Funciones "Puras"

- [ ] **3.1** Crear `calendar-leaves.js`
  - Función: `sendLeaveRequest(payload, msgElementId, isFormData)`
  - Función: `uploadAttachment(leaveId)`
  - Función: `prepareAttachmentSection(event)`
  - Función: `showUploadZone()`

**Consideraciones:**
- Importar desde `calendar-state.js` para URLs y variables
- Mantener validación de solapamientos
- Mantener limpieza de formularios

- [ ] **3.2** Crear `calendar-pending.js`
  - Función: `loadPendingRequests()`
  - Función: `approveLeave(leaveId)`
  - Función: `submitReview(leaveId, action, note)`

**Consideraciones:**
- `loadPendingRequests()` rellena `window._leaveDataMap`
- `approveLeave()` llama a `submitReview()`

- [ ] **3.3** Crear `calendar-resolved.js`
  - Función: `loadResolvedRequests(userId)`
  - Función: `toggleResolved()`
  - Función: `toggleReviewNote(element, note)`

**Consideraciones:**
- Manejo de renderizado de tabla dinámica
- Completamente independiente del resto

### FASE 4: Crear Módulo de Inicialización

- [ ] **4.1** Crear `calendar-init.js`
  - Función: `initCalendar()` - Punto de entrada principal
  - Contenido:
    - Setup de min dates para inputs
    - Configurar filtros de estado
    - Inicializar FullCalendar
    - Selector de equipo listener
    - Listeners de botones (vacaciones, ausencia, rechazo)
    - Cargar pendientes y resueltas inicialmente

**Importa:**
- Funciones de `calendar-leaves.js`
- Funciones de `calendar-pending.js`
- Funciones de `calendar-resolved.js`
- Helpers de `calendar-state.js`

### FASE 5: Actualizar Template

- [ ] **5.1** Reemplazar bloque `{% block extra_scripts %}`

**Mantener:**
```html
{% block extra_scripts %}
<script>
  // Configuración global (CRÍTICO - debe estar antes de los módulos)
  window.AEPTIC_CALENDAR = {
    EVENTS_URL: '{% url "calendar_events" %}',
    LEAVE_CREATE_URL: '{% url "leave_create" %}',
    LEAVE_PENDING_URL: '{% url "leave_pending" %}',
    LEAVE_RESOLVED_URL: '{% url "api_leave_resolved" %}',
    LEAVE_BASE_URL: '/leave/',
    CSRF_TOKEN: '{{ csrf_token }}'
  };

  // Variables globales compartidas (necesarias para FullCalendar y módulos)
  let currentUserId = null;
  let calendarObj = null;
  let _pendingRejectId = null;
  let currentLeaveId = null;
  window._leaveDataMap = {};
  window.selectedStatuses = ['pending', 'approved'];
</script>

<script type="module">
  import { initCalendar } from '{% static "js/modules/calendar/calendar-init.js" %}';
  
  document.addEventListener('DOMContentLoaded', () => {
    initCalendar();
  });
</script>
{% endblock %}
```

**Eliminar:**
- Las ~380 líneas de funciones que se movieron a módulos
- Mantenemos TODO el código que depende de FullCalendar y estado

- [ ] **5.2** Verificar que no hay referencias rotas
  - onclick handlers siguen funcionando (las funciones existen globalmente)
  - FullCalendar se inicializa correctamente

### FASE 6: Garantizar Compatibilidad con onclick

**IMPORTANTE:** Las funciones que se invocan desde `onclick` en HTML dinámico deben quedar globales.

**Funciones invocadas desde onclick:**
```html
<!-- Línea 18 -->
onclick="this.closest('.pending-banner').remove()"  ← Inline, no hay función

<!-- Línea 208 -->
onclick="uploadAttachment(currentLeaveId)"  ← ✅ Exportar a window

<!-- Línea 612 -->
onclick="approveLeave('${l.id}')"  ← ✅ Exportar a window

<!-- Línea 613 -->
onclick="openRejectModal('${l.id}')"  ← ⚠️ Mantener en template o exportar

<!-- Línea 723 -->
onclick="toggleReviewNote(this, '${l.review_note.replace(/'/g, "\\'")}')"  ← ✅ Exportar a window
```

**Solución:**
En `calendar-init.js`, después de importar los módulos:
```javascript
// Exportar funciones a window para que onclick las encuentre
window.uploadAttachment = uploadAttachment;
window.approveLeave = approveLeave;
window.toggleReviewNote = toggleReviewNote;
window.openRejectModal = openRejectModal;
// etc.
```

- [ ] **6.1** Crear wrapper global en `calendar-init.js`
  - Exportar todas las funciones que se llaman desde onclick

### FASE 7: Modularización de FullCalendar

**Considerar:** ¿Extraer inicialización de FullCalendar a módulo separado?

- [ ] **7.1** (OPCIONAL) Crear `calendar-calendar.js`
  - Función: `initializeCalendar(containerEl)`
  - Retorna: `calendarObj`

**Beneficio:** Separa la lógica de inicialización del calendario del resto

**Riesgo:** Aumenta complejidad, probablemente no vale la pena

**Recomendación:** Dejar en `calendar-init.js` por ahora

### FASE 8: Testing & Validación

- [ ] **8.1** Verificar que los filtros funcionan
  - Filtros de estado (pendiente, aprobada, rechazada)
  - Selector de empleado

- [ ] **8.2** Verificar solicitudes de vacaciones
  - Enviar solicitud de vacaciones
  - Validación de solapamientos
  - Limpieza de formulario
  - Mensaje de éxito/error

- [ ] **8.3** Verificar solicitudes de ausencia
  - Enviar solicitud con archivo adjunto
  - Enviar sin archivo adjunto
  - Validación de solapamientos
  - Limpieza de formulario

- [ ] **8.4** Verificar solicitudes pendientes (solo manager)
  - Cargar solicitudes pendientes
  - Aprobar solicitud
  - Rechazar solicitud (con nota)
  - Badge actualiza correctamente

- [ ] **8.5** Verificar solicitudes resueltas
  - Cargar solicitudes resueltas
  - Toggle para mostrar/ocultar
  - Expandir nota de resolución
  - Descargar justificantes

- [ ] **8.6** Verificar upload de justificantes
  - Upload desde modal
  - Validación de archivo
  - Mostrar archivo adjunto
  - Reemplazar archivo

- [ ] **8.7** Verificar calendario
  - Cargar eventos correctamente
  - Click en evento abre modal
  - Modal muestra detalles correctos
  - Navegación mes/semana

- [ ] **8.8** Consola del navegador
  - Sin errores 🟢
  - Solo logs de debug permitidos

---

## 📊 Resumen de Cambios

| Métrica | Antes | Después |
|---------|-------|---------|
| Líneas JS en template | ~535 | ~20 |
| Reducción | — | **96.3%** ✅ |
| Módulos creados | 0 | 5 |
| Funciones extraídas | — | 11 |
| Complejidad template | Alto | Bajo ✅ |
| Testabilidad | Baja | Alta ✅ |

---

## 🔗 Relaciones entre Módulos

```
calendar-init.js
├── Importa de calendar-state.js
├── Importa de calendar-leaves.js
├── Importa de calendar-pending.js
├── Importa de calendar-resolved.js
├── Usa window.AEPTIC_CALENDAR (del template)
├── Usa window.currentUserId, calendarObj, etc. (del template)
└── Exporta funciones a window (para onclick)

calendar-leaves.js
├── Importa de calendar-state.js
└── Usa Bootstrap Modal (librería externa)

calendar-pending.js
├── Importa de calendar-state.js
├── Importa de calendar-leaves.js (submitReview)
└── Usa window._leaveDataMap

calendar-resolved.js
├── Importa de calendar-state.js
└── Independiente del resto

calendar-state.js
└── Solo accede a window.AEPTIC_CALENDAR y variables globales
```

---

## ✅ Diferencia Clave: Híbrida vs Completa

### Si fuera COMPLETAMENTE modular (no recomendado):
```javascript
// Tendríamos que hacer esto:
export function setSelectedStatuses(statuses) {
  window.selectedStatuses = statuses;
  window.calendarObj?.refetchEvents();
}

// Y duplicaríamos muchísimo código
```

### Con estrategia HÍBRIDA (recomendado):
```javascript
// Template mantiene estado
// Módulos usan estado cuando lo necesitan
// Código limpio y simple
```

---

## 📝 Checklist Final

**Antes de empezar:**
- [ ] Has leído y entiendes por qué es híbrida
- [ ] Entiendes qué va en template y qué en módulos
- [ ] Sabes que las funciones onclick necesitan estar globales

**Después de completar:**
- [ ] Todos los módulos están creados
- [ ] Template tiene solo configuración y setup
- [ ] Funciones onclick funcionan correctamente
- [ ] Consola sin errores
- [ ] Toda funcionalidad funciona igual que antes

---

## 🚀 Orden Recomendado

1. **Primero:** `calendar-state.js` (base)
2. **Segundo:** `calendar-leaves.js` (independiente)
3. **Tercero:** `calendar-resolved.js` (independiente)
4. **Cuarto:** `calendar-pending.js` (depende de leaves)
5. **Quinto:** `calendar-init.js` (orquesta todo)
6. **Sexto:** Actualizar template
7. **Séptimo:** Testing

---

## ⚠️ Trampas Potenciales

1. **Olvidar exportar funciones a window** 
   - Las que se llaman desde onclick fallarán

2. **Olvidar importar calendar-state en cada módulo**
   - URLs y variables globales no estarán disponibles

3. **Cambiar orden de módulos**
   - calendar-init.js DEBE ser el último import

4. **No mantener window.AEPTIC_CALENDAR en template**
   - Los módulos lo necesitan

5. **Intentar modularizar FullCalendar.Calendar**
   - Es complicado, mantenerlo en template es más simple

---

## 📌 Variables y Funciones por Módulo

### calendar-state.js (STATE MANAGEMENT)
```javascript
// Getters/Setters
getCalendarObj(), setCalendarObj()
getCurrentUserId(), setCurrentUserId()
getPendingRejectId(), setPendingRejectId()
getCurrentLeaveId(), setCurrentLeaveId()
getSelectedStatuses(), setSelectedStatuses()
getLeaveData(), setLeaveData()

// Helpers de URL
getEventsUrl(), getLeaveCreateUrl(), getLeaveResolvedUrl(), etc.
getCsrfToken()
```

### calendar-leaves.js (LEAVE REQUESTS)
```javascript
sendLeaveRequest(payload, msgElementId, isFormData)
uploadAttachment(leaveId)
prepareAttachmentSection(event)
showUploadZone()
```

### calendar-pending.js (PENDING REQUESTS)
```javascript
loadPendingRequests()
approveLeave(leaveId)
submitReview(leaveId, action, note)
openRejectModal(leaveId)
```

### calendar-resolved.js (RESOLVED REQUESTS)
```javascript
loadResolvedRequests(userId)
toggleResolved()
toggleReviewNote(element, note)
```

### calendar-init.js (INITIALIZER)
```javascript
initCalendar()  // Punto de entrada principal

// + exporta funciones a window para onclick
```

---

## 🎓 Lecciones Aprendidas (para futuros templates)

- No todos los templates son "modularizables" al 100%
- Librerías externas complejas a veces requieren acceso global
- Estado compartido hace que la modularización sea más difícil
- Una estrategia "híbrida" a veces es mejor que una "purista"
- Mantener cosas simples > hacer arquitectura perfecta

---

## 📌 Próximos Pasos Después de Completar

- [ ] Revisar si hay otros templates con funciones similares
- [ ] Considerar crear utilidades compartidas en `/static/js/utils/`
- [ ] Documentar patrones de modularización para el equipo
