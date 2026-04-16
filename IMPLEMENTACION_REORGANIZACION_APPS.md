# 📋 PLAN DE IMPLEMENTACIÓN - Reorganización de Apps (3 nuevas apps)

**Proyecto:** Control Horario  
**Fecha inicio:** 2026-04-16  
**Estado:** 🟡 Planificado (No ejecutado aún)  
**Duración estimada:** 60-90 minutos  

---

## 📌 RESUMEN EJECUTIVO

Este documento guía la reorganización del proyecto Django desde **4 apps** a **7 apps**:

| Apps que permanecen | Apps nuevas |
|-------------------|-------------|
| users/ | ⭐ admin/ (NEW) |
| dashboard/ | ⭐ management/ (NEW) |
| timetracking/ | ⭐ corrections/ (NEW) |
| audit/ | |

**Cambios principales:**
- ✅ `manager_employee()` → `staff()` (renombrado)
- ✅ URLs simplificadas (`/leave/create/` en lugar de `/api/leave/create/`)
- ✅ Separación clara de responsabilidades por dominio

---

## 🎯 OBJETIVOS

- [x] Reducir complejidad en cada app
- [x] Mejorar mantenibilidad
- [x] Preparar para escalabilidad futura
- [x] No romper funcionalidad existente
- [x] Permitir testing incremental

---

## ⚠️ PREREQUISITOS

Antes de empezar:
1. ✅ Asegúrate de estar en branch `maria` (actual)
2. ✅ Haz un commit del estado actual:
   ```bash
   git add .
   git commit -m "Pre-reorganización de apps: checkpoint antes de cambios estructurales"
   ```
3. ✅ La estructura de directorio debe ser:
   ```
   control_horario/
   ├── users/
   ├── dashboard/
   ├── timetracking/
   ├── audit/
   ├── core/
   ├── manage.py
   └── (rest of structure)
   ```

---

## 📊 FASES DE IMPLEMENTACIÓN

---

# FASE 1: PREPARACIÓN - CREAR ESTRUCTURA DE NUEVAS APPS

**Duración:** ~5 minutos  
**Objetivo:** Crear la estructura base de las 3 nuevas apps

## Paso 1.1: Crear las 3 nuevas apps Django

```bash
# Navega a la raíz del proyecto
cd c:\Users\marar\Desktop\Aeptic\control_horario

# Crear las 3 nuevas apps
python manage.py startapp admin
python manage.py startapp management
python manage.py corrections
```

**Resultado esperado:**
```
control_horario/
├── admin/                          # ⭐ NUEVA
│   ├── migrations/
│   │   └── __init__.py
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── models.py
│   ├── tests.py
│   ├── views.py                    # ← Aquí va el código
│   └── urls.py                     # ← Crear este (puede estar vacío)
├── management/                     # ⭐ NUEVA
│   ├── migrations/
│   │   └── __init__.py
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── models.py
│   ├── tests.py
│   ├── views.py                    # ← Aquí va el código
│   └── urls.py                     # ← Crear este (puede estar vacío)
├── corrections/                    # ⭐ NUEVA
│   ├── migrations/
│   │   └── __init__.py
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── models.py
│   ├── tests.py
│   ├── views.py                    # ← Aquí va el código
│   └── urls.py                     # ← Crear este (puede estar vacío)
└── (rest of apps...)
```

### ✅ CHECKPOINT 1.1
Ejecuta:
```bash
ls -la admin/
ls -la management/
ls -la corrections/
```

Debe mostrar ambas carpetas con estructura Django estándar.

---

## Paso 1.2: Crear archivos urls.py faltantes

Las apps generadas por startapp NO incluyen `urls.py`. Créalos (aunque vacíos):

```bash
# Crear urls.py vacíos en cada app
touch admin/urls.py
touch management/urls.py
touch corrections/urls.py
```

O manualmente edita cada archivo y añade (puede estar vacío o con comentario):

**admin/urls.py:**
```python
# admin/urls.py
# URLs manejadas centralmente en core/urls.py
```

**management/urls.py:**
```python
# management/urls.py
# URLs manejadas centralmente en core/urls.py
```

**corrections/urls.py:**
```python
# corrections/urls.py
# URLs manejadas centralmente en core/urls.py
```

### ✅ CHECKPOINT 1.2
```bash
ls admin/urls.py management/urls.py corrections/urls.py
```

Debe listar los 3 archivos.

---

## Paso 1.3: Registrar las 3 nuevas apps en settings.py

Abre `control_horario/settings.py` y localiza `INSTALLED_APPS`:

```python
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Local apps
    'users',
    'dashboard',
    'timetracking',
    'audit',
    'core',
    
    # ⭐ ⭐ ⭐ AGREGAR ESTAS 3 LINEAS ⭐ ⭐ ⭐
    'admin',          # ⭐ NUEVA
    'management',     # ⭐ NUEVA
    'corrections',    # ⭐ NUEVA
]
```

