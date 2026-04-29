# 🧪 Plan de Tests - Control Horario

**Objetivo:** Cobertura del 90% en la app `users` con Django TestCase
**Enfoque:** Tests críticos primero → Cobertura completa
**Estructura:** Carpeta `users/tests/` con archivos por funcionalidad

---

## 📊 Fases del Proyecto

### **FASE 1: Setup y Críticos (40% de tareas - PRIORITARIO)**
Fundaciones + tests que protegen funcionalidad core.

### **FASE 2: Permisos y Validaciones (35% de tareas)**
Tests de cada rol + validaciones de formularios.

### **FASE 3: Búsquedas AJAX y Funcionalidades (20% de tareas)**
Búsquedas AJAX, exportaciones, soft-delete.

### **FASE 4: Cobertura Final (5% de tareas)**
Edge cases y lineas no cubiertas.

---

## 🎯 Orden de Prioridad - Bloques de Trabajo

### **BLOQUE 1: Setup y Fixtures** ⭐⭐⭐ CRÍTICO
- [ ] **1.1** Crear estructura `users/tests/` (carpeta + `__init__.py`)
- [ ] **1.2** Crear `tests/conftest.py` con fixtures base
  - admin_user, manager_user, employee_user, auditor_user
  - company_1, company_2
  - user_company memberships
  - Settings y configuración
- [ ] **1.3** Crear helper fixtures reutilizables
  - create_user_with_company(role)
  - create_company(tax_id)
  - authenticate_user(user)

---

### **BLOQUE 2: Tests de Modelos** ⭐⭐⭐ CRÍTICO
- [ ] **2.1** `tests/test_models.py` - Users Model
  - Normalización de campos (uppercase/lowercase)
  - Soft-delete (deleted_at behavior)
  - must_change_password flag
  - Status choices (active, inactive, suspended)
  - is_auditor flag
  - is_admin flag
  - __str__ method
  - PASSWORD_FIELD = email

- [ ] **2.2** `tests/test_models.py` - Companies Model
  - Soft-delete functionality
  - tax_id uniqueness
  - created_at / updated_at

- [ ] **2.3** `tests/test_models.py` - UserCompany Model
  - unique_together constraint (user, company)
  - Soft-delete
  - Role choices (manager, employee)
  - joined_at timestamp

---

### **BLOQUE 3: Tests de Autenticación** ⭐⭐⭐ CRÍTICO
- [ ] **3.1** `tests/test_auth.py` - Login Happy Path
  - Email + password válidos → login exitoso
  - Redirige a home_timetracking (1 empresa)
  - Redirige a company selector (2+ empresas)
  - Crea AuditLog
  - Session se configura correctamente

- [ ] **3.2** `tests/test_auth.py` - Login Edge Cases
  - Email no existe → error message
  - Password incorrecta → error message
  - Usuario suspended → error + AuditLog
  - Usuario deleted_at != null → error + AuditLog
  - Usuario sin membresías activas → error
  - Form validation errors → logged

- [ ] **3.3** `tests/test_auth.py` - SetPassword Flow
  - must_change_password=True → muestra SetPasswordForm
  - Password < 8 caracteres → error
  - Sin mayúscula/minúscula/número/special → error
  - Passwords no coinciden → error
  - Password válido → login completo
  - must_change_password set a False

- [ ] **3.4** `tests/test_auth.py` - Company Selection
  - 2+ empresas → selector visible
  - Selecciona empresa válida → redirect home
  - Selecciona empresa sin membership → error

- [ ] **3.5** `tests/test_auth.py` - Auditor Login
  - Auditor login → redirige a audit_dashboard
  - Auditor + must_change_password → SetPassword flow
  - Auditor sin password setup → redirect audit_dashboard

- [ ] **3.6** `tests/test_auth.py` - Logout
  - Usuario logueado → logout OK
  - Crea AuditLog reason='Logout'
  - Redirige a login
  - Session limpiada

---

### **BLOQUE 4: Tests de Permisos (ROLES)** ⭐⭐⭐ CRÍTICO
- [ ] **4.1** `tests/test_permissions.py` - lookup_company
  - **Admin** → 200, acceso total
  - **Manager** → 403, sin acceso
  - **Employee** → 403, sin acceso
  - **Auditor** → 403, sin acceso
  - **Anonymous** → 401, sin loguear

