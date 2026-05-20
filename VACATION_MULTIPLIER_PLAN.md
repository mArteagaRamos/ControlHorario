# Plan de Implementación: Sistema de Multiplicadores de Horas Vacacionales

## Contexto General

Sistema de 4 capas para gestionar multiplicadores de horas en periodos vacacionales especiales y límites anuales de días de vacaciones:

1. **Capa 1**: Configuración de periodos especiales y límite anual
2. **Capa 2**: Aprobación de solicitudes con cálculo automático
3. **Capa 3**: Cálculo en reportes mensuales
4. **Capa 4**: Conteo de días consumidos

**Cambios en BBDD (ya realizados)**:
- Tabla `vacation_period_multipliers` creada (id, company_id, name, date_from, date_to, multiplier, created_by, created_at, updated_at, deleted_at)
- Columna `hour_multiplier DECIMAL(4,2) DEFAULT 1.0` en `leave_requests`
- Columna `default_vacation_days INTEGER DEFAULT 23` en `company_settings`

---

## BLOQUE 1: Modelos (models.py) ✅ COMPLETADO

### Archivos a modificar:
- `requests/models.py` → Agregar modelo `VacationPeriodMultiplier`
- `requests/models.py` → Modificar `LeaveRequest`
- `admin/models.py` → Modificar `CompanySettings`

### Tarea 1.1: Crear modelo VacationPeriodMultiplier
**Archivo**: `requests/models.py`

Agregar el modelo con los siguientes campos:
```python
class VacationPeriodMultiplier(UppercaseNormalizationMixin, models.Model):
    # Campos base
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    company = models.ForeignKey(Companies, on_delete=models.CASCADE, db_column='company_id')
    name = models.CharField(max_length=100)  # "Semana Santa", "Navidad", etc.
    date_from = models.DateField()
    date_to = models.DateField()
    multiplier = models.DecimalField(max_digits=4, decimal_places=2, default=1.0)
    
    # Auditoría
    created_by = models.ForeignKey(Users, on_delete=models.SET_NULL, null=True, 
                                    blank=True, db_column='created_by_id', 
                                    related_name='vacation_multipliers_created')
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(default=timezone.now)
    deleted_at = models.DateTimeField(null=True, blank=True, default=None)
    
    # Manager
    objects = SoftDeleteManager()
    
    class Meta:
        managed = False
        db_table = 'vacation_period_multipliers'
    
    def __str__(self):
        return f"{self.name} ({self.date_from} - {self.date_to}) x{self.multiplier}"
```

**Método estático**: `get_multiplier_for_range(company_id, start_date, end_date)`
- Busca overlaps usando: `date_from <= end_date AND date_to >= start_date`
- Retorna el multiplicador si encuentra coincidencia
- Retorna `1.0` si no hay coincidencia
- En caso de múltiples overlaps, devolver el primero encontrado
- Usar `.filter(deleted_at__isnull=True)` para excluir soft-deleted

### Tarea 1.2: Modificar modelo LeaveRequest
**Archivo**: `requests/models.py`

Agregar campo `hour_multiplier`:
```python
class LeaveRequest(models.Model):
    # ... campos existentes ...
    hour_multiplier = models.DecimalField(max_digits=4, decimal_places=2, default=1.0)
```

**Método estático**: `get_consumed_days(user_id, company_id, year)`
- Filtrar: `leave_type='vacation'`, `status='approved'`, `deleted_at__isnull=True`
- Filtrar por año: start_date y end_date en el rango [year-01-01, year-12-31]
- Contar días naturales entre start_date y end_date (inclusive)
- Retornar total de días consumidos (float)
- Usar `(end_date - start_date).days + 1` para contar correctamente

### Tarea 1.3: Modificar modelo CompanySettings
**Archivo**: `admin/models.py`

Agregar campo `default_vacation_days`:
```python
class CompanySettings(UppercaseNormalizationMixin, models.Model):
    # ... campos existentes ...
    default_vacation_days = models.IntegerField(default=23)
```

