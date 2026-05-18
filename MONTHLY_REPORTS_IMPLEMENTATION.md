# 📋 MONTHLY REPORTS IMPLEMENTATION PLAN
## Módulo de Informes Mensuales - Excel Dinámico + Upload

---

## 📌 CONTEXTO Y REQUISITOS

### Tabla BD (✅ YA CREADA)
```sql
CREATE TABLE monthly_reports (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    report_date DATE NOT NULL,  -- Primer día del mes (ej: 2026-05-01)
    status report_status DEFAULT 'draft',  -- draft, generated, signed, archived
    generated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    signed_at TIMESTAMPTZ,
    document_path VARCHAR(500),
    UNIQUE(user_id, company_id, report_date)
);
```

### Modelo Django (✅ YA CREADO)
- Ubicado en `aeptic_reports/models.py`
- Con propiedades: `is_signed`, `month`, `year`

### Datos que debe autocompletar el Excel
- **De TimeEntries**: hora entrada, hora salida, cálculo de horas ordinarias/extras
- **De LeaveRequest**: vacaciones (vacation), ausencias (absence) con tipos específicos
- **De TimeEntryEvent**: pausas (PAUSE_START/PAUSE_END) para columna "Ausencia"
- **De CompanySettings**: horario laboral para determinar ordinarias vs extras

### Formatos de descarga
- ✅ XLSX (openpyxl)
- ✅ CSV (separador `;`, codificación UTF-8 BOM, estándar europeo)

### Lógica de UI
- Toggle selector mes anterior | mes actual (sin reload de página)
- File upload input asociado a cada mes (HTMX o JS vanilla)
- Al cambiar toggle: actualizar plantilla Excel mostrada
- Identificar automáticamente el documento al month del botón desde el que se subió

---

## 🔨 BLOQUES DE IMPLEMENTACIÓN

### BLOQUE 1: SERVICIOS Y HELPERS (Generar Excel/CSV)
**Archivo:** `aeptic_reports/services.py` (NUEVO)

#### 1.1 Clase `ExcelReportGenerator`
```python
class ExcelReportGenerator:
    def __init__(self, user, company, report_date):
        """
        Args:
            user: Users instance
            company: Companies instance
            report_date: date object for first day of month (2026-05-01)
        """
        self.user = user
        self.company = company
        self.report_date = report_date  # First day of month
        self.start_date = report_date
        self.end_date = (report_date + timedelta(days=31)).replace(day=1) - timedelta(days=1)
        self.workbook = None
        self.worksheet = None
    
    def generate(self) -> BytesIO:
        """Generate Excel file and return as BytesIO"""
        # 1. Create workbook structure
        # 2. Add headers (Fecha, Día semana, Entrada, Salida, Ausencia, Vacaciones, Baja, Festivo, Ord Horas, Extras, Firma)
        # 3. Generate rows for each day of month (28-31 days)
        # 4. Populate data from DB:
        #    - Get TimeEntries for user/company/month
        #    - Get LeaveRequests (vacation/absence/sick)
        #    - Get TimeEntryEvents (pause times for "Ausencia" column)
        #    - Get CompanySettings (work hours to calc ordinarias/extras)
        # 5. Format weekends (gray background, red text)
        # 6. Add formulas for total hours if needed
        # 7. Save to BytesIO and return
```

**Métodos internos necesarios:**
- `_create_workbook()`: Inicializar workbook con openpyxl
- `_create_headers()`: Crear fila de encabezados con estilos
- `_get_days_in_month()`: Obtener cantidad de días del mes
- `_populate_time_entries()`: Llenar hora entrada/salida desde BD
- `_populate_absences()`: Llenar tiempo en pausa (columna Ausencia)
- `_populate_leaves()`: Llenar vacaciones/baja/ausencia desde LeaveRequest
- `_populate_holidays()`: Llenar festivos (si existe tabla de holidays)
- `_calculate_hours()`: Calcular horas ordinarias y extras
- `_highlight_weekends()`: Aplicar formato visual a fines de semana
- `_apply_styles()`: Aplicar colores, bordes, fuentes
- `_save_to_bytesio()`: Guardar workbook a BytesIO y retornar

#### 1.2 Columnas del Excel (EN ORDEN)
| N | Columna | Tipo | Auto-completado | Editable |
|---|---------|------|-----------------|----------|
| A | Fecha | DATE (DD/MM/YYYY) | ✅ | ❌ |
| B | Día Semana | TEXT (Mon, Tue, etc) | ✅ | ❌ |
| C | Hora Entrada | TIME (HH:MM) | ✅ (de TimeEntries) | ✅ |
| D | Hora Salida | TIME (HH:MM) | ✅ (de TimeEntries) | ✅ |
| E | Ausencia | DECIMAL (horas) | ✅ (pausas TimeEntryEvent) | ✅ |
| F | Vacaciones | DECIMAL (horas) | ✅ (de LeaveRequest.vacation) | ✅ |
| G | Baja | TEXT (X + Motivo) | ✅ (de LeaveRequest con leave_reason ≠ vacation) | ✅ |
| H | Festivo | DECIMAL (horas) | ✅ (si existe tabla holidays) | ❌ |
| I | Total Horas Ordinarias | DECIMAL | ✅ (fórmula o cálculo) | ❌ |
| J | Total Horas Extras | DECIMAL | ✅ (fórmula o cálculo) | ❌ |
| K | Firma Trabajador | TEXT | ❌ (vacío) | ✅ |