### ✅ CHECKPOINT 1.3

Ejecuta validación Django:
```bash
python manage.py check
```

**Resultado esperado:**
```
System check identified no issues (0 silenced).
```

Si hay errores, verifica que los nombres en `INSTALLED_APPS` coincidan exactamente con los nombres de carpeta.

---

**🎉 FIN FASE 1**

---

# FASE 2: CREAR VIEWS EN NUEVAS APPS

**Duración:** ~30 minutos  
**Objetivo:** Migrar funciones desde apps antiguas a las nuevas

---

## Paso 2.1: Crear management/views.py

Este es el archivo más grande. Vamos a copiar funciones desde `audit/views.py`.

**Funciones a MIGRAR a management/views.py:**
- `manager_logs()` (línea 29) → **Mantener el nombre**
- `exportar_logs()` (línea 213) → **Mantener el nombre**
- `exportar_manager_employees()` (línea 343) → **RENOMBRAR A: `exportar_staff()`**
- `editar_registro()` (línea 408) → **Mantener el nombre**
- `manager_employee()` (línea 487) → **RENOMBRAR A: `staff()`** ⭐ IMPORTANTE
- `edit_employee()` (línea 580) → **Mantener el nombre**
- `delete_employee()` (línea 624) → **Mantener el nombre**
- `anular_registro()` (línea 727) → **Mantener el nombre**
- `entity_info()` (desde dashboard/views.py) → **Copiar versión managers**

### Crear el archivo management/views.py

Abre `audit/views.py` y copia TODAS las siguiente importaciones al inicio de `management/views.py`:

```python
# management/views.py

import csv
from urllib import request
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from users.models import Companies, CorrectionRequests, UserCompany, Users
from timetracking.models import TimeEntries
from django.db.models import OuterRef, Subquery
import uuid
from django.utils import timezone
from datetime import datetime
from django.http import HttpResponseForbidden
from django.db.models import Q
from django.views.decorators.http import require_POST
from django.views.decorators.cache import never_cache
from audit.models import AuditLog
from django.core.paginator import Paginator
from audit.utils import safe_dict
from uuid import uuid4
from core.decorators import manager_or_admin_required, auditor_cannot_access
from core.services import combine_local_date_time, get_effective_context
```

Ahora copia las 9 funciones desde `audit/views.py`. Líneas exactas:

```python
# ═══════════════════════════════════════════════════════════════════════════
# COPIAR DESDE audit/views.py (línea 29-128)
# ═══════════════════════════════════════════════════════════════════════════
@manager_or_admin_required
@never_cache
def manager_logs(request):
    # [CÓDIGO COMPLETO DE audit/views.py:29-128]
    pass

# ═══════════════════════════════════════════════════════════════════════════
# COPIAR DESDE audit/views.py (línea 213-271)
# ═══════════════════════════════════════════════════════════════════════════
@manager_or_admin_required
def exportar_logs(request):
    # [CÓDIGO COMPLETO DE audit/views.py:213-271]
    pass

# ═══════════════════════════════════════════════════════════════════════════
# COPIAR DESDE audit/views.py (línea 343-403)
# ⭐ IMPORTANTE: RENOMBRAR exportar_manager_employees → exportar_staff
# ═══════════════════════════════════════════════════════════════════════════
@manager_or_admin_required
@require_POST
def exportar_staff(request):  # ⭐ era: exportar_manager_employees
    """
    Exporta la lista de empleados de una empresa a CSV.
    POST params: employee_id (lista de IDs seleccionadas)
    """
    # [CÓDIGO COMPLETO DE audit/views.py:343-403, SIN CAMBIOS EN LÓGICA]
    pass

# ═══════════════════════════════════════════════════════════════════════════
# COPIAR DESDE audit/views.py (línea 408-481)
# ═══════════════════════════════════════════════════════════════════════════
@manager_or_admin_required
def editar_registro(request):
    # [CÓDIGO COMPLETO DE audit/views.py:408-481]
    pass

# ═══════════════════════════════════════════════════════════════════════════
# COPIAR DESDE audit/views.py (línea 487-576)
# ⭐ IMPORTANTE: RENOMBRAR manager_employee → staff
# ═══════════════════════════════════════════════════════════════════════════
@login_required
@never_cache
@manager_or_admin_required
def staff(request):  # ⭐ era: manager_employee
    # [CÓDIGO COMPLETO DE audit/views.py:487-576, SIN CAMBIOS EN LÓGICA]
    pass

# ═══════════════════════════════════════════════════════════════════════════
# COPIAR DESDE audit/views.py (línea 580-620)
# ═══════════════════════════════════════════════════════════════════════════
@manager_or_admin_required
@require_POST
def edit_employee(request):
    # [CÓDIGO COMPLETO DE audit/views.py:580-620]
    pass

# ═══════════════════════════════════════════════════════════════════════════
# COPIAR DESDE audit/views.py (línea 624-723)
# ═══════════════════════════════════════════════════════════════════════════
@manager_or_admin_required
@require_POST
def delete_employee(request):
    # [CÓDIGO COMPLETO DE audit/views.py:624-723]
    pass

# ═══════════════════════════════════════════════════════════════════════════
# COPIAR DESDE audit/views.py (línea 727-770)
# ═══════════════════════════════════════════════════════════════════════════
@manager_or_admin_required
@require_POST
def anular_registro(request):
    # [CÓDIGO COMPLETO DE audit/views.py:727-770]
    pass

# ═══════════════════════════════════════════════════════════════════════════
# COPIAR/ADAPTAR DESDE dashboard/views.py (línea 270)
# VERSIÓN PARA MANAGERS (entity_info sin decorador admin_only)
# ═══════════════════════════════════════════════════════════════════════════
@login_required
@manager_or_admin_required
def entity_info(request):
    """
    Managers pueden ver/editar INFO de su propia empresa.
    La lógica es idéntica pero sin permitir cambios globales.
    """
    # [CÓDIGO ADAPTADO DE dashboard/views.py:270, CON RESTRICCIÓN A SU EMPRESA]
    pass
```