**Notas**:
- Este campo es el límite anual de días de vacaciones
- Se utiliza en la vista de aprobación para mostrar consumo
- Editable desde el template entity_info.html

---

## BLOQUE 2: Vistas - Aprobación de Solicitudes ✅ COMPLETADO

### Archivo a modificar:
- `requests/views.py` → Función `api_leave_review()`

### Tarea 2.1: Preparar datos antes de renderizar formulario de aprobación
**Ubicación**: Antes de retornar la vista del modal de aprobación

Cuando se carga la vista para revisar una solicitud de vacaciones (`leave_type='vacation'`):

```python
# Si es vacaciones:
if leave.leave_type == 'vacation':
    # 1. Obtener multiplicador sugerido
    suggested_multiplier = VacationPeriodMultiplier.get_multiplier_for_range(
        company_id=leave.company.id,
        start_date=leave.start_date,
        end_date=leave.end_date
    )
    
    # 2. Calcular días consumidos en el año
    year = leave.start_date.year
    consumed_days = LeaveRequest.get_consumed_days(
        user_id=leave.user.id,
        company_id=leave.company.id,
        year=year
    )
    
    # 3. Obtener límite anual
    settings = CompanySettings.objects.filter(company=leave.company).first()
    available_days = settings.default_vacation_days if settings else 23
    remaining_days = available_days - consumed_days
    
    # 4. Calcular días de esta solicitud
    request_days = (leave.end_date - leave.start_date).days + 1
    
    # 5. Determinar si hay aviso
    exceeds_limit = (consumed_days + request_days) > available_days
    
    # Pasar al contexto:
    context = {
        'suggested_multiplier': suggested_multiplier,
        'consumed_days': consumed_days,
        'available_days': available_days,
        'remaining_days': remaining_days,
        'request_days': request_days,
        'exceeds_limit': exceeds_limit,
    }
```

### Tarea 2.2: Procesar POST con guardado de hour_multiplier
**Ubicación**: En `api_leave_review()` función POST

Modificar la lógica cuando `action == 'approve'`:

```python
if action == 'approve':
    # Obtener hour_multiplier del body JSON
    hour_multiplier = data.get('hour_multiplier', 1.0)
    try:
        hour_multiplier = float(hour_multiplier)
        # Validar rango: 0.1 a 2.0 (ejemplo)
        if not (0.1 <= hour_multiplier <= 2.0):
            return JsonResponse({'error': 'Multiplicador fuera de rango'}, status=400)
    except (ValueError, TypeError):
        return JsonResponse({'error': 'Multiplicador inválido'}, status=400)
    
    # Actualizar leave_request con el multiplicador
    updated = LeaveRequest.objects.filter(pk=leave.pk).update(
        status=LeaveRequest.LeaveStatus.APPROVED,
        reviewed_by=leave.reviewed_by,
        reviewed_at=leave.reviewed_at,
        review_note=leave.review_note,
        hour_multiplier=hour_multiplier,  # ← NUEVO
        force_proof=True,
    )
```

---

## BLOQUE 3: Template de Aprobación ✅ COMPLETADO

### Archivo a crear/modificar:
- Buscar donde se renderiza el modal/formulario de aprobación de LeaveRequest
- Probablemente en un template JavaScript o en AJAX response

### Tarea 3.1: Agregar sección de multiplicador en el modal
**Ubicación**: Formulario de aprobación/rechazo

Mostrar solo si `leave.leave_type == 'vacation'`:

```html
{% if leave_type == 'vacation' %}
<div class="card mb-3 border-info">
  <div class="card-header bg-info bg-opacity-10 fw-semibold">
    <i class="bi bi-calendar-check"></i> Configuración de Vacaciones
  </div>
  <div class="card-body">
    <!-- Multiplicador de horas -->
    <div class="mb-3">
      <label class="form-label">Multiplicador de horas</label>
      <div class="input-group">
        <input 
          type="number" 
          class="form-control" 
          id="hour_multiplier" 
          name="hour_multiplier"
          min="0.1" 
          max="2.0" 
          step="0.1"
          value="{{ suggested_multiplier }}"
          required
        >
        <span class="input-group-text">×</span>
      </div>
      <small class="form-text text-muted">
        Calculado automáticamente según los periodos configurados. 
        Rango permitido: 0.1 a 2.0
      </small>
    </div>
    
    <!-- Indicador de días consumidos -->
    <div class="mb-3">
      <label class="form-label">Consumo de vacaciones</label>
      <div class="progress mb-2" style="height: 24px;">
        <div 
          class="progress-bar {% if exceeds_limit %}bg-danger{% else %}bg-success{% endif %}" 
          role="progressbar" 
          style="width: {{ consumed_percentage }}%"
          aria-valuenow="{{ consumed_days }}" 
          aria-valuemin="0" 
          aria-valuemax="{{ available_days }}"
        >
          {{ consumed_days }}/{{ available_days }} días
        </div>
      </div>
      <small class="d-block mb-2">
        <strong>Solicitados:</strong> {{ request_days }} días<br>
        <strong>Restantes tras aprobación:</strong> {{ remaining_days_after }} días
      </small>
      
      {% if exceeds_limit %}
      <div class="alert alert-warning py-2 px-3 mb-0" role="alert">
        <i class="bi bi-exclamation-triangle"></i>
        <strong>Aviso:</strong> Esta solicitud superaría el límite anual de {{ available_days }} días 
        (consumo total: {{ consumed_days_with_request }} días).
        <br><small>Puedes aprobarla igualmente; este es solo un aviso informativo.</small>
      </div>
      {% endif %}
    </div>
  </div>
</div>
{% endif %}
```

**Valores a pasar al template**:
- `suggested_multiplier`: valor sugerido (ej: 0.8)
- `consumed_days`: días consumidos hasta hoy en el año
- `available_days`: límite anual (default_vacation_days)
- `remaining_days`: disponibles después de esta solicitud (sin contar esta solicitud)
- `request_days`: días de esta solicitud
- `exceeds_limit`: boolean si supera el límite
- `remaining_days_after`: días restantes si se aprueba (available - consumed - request_days)
- `consumed_percentage`: porcentaje para la barra de progreso

---

## BLOQUE 4: Vistas CRUD para VacationPeriodMultiplier ✅ COMPLETADO

### Archivo a crear/modificar:
- `requests/views.py` → Agregar 4 nuevas funciones

### Tarea 4.1: Vista para listar periodos (GET)
**Función**: `list_vacation_periods(request)`

```python
@login_required_with_delegation_support
def list_vacation_periods(request):
    """Lista todos los periodos vacacionales de la empresa del manager"""
    company = get_company(request)
    
    # Solo managers pueden acceder
    if not is_manager(request, company):
        raise PermissionDenied()
    
    periods = VacationPeriodMultiplier.objects.filter(
        company=company,
        deleted_at__isnull=True
    ).order_by('date_from')
    
    return JsonResponse({
        'periods': [
            {
                'id': str(p.id),
                'name': p.name,
                'date_from': p.date_from.isoformat(),
                'date_to': p.date_to.isoformat(),
                'multiplier': float(p.multiplier),
                'created_by': p.created_by.username if p.created_by else 'Sistema',
                'created_at': p.created_at.isoformat(),
            }
            for p in periods
        ]
    })
```

### Tarea 4.2: Vista para crear periodo (POST)
**Función**: `create_vacation_period(request)`

