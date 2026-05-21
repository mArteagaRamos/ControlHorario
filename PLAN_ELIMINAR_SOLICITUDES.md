# 📋 PLAN: Eliminación de Solicitudes por Managers en "Solicitudes Resueltas"

## 🎯 Objetivo
Permitir que los managers eliminen (soft-delete) solicitudes de vacaciones, ausencias y bajas de los empleados de su empresa directamente desde la tabla de "Solicitudes Resueltas" en el calendario.

---

## 🔄 Cambio de Enfoque (Actualización)

**Enfoque Original**: Modificar módulos ES6 (`calendar-resolved.js`, `calendar-init.js`)
- ❌ Causaba errores de módulo que rompían todo el calendario

**Nuevo Enfoque**: Script inline en el template
- ✅ No toca módulos ES6 ya funcionales
- ✅ Inyecta columna de eliminación dinámicamente
- ✅ Riesgo mínimo, implementación más robusta
- ✅ Mantiene el calendario funcionando en todo momento

---

## 📊 Vista General

### Requisitos Funcionales
- ✅ Agregar columna "Eliminar" después de "Justificante" en la tabla
- ✅ Mostrar icono de papelera (trash) en cada fila
- ✅ Al clic: realiza soft-delete (marca `deleted_at`) de la solicitud
- ✅ **Condición de visibilidad**: NO mostrar la columna si el manager ve "Mi calendario" (sin `user_id`)
- ✅ Confirmación antes de eliminar
- ✅ Auditoría de la acción (registro en AuditLog)
- ✅ Solo accesible para managers

### Estatutos Donde Aplica
La columna "Eliminar" debe estar disponible para solicitudes con estos estados:
- ✅ **APPROVED** (Aprobada)
- ✅ **REJECTED** (Rechazada)
- ✅ **CANCELED** (Cancelada)
- ❌ **PENDING** (Pendiente) - No se debe eliminar, solo usar botón de edición

---

## 🏗️ Arquitectura de Cambios

```
Frontend (HTML Template)            Backend (Django)                  Database
─────────────────────────────────────────────────────────────────────────────
calendar.html              ──────→   api_delete_leave_request   ──────→  leave_requests
   (inline script)          (POST)        (requests/views.py)          (soft-delete)
   (agregar columna           ↑                                           ↓
    + icono papelera)         └─────────── Auditoría (AuditLog)

```

---

## 📦 BLOQUES DE TRABAJO

### BLOQUE 1: Backend - Crear Vista de Eliminación
**Archivo**: `requests/views.py`

**Tarea 1.1**: Nueva función `api_delete_leave_request`
```python
@login_required
@require_POST
def api_delete_leave_request(request, leave_id):
    """
    Soft-delete de una solicitud de vacaciones/ausencia por el manager.
    
    - Solo managers pueden eliminar
    - Solo si NO es PENDING
    - Registra en AuditLog
    
    POST params:
    - leave_id (URL)
    
    Returns: JSON con status OK o error
    """
```

**Criterios de Aceptación**:
- ✅ Validar que el usuario sea manager de la empresa
- ✅ Obtener la solicitud por ID
- ✅ Verificar que la empresa coincida
- ✅ Verificar que NO sea PENDING (no se pueden eliminar pendientes)
- ✅ Verificar que NO esté ya eliminada (`deleted_at is not None`)
- ✅ Realizar soft-delete: `leave.deleted_at = timezone.now()`
- ✅ Registrar en AuditLog con `action_type='voided'`
- ✅ Retornar `{'ok': True}` o error JSON con mensaje

**Referencia de implementación**: Ver `eliminar_incidencia_rechazada` en línea 270 de `requests/views.py`

---

### BLOQUE 2: Backend - Agregar Ruta URL
**Archivo**: `core/urls.py`

**Tarea 2.1**: Agregar nueva ruta
```python
path('leave/<uuid:leave_id>/delete/', requests_views.api_delete_leave_request, name='api_delete_leave'),
```

**Ubicación**: Cerca de las otras rutas de `leave/` (alrededor de línea 91-98)

**Criterios de Aceptación**:
- ✅ Ruta disponible en `window.AEPTIC_CALENDAR` (actualizar en template si es necesario)

---

### BLOQUE 3: Frontend - Modificar Template HTML
**Archivo**: `templates/calendar.html`

**Tarea 3.1**: Agregar estructura HTML para la columna "Eliminar"
**Ubicación**: Tabla de "Solicitudes Resueltas" (buscar `resolvedContainer`)

**Cambios necesarios**:

1. **Buscar la sección donde se renderiza la tabla de solicitudes** (línea aproximada 600-700)
2. **Agregar contenedor para el script inline** (al final del template):
```html
<!-- Script para manejar eliminación de solicitudes -->
<script>
  // Será agregado en BLOQUE 5
</script>
```

3. **NO modificar** `calendar-resolved.js` - El contenido de la columna será generado por el script inline que se ejecutará después de que el módulo carga la tabla.