### ✅ CHECKPOINT 2.1

```bash
python manage.py shell
>>> from management import views as mgmt
>>> print(dir(mgmt))
```

Debe listar (entre otros): `staff`, `manager_logs`, `edit_employee`, `delete_employee`, `editar_registro`, `anular_registro`, `exportar_logs`, `exportar_staff`, `entity_info`

---

## Paso 2.2: Crear admin/views.py

Copia desde `users/views.py` las siguientes funciones:

```python
# admin/views.py

import json
import csv
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.decorators.cache import never_cache
from uuid import uuid4
from users.models import Users, Companies, UserCompany, CompanySettings, CorrectionRequests
from timetracking.models import TimeEntries
from audit.models import TimeEntryEvent, AuditLog
from audit.utils import safe_dict
from django.core.paginator import Paginator
from core.decorators import admin_only_required

# ═══════════════════════════════════════════════════════════════════════════
# COPIAR DESDE users/views.py (línea 1087-1105)
# ═══════════════════════════════════════════════════════════════════════════
@admin_only_required
@never_cache
def admin_dashboard(request):
    """Admin dashboard to manage companies and workers globally"""
    # [CÓDIGO COMPLETO DE users/views.py:1087-1105]
    pass

# ═══════════════════════════════════════════════════════════════════════════
# COPIAR DESDE users/views.py (línea 1249-1291)
# ═══════════════════════════════════════════════════════════════════════════
@admin_only_required
@require_POST
def select_delegated_worker(request):
    """
    Admin selecciona un trabajador para delegar las acciones.
    Guarda user_id, name y company_id en sesión.
    """
    # [CÓDIGO COMPLETO DE users/views.py:1249-1291]
    pass

# ═══════════════════════════════════════════════════════════════════════════
# COPIAR DESDE users/views.py (línea 1296-1306)
# ═══════════════════════════════════════════════════════════════════════════
@admin_only_required
@require_POST
def clear_delegated_worker(request):
    """
    Admin cancela la delegación de usuario.
    Limpia las variables de sesión asociadas.
    """
    # [CÓDIGO COMPLETO DE users/views.py:1296-1306]
    pass

# ═══════════════════════════════════════════════════════════════════════════
# COPIAR DESDE users/views.py (línea 1314-1355)
# ═══════════════════════════════════════════════════════════════════════════
@admin_only_required
def deleted_records(request):
    """
    Vista para mostrar todos los registros eliminados (soft-deleted) agrupados por tipo.
    Solo accesible para administradores.
    """
    # [CÓDIGO COMPLETO DE users/views.py:1314-1355]
    pass

# ═══════════════════════════════════════════════════════════════════════════
# COPIAR DESDE users/views.py (línea 1360-1444)
# ═══════════════════════════════════════════════════════════════════════════
@admin_only_required
@require_POST
def restore_record(request):
    """
    Restaura un registro eliminado (soft-deleted).
    Solo accesible para administradores.
    """
    # [CÓDIGO COMPLETO DE users/views.py:1360-1444]
    pass

# ═══════════════════════════════════════════════════════════════════════════
# COPIAR DESDE users/views.py (línea 1449-1496)
# ═══════════════════════════════════════════════════════════════════════════
@admin_only_required
@require_POST
def permanently_delete_record(request):
    """
    Elimina permanentemente un registro eliminado (hard-delete).
    Solo accesible para administradores.
    """
    # [CÓDIGO COMPLETO DE users/views.py:1449-1496]
    pass

# ═══════════════════════════════════════════════════════════════════════════
# COPIAR DESDE users/views.py (línea 1501-1565)
# ═══════════════════════════════════════════════════════════════════════════
@admin_only_required
@require_POST
def delete_company(request):
    """
    Elimina una empresa (soft-delete) y todas sus membresías asociadas.
    Solo accesible para administradores.
    """
    # [CÓDIGO COMPLETO DE users/views.py:1501-1565]
    pass

# ═══════════════════════════════════════════════════════════════════════════
# COPIAR DESDE users/views.py (línea 1109-1242)
# ═══════════════════════════════════════════════════════════════════════════
@admin_only_required
@require_POST
def exportar_deleted_records(request):
    """
    Exporta registros eliminados agrupados por tipo a CSV.
    POST params: record_type (users, companies, user_companies, corrections, time_entries, time_events)
    """
    # [CÓDIGO COMPLETO DE users/views.py:1109-1242]
    pass

# ═══════════════════════════════════════════════════════════════════════════
# COPIAR/ADAPTAR DESDE dashboard/views.py (línea 270)
# VERSIÓN PARA ADMIN (entity_info con decorador admin_only)
# ═══════════════════════════════════════════════════════════════════════════
@admin_only_required
def entity_info(request):
    """
    Admin puede ver/editar INFO de CUALQUIER empresa (global).
    La lógica es idéntica a managers pero sin restricciones.
    """
    # [CÓDIGO ADAPTADO DE dashboard/views.py:270, SIN RESTRICCIÓN A SU EMPRESA]
    pass
```