```python
@login_required_with_delegation_support
@require_POST
def create_vacation_period(request):
    """Crea un nuevo periodo de multiplicador"""
    company = get_company(request)
    
    if not is_manager(request, company):
        raise PermissionDenied()
    
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido'}, status=400)
    
    # Validar campos requeridos
    required = ['name', 'date_from', 'date_to', 'multiplier']
    if not all(data.get(f) for f in required):
        return JsonResponse({'error': 'Campos requeridos incompletos'}, status=400)
    
    try:
        name = data.get('name').strip()
        date_from = datetime.strptime(data.get('date_from'), '%Y-%m-%d').date()
        date_to = datetime.strptime(data.get('date_to'), '%Y-%m-%d').date()
        multiplier = float(data.get('multiplier'))
        
        # Validaciones
        if not (0.1 <= multiplier <= 2.0):
            return JsonResponse({'error': 'Multiplicador debe estar entre 0.1 y 2.0'}, status=400)
        if date_from > date_to:
            return JsonResponse({'error': 'Fecha inicio debe ser anterior a fecha fin'}, status=400)
        if len(name) > 100:
            return JsonResponse({'error': 'Nombre muy largo'}, status=400)
        
        # Crear periodo
        period = VacationPeriodMultiplier.objects.create(
            id=uuid.uuid4(),
            company=company,
            name=name,
            date_from=date_from,
            date_to=date_to,
            multiplier=multiplier,
            created_by=request.user,
            created_at=timezone.now(),
            updated_at=timezone.now(),
        )
        
        # Auditoría
        AuditLog.objects.create(
            id=uuid.uuid4(),
            table_name='vacation_period_multipliers',
            record_id=str(period.id),
            user=request.user,
            action_type='create',
            reason=f"Creación de periodo vacacional '{name}'",
            source='web'
        )
        
        return JsonResponse({'ok': True, 'id': str(period.id)})
    
    except (ValueError, TypeError) as e:
        return JsonResponse({'error': f'Datos inválidos: {str(e)}'}, status=400)
```

### Tarea 4.3: Vista para editar periodo (POST)
**Función**: `edit_vacation_period(request)`

```python
@login_required_with_delegation_support
@require_POST
def edit_vacation_period(request):
    """Edita un periodo existente"""
    company = get_company(request)
    
    if not is_manager(request, company):
        raise PermissionDenied()
    
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido'}, status=400)
    
    period_id = data.get('id')
    if not period_id:
        return JsonResponse({'error': 'ID del periodo requerido'}, status=400)
    
    period = get_object_or_404(
        VacationPeriodMultiplier, 
        id=period_id, 
        company=company
    )
    
    try:
        # Guardamos el estado anterior
        before = {
            'name': period.name,
            'date_from': str(period.date_from),
            'date_to': str(period.date_to),
            'multiplier': float(period.multiplier),
        }
        
        # Actualizar campos si se proporcionan
        if 'name' in data:
            period.name = data['name'].strip()
        if 'date_from' in data:
            period.date_from = datetime.strptime(data['date_from'], '%Y-%m-%d').date()
        if 'date_to' in data:
            period.date_to = datetime.strptime(data['date_to'], '%Y-%m-%d').date()
        if 'multiplier' in data:
            mult = float(data['multiplier'])
            if not (0.1 <= mult <= 2.0):
                return JsonResponse({'error': 'Multiplicador debe estar entre 0.1 y 2.0'}, status=400)
            period.multiplier = mult
        
        # Validación de fechas
        if period.date_from > period.date_to:
            return JsonResponse({'error': 'Fecha inicio debe ser anterior a fecha fin'}, status=400)
        
        period.updated_at = timezone.now()
        period.save()
        
        # Auditoría
        after = {
            'name': period.name,
            'date_from': str(period.date_from),
            'date_to': str(period.date_to),
            'multiplier': float(period.multiplier),
        }
        
        AuditLog.objects.create(
            id=uuid.uuid4(),
            table_name='vacation_period_multipliers',
            record_id=str(period.id),
            user=request.user,
            action_type='update',
            before=before,
            after=after,
            reason=f"Edición de periodo vacacional '{period.name}'",
            source='web'
        )
        
        return JsonResponse({'ok': True})
    
    except (ValueError, TypeError) as e:
        return JsonResponse({'error': f'Datos inválidos: {str(e)}'}, status=400)
```