- [ ] **4.2** `tests/test_permissions.py` - lookup_user
  - **Admin** global search → 200, todos usuarios
  - **Admin** busqueda → exclude suspended
  - **Manager** search en su empresa → 200
  - **Manager** search otra empresa → 403
  - **Employee** → búsqueda limitada o 403
  - **Auditor** → 403

- [ ] **4.3** `tests/test_permissions.py` - register_unified
  - **Admin** crea usuario nuevo → 200
  - **Admin** crea auditor → 200
  - **Manager** crea en su empresa → 200
  - **Manager** crea en otra empresa → 403
  - **Employee** → 403
  - **Auditor** → 403
  - **Anonymous** → 401

- [ ] **4.4** `tests/test_permissions.py` - check_last_manager
  - **Admin** check cualquier user/company → 200
  - **Manager** check en su company → 200
  - **Manager** check otra company → 403
  - **Employee** → 403
  - Lógica: detecta si es último manager

- [ ] **4.5** `tests/test_permissions.py` - switch_company
  - Cambiar a empresa con membership → 302 redirect
  - Cambiar a empresa sin membership → error
  - Session['company_id'] actualizada
  - **Anonymous** → 401

- [ ] **4.6** `tests/test_permissions.py` - workday (user dashboard)
  - **Employee** ve su propio workday → 200
  - **Employee** intenta workday de otro → delegación/error
  - **Manager** ve workday de su empresa → depende lógica
  - **Auditor** → ???
  - Datos correctos en contexto

---

### **BLOQUE 5: Tests de Formularios** ⭐⭐
- [ ] **5.1** `tests/test_forms.py` - LoginForm
  - Email obligatorio
  - Password obligatorio
  - Email normalizado (lowercase)
  - Email format validation

