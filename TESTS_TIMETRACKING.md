# Tests para la App Timetracking

Este documento describe la suite completa de tests para la aplicación de control horario.

## 📋 Resumen de Tests

Se han creado **41 test cases** cubriendo:
- ✅ Modelos (TimeEntries y TimeEntryEvent)
- ✅ Vistas (Clock-in, Clock-out, Pause)
- ✅ Manager personalizado (SoftDelete)
- ✅ Flujos de trabajo completos
- ✅ Casos extremos y errores

---

## 📂 Estructura de Carpetas

Los tests están organizados en una carpeta `tests/` dentro de la app timetracking:

```
timetracking/
├── tests/
│   ├── __init__.py
│   ├── fixtures.py          # Clase base TimeTrackingTestBase
│   ├── test_models.py       # Tests de modelos (TimeEntries, TimeEntryEvent)
│   ├── test_views.py        # Tests de vistas (Clock-in, Clock-out, Pause)
│   ├── test_integration.py  # Tests de integración (flujos completos)
│   └── test_edge_cases.py   # Tests de casos extremos y errores
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
# Opción 1: Con PostgreSQL (recomendado para desarrollo)
python manage.py migrate

# Opción 2: Con SQLite (si prefieres SQLite para tests)
python manage.py migrate --database=default
```

### Ejecutar todos los tests de timetracking

```bash
python manage.py test timetracking
```

### Ejecutar tests con PostgreSQL
Si ejecutas los tests normalmente, usarán SQLite. Para usar PostgreSQL en tests, edita temporalmente `settings.py` o usa:

```bash
# Ejecutar contra PostgreSQL directamente
python manage.py test timetracking --settings=core.settings_test
```

### Ejecutar tests de un módulo específico

```bash
# Solo tests de modelos
python manage.py test timetracking.tests.test_models

# Solo tests de vistas
python manage.py test timetracking.tests.test_views

# Solo tests de integración
python manage.py test timetracking.tests.test_integration

# Solo tests de casos extremos
python manage.py test timetracking.tests.test_edge_cases
```

### Ejecutar una clase específica de tests
```bash
python manage.py test timetracking.tests.test_models.TimeEntriesModelTest
python manage.py test timetracking.tests.test_models.TimeEntryEventModelTest
python manage.py test timetracking.tests.test_views.TimeTrackingViewsTest
python manage.py test timetracking.tests.test_integration.TimeTrackingIntegrationTest
python manage.py test timetracking.tests.test_edge_cases.TimeTrackingEdgeCasesTest
```

### Ejecutar un test específico
```bash
python manage.py test timetracking.tests.test_models.TimeEntriesModelTest.test_create_time_entry
```

### Ejecutar con verbosidad aumentada (muestra detalles)
```bash
python manage.py test timetracking -v 2
```

### Ejecutar con cobertura de código (si tienes coverage instalado)
```bash
coverage run --source='timetracking' manage.py test timetracking
coverage report
coverage html  # Genera un reporte HTML
```

---

## 📂 Estructura de Tests

### 1. **fixtures.py** - Setup Común

Contiene la clase `TimeTrackingTestBase` con setup común para todos los tests:
- Crea usuario Django
- Crea empresa
- Crea usuario custom
- Crea relación UserCompany
- Crea CompanySettings

```python
from timetracking.tests.fixtures import TimeTrackingTestBase

class MyTest(TimeTrackingTestBase):
    def test_something(self):
        # Uso automático de self.user, self.company, self.client
        pass
```

### 2. **test_models.py** - Tests de Modelos (13 tests)

#### TimeEntriesModelTest (6 tests)
| Test | Descripción |
|------|-------------|
| `test_create_time_entry` | Crear una entrada básica |
| `test_time_entry_total_seconds_display_ongoing` | Display sin duración |
| `test_time_entry_total_seconds_display_with_duration` | Display con duración (HH:MM:SS) |
| `test_entry_status_choices` | Todos los estados válidos |
| `test_soft_delete_entry` | Soft delete funciona correctamente |
| `test_restore_deleted_entry` | Restaurar entrada eliminada |

#### TimeEntryEventModelTest (7 tests)
| Test | Descripción |
|------|-------------|
| `test_create_clock_in_event` | Crear evento de entrada |
| `test_create_clock_out_event` | Crear evento de salida |
| `test_create_pause_events` | Crear eventos de pausa |
| `test_event_with_note` | Crear evento con nota |
| `test_soft_delete_event` | Soft delete de eventos |

### 3. **test_views.py** - Tests de Vistas (9 tests)

Tests para las vistas (acciones HTTP):

| Test | Descripción |
|------|-------------|
| `test_clock_in_successful` | Clock-in exitoso |
| `test_cannot_clock_in_twice` | Prevenir dos clock-ins concurrentes |
| `test_clock_out_successful` | Clock-out exitoso |
| `test_clock_out_without_active_entry` | Error cuando no hay entrada activa |
| `test_pause_start_successful` | Pausa exitosa |
| `test_cannot_start_pause_twice` | Prevenir dos pausas concurrentes |
| `test_pause_end_successful` | Fin de pausa exitoso |
| `test_pause_end_without_active_pause` | Error sin pausa activa |
| `test_inactive_user_cannot_clock_in` | Usuario inactivo no puede fichar |

### 4. **test_integration.py** - Tests de Integración (2 tests)

Tests de flujos completos:

| Test | Descripción |
|------|-------------|
| `test_complete_work_day_workflow` | Día completo: clock-in → pausa → clock-out |
| `test_multiple_entries_per_user` | Usuario puede tener múltiples registros |

### 5. **test_edge_cases.py** - Tests de Casos Extremos (8 tests)

Casos extremos y errores:

| Test | Descripción |
|------|-------------|
| `test_total_seconds_calculation` | Cálculo correcto de segundos |
| `test_entry_with_null_notes` | Campo notes puede ser null |
| `test_entry_with_notes` | Campo notes puede tener valor |
| `test_entry_date_defaults_to_today` | Fecha por defecto es hoy |
| `test_entry_status_transition` | Transiciones de estado válidas |
| `test_event_without_actor` | Evento sin actor (auto-close) |
| `test_zero_duration_entry` | Entrada con duración cero |
| `test_very_long_entry` | Entrada muy larga (48+ horas) |

---

## ⚠️ Nota Importante

El archivo anterior `timetracking/tests.py` **ya no se usa**. Todos los tests están ahora en la carpeta `timetracking/tests/`. Django automáticamente descubrirá todos los archivos `test_*.py` dentro de esa carpeta.

---

## ✅ Casos Cubiertos

### Modelos
- [x] Crear TimeEntries con todos los campos
- [x] Crear TimeEntryEvent con todos los tipos
- [x] Estados válidos del modelo
- [x] Soft delete y restauración
- [x] Propiedades calculadas (total_seconds_display)
- [x] Relaciones entre modelos
- [x] Campos opcionales (notes, actor)

### Vistas
- [x] Clock-in exitoso
- [x] Clock-out exitoso
- [x] Pausa exitosa
- [x] Validaciones (no doble clock-in, no pausa sin entrada)
- [x] Usuario inactivo no puede fichar
- [x] Sin entrada activa para acciones

### Funcionalidad
- [x] Flujo completo de trabajo (día completo)
- [x] Múltiples registros por usuario
- [x] Cálculo de duración
- [x] Transiciones de estado

### Edge Cases
- [x] Campos null opcionales
- [x] Valores por defecto
- [x] Eventos sin actor
- [x] Duración con minutos y segundos

---

## 🔧 Setup en Diferentes Ambientes

### Desarrollo Local
```bash
python manage.py test timetracking -v 2
```

### Con Base de Datos SQLite (por defecto)
Los tests usan una BD temporal que se crea y elimina automáticamente.

### Con Base de Datos PostgreSQL (producción)
```bash
# Asegúrate de que las credenciales estén en settings.py
python manage.py test timetracking
```

### En CI/CD (GitHub Actions, etc)
```bash
python manage.py test timetracking --no-migrations
```

---

## 📊 Cobertura de Código

Para generar un reporte de cobertura:

```bash
# Instalar coverage si no lo tienes
pip install coverage

# Ejecutar tests con coverage
coverage run --source='timetracking' manage.py test timetracking

# Ver reporte en consola
coverage report

# Generar reporte HTML
coverage html

# Abrir reporte en navegador
open htmlcov/index.html  # macOS
start htmlcov/index.html  # Windows
xdg-open htmlcov/index.html  # Linux
```

**Meta esperada**: 85%+ de cobertura

---

## 🎯 Tests Mínimos por Entregar

Según el documento PDF, los tests mínimos obligatorios son:

1. **Tests de Modelos**
   - [x] Crear modelo
   - [x] Propiedades del modelo
   - [x] Estados del modelo
   - [x] Relaciones

2. **Tests de Vistas**
   - [x] Clock-in
   - [x] Clock-out
   - [x] Pausa
   - [x] Validaciones

3. **Tests de Integración**
   - [x] Flujo completo
   - [x] Múltiples operaciones

---

## 🐛 Solución de Problemas

### ImportError: No module named 'timetracking'
```bash
# Asegúrate de que INSTALLED_APPS incluya 'timetracking'
# en settings.py
```

### No se crean las tablas de test
```bash
python manage.py migrate --run-syncdb
python manage.py test timetracking
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
Verifica que la función `setUp()` en TimeTrackingTestBase cree todos los usuarios necesarios.

---

## 📝 Ejemplo de Test Personalizado

Para agregar un nuevo test:

```python
class MyCustomTest(TimeTrackingTestBase):
    """Descripción del test"""
    
    def test_my_feature(self):
        """Test case description"""
        # Arrange - Preparar datos
        entry = TimeEntries.objects.create(
            id=uuid4(),
            user=self.user,
            company=self.company,
            date=timezone.localdate(),
            clock_in=timezone.now(),
            status=TimeEntries.EntryStatus.ONGOING
        )
        
        # Act - Ejecutar acción
        entry.status = TimeEntries.EntryStatus.CONFIRMED
        entry.save()
        
        # Assert - Verificar resultado
        entry.refresh_from_db()
        self.assertEqual(entry.status, TimeEntries.EntryStatus.CONFIRMED)
```

---

## � Archivos Modificados/Creados

```
timetracking/tests/
├── __init__.py                # Marca como paquete Python
├── fixtures.py                # TimeTrackingTestBase (setup común)
├── test_models.py             # Tests de TimeEntries y TimeEntryEvent
├── test_views.py              # Tests de vistas (clock-in/out/pause)
├── test_integration.py        # Tests de flujos completos
└── test_edge_cases.py         # Tests de casos extremos

TESTS_TIMETRACKING.md          # Esta documentación
```

---

- [Django Testing Documentation](https://docs.djangoproject.com/en/stable/topics/testing/)
- [TestCase API Reference](https://docs.djangoproject.com/en/stable/topics/testing/tools/#testcase)
- [Testing Best Practices](https://docs.djangoproject.com/en/stable/topics/testing/overview/)

---

## 🎓 Notas

- Los tests están organizados por funcionalidad (modelos, vistas, integración)
- Cada test es independiente y se ejecuta en una transacción
- La base de datos se reinicia después de cada test
- Los datos de setup se crean en `setUp()` automáticamente
- Los tests usan UUIDs válidos con `uuid4()`
- Se usa `timezone.now()` para fechas consistentes