### Tarea 4.4: Vista para eliminar periodo (POST - soft delete)
**Función**: `delete_vacation_period(request)`

```python
@login_required_with_delegation_support
@require_POST
def delete_vacation_period(request):
    """Soft-delete de un periodo vacacional"""
    company = get_company(request)
    
    if not is_manager(request, company):
        raise PermissionDenied()
    
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido'}, status=400)
    
    period_id = data.get('id')
    if not period_id:
        return JsonResponse({'error': 'ID del periodo requerido'}, status=400)
    
    period = get_object_or_404(
        VacationPeriodMultiplier, 
        id=period_id, 
        company=company,
        deleted_at__isnull=True
    )
    
    # Soft-delete
    before = {
        'name': period.name,
        'deleted_at': None,
    }
    
    period.deleted_at = timezone.now()
    period.save()
    
    # Auditoría
    AuditLog.objects.create(
        id=uuid.uuid4(),
        table_name='vacation_period_multipliers',
        record_id=str(period.id),
        user=request.user,
        action_type='voided',
        before=before,
        after={'deleted_at': str(period.deleted_at)},
        reason=f"Eliminación (soft-delete) de periodo '{period.name}'",
        source='web'
    )
    
    return JsonResponse({'ok': True})
```

---

## BLOQUE 5: URLs (core/urls.py) ✅ COMPLETADO

### Archivo a modificar:
- `core/urls.py`

### Tarea 5.1: Registrar rutas CRUD

Agregar bajo la sección de REQUESTS - LEAVE REQUESTS:

```python
# Vacation Period Multipliers (manager only)
path('api/vacation-periods/', requests_views.list_vacation_periods, name='list_vacation_periods'),
path('api/vacation-period/create/', requests_views.create_vacation_period, name='create_vacation_period'),
path('api/vacation-period/edit/', requests_views.edit_vacation_period, name='edit_vacation_period'),
path('api/vacation-period/delete/', requests_views.delete_vacation_period, name='delete_vacation_period'),
```

---

## BLOQUE 6: Template entity_info.html

### Archivo a modificar:
- `templates/team/entity_info.html`

### Tarea 6.1: Agregar sección de "Periodos vacacionales especiales"

**Ubicación**: Después de la card "Configuración de jornada" (después de la línea 167)

```html
{# ── Card: Periodos vacacionales especiales ── #}
{% if user_role == 'manager' or user_role == 'admin' %}
<div class="card mb-3">
  <div class="card-header fw-semibold d-flex justify-content-between align-items-center">
    <span><i class="bi bi-calendar-event"></i> Periodos vacacionales especiales</span>
    <button type="button" class="btn btn-sm btn-success" onclick="openAddPeriodModal()" data-bs-toggle="modal" data-bs-target="#addPeriodModal">
      <i class="bi bi-plus-circle"></i> Agregar período
    </button>
  </div>
  <div class="card-body">
    <div id="vacation-periods-container">
      <div class="text-center text-muted py-3">
        <small>Cargando periodos...</small>
      </div>
    </div>
  </div>
</div>

{# ── Modal: Agregar/Editar Periodo ── #}
<div class="modal fade" id="addPeriodModal" tabindex="-1" aria-labelledby="periodModalLabel" aria-hidden="true">
  <div class="modal-dialog">
    <div class="modal-content">
      <div class="modal-header">
        <h5 class="modal-title" id="periodModalLabel">Agregar período vacacional</h5>
        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
      </div>
      <div class="modal-body">
        <div class="mb-3">
          <label class="form-label">Nombre del período</label>
          <input type="text" class="form-control form-control-sm" id="period_name" placeholder="ej: Semana Santa" maxlength="100">
        </div>
        <div class="row mb-3">
          <div class="col-md-6">
            <label class="form-label">Fecha inicio</label>
            <input type="date" class="form-control form-control-sm" id="period_date_from">
          </div>
          <div class="col-md-6">
            <label class="form-label">Fecha fin</label>
            <input type="date" class="form-control form-control-sm" id="period_date_to">
          </div>
        </div>
        <div class="mb-3">
          <label class="form-label">Multiplicador de horas</label>
          <div class="input-group input-group-sm">
            <input type="number" class="form-control" id="period_multiplier" 
              min="0.1" max="2.0" step="0.1" value="1.0" required>
            <span class="input-group-text">×</span>
          </div>
          <small class="form-text text-muted">Rango permitido: 0.1 a 2.0 (ejemplo: 0.8 = 80% de jornada)</small>
        </div>
      </div>
      <div class="modal-footer">
        <button type="button" class="btn btn-sm btn-secondary" data-bs-dismiss="modal">Cancelar</button>
        <button type="button" class="btn btn-sm btn-primary" id="savePeriodBtn">Guardar</button>
      </div>
    </div>
  </div>
</div>

{% endif %}
```