### ✅ CHECKPOINT 2.2

```bash
python manage.py shell
>>> from admin import views as admin_views
>>> print(dir(admin_views))
```

Debe listar (entre otros): `admin_dashboard`, `select_delegated_worker`, `clear_delegated_worker`, `deleted_records`, `restore_record`, `permanently_delete_record`, `delete_company`, `exportar_deleted_records`, `entity_info`

---

## Paso 2.3: Crear corrections/views.py

Copia desde `audit/views.py` y `dashboard/views.py`:

```python
# corrections/views.py

import csv
import json
from datetime import date, timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.utils.dateparse import parse_date
import uuid
from uuid import uuid4

from users.models import Users, Companies, CorrectionRequests, UserCompany
from timetracking.models import TimeEntries
from dashboard.models import LeaveRequest
from audit.models import AuditLog
from audit.utils import safe_dict
from core.decorators import manager_or_admin_required
from core.services import get_effective_context, serialize_leave, log_leave

# ═══════════════════════════════════════════════════════════════════════════
# COPIAR DESDE audit/views.py (línea 132-209)
# ═══════════════════════════════════════════════════════════════════════════
@manager_or_admin_required
def resolver_incidencia(request):
    """
    View for the manager to accept or deny an incident, with their resolution note
    """
    # [CÓDIGO COMPLETO DE audit/views.py:132-209]
    pass

# ═══════════════════════════════════════════════════════════════════════════
# COPIAR DESDE audit/views.py (línea 775-830)
# ═══════════════════════════════════════════════════════════════════════════
@manager_or_admin_required
@require_POST
def editar_incidencia_rechazada(request):
    """
    Allow managers/admins to edit a rejected correction request (change times and reason)
    """
    # [CÓDIGO COMPLETO DE audit/views.py:775-830]
    pass

# ═══════════════════════════════════════════════════════════════════════════
# COPIAR DESDE audit/views.py (línea 835-867)
# ═══════════════════════════════════════════════════════════════════════════
@manager_or_admin_required
@require_POST
def eliminar_incidencia_rechazada(request):
    """
    Soft-delete a rejected correction request
    """
    # [CÓDIGO COMPLETO DE audit/views.py:835-867]
    pass

# ═══════════════════════════════════════════════════════════════════════════
# COPIAR DESDE audit/views.py (línea 276-338)
# ═══════════════════════════════════════════════════════════════════════════
@manager_or_admin_required
@require_POST
def exportar_logs_rechazadas(request):
    """
    Exporta las incidencias rechazadas a CSV.
    POST params: incidencia_id (lista de IDs seleccionadas)
    """
    # [CÓDIGO COMPLETO DE audit/views.py:276-338]
    pass

# ═══════════════════════════════════════════════════════════════════════════
# COPIAR DESDE dashboard/views.py (línea 550-579)
# ═══════════════════════════════════════════════════════════════════════════
@login_required
@manager_or_admin_required
def api_leave_pending(request):
    """
    Manager puede ver todas las solicitudes de ausencia pendientes de su equipo.
    """
    # [CÓDIGO COMPLETO DE dashboard/views.py:550-579]
    pass

# ═══════════════════════════════════════════════════════════════════════════
# COPIAR DESDE dashboard/views.py (línea 586-635)
# ═══════════════════════════════════════════════════════════════════════════
@login_required
@manager_or_admin_required
@require_POST
def api_leave_review(request, leave_id):
    """Manager aprueba o rechaza una solicitud."""
    # [CÓDIGO COMPLETO DE dashboard/views.py:586-635]
    pass
```

### ✅ CHECKPOINT 2.3