#### 1.3 Lógica de "Ausencia" (Columna E)
- Suma de TODAS las pausas ese día: `TimeEntryEvent.objects.filter(time_entry__date=day, event_type__in=['pause_start', 'pause_end'])`
- Calcular duraciones entre pause_start y pause_end
- Expresar en horas decimales (ej: 1.5 = 1 hora 30 minutos)

#### 1.4 Lógica de "Vacaciones" / "Baja" (Columnas F, G)
- **Columna F (Vacaciones):**
  - Buscar `LeaveRequest` para ese día dentro de `[start_date, end_date]`
  - Si `leave_type='vacation'` y `status='approved'` → mostrar `8` horas (o valor de jornada laboral)
  
- **Columna G (Baja):**
  - Buscar `LeaveRequest` para ese día con `leave_type='absence'` y `status='approved'`
  - Si existe cualquier `leave_reason` que NO sea 'annual' → mostrar **`X - {motivo_legible}`**
  - Mapeo de leave_reason a motivo legible:
    - `sick` → "Baja por enfermedad"
    - `maternity` → "Maternidad / Paternidad"
    - `wedding` → "Matrimonio"
    - `bereavement` → "Fallecimiento familiar"
    - `medical_appointment` → "Cita médica"
    - `legal_duty` → "Deber público / legal"
    - `personal` → "Asuntos propios"
    - `other` → "Otro"
  
  **Ejemplo:** Si el usuario tiene una baja por enfermedad el 5 de mayo, columna G mostrará: `X - Baja por enfermedad`

#### 1.5 Lógica de "Total Horas Ordinarias" (Columna I)
- Horas trabajadas (C-D) MENOS pausas (E) MENOS vacaciones (F) MENOS festivos (H)
- **Nota:** La columna G (Baja) es solo indicativa (muestra X + motivo), NO se descuenta de horas ordinarias
  - Si un empleado tiene baja, se asume que NO trabajó ese día, por lo que Entrada/Salida estarán vacías
  - El descuento de horas se hace automáticamente por ausencia de entrada/salida
- Si resultado > 8 horas: el exceso pasa a "extras"
- Si resultado <= 0: = 0

#### 1.6 Lógica de "Total Horas Extras" (Columna J)
- Si (C-D) - (E+F+H) > 8 → extras = diferencia
- Si <= 8 → extras = 0
- **Nota:** G (Baja) no participa en el cálculo, es solo info visual

#### 1.7 Formateo Visual (Fines de Semana)
- Detectar sábados y domingos
- Aplicar formato:
  - Fondo gris claro (ej: RGB 220, 220, 220)
  - Texto en rojo (ej: RGB 255, 0, 0)
  - Border gris oscuro

#### 1.8 Clase `CSVReportGenerator`
```python
class CSVReportGenerator:
    """Similar a ExcelReportGenerator pero genera CSV"""
    def generate(self) -> str:
        # 1. Generar datos (reusar logic de Excel si es posible)
        # 2. Formatear como CSV con:
        #    - Separador: `;` (semicolon)
        #    - Codificación: UTF-8 with BOM (u'\ufeff')
        #    - Quotechar: `"`
        # 3. Retornar string CSV
```

**Método:**
- `_generate_csv_content()`: Construir filas CSV
- `_add_bom()`: Agregar BOM UTF-8 al inicio

#### 1.9 Helper Functions en `aeptic_reports/services.py`
```python
# Mapeo de leave_reason a etiqueta legible
LEAVE_REASON_LABELS = {
    'sick': 'Baja por enfermedad',
    'maternity': 'Maternidad / Paternidad',
    'wedding': 'Matrimonio',
    'bereavement': 'Fallecimiento familiar',
    'medical_appointment': 'Cita médica',
    'legal_duty': 'Deber público / legal',
    'personal': 'Asuntos propios',
    'other': 'Otro',
}

def get_pause_hours_for_day(user_id, company_id, date) -> float:
    """Calcular total pausas del día en horas"""
    # Query TimeEntryEvent para ese día
    
def get_vacation_hours_for_day(user_id, company_id, date) -> float:
    """Obtener horas de vacaciones para un día específico"""
    # Query LeaveRequest con leave_type='vacation' y status='approved'
    
def get_absence_for_day(user_id, company_id, date) -> str:
    """Obtener ausencia (baja) para un día: retorna 'X - Motivo' o vacío"""
    # Query LeaveRequest con leave_type='absence', status='approved'
    # Si existe, retorna f"X - {LEAVE_REASON_LABELS[leave_reason]}"
    # Si no existe, retorna ""
    
def get_work_hours_per_day(company_id) -> float:
    """Obtener jornada laboral de la empresa (default 8h)"""
    # Query CompanySettings o usar default 8
    