### Tarea 6.2: Agregar sección para editar default_vacation_days

**Ubicación**: Dentro de la card "Configuración de jornada", después de "Cierre automático" (después de la línea 120)

```html
          <div class="col-6 col-md-3">
            <label class="form-label text-muted small mb-1">Días vacaciones anuales</label>
            <div class="view-mode">{{ settings.default_vacation_days }} días</div>
            <div class="edit-mode d-none">
              <input class="form-control form-control-sm" type="number" name="default_vacation_days"
                value="{{ settings.default_vacation_days }}" min="1" max="365">
            </div>
          </div>
```

### Tarea 6.3: Agregar JavaScript para gestionar periodos

**Ubicación**: Antes del script de toggleEdit() (antes de la línea 178)

```html
<script>
// ========== Vacation Periods Management ==========

let currentEditingPeriodId = null;
const vacationPeriodsModal = new bootstrap.Modal(document.getElementById('addPeriodModal'));

// Cargar periodos al cargar la página
document.addEventListener('DOMContentLoaded', function() {
  loadVacationPeriods();
  
  // Cargar periodos cada 5 segundos si estamos viendo el modal
  document.getElementById('addPeriodModal').addEventListener('show.bs.modal', loadVacationPeriods);
});

async function loadVacationPeriods() {
  try {
    const response = await fetch("{% url 'list_vacation_periods' %}");
    const data = await response.json();
    
    if (response.ok) {
      renderVacationPeriods(data.periods);
    } else {
      showError("Error al cargar períodos: " + (data.error || 'Desconocido'));
    }
  } catch (e) {
    console.error('Error loading vacation periods:', e);
  }
}

function renderVacationPeriods(periods) {
  const container = document.getElementById('vacation-periods-container');
  
  if (!periods || periods.length === 0) {
    container.innerHTML = '<div class="text-center text-muted py-3"><small>No hay períodos especiales configurados</small></div>';
    return;
  }
  
  let html = `
    <div class="table-responsive">
      <table class="table table-sm table-hover mb-0">
        <thead class="table-light">
          <tr>
            <th>Nombre</th>
            <th>Fechas</th>
            <th>Multiplicador</th>
            <th class="text-end">Acciones</th>
          </tr>
        </thead>
        <tbody>
  `;
  
  periods.forEach(p => {
    const dateFrom = new Date(p.date_from).toLocaleDateString('es-ES');
    const dateTo = new Date(p.date_to).toLocaleDateString('es-ES');
    
    html += `
      <tr>
        <td><strong>${p.name}</strong></td>
        <td><small>${dateFrom} → ${dateTo}</small></td>
        <td><span class="badge text-bg-info">${p.multiplier}×</span></td>
        <td class="text-end">
          <button class="btn btn-xs btn-warning py-0 px-1" 
            onclick="editPeriod('${p.id}', '${p.name}', '${p.date_from}', '${p.date_to}', ${p.multiplier})"
            title="Editar">
            <i class="bi bi-pencil-square"></i>
          </button>
          <button class="btn btn-xs btn-danger py-0 px-1" 
            onclick="deletePeriod('${p.id}', '${p.name}')"
            title="Eliminar">
            <i class="bi bi-trash"></i>
          </button>
        </td>
      </tr>
    `;
  });
  
  html += `
        </tbody>
      </table>
    </div>
  `;
  
  container.innerHTML = html;
}

function openAddPeriodModal() {
  currentEditingPeriodId = null;
  document.getElementById('periodModalLabel').textContent = 'Agregar período vacacional';
  document.getElementById('period_name').value = '';
  document.getElementById('period_date_from').value = '';
  document.getElementById('period_date_to').value = '';
  document.getElementById('period_multiplier').value = '1.0';
}

function editPeriod(id, name, dateFrom, dateTo, multiplier) {
  currentEditingPeriodId = id;
  document.getElementById('periodModalLabel').textContent = 'Editar período vacacional';
  document.getElementById('period_name').value = name;
  document.getElementById('period_date_from').value = dateFrom;
  document.getElementById('period_date_to').value = dateTo;
  document.getElementById('period_multiplier').value = multiplier;
  vacationPeriodsModal.show();
}

document.getElementById('savePeriodBtn').addEventListener('click', async function() {
  const name = document.getElementById('period_name').value.trim();
  const dateFrom = document.getElementById('period_date_from').value;
  const dateTo = document.getElementById('period_date_to').value;
  const multiplier = parseFloat(document.getElementById('period_multiplier').value);
  
  // Validaciones básicas
  if (!name) {
    showError('El nombre del período es requerido');
    return;
  }
  if (!dateFrom || !dateTo) {
    showError('Las fechas son requeridas');
    return;
  }
  if (isNaN(multiplier) || multiplier < 0.1 || multiplier > 2.0) {
    showError('El multiplicador debe estar entre 0.1 y 2.0');
    return;
  }
  if (new Date(dateFrom) > new Date(dateTo)) {
    showError('La fecha de inicio debe ser anterior a la de fin');
    return;
  }
  
  try {
    const url = currentEditingPeriodId 
      ? "{% url 'edit_vacation_period' %}"
      : "{% url 'create_vacation_period' %}";
    
    const payload = {
      name,
      date_from: dateFrom,
      date_to: dateTo,
      multiplier,
    };
    
    if (currentEditingPeriodId) {
      payload.id = currentEditingPeriodId;
    }
    
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': '{{ csrf_token }}'
      },
      body: JSON.stringify(payload)
    });
    
    const data = await response.json();
    
    if (response.ok && data.ok) {
      showSuccess(currentEditingPeriodId ? 'Período actualizado' : 'Período agregado');
      vacationPeriodsModal.hide();
      loadVacationPeriods();
    } else {
      showError('Error: ' + (data.error || 'Desconocido'));
    }
  } catch (e) {
    showError('Error de conexión: ' + e.message);
  }
});

function deletePeriod(id, name) {
  if (!confirm(`¿Eliminar el período "${name}"?`)) {
    return;
  }
  
  fetch("{% url 'delete_vacation_period' %}", {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': '{{ csrf_token }}'
    },
    body: JSON.stringify({ id })
  })
  .then(response => response.json())
  .then(data => {
    if (data.ok) {
      showSuccess('Período eliminado');
      loadVacationPeriods();
    } else {
      showError('Error: ' + (data.error || 'Desconocido'));
    }
  })
  .catch(e => showError('Error: ' + e.message));
}

function showError(msg) {
  alert('❌ ' + msg);
}

function showSuccess(msg) {
  console.log('✓ ' + msg);
  // Podrías usar un toast o mensaje mejor aquí
}
</script>
```