**Criterios de Aceptación**:
- ✅ Template carga sin errores
- ✅ Tabla de solicitudes se renderiza normalmente
- ✅ Script inline está listo para ejecutarse

---

### BLOQUE 4: Backend - Preparar Respuesta en api_leave_resolved
**Archivo**: `requests/views.py`

**Tarea 4.1**: Modificar `api_leave_resolved` para pasar `show_delete_col`
**Ubicación**: Línea 502-573

**Cambios**:
1. Agregar variable: `show_delete_col`
   ```python
   # La columna de eliminar se muestra SOLO si:
   # 1. El usuario ES manager, AND
   # 2. Está viendo otros empleados (user_id != '' AND user_id != None)
   show_delete_col = user_is_manager and user_id and user_id != '' and user_id != 'all'
   ```

2. En `JsonResponse` (final de función):
   ```python
   return JsonResponse({
       'requests': data,
       'show_user_col': user_is_manager and user_id == 'all',
       'show_delete_col': show_delete_col,  # ← AGREGAR
   })
   ```

**Criterios de Aceptación**:
- ✅ `show_delete_col = False` cuando usuario NO es manager
- ✅ `show_delete_col = False` cuando manager ve "Mi calendario" (`user_id == ''`)
- ✅ `show_delete_col = False` cuando manager ve "Todos los empleados" (`user_id == 'all'`)
- ✅ `show_delete_col = True` cuando manager ve un empleado específico (`user_id = UUID`)

---

### BLOQUE 5: Frontend - Script Inline para Manejo de Eliminación
**Archivo**: `templates/calendar.html`

**Tarea 5.1**: Agregar script inline al final del template para manejar eliminación

**Ubicación**: Al final de `calendar.html`, dentro de `<script>` inline

**Script a agregar**:
```javascript
// Manejo de eliminación de solicitudes
window.deleteLeaveRequest = async function(leaveId) {
  if (!confirm('¿Eliminar esta solicitud? Esta acción no se puede deshacer.')) {
    return;
  }

  try {
    const csrfToken = document.querySelector('input[name="csrfmiddlewaretoken"]')?.value || '';
    const res = await fetch(`/leave/${leaveId}/delete/`, {
      method: 'POST',
      headers: {
        'X-CSRFToken': csrfToken,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({})
    });

    const data = await res.json();
    if (data.ok) {
      // Recargar tabla de solicitudes resueltas
      const selector = document.getElementById('teamSelector');
      const userId = selector?.value || null;
      await loadResolvedRequests(userId);
      alert('Solicitud eliminada correctamente');
    } else {
      alert(`Error: ${data.error || 'No se pudo eliminar'}`);
    }
  } catch (err) {
    console.error('Delete error:', err);
    alert('Error de conexión');
  }
};

// Inyectar columna de eliminación después de que la tabla se renderiza
// Observer para cuando se actualiza resolvedContainer
const observerConfig = { childList: true, subtree: true };
const observer = new MutationObserver(function(mutations) {
  // Buscar tabla en resolvedContainer
  const table = document.querySelector('#resolvedContainer table');
  if (!table) return;

  // Agregar encabezado si no existe
  const headerRow = table.querySelector('thead tr');
  if (headerRow && !headerRow.querySelector('.delete-header')) {
    const deleteHeader = document.createElement('th');
    deleteHeader.className = 'delete-header';
    deleteHeader.style.cssText = 'padding:.4rem .6rem;font-weight:600;text-align:center;';
    deleteHeader.textContent = 'Eliminar';
    headerRow.appendChild(deleteHeader);
  }

  // Agregar botones en filas (solo si no existen)
  const bodyRows = table.querySelectorAll('tbody tr:not(.review-note-row):not([data-delete-added])');
  bodyRows.forEach(row => {
    // Verificar que la fila tiene el contenido de la solicitud (no es fila de nota)
    if (row.cells.length > 0 && !row.hasAttribute('data-delete-added')) {
      const deleteCell = document.createElement('td');
      deleteCell.style.cssText = 'padding:.5rem .6rem;text-align:center;';
      
      // Obtener el ID de la solicitud desde los atributos o data
      // Buscar en el onclick de botones existentes
      const editBtn = row.querySelector('[onclick*="editLeaveRequest"]');
      let leaveId = null;
      if (editBtn) {
        const match = editBtn.getAttribute('onclick').match(/leave-([^']+)/);
        if (match) leaveId = match[1];
      }
      
      if (leaveId) {
        const deleteBtn = document.createElement('button');
        deleteBtn.onclick = function(e) { e.preventDefault(); deleteLeaveRequest(leaveId); };
        deleteBtn.style.cssText = 'background:none;border:none;cursor:pointer;padding:0 .25rem;color:#dc2626;';
        deleteBtn.title = 'Eliminar solicitud';
        deleteBtn.className = 'btn-delete-leave';
        deleteBtn.innerHTML = '<i class="bi bi-trash"></i>';
        deleteCell.appendChild(deleteBtn);
      }
      
      row.appendChild(deleteCell);
      row.setAttribute('data-delete-added', 'true');
    }
  });
});

observer.observe(document.getElementById('resolvedContainer'), observerConfig);
```

