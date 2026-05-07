# Tests para la App Corrections

Este documento describe la suite completa de tests para la aplicación de correcciones de horario y solicitudes de ausencia.

## 📋 Resumen de Tests

Se han creado **33 test cases** cubriendo:
- ✅ Modelos (CorrectionRequests y LeaveRequest)
- ✅ Vistas (Resolver correcciones, exportar reportes)
- ✅ Flujos de trabajo completos
- ✅ Casos extremos y errores

---

## 📂 Estructura de Carpetas

Los tests están organizados en una carpeta `tests/` dentro de la app corrections:

```
corrections/
├── tests/
│   ├── __init__.py
│   ├── fixtures.py              # Clase base CorrectionsTestBase
│   ├── test_models.py           # Tests de modelos (CorrectionRequests, LeaveRequest)
│   ├── test_views.py            # Tests de vistas (resolver correcciones, exportar)
│   ├── test_integration.py      # Tests de integración (flujos completos)
│   └── test_edge_cases.py       # Tests de casos extremos y errores
├── models.py
├── views.py
├── admin.py
├── apps.py
└── ...
```

---

## 🚀 Cómo Ejecutar los Tests

### ⚠️ Requisitos Previos

Los tests requieren que las tablas de la base de datos estén creadas. Ejecuta esto ANTES de correr los tests por primera vez:

```bash
python manage.py migrate
```

### Ejecutar todos los tests de corrections

```bash
python manage.py test corrections
```

### Ejecutar tests de un módulo específico

```bash
# Solo tests de modelos
python manage.py test corrections.tests.test_models

# Solo tests de vistas
python manage.py test requests.tests.test_views

# Solo tests de integración
python manage.py test corrections.tests.test_integration

# Solo tests de casos extremos
python manage.py test corrections.tests.test_edge_cases
```

### Ejecutar una clase específica de tests

```bash
python manage.py test corrections.tests.test_models.CorrectionRequestsModelTest
python manage.py test corrections.tests.test_models.LeaveRequestModelTest
python manage.py test corrections.tests.test_views.CorrectionsViewsTest
python manage.py test corrections.tests.test_integration.CorrectionsIntegrationTest
python manage.py test corrections.tests.test_edge_cases.CorrectionsEdgeCasesTest
```

### Ejecutar un test específico

```bash
python manage.py test corrections.tests.test_models.CorrectionRequestsModelTest.test_create_correction_request
```

### Ejecutar con verbosidad aumentada

```bash
python manage.py test corrections -v 2
```

### Ejecutar con cobertura de código

```bash
coverage run --source='corrections' manage.py test corrections
coverage report
coverage html
```

---

## 📂 Estructura de Tests

### 1. **fixtures.py** - Setup Común

Contiene la clase `CorrectionsTestBase` con setup común para todos los tests:
- Crea usuario Django (testuser)
- Crea usuario manager (testmanager)
- Crea empresa
- Crea relaciones UserCompany para ambos usuarios
- Crea una TimeEntry para usar en correcciones

```python
from corrections.tests.fixtures import CorrectionsTestBase

class MyTest(CorrectionsTestBase):
    def test_something(self):
        # Uso automático de self.user, self.manager, self.company, self.time_entry
        pass
```

### 2. **test_models.py** - Tests de Modelos (12 tests)

#### CorrectionRequestsModelTest (4 tests)
| Test | Descripción |
|------|-------------|
| `test_create_correction_request` | Crear una solicitud de corrección básica |
| `test_correction_request_status_choices` | Todos los estados válidos (pending, approved, rejected) |
| `test_approve_correction_request` | Aprobar una corrección y asignar approver |
| `test_reject_correction_request` | Rechazar una corrección |

#### LeaveRequestModelTest (8 tests)
| Test | Descripción |
|------|-------------|
| `test_create_leave_request` | Crear una solicitud de ausencia básica |
| `test_leave_request_status_choices` | Todos los estados de ausencia (pending, approved, rejected, canceled) |
| `test_leave_reason_choices` | Todos los motivos de ausencia disponibles |
| `test_leave_request_with_reason_note` | Crear ausencia con nota de motivo |
| `test_approve_leave_request` | Aprobar una solicitud de ausencia |

### 3. **test_views.py** - Tests de Vistas (5 tests)

Tests para las acciones HTTP:

| Test | Descripción |
|------|-------------|
| `test_resolver_incidencia_approve_successful` | Aprobar corrección vía vista |
| `test_resolver_incidencia_reject_successful` | Rechazar corrección vía vista |
| `test_resolver_incidencia_approve_creates_new_entry` | Aprobación crea nuevo TimeEntry |
| `test_resolver_incidencia_reject_no_new_entry` | Rechazo no crea nuevo TimeEntry |
| `test_only_manager_can_resolve` | Solo managers pueden resolver correcciones |

### 4. **test_integration.py** - Tests de Integración (4 tests)

Tests de flujos completos:

| Test | Descripción |
|------|-------------|
| `test_complete_correction_workflow` | Flujo completo: crear → aprobar → verificar |
| `test_complete_leave_request_workflow` | Flujo completo de ausencia: crear → aprobar |
| `test_multiple_corrections_per_user` | Usuario puede tener múltiples correcciones |
| `test_multiple_leaves_per_user` | Usuario puede tener múltiples ausencias |

### 5. **test_edge_cases.py** - Tests de Casos Extremos (8 tests)

Casos extremos y errores:

| Test | Descripción |
|------|-------------|
| `test_correction_with_partial_new_times` | Corrección con solo uno de los tiempos |
| `test_correction_seconds_calculation` | Cálculo correcto de duración en segundos |
| `test_leave_spanning_multiple_days` | Ausencia que abarca 30+ días |
| `test_leave_request_single_day` | Ausencia de un solo día |
| `test_leave_request_with_attachment` | Ausencia con archivo adjunto |
| `test_correction_with_zero_duration` | Corrección con duración 0 |
| `test_leave_with_review_timestamp` | Verificación de timestamps de revisión |

---

## ✅ Casos Cubiertos

### Modelos
- [x] Crear CorrectionRequests con todos los campos
- [x] Crear LeaveRequest con todos los campos
- [x] Todos los estados válidos de correcciones
- [x] Todos los estados de ausencias
- [x] Todos los motivos de ausencia
- [x] Relaciones entre modelos
- [x] Campos opcionales (notes, attachments)

### Vistas
- [x] Aprobar correcciones y crear nuevo TimeEntry
- [x] Rechazar correcciones sin crear nuevo registro
- [x] Solo managers pueden resolver
- [x] Asignación correcta de approver y timestamps

### Funcionalidad
- [x] Flujo completo de correcciones
- [x] Flujo completo de ausencias
- [x] Múltiples correcciones por usuario
- [x] Múltiples ausencias por usuario

### Edge Cases
- [x] Correcciones con tiempos parciales
- [x] Cálculo correcto de duración
- [x] Ausencias de múltiples días
- [x] Ausencias con attachments
- [x] Ausencias de un día
- [x] Duración cero
- [x] Timestamps correctos

---

## 🔧 Setup en Diferentes Ambientes

### Desarrollo Local
```bash
python manage.py test corrections -v 2
```

### Base de Datos SQLite
Los tests usan una BD temporal que se crea y elimina automáticamente.

### Base de Datos PostgreSQL
```bash
python manage.py test corrections
```

### En CI/CD
```bash
python manage.py test corrections --no-migrations
```

---

## 📊 Cobertura de Código

Para generar un reporte de cobertura:

```bash
pip install coverage
coverage run --source='corrections' manage.py test corrections
coverage report
coverage html
start htmlcov/index.html
```

**Meta esperada**: 85%+ de cobertura

---

## 🎯 Tests Mínimos por Entregar

Según el documento de especificaciones, los tests mínimos obligatorios son:

1. **Tests de Modelos**
   - [x] Crear modelos
   - [x] Estados válidos
   - [x] Relaciones

2. **Tests de Vistas**
   - [x] Resolver correcciones
   - [x] Validaciones de permisos
   - [x] Creación de registros

3. **Tests de Integración**
   - [x] Flujo completo de correcciones
   - [x] Flujo completo de ausencias

---

## 🐛 Solución de Problemas

### ImportError: No module named 'corrections'
```bash
# Asegúrate de que INSTALLED_APPS incluya 'corrections' en settings.py
```

### No se crean las tablas de test
```bash
python manage.py migrate --run-syncdb
python manage.py test corrections
```

### Tests timeout
Aumenta el timeout en settings.py:
```python
DATABASES = {
    'default': {
        'TEST': {
            'TIMEOUT': 60,
        }
    }
}
```

### Faltan datos del usuario
Verifica que la función `setUp()` en CorrectionsTestBase cree todos los usuarios necesarios.

---

## 📝 Ejemplo de Test Personalizado

Para agregar un nuevo test:

```python
class MyCustomTest(CorrectionsTestBase):
    """Descripción del test"""
    
    def test_my_feature(self):
        """Test case description"""
        # Arrange - Preparar datos
        correction = CorrectionRequests.objects.create(
            id=uuid4(),
            time_entry=self.time_entry,
            requester=self.user,
            request_date=timezone.now(),
            reason='Test reason',
            new_clock_in=timezone.now(),
            new_clock_out=timezone.now() + datetime.timedelta(hours=8),
            status=CorrectionRequests.CorrectionStatus.PENDING
        )
        
        # Act - Ejecutar acción
        correction.status = CorrectionRequests.CorrectionStatus.APPROVED
        correction.save()
        
        # Assert - Verificar resultado
        correction.refresh_from_db()
        self.assertEqual(correction.status, CorrectionRequests.CorrectionStatus.APPROVED)
```

---

## 📁 Archivos Modificados/Creados

```
corrections/tests/
├── __init__.py                  # Marca como paquete Python
├── fixtures.py                  # CorrectionsTestBase (setup común)
├── test_models.py               # Tests de CorrectionRequests y LeaveRequest
├── test_views.py                # Tests de vistas (resolver correcciones)
├── test_integration.py          # Tests de flujos completos
└── test_edge_cases.py           # Tests de casos extremos

TESTS_CORRECTIONS.md             # Esta documentación
```

---

## 🔗 Referencias

- [Django Testing Documentation](https://docs.djangoproject.com/en/stable/topics/testing/)
- [TestCase API Reference](https://docs.djangoproject.com/en/stable/topics/testing/tools/#testcase)
- [Testing Best Practices](https://docs.djangoproject.com/en/stable/topics/testing/overview/)

---

## 🎓 Notas

- Los tests están organizados por funcionalidad (modelos, vistas, integración)
- Cada test es independiente y se ejecuta en una transacción
- La base de datos se reinicia después de cada test
- Los datos de setup se crean en `setUp()` automáticamente
- Se usa `timezone.now()` para fechas consistentes
- Los tests incluyen tanto casos exitosos como casos de error/restricción