---

## BLOQUE 7: Lógica de Reportes

### Archivo a modificar:
- `aeptic_reports/services.py` → Función `get_vacation_hours_for_day()`

### Tarea 7.1: Modificar cálculo de horas de vacaciones

**Ubicación**: Función `get_vacation_hours_for_day()`

**Código actual** (línea ~106):
```python
def get_vacation_hours_for_day(user_id, company_id, date):
    """Obtener horas de vacaciones para un día específico"""
    try:
        leave_request = LeaveRequest.objects.filter(
            user_id=user_id,
            company_id=company_id,
            leave_type='vacation',
            status='approved',
            start_date__lte=date,
            end_date__gte=date
        ).first()

        if leave_request:
            # Retornar jornada laboral completa (default 8h)
            return get_work_hours_per_day(company_id)

        return 0.0

    except Exception:
        return 0.0
```

**Modificación**:
```python
def get_vacation_hours_for_day(user_id, company_id, date):
    """Obtener horas de vacaciones para un día específico
    
    Utiliza el multiplicador de horas (hour_multiplier) si está disponible
    para periodos vacacionales especiales.
    """
    try:
        leave_request = LeaveRequest.objects.filter(
            user_id=user_id,
            company_id=company_id,
            leave_type='vacation',
            status='approved',
            start_date__lte=date,
            end_date__gte=date
        ).first()

        if leave_request:
            # Obtener jornada laboral diaria
            daily_hours = get_work_hours_per_day(company_id)
            
            # Aplicar multiplicador (default 1.0)
            multiplier = leave_request.hour_multiplier or 1.0
            
            # Calcular horas finales
            vacation_hours = daily_hours * multiplier
            
            return round(vacation_hours, 2)

        return 0.0

    except Exception:
        return 0.0
```