def calculate_ordinary_hours(work_time, pauses, vacations, holidays, work_hours_per_day=8) -> float:
    """Calcular horas ordinarias
    
    work_time: horas trabajadas (entrada - salida)
    pauses: horas de pausa
    vacations: horas de vacaciones
    holidays: horas festivos
    
    Fórmula: work_time - pauses - vacations - holidays
    Si > work_hours_per_day: se recorta a work_hours_per_day
    """
    
def calculate_extra_hours(work_time, ordinary_hours, work_hours_per_day=8) -> float:
    """Calcular horas extras
    
    extras = work_time - ordinary_hours
    Si <= 0: = 0
    """
```

---

### BLOQUE 2: VISTAS DJANGO (Class-Based Views)
**Archivo:** `aeptic_reports/views.py`

#### 2.1 Vista `MonthlyReportDownloadView` (GET)
```python
class MonthlyReportDownloadView(LoginRequiredMixin, View):
    """
    GET /api/monthly-reports/download/
    Params: ?month=2026-05-01&format=xlsx|csv
    
    - month: YYYY-MM-DD (primer día del mes)
    - format: 'xlsx' | 'csv' (default: xlsx)
    
    Flujo:
    1. Validar user pertenece a company (de sesión o URL param)
    2. Validar que month sea válido
    3. Obtener o crear MonthlyReport con status=draft
    4. Generar archivo con ExcelReportGenerator o CSVReportGenerator
    5. Guardar referencia en BD (actualizar document_path si es necesario)
    6. Retornar archivo como descarga
    7. Auditar: CREATE en audit_log con tabla='monthly_reports'
    """
    def get(self, request):
        pass
```

**Lógica interna:**
- Leer parámetro `month` (formato: YYYY-MM-DD, ej: 2026-05-01)
- Leer parámetro `format` (xlsx o csv, default xlsx)
- Obtener `company_id` de sesión: `request.session.get('company_id')`
- Validar que user es miembro de esa company
- Crear/actualizar MonthlyReport con status='generated'
- Generar archivo llamando `ExcelReportGenerator` o `CSVReportGenerator`
- Preparar `HttpResponse` con:
  ```python
  response = HttpResponse(
      file_content,
      content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'  # xlsx
      # O: 'text/csv'  # csv
  )
  response['Content-Disposition'] = f'attachment; filename="report_{user.email}_{month}.xlsx"'
  ```
- Auditar la acción
- Retornar response

#### 2.2 Vista `MonthlyReportUploadView` (POST)
```python
class MonthlyReportUploadView(LoginRequiredMixin, View):
    """
    POST /api/monthly-reports/upload/
    Body: multipart/form-data con:
      - file: archivo Excel/CSV firmado
      - month: YYYY-MM-DD (identificar a qué mes pertenece)
    
    Flujo:
    1. Validar que file está presente
    2. Validar extensión (.xlsx o .csv)
    3. Validar que month es válido
    4. Obtener o crear MonthlyReport (con status='draft' inicialmente)
    5. Guardar archivo en storage (carpeta: media/monthly_reports/{user_id}/{company_id}/)
    6. Actualizar MonthlyReport:
       - document_path = ruta relativa guardada
       - status = 'signed'
       - signed_at = timezone.now()
    7. Auditar: UPDATE en audit_log
    8. Retornar JSON response con status y mensaje
    """
    def post(self, request):
        pass
```

**Lógica interna:**
- Obtener `file` de `request.FILES['file']`
- Validar nombre archivo
- Obtener `month` de `request.POST.get('month')`
- Obtener `company_id` de sesión
- Validar pertenencia a company
- Crear carpeta: `settings.MEDIA_ROOT / 'monthly_reports' / str(user.id) / str(company.id)`
- Guardar archivo con nombre: `{user.email}_{report_date}.{ext}`
- Crear/actualizar MonthlyReport en BD
- Retornar JSON: `{'status': 'success', 'message': 'Documento subido', 'report_id': str(report.id)}`

#### 2.3 Vista `MonthlyReportListView` (GET - para mostrar status)
```python
class MonthlyReportListView(LoginRequiredMixin, View):
    """
    GET /api/monthly-reports/
    Retorna lista de MonthlyReports del user actual
    
    Response:
    {
        'reports': [
            {
                'id': 'uuid',
                'report_date': '2026-05-01',
                'month': 5,
                'year': 2026,
                'month_name': 'Mayo',
                'status': 'signed',
                'signed_at': '2026-05-15T10:30:00Z',
                'document_path': 'monthly_reports/user_id/company_id/email_2026-05-01.xlsx'
            }
        ]
    }
    """
    def get(self, request):
        pass
```

**Validaciones comunes en varias vistas:**
```python
def _validate_user_company_access(user, company_id):
    """Verificar que user pertenece a company"""
    membership = UserCompany.objects.filter(
        user=user,
        company_id=company_id
    ).first()
    if not membership:
        raise PermissionDenied()
    return membership

def _validate_month_format(month_str):
    """Validar formato YYYY-MM-DD y que sea primer día del mes"""
    try:
        date_obj = datetime.strptime(month_str, '%Y-%m-%d').date()
        if date_obj.day != 1:
            raise ValueError("Must be first day of month")
        return date_obj
    except:
        raise ValueError("Invalid month format")