```bash
python manage.py shell
>>> from corrections import views as corr_views
>>> print(dir(corr_views))
```

Debe listar (entre otros): `resolver_incidencia`, `editar_incidencia_rechazada`, `eliminar_incidencia_rechazada`, `exportar_logs_rechazadas`, `api_leave_pending`, `api_leave_review`

---

**🎉 FIN FASE 2**

---

# FASE 3: LIMPIAR FUNCIONES DE APPS ORIGINALES

**Duración:** ~5 minutos  
**Objetivo:** Remover funciones migradas de las apps antiguas para evitar duplicados

⚠️ **IMPORTANTE:** Solo ELIMINA exactamente las líneas listadas. No elimines nada más.

---

## Paso 3.1: Limpiar audit/views.py

**Abre:** `audit/views.py`

**ELIMINA estas funciones COMPLETAS:**

```python
# ❌ ELIMINAR (línea 29-128): manager_logs()
# ❌ ELIMINAR (línea 132-209): resolver_incidencia()
# ❌ ELIMINAR (línea 213-271): exportar_logs()
# ❌ ELIMINAR (línea 276-338): exportar_logs_rechazadas()
# ❌ ELIMINAR (línea 343-403): exportar_manager_employees()
# ❌ ELIMINAR (línea 408-481): editar_registro()
# ❌ ELIMINAR (línea 487-576): manager_employee()
# ❌ ELIMINAR (línea 580-620): edit_employee()
# ❌ ELIMINAR (línea 624-723): delete_employee()
# ❌ ELIMINAR (línea 727-770): anular_registro()
# ❌ ELIMINAR (línea 775-830): editar_incidencia_rechazada()
# ❌ ELIMINAR (línea 835-867): eliminar_incidencia_rechazada()
```

**MANTÉN:**
- `audit_dashboard()`
- `audit_fichajes()`
- `audit_vacaciones()`
- `audit_usuarios()`
- `audit_incidencias()`
- `audit_company()`
- Todas las importaciones que usen las funciones que mantenes

**Resultado esperado:** `audit/views.py` pasará de ~1295 líneas a ~400 líneas

### ✅ CHECKPOINT 3.1

```bash
python manage.py check
```

Debe producir: `System check identified no issues (0 silenced).`

Si hay errores sobre imports no usados, es normal (los limpiaremos después).

---

## Paso 3.2: Limpiar users/views.py

**Abre:** `users/views.py`

**ELIMINA estas funciones COMPLETAS:**

```python
# ❌ ELIMINAR (línea 1087-1105): admin_dashboard()
# ❌ ELIMINAR (línea 1109-1242): exportar_deleted_records()
# ❌ ELIMINAR (línea 1249-1291): select_delegated_worker()
# ❌ ELIMINAR (línea 1296-1306): clear_delegated_worker()
# ❌ ELIMINAR (línea 1314-1355): deleted_records()
# ❌ ELIMINAR (línea 1360-1444): restore_record()
# ❌ ELIMINAR (línea 1449-1496): permanently_delete_record()
# ❌ ELIMINAR (línea 1501-1565): delete_company()
```

**MANTÉN:**
- `login_view()`
- `logout_view()`
- `lookup_company()`
- `lookup_user()`
- `check_last_manager()`
- `register_unified()`
- `switch_company()`
- `workday()`
- `exportar_workday_entries()`
- `exportar_workday_requests()`

**Resultado esperado:** `users/views.py` pasará de ~1566 líneas a ~800 líneas

### ✅ CHECKPOINT 3.2

```bash
python manage.py check
```

Debe producir: `System check identified no issues (0 silenced).`

---

## Paso 3.3: Limpiar dashboard/views.py

**Abre:** `dashboard/views.py`

**ELIMINA estas funciones COMPLETAS:**

```python
# ❌ ELIMINAR (línea 550-579): api_leave_pending()
# ❌ ELIMINAR (línea 586-635): api_leave_review()
```

**MANTÉN:**
- `calendar()`
- `api_calendar_events()`
- `profile()`
- `security()`
- `entity_info()`
- `api_leave_request_create()`
- `api_leave_request_cancel()`
- `staff()`
- `notes()`

**Resultado esperado:** `dashboard/views.py` pasará de ~655 líneas a ~480 líneas

### ✅ CHECKPOINT 3.3

```bash
python manage.py check
```

Debe producir: `System check identified no issues (0 silenced).`

---

**🎉 FIN FASE 3**

---

# FASE 4: ACTUALIZAR URLs

**Duración:** ~5 minutos  
**Objetivo:** Reescribir `core/urls.py` con la nueva estructura de rutas

---

## Paso 4.1: Reescribir core/urls.py

**Abre:** `core/urls.py`

**Reemplaza COMPLETAMENTE el contenido con:**