---

## Resumen de Cambios por Archivo

| Archivo | Cambios |
|---------|---------|
| `requests/models.py` | + VacationPeriodMultiplier + get_multiplier_for_range()  + hour_multiplier a LeaveRequest + get_consumed_days() |
| `admin/models.py` | + default_vacation_days a CompanySettings |
| `requests/views.py` | + list_vacation_periods() + create_vacation_period() + edit_vacation_period() + delete_vacation_period() + lógica en api_leave_review() para sugerir multiplier |
| `core/urls.py` | + 4 rutas CRUD para vacation_periods |
| `templates/team/entity_info.html` | + sección "Periodos vacacionales especiales" + campo default_vacation_days + JavaScript para gestión |
| `aeptic_reports/services.py` | ~ modificar get_vacation_hours_for_day() |

---

## Orden de Implementación Recomendado

1. **BLOQUE 1**: Crear/modificar modelos → Pruebas básicas en shell
2. **BLOQUE 4**: Crear vistas CRUD → Probar endpoints con curl/Postman
3. **BLOQUE 6**: Agregar URLs y template entity_info
4. **BLOQUE 2**: Modificar vista api_leave_review()
5. **BLOQUE 3**: Actualizar template de aprobación
6. **BLOQUE 7**: Modificar lógica de reportes
7. **Integración**: Pruebas E2E del flujo completo

---

## Notas Técnicas Importantes

- **Soft-delete**: Usar `.filter(deleted_at__isnull=True)` en todas las queries
- **Manager check**: Usar `is_manager(request, company)` que ya existe en core/services
- **Auditoría**: Siempre crear AuditLog cuando se modifique vacaciones
- **Validación de fechas**: `strptime()` con formato 'YYYY-MM-DD'
- **JSON responses**: Consistent format con `{'ok': True}` o `{'error': 'msg'}`
- **Permissions**: Solo managers pueden CRUD periodos de su empresa
- **Décimas**: Usar `Decimal` en modelos, convertir a float en JSON