```

---

### BLOQUE 3: RUTAS Y URLS
**Archivo:** `aeptic_reports/urls.py` (NUEVO)

```python
from django.urls import path
from . import views

app_name = 'aeptic_reports'

urlpatterns = [
    # Descargar reporte (Excel o CSV)
    path('download/', views.MonthlyReportDownloadView.as_view(), name='download_report'),
    
    # Subir documento firmado
    path('upload/', views.MonthlyReportUploadView.as_view(), name='upload_report'),
    
    # Listar reportes del usuario
    path('list/', views.MonthlyReportListView.as_view(), name='list_reports'),
]
```

**Integrar en `core/urls.py`:**
```python
from aeptic_reports import views as aeptic_views

urlpatterns = [
    # ... existing routes ...
    
    # Monthly Reports
    path('reports/', include('aeptic_reports.urls')),
]
```

---

### BLOQUE 4: TEMPLATES
**Archivo:** `templates/aeptic_reports/aeptic_summary.html` (USAR EXISTENTE)

#### 4.1 Estructura a implementar en el template existente
El template debe heredar de `base/base.html` y contener:

```html
{% extends 'base/base.html' %}
{% load django_bootstrap5 %}
{% load static %}

{% block title %}Informes Mensuales{% endblock %}

{% block content %}
<link rel="stylesheet" href="{% static 'css/aeptic_reports.css' %}">

<div class="container-fluid py-4">
    <div class="row mb-4">
        <div class="col-12">
            <h2 class="mb-0">
                <i class="bi bi-file-earmark-pdf"></i> Informes Mensuales
            </h2>
            <small class="text-muted">Descarga, firma y carga tus informes mensuales de horas</small>
        </div>
    </div>

    <!-- TOGGLE SELECTOR MONTHS -->
    <div class="row mb-4">
        <div class="col-12">
            <div class="months-toggle-section">
                <div class="toggle-container">
                    <!-- Mes anterior -->
                    <div class="toggle-group" id="prev-month-group">
                        <div class="toggle-month-info">
                            <button class="month-toggle-btn" id="prev-month-btn" data-month="2026-04-01">
                                <i class="bi bi-calendar"></i>
                                <span class="month-name">Abril 2026</span>
                            </button>
                            <span class="toggle-indicator"></span>
                        </div>
                        
                        <div class="file-input-wrapper">
                            <input type="file" id="prev-month-file" class="month-file-input" 
                                   accept=".xlsx,.csv" data-month="2026-04-01" hidden>
                            <label for="prev-month-file" class="file-upload-label">
                                <i class="bi bi-cloud-upload"></i> Subir firmado
                            </label>
                        </div>
                    </div>
                    
                    <!-- Mes actual -->
                    <div class="toggle-group active" id="current-month-group">
                        <div class="toggle-month-info">
                            <button class="month-toggle-btn" id="current-month-btn" data-month="2026-05-01">
                                <i class="bi bi-calendar"></i>
                                <span class="month-name">Mayo 2026</span>
                            </button>
                            <span class="toggle-indicator"></span>
                        </div>
                        
                        <div class="file-input-wrapper">
                            <input type="file" id="current-month-file" class="month-file-input" 
                                   accept=".xlsx,.csv" data-month="2026-05-01" hidden>
                            <label for="current-month-file" class="file-upload-label">
                                <i class="bi bi-cloud-upload"></i> Subir firmado
                            </label>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- BOTONES DESCARGA -->
    <div class="row mb-4">
        <div class="col-12">
            <div class="download-buttons-section">
                <button id="download-xlsx-btn" class="btn btn-primary std-btn">
                    <i class="bi bi-file-earmark-excel"></i> Descargar Excel (.xlsx)
                </button>
                <button id="download-csv-btn" class="btn btn-outline-primary std-btn">
                    <i class="bi bi-file-earmark-csv"></i> Descargar CSV (.csv)
                </button>
            </div>
        </div>
    </div>

    <!-- STATUS / MENSAJES -->
    <div class="row mb-4">
        <div class="col-12">
            <div id="status-message" class="alert" style="display:none;" role="alert"></div>
        </div>
    </div>

    <!-- PREVIEW / TABLA PRINCIPAL -->
    <div class="row">
        <div class="col-12">
            <div id="report-preview-container" class="card">
                <div class="card-header bg-dark text-white">
                    <h6 class="mb-0">Preview de Reporte</h6>
                </div>
                <div class="card-body">
                    <div class="table-scroll-container">
                        <table id="report-table" class="table table-sm table-bordered table-hover mb-0">
                            <thead>
                                <!-- Headers populated by JavaScript -->
                            </thead>
                            <tbody>
                                <!-- Rows populated by JavaScript -->
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>

<script src="{% static 'aeptic_reports/monthly_reports.js' %}"></script>
{% endblock %}
```

#### 4.2 CSS personalizado para aeptic_reports
**Archivo:** `static/css/aeptic_reports.css` (NUEVO)

```css
/* --- VARIABLES Y UTILIDADES --- */
:root {
    --transition-speed: 0.2s;
    --primary-color: #007bff;
    --success-color: #28a745;
    --danger-color: #dc3545;
}