```python
# ---------- URL Routing: core/urls.py ----------

from django.contrib import admin
from django.urls import path
from users import views as user_views
from dashboard import views as dashboard_views
from timetracking import views as timetracking_views
from audit import views as audit_views
from admin import views as admin_views                    # ⭐ NEW
from management import views as management_views         # ⭐ NEW
from corrections import views as corrections_views       # ⭐ NEW

urlpatterns = [
    # ════════════════════════════════════════════════════════════════════════
    # AUTH & CORE (users/)
    # ════════════════════════════════════════════════════════════════════════
    path('', user_views.login_view, name='login'),
    path('logout/', user_views.logout_view, name='logout'),
    path('register/', user_views.register_unified, name='register_unified'),
    path('switch-company/<uuid:company_id>/', user_views.switch_company, name='switch_company'),
    
    # API Lookups
    path('api/lookup-company/', user_views.lookup_company, name='lookup_company'),
    path('api/lookup-user/', user_views.lookup_user, name='lookup_user'),
    path('api/check-last-manager/', user_views.check_last_manager, name='check_last_manager'),
    
    # ════════════════════════════════════════════════════════════════════════
    # HOME & TIMETRACKING
    # ════════════════════════════════════════════════════════════════════════
    path('home/', timetracking_views.time_entries, name='home_timetracking'),

    # ════════════════════════════════════════════════════════════════════════
    # DASHBOARD - PERSONAL (dashboard/)
    # ════════════════════════════════════════════════════════════════════════
    
    # Personal Time Tracking
    path('workday/', dashboard_views.workday, name='workday'),
    path('workday/exportar_entries/', dashboard_views.exportar_workday_entries, name='exportar_workday_entries'),
    path('workday/exportar_requests/', dashboard_views.exportar_workday_requests, name='exportar_workday_requests'),
    
    # Personal Info
    path('profile/', dashboard_views.profile, name='profile'),
    path('security/', dashboard_views.security, name='security'),
    
    # Personal Leave & Calendar
    path('calendar/', dashboard_views.calendar, name='calendar'),
    path('calendar/events/', dashboard_views.api_calendar_events, name='calendar_events'),
    path('leave/create/', dashboard_views.api_leave_request_create, name='leave_create'),
    path('leave/<uuid:leave_id>/cancel/', dashboard_views.api_leave_request_cancel, name='leave_cancel'),
    
    # Team Views (static)
    path('team/', dashboard_views.staff, name='team_staff'),  # ⭐ CHANGED FROM /staff/
    path('notes/', dashboard_views.notes, name='team_notes'),

    # ════════════════════════════════════════════════════════════════════════
    # MANAGEMENT - MANAGER FUNCTIONS (management/) ⭐ NEW
    # ════════════════════════════════════════════════════════════════════════
    
    # Time Logs
    path('logs/', management_views.manager_logs, name='manager_logs'),
    path('logs/export/', management_views.exportar_logs, name='exportar_logs'),
    path('logs/edit/', management_views.editar_registro, name='editar_registro'),
    path('logs/void/', management_views.anular_registro, name='anular_registro'),
    
    # Staff Management (UPDATED: manager_employees → staff)
    path('staff/', management_views.staff, name='staff'),  # ⭐ MOVED HERE
    path('staff/edit/', management_views.edit_employee, name='edit_employee'),
    path('staff/delete/', management_views.delete_employee, name='delete_employee'),
    path('staff/export/', management_views.exportar_staff, name='exportar_staff'),
    
    # Company Configuration
    path('company-info/', management_views.entity_info, name='manager_entity_info'),

    # ════════════════════════════════════════════════════════════════════════
    # CORRECTIONS - CORRECTIONS & ABSENCES (corrections/) ⭐ NEW
    # ════════════════════════════════════════════════════════════════════════
    
    # Correction Requests (manager approval)
    path('logs/resolve/', corrections_views.resolver_incidencia, name='resolver_incidencia'),
    path('corrections/edit/', corrections_views.editar_incidencia_rechazada, name='editar_incidencia_rechazada'),
    path('corrections/delete/', corrections_views.eliminar_incidencia_rechazada, name='eliminar_incidencia_rechazada'),
    path('corrections/export/', corrections_views.exportar_logs_rechazadas, name='exportar_logs_rechazadas'),
    
    # Leave Requests (manager review) - SIMPLIFIED URLS
    path('leave/pending/', corrections_views.api_leave_pending, name='leave_pending'),  # ⭐ SIMPLIFIED
    path('leave/<uuid:leave_id>/review/', corrections_views.api_leave_review, name='leave_review'),  # ⭐ SIMPLIFIED

    # ════════════════════════════════════════════════════════════════════════
    # ADMIN - GLOBAL ADMINISTRATION (admin/) ⭐ NEW
    # ════════════════════════════════════════════════════════════════════════
    
    path('admin/', admin_views.admin_dashboard, name='admin_dashboard'),
    path('admin/company-info/', admin_views.entity_info, name='admin_entity_info'),
    
    # Soft Delete Management
    path('admin/deleted-records/', admin_views.deleted_records, name='deleted_records'),
    path('admin/deleted-records/export/', admin_views.exportar_deleted_records, name='exportar_deleted_records'),
    path('admin/restore/', admin_views.restore_record, name='restore_record'),
    path('admin/delete-permanent/', admin_views.permanently_delete_record, name='permanently_delete_record'),
    path('admin/delete-company/', admin_views.delete_company, name='delete_company'),
    
    # API - Admin Delegation
    path('api/admin/delegate/', admin_views.select_delegated_worker, name='select_delegated_worker'),  # ⭐ SIMPLIFIED
    path('api/admin/clear-delegate/', admin_views.clear_delegated_worker, name='clear_delegated_worker'),  # ⭐ SIMPLIFIED

    # ════════════════════════════════════════════════════════════════════════
    # AUDIT - READ-ONLY LOGS (audit/) - SIN CAMBIOS
    # ════════════════════════════════════════════════════════════════════════
    path('audit/', audit_views.audit_dashboard, name='audit_dashboard'),
    path('audit/logs/', audit_views.audit_fichajes, name='audit_fichajes'),
    path('audit/leave/', audit_views.audit_vacaciones, name='audit_vacaciones'),
    path('audit/users/', audit_views.audit_usuarios, name='audit_usuarios'),
    path('audit/corrections/', audit_views.audit_incidencias, name='audit_incidencias'),
    path('audit/company/', audit_views.audit_company, name='audit_company'),
]
```

