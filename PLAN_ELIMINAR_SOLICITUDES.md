# 📋 PLAN: Eliminación de Solicitudes por Managers en "Solicitudes Resueltas"

## 🎯 Objetivo
Permitir que los managers eliminen (soft-delete) solicitudes de vacaciones, ausencias y bajas de los empleados de su empresa directamente desde la tabla de "Solicitudes Resueltas" en el calendario.

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
Frontend (JavaScript)              Backend (Django)                  Database
─────────────────────────────────────────────────────────────────────────────
calendar-resolved.js    ──────→   api_delete_leave_request   ──────→  leave_requests
   (agregar columna        (POST)        (requests/views.py)          (soft-delete)
    + icono papelera)                                                     ↓
                                        Auditoría (AuditLog)
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

### BLOQUE 3: Frontend - Actualizar Tabla en calendar-resolved.js
**Archivo**: `static/js/modules/calendar/calendar-resolved.js`

**Tarea 3.1**: Modificar función `loadResolvedRequests`
**Ubicación**: Línea 72-134 (generación de filas HTML)

**Cambios necesarios**:

1. **Parámetro `show_delete_col`**:
   - Recibir desde el backend: `show_delete_col` (boolean)
   - Condición: `show_delete_col = user_is_manager && user_id != ''` (en la vista)
   - Si manager está en "Mi calendario", NO mostrar

2. **Función generadora de filas (línea 72)**:
   - Agregar nueva celda en cada fila para el botón de eliminar
   - Ubicación: DESPUÉS de la columna "Justificante" (línea 132)
   - HTML del botón:
   ```html
   <td style="padding:.5rem .6rem;text-align:center;">
     <button onclick="deleteLeaveRequest('${l.id}')"
             style="background:none;border:none;cursor:pointer;padding:0 .25rem;color:#dc2626;"
             title="Eliminar solicitud"
             class="btn-delete-leave">
       <i class="bi bi-trash"></i>
     </button>
   </td>
   ```

3. **Condición en header de tabla**:
   - Agregar `<th>` solo si `show_delete_col = true`
   ```html
   ${show_delete_col ? '<th style="...">Eliminar</th>' : ''}
   ```

4. **Guardar en contexto global**:
   - Agregar a `window.AEPTIC_CALENDAR` o variable local: `window.showDeleteCol = show_delete_col`

**Criterios de Aceptación**:
- ✅ Columna "Eliminar" aparece SOLO cuando manager ve otros empleados (`user_id != ''`)
- ✅ Columna NO aparece cuando manager ve "Mi calendario" (sin `user_id`)
- ✅ Botón de papelera con estilo rojo (#dc2626)
- ✅ Tooltip con texto "Eliminar solicitud"
- ✅ Bootstrap Icons (bi bi-trash) disponible

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

### BLOQUE 5: Frontend - Función de Eliminación
**Archivo**: `static/js/modules/calendar/calendar-resolved.js`

**Tarea 5.1**: Agregar función `deleteLeaveRequest(leave_id)`
**Ubicación**: Al final del archivo, antes de los comentarios finales

**Función**:
```javascript
export function deleteLeaveRequest(leaveId) {
  // 1. Confirmar con modal/dialog
  if (!confirm('¿Estás seguro de que deseas eliminar esta solicitud? Esta acción no se puede deshacer.')) {
    return;
  }

  // 2. Enviar DELETE por POST (Django no soporta DELETE en forms)
  fetch(`/leave/${leaveId}/delete/`, {
    method: 'POST',
    headers: {
      'X-CSRFToken': '{{ csrf_token }}',
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({})
  })
  .then(res => res.json())
  .then(data => {
    if (data.ok) {
      // 3. Recargar tabla
      const selector = document.getElementById('teamSelector');
      const userId = selector ? selector.value : '';
      loadResolvedRequests(userId);
      showNotification('Solicitud eliminada correctamente', 'success');
    } else {
      showNotification(data.error || 'Error al eliminar', 'error');
    }
  })
  .catch(err => {
    console.error('Delete error:', err);
    showNotification('Error de conexión', 'error');
  });
}
```

**Notas Importantes**:
- El CSRF token debe obtenerse del contexto (ver línea 466 en calendar.html)
- O mejor: usar `window.AEPTIC_CALENDAR.CSRF_TOKEN`
- Función `showNotification` debe existir o crear una simple

**Criterios de Aceptación**:
- ✅ Muestra confirmación antes de eliminar
- ✅ Envía POST a `/leave/{id}/delete/`
- ✅ Incluye CSRF token
- ✅ Refresca la tabla después de eliminar
- ✅ Muestra mensaje de éxito
- ✅ Maneja errores con mensaje visual

---

### BLOQUE 6: Frontend - Helper para Notificaciones (Opcional)
**Archivo**: `static/js/modules/calendar/calendar-resolved.js`

**Tarea 6.1**: Agregar función `showNotification` (si no existe)
```javascript
function showNotification(message, type = 'info') {
  // Crear elemento temporal
  const notifClass = type === 'success' ? 'alert-success' : 
                    type === 'error' ? 'alert-danger' : 'alert-info';
  
  const html = `<div class="alert ${notifClass} alert-dismissible fade show" role="alert">
    ${message}
    <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
  </div>`;
  
  // Insertar en top del documento
  const container = document.querySelector('.cal-page');
  if (container) {
    container.insertAdjacentHTML('afterbegin', html);
    setTimeout(() => {
      const alert = container.querySelector('.alert');
      if (alert) alert.remove();
    }, 3000);
  }
}
```

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
| `calendar-resolved.js` | 72-154 | **EDIT** | Agregar columna "Eliminar" a tabla |
| `calendar-resolved.js` | 217+ | **ADD** | Nueva función `deleteLeaveRequest()` |
| `calendar-resolved.js` | 217+ | **ADD** | Helper `showNotification()` (opcional) |

---

## ✅ Orden Recomendado de Ejecución

1. **BLOQUE 1**: Crear vista backend ✓
2. **BLOQUE 4**: Modificar respuesta JSON ✓
3. **BLOQUE 2**: Agregar ruta URL ✓
4. **BLOQUE 3**: Actualizar tabla HTML ✓
5. **BLOQUE 5**: Agregar función de eliminación ✓
6. **BLOQUE 6**: Agregar notificaciones (opcional) ✓
7. **BLOQUE 7**: Validar en navegador ✓

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

**Estado del Plan**: 📋 Listo para ejecución
**Última actualización**: 2026-05-21