**Criterios de Aceptación**:
- ✅ Función `deleteLeaveRequest()` se registra en `window`
- ✅ Se ejecuta después de que la tabla se renderiza
- ✅ Agrega columna "Eliminar" con botones de papelera
- ✅ Botones solo en filas de solicitudes (no en filas de notas)
- ✅ Confirmación antes de eliminar
- ✅ Refresca la tabla tras eliminación exitosa
- ✅ Maneja errores apropiadamente

---

### BLOQUE 7: Pruebas y Validación
**Archivo**: Manual (navegador + browser console)

**Escenarios a Validar**:

1. **Manager en "Mi calendario"**:
   - ✅ No ver columna "Eliminar"
   - ✅ Tabla muestra solo solicitudes del manager

2. **Manager viendo empleado específico**:
   - ✅ VER columna "Eliminar"
   - ✅ Botón papelera funcional
   - ✅ Confirmación antes de eliminar
   - ✅ Solicitud desaparece de tabla tras eliminación

3. **Manager viendo "Todos los empleados"**:
   - ✅ NO ver columna "Eliminar"
   - ✅ Tabla muestra solicitudes de todos

4. **Validaciones de la vista**:
   - ✅ Non-manager NO puede acceder a `/leave/{id}/delete/`
   - ✅ PENDING status NO se puede eliminar
   - ✅ Ya eliminada (deleted_at ≠ NULL) NO se puede eliminar de nuevo
   - ✅ Auditoría registra la eliminación

5. **Casos edge**:
   - ✅ Tabla vacía: no hay fila ni columna
   - ✅ Solo solicitudes PENDING: columna visible pero sin botones
   - ✅ CSRF token válido en cada eliminación

---

## 🔐 Consideraciones de Seguridad

1. **Permisos**:
   - ✅ Validar `is_manager(request, company)` en la vista
   - ✅ Validar que la solicitud pertenece a un empleado de su empresa

2. **Soft-delete, no hard-delete**:
   - ✅ Solo marcar `deleted_at = timezone.now()`
   - ✅ Datos permanecen en BD para auditoría

3. **Auditoría**:
   - ✅ `AuditLog.objects.create(...)` con `action_type='voided'`
   - ✅ Incluir `before` y `after` states
   - ✅ Registrar motivo: "Eliminación (soft-delete) de solicitud de vacación/ausencia"

4. **CSRF Protection**:
   - ✅ Usar `@require_POST` en la vista
   - ✅ Validar CSRF token en frontend

---

## 📝 Cambios de Archivo (Resumen)

| Archivo | Línea(s) | Tipo | Descripción |
|---------|----------|------|-------------|
| `requests/views.py` | ~1410+ | **NEW** | Nueva función `api_delete_leave_request` |
| `requests/views.py` | 502-573 | **EDIT** | Modificar `api_leave_resolved` para agregar `show_delete_col` |
| `core/urls.py` | ~100 | **ADD** | Nueva ruta `/leave/<id>/delete/` |
| `templates/calendar.html` | Final | **ADD** | Script inline para manejar eliminación y inyectar botones |

---

## ✅ Orden Recomendado de Ejecución

1. **BLOQUE 1**: Crear vista backend ✓
2. **BLOQUE 4**: Modificar respuesta JSON ✓
3. **BLOQUE 2**: Agregar ruta URL ✓
4. **BLOQUE 5**: Agregar script inline en template ✓
5. **BLOQUE 7**: Validar en navegador ✓

---

## 🎨 Estilo Visual (Referencias)

- **Icono**: `<i class="bi bi-trash"></i>` (Bootstrap Icons)
- **Color**: `#dc2626` (rojo - consistente con acciones destructivas)
- **Padding**: `.5rem .6rem` (consistente con otras celdas)
- **Hover**: `cursor: pointer` (feedback visual)
- **Tooltip**: `title="Eliminar solicitud"` (ayuda)

---

## 📚 Referencias en Código Existente

- Vista similar: `eliminar_incidencia_rechazada` (línea 270, requests/views.py)
- Tabla renderizada: `loadResolvedRequests` (línea 33, calendar-resolved.js)
- Configuración global: `window.AEPTIC_CALENDAR` (línea 460, calendar.html)
- Soft-delete pattern: `deleted_at` field en LeaveRequest model

---

## 🚀 Próximos Pasos Después de Implementar

1. ✅ Documentar la nueva funcionalidad en el changelog
2. ✅ Notificar a los managers sobre la nueva capacidad
3. ✅ Monitorear auditoría para uso indebido
4. ✅ Considerar agregar auditoría de restauraciones (undo)
5. ✅ Opcional: Agregar confirmación con modal más detallado

---

**Estado del Plan**: 📋 Actualizado con nuevo enfoque - Listo para ejecución
**Última actualización**: 2026-05-21 (Cambio de enfoque: ES6 modules → Script inline en template)