### ✅ CHECKPOINT 4.1

```bash
python manage.py check
```

Debe producir: `System check identified no issues (0 silenced).`

---

**🎉 FIN FASE 4**

---

# FASE 5: TESTING Y VALIDACIÓN

**Duración:** ~15 minutos  
**Objetivo:** Verificar que todo funciona correctamente

---

## Paso 5.1: Ejecución de validaciones Django

```bash
python manage.py check
```

**Resultado esperado:**
```
System check identified no issues (0 silenced).
```

**Si hay errores:**
- Verifica los nombres exactos en core/urls.py
- Verifica que imports están correctos
- Verifica que no hay funciones duplicadas

---

## Paso 5.2: Verificar import de nuevas apps en shell

```bash
python manage.py shell
```

Dentro del shell Python:

```python
# Verificar que las 3 nuevas apps se importan correctamente
>>> from management import views as mgmt_views
>>> from admin import views as admin_views
>>> from corrections import views as corr_views
>>> 
>>> # Verificar que las funciones renombradas existen
>>> print(hasattr(mgmt_views, 'staff'))
True
>>> print(hasattr(mgmt_views, 'exportar_staff'))
True
>>> 
>>> print("✅ Todos los imports funcionan correctamente")
✅ Todos los imports funcionan correctamente
>>> 
>>> exit()
```

---

## Paso 5.3: Inicio del servidor y testing de URLs

Inicia el servidor:

```bash
python manage.py runserver
```

Debe mostrar:
```
Starting development server at http://127.0.0.1:8000/
```

---

## Paso 5.4: Testing de URLs en navegador

**Abre navegador** y prueba estas URLs EN ORDEN (asegúrate de estar logueado como admin/manager):

### Auth (users/views.py) ✅
- `http://localhost:8000/` → Login page
- `http://localhost:8000/register/` → Register page

### Dashboard Personal (dashboard/views.py) ✅
- `http://localhost:8000/workday/` → Debe cargar "Mi jornada"
- `http://localhost:8000/calendar/` → Debe cargar "Mi calendario"
- `http://localhost:8000/profile/` → Debe cargar "Mi perfil"
- `http://localhost:8000/team/` → Debe cargar "Ver equipo" ⭐ NOTA: cambió de /staff/

### Management (management/views.py) ✅
- `http://localhost:8000/logs/` → Ver fichajes del equipo
- `http://localhost:8000/staff/` → Ver empleados ⭐ NOTA: ahora es aquí
- `http://localhost:8000/company-info/` → Info empresa (manager)

### Corrections (corrections/views.py) ✅
- `http://localhost:8000/leave/pending/` → Solicitudes pendientes
- `http://localhost:8000/corrections/edit/` → Editar incidencia

### Admin (admin/views.py) ✅
- `http://localhost:8000/admin/` → Panel admin
- `http://localhost:8000/admin/deleted-records/` → Registros eliminados
- `http://localhost:8000/admin/company-info/` → Info empresa (admin)

### Audit (audit/views.py) ✅
- `http://localhost:8000/audit/` → Dashboard auditoría
- `http://localhost:8000/audit/logs/` → Auditoría fichajes

---

## Paso 5.5: Resolver conflictos potenciales

### ⚠️ CONFLICTO IDENTIFICADO: `/staff/` aparece en dos contextos

**Problema:**
```
ANTES (dashboard):  path('staff/', dashboard_views.staff, name='staff')
AHORA (management): path('staff/', management_views.staff, name='staff')
```