- [ ] **5.2** `tests/test_forms.py` - SetPasswordForm
  - Min 8 caracteres
  - Requiere mayúscula
  - Requiere minúscula
  - Requiere dígito
  - Requiere special char (!¡¿?@#$%^&*-_;:./~)
  - Confirmación coincide
  - Error messages claros

- [ ] **5.3** `tests/test_forms.py` - CompanyCreateForm / CompanyForm
  - CompanyForm fields opcionales
  - CompanyCreateForm fields obligatorios
  - tax_id validation (uniqueness en context)
  - Nombre validation
  - Legal name validation

- [ ] **5.4** `tests/test_forms.py` - WorkerCreateForm
  - Email obligatorio + único
  - DNI obligatorio + único
  - Username obligatorio
  - Surname obligatorio
  - is_auditor checkbox
  - Password field para temp password
  - Role selection
  - Status choices

- [ ] **5.5** `tests/test_forms.py` - WorkerSelectForm
  - Edita usuario existente
  - Email unique (exclude self)
  - DNI unique (exclude self)
  - No require password
  - Campos opcionales

- [ ] **5.6** `tests/test_forms.py` - UserPersonalDataForm
  - Email unique (exclude self)
  - DNI unique (exclude self)
  - Normalización de campos
  - Username, surname, email, dni fields

- [ ] **5.7** `tests/test_forms.py` - CompanySelectLoginForm
  - Choices populated from companies
  - Company selection valid

---

### **BLOQUE 6: Búsquedas AJAX** ⭐⭐
- [ ] **6.1** `tests/test_ajax_lookups.py` - lookup_company
  - Por tax_id → encuentra empresa
  - Por name (autocomplet) → lista 10 items
  - Por company_id → devuelve + member_count
  - Sin parámetros → error 400
  - include_created parameter
  - Empresas creadas_at formatted
  - Response JSON válido

- [ ] **6.2** `tests/test_ajax_lookups.py` - lookup_user
  - Por email → usuario único
  - Por dni → usuario único
  - Por name → múltiples resultados (max 10)
  - Con company_id → filtra por empresa
  - Admin búsqueda global
  - Excluye suspended users
  - Excluye deleted users (deleted_at != null)
  - Solo membresías activas (deleted_at__isnull=True)
  - include_companies parameter
  - Response JSON válido
  - Permissions: solo admin búsqueda global

- [ ] **6.3** `tests/test_ajax_lookups.py` - check_last_manager
  - User es manager → is_manager=True
  - User no es manager → is_manager=False
  - Cuenta otros managers
  - is_last_manager=True si es único
  - Devuelve JSON valid
  - Permissions check

---

### **BLOQUE 7: Registro Unificado** ⭐⭐
- [ ] **7.1** `tests/test_register.py` - Create New User + Company (Admin)
  - Admin POST company_mode='create' + worker_action='create'
  - Valida datos empresa (CompanyCreateForm)
  - Crea empresa nueva (UUID, timestamps)
  - Crea usuario nuevo (email, username, dni, password hash)
  - Crea UserCompany (role=EMPLOYEE o MANAGER)
  - must_change_password=True
  - Envía email (send_new_user_email)
  - Crea AuditLog

- [ ] **7.2** `tests/test_register.py` - Update Existing Company (Admin)
  - Admin busca empresa por tax_id
  - Encuentra empresa existente
  - Actualiza datos (name, legal_name)
  - updated_at se modifica
  - Crea AuditLog de update

- [ ] **7.3** `tests/test_register.py` - Create Auditor
  - Admin POST is_auditor='on'
  - NO requiere empresa (company_form skipped)
  - is_auditor=True en usuario
  - NO crea UserCompany
  - Envía email diferente (send_new_auditor_email)
  - Crea AuditLog

- [ ] **7.4** `tests/test_register.py` - Add to Existing Company (Admin/Manager)
  - company_mode='select'
  - Busca empresa por ID
  - Valida acceso (manager solo su empresa)
  - Crea/actualiza membership

- [ ] **7.5** `tests/test_register.py` - Existing User New Membership
  - Email existe en DB
  - Busca usuario por email
  - Crea membresía en nueva empresa
  - Envía email (send_existing_user_email)
  - Valida cambios de rol

- [ ] **7.6** `tests/test_register.py` - Role Change Validation
  - Intenta cambiar último manager a employee → error
  - validate_manager_role_change() devuelve (False, msg)
  - Otros cambios de rol → OK
  - Muestra error a usuario

- [ ] **7.7** `tests/test_register.py` - Error Handling
  - Errores acumulados en lista
  - Mostrados al usuario
  - No crea usuario si hay errores
  - Rollback transaccional si es necesario

---

### **BLOQUE 8: Delegación Segura** ⭐⭐
- [ ] **8.1** `tests/test_permissions.py` - Delegation Setup
  - Admin setea delegated_user_id en session
  - Admin setea delegated_company_id en session
  - get_effective_context() devuelve is_delegating=True

- [ ] **8.2** `tests/test_permissions.py` - Delegation Validation
  - Delegated user existe → validación OK
  - Delegated user no existe → limpia session
  - Delegated company existe → validación OK
  - Delegated company no existe → limpia session

- [ ] **8.3** `tests/test_permissions.py` - Delegation Permission Check
  - Delegated user es manager en company → permiso OK
  - Delegated user es admin → permiso OK
  - Delegated user es employee → limpia delegation
  - Delegated user tiene membresía deleted_at → limpia

- [ ] **8.4** `tests/test_permissions.py` - manager_or_admin_with_delegation_check
  - Admin delegando válido → acceso OK
  - Admin delegando inválido → limpia + accede como admin
  - Manager normal → acceso OK
  - Employee → 403
  - Anonymous → 401

---

### **BLOQUE 9: Exportaciones CSV** ⭐
- [ ] **9.1** `tests/test_exports.py` - exportar_workday_entries
  - POST sin selection → error/message
  - POST con entry_ids válidas → CSV descargado
  - Response content-type='text/csv'
  - Columnas: Fecha, Entrada, Salida, Tiempo Total (HH:MM:SS), Estado, Notas
  - Timestamps formateados correctamente
  - Crea AuditLog con reason
  - BOM UTF-8 presente (para Excel)
  - Filename contiene fecha

- [ ] **9.2** `tests/test_exports.py` - exportar_workday_requests
  - POST sin selection → error
  - POST con request_ids válidas → CSV descargado
  - Columnas: Fecha Solicitud, Fecha Evento, Entrada Orig, Salida Orig, etc.
  - Formatos correctos
  - Crea AuditLog
  - Solo requests del usuario (si no es admin)

---

### **BLOQUE 10: Soft-Delete Integration** ⭐
- [ ] **10.1** `tests/test_models.py` - Soft-Delete Queries
  - deleted_at=None → visible en queries normales
  - deleted_at != null → excluido de queries normales
  - all_with_deleted() → incluye deleted
  - only_deleted() → solo deleted
  - restore() marca deleted_at=None
  - hard_delete() elimina permanente

- [ ] **10.2** `tests/test_auth.py` - Soft-Delete Login
  - Usuario con deleted_at != null → no puede login
  - AuditLog con reason='Intento de login: cuenta eliminada'
  - Membresía con deleted_at != null → no cuenta como activa

---

### **BLOQUE 11: Edge Cases & Coverage Gaps** 
- [ ] **11.1** Password normalization & validation edge cases
- [ ] **11.2** Unicode/special chars en nombres
- [ ] **11.3** Concurrent requests (race conditions)
- [ ] **11.4** Session timeout & middleware
- [ ] **11.5** Email case variations
- [ ] **11.6** Multiple company memberships edge cases
- [ ] **11.7** Admin delegation edge cases
- [ ] **11.8** Form submission errors & recovery

---

## 📋 Estructura de Archivos

```
users/
├── tests/
│   ├── __init__.py
│   ├── conftest.py                 # Fixtures compartidas
│   ├── test_models.py              # Models: Users, Companies, UserCompany
│   ├── test_auth.py                # Auth: login, logout, password, auditor
│   ├── test_permissions.py         # Permisos por rol + delegación
│   ├── test_forms.py               # Validación de formularios
│   ├── test_ajax_lookups.py        # lookup_company, lookup_user, check_last_manager
│   ├── test_register.py            # register_unified flow
│   ├── test_exports.py             # Exportaciones CSV
│   └── fixtures.py (opcional)      # Helpers adicionales
│
├── models.py
├── views.py
├── forms.py
├── middleware.py
└── ...
```

---

## 🔧 Utilidades Recomendadas

### BaseTestCase class (crear en conftest.py):
```python
from django.test import TestCase, Client
from django.contrib.auth import get_user_model

class BaseTestCase(TestCase):
    """Base para todos los tests con helpers comunes"""
    
    def setUp(self):
        self.client = Client()
        self.admin = self._create_admin()
        self.manager = self._create_manager()
        self.employee = self._create_employee()
        self.auditor = self._create_auditor()
        self.company1 = self._create_company('ES12345678A')
        
    def _create_admin(self):
        # Create admin user
        pass
    
    def _login(self, user):
        self.client.force_login(user)
        
    def _assert_has_permission(self, user, url, expected_status):
        # Assert user has permission
        pass
```

---

## 📊 Cobertura Target: 90%

**Distribución esperada:**
- Models: 95%+ (muy simple)
- Views: 85-90% (lógica compleja, edge cases)
- Forms: 92%+ (validaciones)
- Auth: 88%+ (flujos multi-paso)

**Líneas excluidas:**
- Debug statements
- Except clauses que no ocurren en tests
- Template rendering details

---

## ✅ Checklist de Validación

- [ ] Todos los testes pasan (`python manage.py test users`)
- [ ] Coverage >= 90% (`coverage run --source='users' manage.py test`)
- [ ] No hay warnings ni deprecations
- [ ] Fixtures son reutilizables y limpias
- [ ] Tests son independientes (no orden-dependientes)
- [ ] Nombres descriptivos (test_login_with_valid_credentials_redirects_to_home)
- [ ] Docstrings en tests complejos
- [ ] Cada test prueba UNA cosa
- [ ] Setup/teardown maneja soft-deletes

---

## 🚀 Próximos Pasos

1. **Crear estructura de carpeta** `users/tests/`
2. **Crear `conftest.py`** con fixtures base
3. **Iniciar BLOQUE 1** (Setup)
4. **Iniciar BLOQUE 2** (Models)
5. **Iniciar BLOQUE 3** (Auth)
6. **... continuar por orden**

**Recomendación:** Hacer 1-2 bloques por sesión para mantener contexto.

---

## 📝 Notas Importantes

### Para Django TestCase:
- `setUp()` se ejecuta antes de cada test
- `tearDown()` se ejecuta después (soft-delete limpia automáticamente)
- Usa `self.client` para requests HTTP
- Usa `self.assertEqual()`, `self.assertTrue()`, etc.
- Database es limpiada entre tests

### Para Fixtures:
- Definir en `conftest.py` o en clase base
- Reutilizar máximo (crear en setUp, no en cada test)
- Usar UUIDs aleatorios para evitar conflictos

### Para Permisos:
- SIEMPRE testear: Usuario autenticado + Rol + URL → Status code
- SIEMPRE testear: Anonymous → 401
- SIEMPRE testear: Rol sin permisos → 403

---

**Documento actualizado:** 2026-04-29
**Estado:** Listo para comenzar