/* --- TOGGLE MONTHS SECTION --- */
.months-toggle-section {
    margin-bottom: 2rem;
}

.toggle-container {
    display: flex;
    justify-content: space-between;
    gap: 2rem;
    flex-wrap: wrap;
}

.toggle-group {
    flex: 1;
    min-width: 300px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 1.5rem;
    border: 2px solid #e0e0e0;
    border-radius: 8px;
    background: #f9f9f9;
    transition: all 0.3s ease;
}

.toggle-group:hover {
    border-color: #bbb;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.toggle-group.active {
    border-color: var(--primary-color);
    background: #e7f3ff;
    box-shadow: 0 4px 12px rgba(0, 123, 255, 0.15);
}

.toggle-month-info {
    flex: 1;
}

.month-toggle-btn {
    background: none;
    border: none;
    font-size: 1.1rem;
    font-weight: 600;
    cursor: pointer;
    padding: 0.5rem;
    color: #333;
    display: flex;
    align-items: center;
    gap: 0.75rem;
    transition: color 0.2s;
}

.month-toggle-btn:hover {
    color: var(--primary-color);
}

.toggle-group.active .month-toggle-btn {
    color: var(--primary-color);
}

.toggle-indicator {
    display: inline-block;
    width: 14px;
    height: 14px;
    border-radius: 50%;
    background: #d0d0d0;
    margin-left: 0.75rem;
    transition: background 0.2s;
}

.toggle-group.active .toggle-indicator {
    background: var(--primary-color);
    box-shadow: 0 0 8px rgba(0, 123, 255, 0.4);
}

/* --- FILE UPLOAD --- */
.file-input-wrapper {
    flex-shrink: 0;
}

.file-upload-label {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    cursor: pointer;
    padding: 0.75rem 1.25rem;
    background: var(--success-color);
    color: white;
    border-radius: 6px;
    font-weight: 500;
    transition: all 0.2s;
    white-space: nowrap;
}

.file-upload-label:hover {
    background: #218838;
    transform: translateY(-2px);
    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.15);
}

.file-upload-label:active {
    transform: translateY(0);
}

.file-upload-label.loading {
    opacity: 0.7;
    pointer-events: none;
}

/* --- DOWNLOAD BUTTONS SECTION --- */
.download-buttons-section {
    display: flex;
    gap: 1rem;
    flex-wrap: wrap;
}

.std-btn {
    border-radius: 6px;
    font-weight: 600;
    letter-spacing: 0.3px;
    transition: all var(--transition-speed) ease-in-out;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    padding: 0.75rem 1.5rem;
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
}

.std-btn:hover:not(:disabled) {
    transform: translateY(-2px);
    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.15);
}

.std-btn:active:not(:disabled) {
    transform: translateY(0);
}

.std-btn:disabled {
    opacity: 0.6;
    cursor: not-allowed;
}

/* --- REPORT TABLE --- */
#report-preview-container {
    border-radius: 8px;
    overflow: hidden;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.table-scroll-container {
    max-height: 600px;
    overflow-y: auto;
    overflow-x: auto;
}

.table-scroll-container thead th {
    position: sticky;
    top: 0;
    z-index: 10;
    background-color: #212529 !important;
    color: white;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    font-weight: 600;
    font-size: 0.85rem;
    padding: 1rem 0.75rem;
    text-align: center;
}

.table-scroll-container tbody td {
    padding: 0.75rem;
    vertical-align: middle;
    font-size: 0.9rem;
}

.table-scroll-container tbody tr.weekend {
    background: #e8e8e8;
    color: #ff0000;
}

.table-scroll-container tbody tr.weekend td {
    font-weight: 500;
}

.table-scroll-container tbody tr:hover {
    background: #f5f5f5;
}

.table-scroll-container tbody tr.weekend:hover {
    background: #ddd;
}

/* --- SCROLLBAR STYLING --- */
.table-scroll-container::-webkit-scrollbar {
    width: 8px;
    height: 8px;
}

.table-scroll-container::-webkit-scrollbar-thumb {
    background: #adb5bd;
    border-radius: 4px;
}

.table-scroll-container::-webkit-scrollbar-thumb:hover {
    background: #6c757d;
}

.table-scroll-container::-webkit-scrollbar-track {
    background: #f8f9fa;
}

/* --- STATUS MESSAGES --- */
.alert {
    border-radius: 6px;
    padding: 1rem;
    animation: slideIn 0.3s ease-out;
}