**Solución implementada en urls.py:**
```python
# DASHBOARD - cambiar a /team/
path('team/', dashboard_views.staff, name='team_staff')

# MANAGEMENT - mantiene /staff/
path('staff/', management_views.staff, name='staff')
```

**Si aún tienes problemas:**

Busca en templates referencias a `/staff/`:

```bash
grep -r "staff" templates/ | grep -E "href|url"
```

Y actualiza a `/team/`:

```html
<!-- ANTES -->
<a href="{% url 'staff' %}">Ver equipo</a>

<!-- AHORA -->
<a href="{% url 'team_staff' %}">Ver equipo</a>
```

### ✅ CHECKPOINT 5.5

- [x] `/staff/` → management_views.staff ✅
- [x] `/team/` → dashboard_views.staff ✅
- [x] No hay conflictos de rutas
- [x] Todos los URL names son únicos

---

**🎉 FIN FASE 5**

---

# FASE 6: ACTUALIZAR TEMPLATES (Opcional pero recomendado)

**Duración:** ~5 minutos  
**Objetivo:** Actualizar referencias a URLs en templates

---

## Paso 6.1: Buscar referencias a URLs antiguas

```bash
# En la raíz del proyecto, ejecuta:
grep -r "manager_employees" templates/
grep -r "manager_employee" templates/
grep -r "{% url 'manager_employee" templates/
grep -r "store-manager-employees" templates/
```

---

## Paso 6.2: Actualizar referencias encontradas

**Ejemplo de actualización:**

```html
<!-- ANTES (manager_employee) -->
<a href="{% url 'manager_employee' %}">Ver empleados</a>
<form action="{% url 'exportar_manager_employees' %}" method="POST">

<!-- AHORA (staff, con nueva app) -->
<a href="{% url 'staff' %}">Ver empleados</a>
<form action="{% url 'exportar_staff' %}" method="POST">
```

**También buscar referencias a URLs simplificadas:**

```html
<!-- ANTES (api/leave) -->
<button data-action="{% url 'api_leave_pending' %}">

<!-- AHORA (leave simplificado) -->
<button data-action="{% url 'leave_pending' %}">
```

---

## Paso 6.3: Verificar no hay URLs rotas en templates

Inicia el servidor y abre cada página, verificando que NO hay errores de URL `NoReverseMatch`.

---

**🎉 FIN FASE 6**

---

# FASE 7: CREAR MIGRACIONES (Si es necesario)

**Duración:** ~2 minutos  
**Objetivo:** Registrar cualquier cambio en BD (probablemente ninguno)

---

## Paso 7.1: Crear migraciones

```bash
python manage.py makemigrations admin management corrections
```

**Resultado esperado:**
```
No changes detected
```

(Las nuevas apps probablemente NO tendrán modelos, por lo que no habrá migraciones)

---

## Paso 7.2: Ejecutar migraciones

```bash
python manage.py migrate
```

**Resultado esperado:**
```
Operations to perform:
  Apply all migrations:
    ...
Running migrations:
    No migrations to apply.
```

---

**🎉 FIN FASE 7**

---

## ✅ RESUMEN FINAL

| Fase | Tarea | Estado | Tiempo |
|------|-------|--------|--------|
| 1 | Crear estructura apps | ⏳ Pendiente | 5 min |
| 2 | Crear views en nuevas apps | ⏳ Pendiente | 30 min |
| 3 | Limpiar apps antiguas | ⏳ Pendiente | 5 min |
| 4 | Actualizar URLs | ⏳ Pendiente | 5 min |
| 5 | Testing y validación | ⏳ Pendiente | 15 min |
| 6 | Actualizar templates | ⏳ Pendiente | 5 min |
| 7 | Migraciones | ⏳ Pendiente | 2 min |
| | **TOTAL** | | **60-90 min** |

---

## 🔄 SI ALGO FALLA - ROLLBACK

Si en cualquier momento algo sale mal, puedes volver al estado anterior:

```bash
# Ver commit anterior
git log --oneline -5

# Revertir cambios (si aún no has hecho commit)
git reset --hard HEAD

# O si quieres mantener cambios en rama nueva
git checkout -b rollback-reorganizacion
git reset --hard origin/maria
git checkout maria
```

---

## 📝 NOTAS IMPORTANTES

1. **NO ejecutes TODO de una vez.** Hazlo fase por fase.
2. **CHECKPOINT después de cada paso.** Verifica que funciona antes de pasar al siguiente.
3. **Los nombres de URLS cam

biaron.** Si tienes JavaScript que llama URLs, actualízalas.
4. **Las funciones renombradas:** `manager_employee()` → `staff()` y `exportar_manager_employees()` → `exportar_staff()`
5. **Conflicto de rutas resuelto:** `/staff/` ahora es management (lógica real), `/team/` es dashboard (estático)

---

**Documento creado:** 2026-04-16  
**Última actualización:** 2026-04-16  
**Status:** 🟡 Listo para implementar paso a paso
