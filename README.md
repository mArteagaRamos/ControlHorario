# Control Horario

Aplicación de control horario y gestión de jornadas laborales desarrollada en Django 6.0.

## Descripción

Plataforma web para gestionar entrada/salida de empleados, jornadas laborales, correcciones de horarios y auditoría de cambios. Incluye permisos granulares (admin, manager, empleado), soft-delete, notificaciones por email y reportes.

## Características Principales

- Autenticación y gestión de usuarios
- Registro de entrada/salida con timestamps
- Solicitudes de corrección de horarios
- Sistema de soft-delete (eliminación reversible)
- Reset de contraseña por email (SMTP configurado)
- Panel administrativo con dashboard y auditoría
- Delegación segura de permisos
- Exportación de datos (CSV/PDF)
- Reportes y estadísticas

## Requisitos

- Python 3.11+
- Django 6.0.3+
- PostgreSQL 12+ (SQLite para desarrollo)
- pip

## Instalación Rápida

### 1. Clonar y configurar entorno

```bash
git clone <repository-url>
cd control_horario
python -m venv .venv

# Windows
.\.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate
```

### 2. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 3. Configurar variables de entorno

Crear archivo `.env`:

```env
DEBUG=True
SECRET_KEY=tu-clave-secreta
DATABASE_URL=sqlite:///db.sqlite3

# Email SMTP (para reset de contraseña)
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=tu-email@gmail.com
EMAIL_HOST_PASSWORD=tu-app-password
DEFAULT_FROM_EMAIL=tu-email@gmail.com
```

### 4. Migraciones y usuario

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

La app estará en `http://127.0.0.1:8000/`

## Estructura del Proyecto

```
.
├── core/                # Configuración Django, auth, managers
├── users/               # Usuarios, autenticación, admin panel
├── timetracking/        # Entrada/salida, jornadas
├── requests/            # Solicitudes de correcciones
├── audit/               # Auditoría y logs
├── admin/               # Panel administrativo
├── dashboard/           # Panel del usuario
├── aeptic_reports/      # Reportes y estadísticas
├── templates/           # Plantillas HTML
├── static/              # CSS, JS, imágenes
└── manage.py           # Django CLI
```

## Uso

**Empleados**
1. Regístrate en `/register`
2. Cambia tu contraseña inicial
3. Registra entrada/salida en el dashboard
4. Solicita correcciones si necesitas

**Managers**
1. Inicia sesión con tu cuenta
2. Visualiza personal de tu empresa
3. Aprueba/rechaza solicitudes de corrección
4. Consulta reportes de tu equipo

**Administradores**
1. Accede a `/admin/` 
2. Gestiona empresas, usuarios y membresías
3. Visualiza auditoría completa
4. Gestiona registros eliminados (soft-delete)

## Características Técnicas

### Soft-Delete
- Todos los registros se marcan con `deleted_at` en lugar de eliminarse
- Las queries filtran automáticamente registros eliminados
- Métodos: `all_with_deleted()`, `only_deleted()`, `restore()`, `hard_delete()`
- Interfaz admin para restore/hard-delete en `/admin/deleted-records/`

### Autenticación
- Backend personalizado con soporte para soft-delete
- Cambio obligatorio de contraseña para nuevos usuarios (campo `must_change_password`)
- Middleware de validación de inactividad
- Decoradores para permisos (`@admin_only_required`, `@manager_required`)

### Email
- Reset de contraseña con enlace seguro
- Notificaciones de cambios en correcciones
- Verificación de email en registro

### Auditoría
- Registro de cada cambio en entrada/salida (`TimeEntryEvent`)
- Log de acciones del sistema (`AuditLog`)
- Panel de visualización de eventos

## Variables de Entorno

```env
# Django
DEBUG=True
SECRET_KEY=tu-clave-secreta
DATABASE_URL=sqlite:///db.sqlite3
ALLOWED_HOSTS=localhost,127.0.0.1

# Email
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=tu-email@gmail.com
EMAIL_HOST_PASSWORD=tu-app-password
```

## Testing

```bash
# Tests de una app
python manage.py test users
python manage.py test timetracking

# Todos los tests
python manage.py test

# Con cobertura
pip install coverage
coverage run --source='.' manage.py test
coverage report
```

Target de cobertura: 90%. Ver `TESTING_PLAN.md` para detalles.

## Troubleshooting

**Email no se envía**
- Gmail: Usar app-specific password (no contraseña de cuenta)
- Revisar `EMAIL_HOST_USER` y `EMAIL_HOST_PASSWORD` en `.env`

**Soft-delete no funciona**
- Verificar que el modelo usa `SoftDeleteManager`
- Usar `only_deleted()` para ver eliminados, `all_with_deleted()` para todos

**Tests fallan**
- Verificar permisos en carpetas `media/` y `static/`
- Ejecutar con `sudo python manage.py test` si es necesario

**Static files no cargan en desarrollo**
```bash
python manage.py collectstatic --noinput
```

## Estado del Proyecto

Completado:
- Autenticación y usuarios
- Control horario (entrada/salida)
- Reset de contraseña
- Soft-delete con restore
- Correcciones de horarios
- Panel admin y auditoría
- Delegación de permisos
- Email SMTP
- Reportes

En progreso:
- Tests (target 90% coverage)
- Optimización de performance

## Documentación

- `/Documentación` - Documentación del proyecto
- `core/urls.py` - Todas las rutas

## Licencia

Proyecto propietario - Aeptic

## Contacto

info@aeptic.com

---

**Última actualización**: 2026-05-29