@keyframes slideIn {
    from {
        opacity: 0;
        transform: translateY(-10px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

.alert-success {
    background: #d4edda;
    border: 1px solid #c3e6cb;
    color: #155724;
}

.alert-danger {
    background: #f8d7da;
    border: 1px solid #f5c6cb;
    color: #721c24;
}

.alert-info {
    background: #d1ecf1;
    border: 1px solid #bee5eb;
    color: #0c5460;
}

/* --- RESPONSIVE --- */
@media (max-width: 768px) {
    .toggle-container {
        flex-direction: column;
        gap: 1rem;
    }

    .toggle-group {
        flex-direction: column;
        gap: 1rem;
        min-width: auto;
    }

    .toggle-month-info {
        width: 100%;
    }

    .file-input-wrapper {
        width: 100%;
    }

    .file-upload-label {
        width: 100%;
        justify-content: center;
    }

    .download-buttons-section {
        flex-direction: column;
    }

    .download-buttons-section .btn {
        width: 100%;
        justify-content: center;
    }

    .table-scroll-container {
        max-height: 400px;
    }

    .table-scroll-container thead th {
        font-size: 0.75rem;
        padding: 0.5rem 0.25rem;
    }

    .table-scroll-container tbody td {
        font-size: 0.8rem;
        padding: 0.5rem 0.25rem;
    }
}

@media (max-width: 480px) {
    .container-fluid {
        padding-left: 0.5rem;
        padding-right: 0.5rem;
    }

    .std-btn {
        padding: 0.5rem 1rem;
        font-size: 0.9rem;
    }

    .month-toggle-btn {
        font-size: 1rem;
    }
}
```

#### 4.3 Integración en el template
- El archivo CSS se carga desde `static/css/aeptic_reports.css`
- El archivo JS se carga desde `static/aeptic_reports/monthly_reports.js`
- Ambos se cargan en el bloque `{% block content %}` del template heredado
- Usa Bootstrap 5 y Bootstrap Icons (ya disponibles en base.html)
- Utiliza variables CSS personalizadas (`:root`)
- Responsive design con media queries para móviles

---

### BLOQUE 5: JAVASCRIPT / FRONTEND
**Archivo:** `static/aeptic_reports/monthly_reports.js` (NUEVO)

#### 5.1 Lógica principal
```javascript
class MonthlyReportsManager {
    constructor() {
        this.currentMonth = new Date();
        this.currentMonth.setDate(1);  // Primer día del mes actual
        this.init();
    }
    
    init() {
        this.setupEventListeners();
        this.updateMonthButtons();
        this.loadReport(this.currentMonth);
    }
    
    setupEventListeners() {
        // Cambiar entre meses
        document.getElementById('prev-month-btn').addEventListener('click', () => {
            this.currentMonth = new Date(this.currentMonth.getFullYear(), 
                                          this.currentMonth.getMonth() - 1, 1);
            this.updateMonthButtons();
            this.loadReport(this.currentMonth);
        });
        
        document.getElementById('current-month-btn').addEventListener('click', () => {
            const today = new Date();
            this.currentMonth = new Date(today.getFullYear(), today.getMonth(), 1);
            this.updateMonthButtons();
            this.loadReport(this.currentMonth);
        });
        
        // Descargar Excel
        document.getElementById('download-xlsx-btn').addEventListener('click', () => {
            this.downloadReport('xlsx');
        });
        
        // Descargar CSV
        document.getElementById('download-csv-btn').addEventListener('click', () => {
            this.downloadReport('csv');
        });
        
        // Subir documentos
        document.getElementById('prev-month-file').addEventListener('change', (e) => {
            this.uploadReport(e, this.getPreviousMonth());
        });
        
        document.getElementById('current-month-file').addEventListener('change', (e) => {
            this.uploadReport(e, this.currentMonth);
        });
    }
    
    updateMonthButtons() {
        const prevMonth = this.getPreviousMonth();
        const currentToday = new Date();
        currentToday.setDate(1);
        
        const prevBtn = document.getElementById('prev-month-btn');
        const currBtn = document.getElementById('current-month-btn');
        
        const isCurrentMonthActive = 
            this.currentMonth.getFullYear() === currentToday.getFullYear() &&
            this.currentMonth.getMonth() === currentToday.getMonth();
        
        prevBtn.closest('.toggle-group').classList.toggle('active', !isCurrentMonthActive);
        currBtn.closest('.toggle-group').classList.toggle('active', isCurrentMonthActive);
    }
    
    loadReport(date) {
        // Hacer AJAX para obtener datos del mes y popular tabla
        const monthStr = this.dateToString(date);
        
        fetch(`/reports/list/?month=${monthStr}`)
            .then(r => r.json())
            .then(data => this.populateTable(data))
            .catch(err => this.showError('Error cargando reporte'));
    }
    
    downloadReport(format) {
        const monthStr = this.dateToString(this.currentMonth);
        window.location.href = `/reports/download/?month=${monthStr}&format=${format}`;
    }
    
    uploadReport(event, date) {
        const file = event.target.files[0];
        if (!file) return;
        
        const formData = new FormData();
        formData.append('file', file);
        formData.append('month', this.dateToString(date));
        
        fetch('/reports/upload/', {
            method: 'POST',
            headers: {
                'X-CSRFToken': this.getCSRFToken()
            },
            body: formData
        })
        .then(r => r.json())
        .then(data => {
            if (data.status === 'success') {
                this.showSuccess('Documento subido correctamente');
                this.loadReport(date);
            } else {
                this.showError(data.message || 'Error al subir');
            }
        })
        .catch(err => this.showError('Error de red'));
    }
    
    populateTable(data) {
        // Llenar tabla con datos (si es preview)
        // O solo mostrar mensaje de estado si no es preview
    }
    
    getPreviousMonth() {
        const prev = new Date(this.currentMonth);
        prev.setMonth(prev.getMonth() - 1);
        return prev;
    }
    
    dateToString(date) {
        return date.toISOString().split('T')[0];
    }
    
    getCSRFToken() {
        return document.querySelector('input[name="csrfmiddlewaretoken"]')?.value ||
               document.cookie.split('; ').find(r => r.startsWith('csrftoken='))?.split('=')[1];
    }
    
    showError(msg) {
        const statusDiv = document.getElementById('status-message');
        statusDiv.className = 'alert alert-danger';
        statusDiv.textContent = msg;
        statusDiv.style.display = 'block';
    }
    
    showSuccess(msg) {
        const statusDiv = document.getElementById('status-message');
        statusDiv.className = 'alert alert-success';
        statusDiv.textContent = msg;
        statusDiv.style.display = 'block';
    }
}

// Inicializar cuando el DOM está listo
document.addEventListener('DOMContentLoaded', () => {
    new MonthlyReportsManager();
});
```

#### 5.2 Integración en template existente
- Agregar `<script src="{% static 'aeptic_reports/monthly_reports.js' %}"></script>` en base template o en la página específica

---

### BLOQUE 6: AUDITORÍA
**Integración en vistas con `AuditLog`**

Cada vista debe crear entrada en `audit/models.py::AuditLog`

```python
from audit.models import AuditLog
from uuid import uuid4

def audit_report_generation(user, report):
    """Auditar generación de reporte"""
    AuditLog.objects.create(
        id=uuid4(),
        table_name='monthly_reports',
        record_id=str(report.id),
        user=user,
        action_type=AuditLog.AuditAction.CREATE,  # O UPDATE
        reason=f'Generación/descarga reporte {report.report_date.strftime("%B %Y")}',
        after={
            'report_id': str(report.id),
            'user': str(report.user.email),
            'company': str(report.company.name),
            'month': report.report_date.strftime('%Y-%m'),
            'status': report.status,
        },
        source='web'
    )
```

---

### BLOQUE 7: CONFIGURACIONES Y SETTINGS
**Archivo:** `core/settings.py` (ACTUALIZAR si es necesario)

```python
# Media files for monthly reports
MEDIA_ROOT = BASE_DIR / 'media'
MEDIA_URL = '/media/'

# Max upload size: 10MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 10485760

# Installed apps: asegurar que 'aeptic_reports' está incluida
INSTALLED_APPS = [
    # ...
    'aeptic_reports',
]
```

**Archivo:** `core/urls.py` (ACTUALIZAR)

```python
from django.conf import settings
from django.conf.urls.static import static

# ... existing patterns ...

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
```

---

### BLOQUE 8: DEPENDENCIAS (requirements.txt)
Verificar que estén instaladas:
```
openpyxl==3.10.0          # Para generar Excel
pandas==2.0.0             # Opcional: facilita manejo de datos
python-dateutil==2.8.2    # Para cálculos de fechas
```

---

## 🎯 ORDEN DE IMPLEMENTACIÓN RECOMENDADO

### Fase 1: Backend Core
1. ✅ BLOQUE 1: `aeptic_reports/services.py` - `ExcelReportGenerator` + `CSVReportGenerator`
   - Empezar con estructura simple (sin soft-delete aún)
   - Implementar columnas básicas
   - Testing local con datos de prueba

2. ✅ BLOQUE 2: `aeptic_reports/views.py` - Las 3 vistas
   - `MonthlyReportDownloadView`
   - `MonthlyReportUploadView`
   - `MonthlyReportListView`
   - Con validaciones y auditoría

3. ✅ BLOQUE 3: `aeptic_reports/urls.py` + integrar en `core/urls.py`

### Fase 2: Frontend
4. ✅ BLOQUE 4: Template HTML básico
5. ✅ BLOQUE 5: JavaScript - Toggle de meses + upload/download

### Fase 3: Polish
6. ✅ BLOQUE 6: Auditoría completa
7. ✅ BLOQUE 7: Settings y media files
8. ✅ Testing E2E (manual en navegador)

---

## 📝 DETALLES DE IMPLEMENTACIÓN POR SECCIÓN

### Services.py - Detalles Adicionales

#### Estructura de carpetas para archivos subidos:
```
media/
├── monthly_reports/
│   ├── {user_id}/
│   │   ├── {company_id}/
│   │   │   ├── user@email_2026-05-01.xlsx
│   │   │   ├── user@email_2026-04-01.xlsx
│   │   │   └── user@email_2026-03-01.csv
```

#### Caché de datos (optimización):
```python
def _fetch_month_data(self, user_id, company_id, start_date, end_date):
    """Cachear queries para no repetir"""
    time_entries = TimeEntries.objects.filter(
        user_id=user_id,
        company_id=company_id,
        date__range=[start_date, end_date]
    ).select_related('user')
    
    leave_requests = LeaveRequest.objects.filter(
        user_id=user_id,
        company_id=company_id,
        start_date__lte=end_date,
        end_date__gte=start_date,
        status='approved'
    )
    
    return {
        'time_entries': time_entries,
        'leave_requests': leave_requests,
    }
```

#### Estilos avanzados en Excel:
```python
def _apply_styles(self):
    """Aplicar colores, bordes, alineación"""
    from openpyxl.styles import Font, PatternFill, Border, Side, Alignment
    
    # Header style
    header_fill = PatternFill(start_color='000000', end_color='000000', fill_type='solid')
    header_font = Font(bold=True, color='FFFFFF', size=11)
    
    # Weekend style
    weekend_fill = PatternFill(start_color='ABABAB', end_color='ABABAB', fill_type='solid')
    weekend_font = Font(color='FF0000')
    
    # Border
    thin_border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )
    
    # Apply to cells...
```

---

## ✅ CHECKLIST DE VALIDACIONES

### En ExcelReportGenerator:
- [ ] Validar que `report_date` es primer día del mes
- [ ] Validar que user/company existen
- [ ] Manejar meses con 28/29/30/31 días correctamente
- [ ] Fines de semana identificados correctamente (localtime aware)
- [ ] Pausas calculadas correctamente (pares start/end)
- [ ] Vacaciones solo si status='approved' y leave_type='vacation'
- [ ] Ausencias (Baja) solo si status='approved' y leave_type='absence', con leave_reason mapeado correctamente
- [ ] Columna G (Baja) muestra "X - Motivo" (no se incluye en cálculo de horas)
- [ ] Cálculo de ordinarias/extras sin incluir columna G
- [ ] Filas en blanco si no hay datos (user llena manual)

### En Views:
- [ ] CSRF protection en POST
- [ ] user_id extraído de request.user
- [ ] company_id validado vs UserCompany
- [ ] File extension validada (.xlsx / .csv)
- [ ] File size validado (max 10MB)
- [ ] Month formato validado (YYYY-MM-DD, day=01)
- [ ] Storage path creada si no existe
- [ ] MonthlyReport.unique_together respetado

### En Frontend:
- [ ] Month toggle muestra mes anterior/actual correctamente
- [ ] File input trigger en cada botón de upload
- [ ] Mensajes error/success claros
- [ ] Spinner/loading durante descarga/upload
- [ ] Desabilitar buttons mientras se procesa
- [ ] CSRF token incluido en POST

---

## 🔗 REFERENCIAS DE BD

### Tablas involucradas:
- `users` - user_id
- `companies` - company_id
- `monthly_reports` - tabla principal
- `time_entries` - clock_in, clock_out, date
- `time_entry_event` - pause_start, pause_end
- `leave_requests` - vacation, absence, start_date, end_date, status
- `user_company` - permisos user-company
- `audit_log` - auditoría (si aplica)

### Soft-Delete:
- Todos los modelos con `deleted_at` deben usar `SoftDeleteManager`
- En queries: automático (filtra `deleted_at__isnull=True`)
- Al eliminar: `instance.deleted_at = timezone.now()` + `save()`

---

## 📞 PREGUNTAS ABIERTAS (RESOLVER ANTES DE IMPLEMENTAR)

1. **¿Existen "Festivos" en BD?** → Buscar tabla `holidays` o similar
2. **¿Jornada laboral dinámica?** → Buscar en `CompanySettings` o usar default 8h
3. **¿Ausencias parciales en LeaveRequest?** → Confirmar si solo son full-day o soportan horas parciales
4. **¿Soft-delete en MonthlyReport?** → ¿Agregar `deleted_at` field?
5. **¿Límite de tiempo: cuántos meses atrás se puede descargar?** → ¿Ilimitado o últimos 12?
6. **¿Notificación cuando se sube documento?** → ¿Enviar email a manager?
7. **¿Validación antes de "signed"?** → ¿Requerimientos antes de marcar como firmado?
8. **¿Mostrar leave_reason en columna G?** → Confirmar si se muestra solo el motivo o también horas (actualmente: "X - Motivo")

---

## 📊 TESTING MANUAL

### Caso 1: Generar Excel mayo 2026
1. Login como empleado
2. Click "Descargar Excel"
3. Verificar:
   - Archivo descargado: `report_user@email_2026-05-01.xlsx`
   - Filas: 31 (mayo tiene 31 días)
   - Sábados/domingos: fondo gris, texto rojo
   - Datos completados desde BD

### Caso 2: Subir documento firmado
1. Download Excel → Firmar en local → Upload
2. Verificar:
   - Status cambia a 'signed' en BD
   - Archivo guardado en `media/monthly_reports/...`
   - signed_at actualizado

### Caso 3: Toggle de meses
1. Click mes anterior ↔ Click mes actual
2. Verificar:
   - Tabla actualiza sin reload
   - Botón activo cambia visualmente
   - File inputs siguen asociados correctamente

---

## 🚀 DEPLOYMENT NOTES

### Pre-deployment:
- Crear carpeta `media/monthly_reports/` con permisos 755
- Revisar `MEDIA_URL` y `MEDIA_ROOT` en settings.py
- Testear upload en servidor con permisos de archivo
- Verificar memoria disponible (Excel grandes consume ~50MB)

### Post-deployment:
- Monitorear logs por errores de openpyxl
- Verificar que archivos se guardan correctamente
- Probar descarga y upload en prod
- Configurar CORS si frontend está en dominio diferente

---

**Fin del Plan | Última actualización: 2026-05-14**
