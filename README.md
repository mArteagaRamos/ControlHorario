# Control Horario

Aplicación empresarial de control horario y gestión de jornadas laborales desarrollada en Django.

## Descripción del Proyecto

Control Horario es una plataforma web completa para gestionar entradas/salidas de empleados, registro de jornadas, solicitudes de corrección de horarios y auditoría de cambios. Diseñada para empresas que necesitan mantener un control riguroso de asistencia y flexibilidad en la corrección de registros.

### Funcionalidades Principales

**Gestión de Usuarios y Seguridad**
- Autenticación de usuarios con correo y contraseña
- Registro de nuevos usuarios con verificación por email
- Control de permisos: administrador, manager, empleado
- Cambio obligatorio de contraseña para nuevos usuarios
- Delegación segura de permisos de administración
- Soft-delete de registros (eliminación lógica)

**Control Horario (Time Tracking)**
- Registro de entrada/salida con timestamps automáticos
- Estados de entrada: en curso, confirmado, auto-cerrado, corregido, anulado
- Visualización de jornadas diarias con duración total
- Exportación de registros por período
- Historial completo de cambios en auditoría

**Gestión de Correcciones**
- Solicitud de corrección de horarios por empleados
- Aprobación/rechazo de correcciones por managers/admins
- Comentarios y justificación en correcciones
- Historial de correcciones aplicadas
- Validación de cambios en tiempos

**Panel de Administración**
- Dashboard para admins con estadísticas de empresas
- Visualización de personal por empresa (inspección)
- Gestión de registros eliminados (restore/hard-delete)
- Auditoría completa de acciones del sistema
- Logs de eventos de entrada/salida

**Gestión de Empresas**
- Creación y configuración de empresas
- Membresías de usuarios en empresas
- Rol y permisos dentro de cada empresa
- Configuración de empresa (settings)

## Estructura del Proyecto

```
.
├── core/                    # Configuración principal de Django
│   ├── settings.py         # Configuración de la aplicación
│   ├── urls.py             # Rutas principales
│   ├── auth.py             # Backend de autenticación con soft-delete
│   ├── managers.py         # Managers centralizados para soft-delete
│   └── wsgi/asgi.py        # Puntos de entrada de producción
│
├── users/                   # Gestión de usuarios y autenticación
│   ├── models.py           # Usuario, Empresa, UserCompany, CompanySettings
│   ├── views.py            # Login, registro, cambio contraseña, admin panel
│   ├── forms.py            # Formularios de autenticación y gestión
│   ├── middleware.py       # Middleware de empresa, sesión e inactividad
│   ├── email_utils.py      # Utilidades de envío de emails
│   └── context_processors.py # Procesadores de contexto para templates
│
├── timetracking/            # Control horario
│   ├── models.py           # TimeEntries (entrada/salida)
│   ├── views.py            # Vistas de entrada/salida y visualización
│   └── tests.py            # Tests (pendiente completar)
│
├── requests/                # Gestión de solicitudes de correcciones y ausencias
│   ├── models.py           # CorrectionRequest
│   ├── views.py            # Solicitud, aprobación, rechazo de correcciones
│   └── tests.py            # Tests (pendiente completar)
│
├── audit/                   # Auditoría y logging
│   ├── models.py           # TimeEntryEvent, AuditLog
│   ├── views.py            # Visualización de logs y eventos
│   └── tests.py            # Tests (pendiente completar)
│
├── admin/                   # Panel administrativo
│   ├── models.py           # Modelo Admin
│   ├── views.py            # Vistas del panel admin
│   └── tests.py            # Tests (pendiente completar)
│
├── dashboard/               # Panel de usuario
│   ├── views.py            # Home y panel del usuario
│   └── tests.py            # Tests (pendiente completar)
│
├── management/              # Comandos de gestión personalizados
│   └── commands/
│
├── templates/               # Plantillas HTML
│   ├── base/                # Templates base (navbar, sidebar)
│   ├── login/               # Templates de autenticación
│   ├── dashboard/           # Templates del panel
│   ├── admin/               # Templates del admin
│   ├── audit/               # Templates de auditoría
│   └── error/               # Páginas de error
│
└── static/                  # Archivos estáticos
    ├── css/                 # Estilos personalizados
    ├── js/                  # Scripts JavaScript
    └── img/                 # Imágenes y recursos
```

## Requisitos

- **Python 3.11+**
- **Django 6.0.3**
- **PostgreSQL** (se puede usar SQLite en desarrollo)
- Dependencias en `requirements.txt`

## Instalación y Configuración

### 1. Clonar el repositorio

```bash
git clone <repository-url>
cd control_horario
```

### 2. Crear y activar entorno virtual

```bash
# Windows
python -m venv .venv
.\.venv\Scripts\activate

# Linux/macOS
python -m venv .venv
source .venv/bin/activate
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4. Configurar variables de entorno

Crear archivo `.env` en la raíz del proyecto:

```
DEBUG=True
SECRET_KEY=tu-clave-secreta
DATABASE_URL=sqlite:///db.sqlite3  # o postgresql://...
```

### 5. Ejecutar migraciones

```bash
python manage.py migrate
```

### 6. Crear superusuario

```bash
python manage.py createsuperuser
```

### 7. Ejecutar servidor de desarrollo

```bash
python manage.py runserver
```

La aplicación estará disponible en `http://127.0.0.1:8000/`

## Uso

### Para Empleados
1. Regístrate en la plataforma con email y contraseña
2. Cambia tu contraseña inicial (requerido)
3. Accede a tu panel de control horario
4. Registra entrada/salida con un clic
5. Visualiza tu jornada del día y histórico
6. Solicita correcciones si es necesario

### Para Managers
1. Accede al panel con credenciales de manager
2. Visualiza el personal de tu empresa
3. Revisa y aprueba/rechaza solicitudes de corrección
4. Consulta logs de cambios

### Para Administradores
1. Accede al panel administrativo
2. Gestiona empresas, usuarios y membresías
3. Visualiza estadísticas globales
4. Inspecciona personal de cualquier empresa
5. Revisa auditoría completa del sistema
6. Gestiona registros eliminados (restore/hard-delete)

## Características Técnicas

### Soft-Delete (Eliminación Lógica)
- Todos los modelos principales usan soft-delete
- Los registros se marcan con `deleted_at` en lugar de eliminarse
- Las querys filtran automáticamente registros eliminados
- Métodos disponibles: `all_with_deleted()`, `only_deleted()`, `restore()`, `hard_delete()`

### Autenticación Segura
- Backend personalizado que soporta soft-delete
- Validación de tokens por email
- Cambio obligatorio de contraseña para nuevos usuarios
- Middleware de verificación de inactividad

### Auditoría Completa
- Registro de cada cambio en TimeEntries
- Logs de acciones en el sistema
- Rastreo de quién cambió qué y cuándo

## Estado del Proyecto

**✅ Funcionalidades Completadas:**
- Autenticación y gestión de usuarios
- Control horario (entrada/salida)
- Solicitudes de corrección
- Panel administrativo
- Soft-delete con interfaz de restore
- Auditoría y logging
- Delegación segura de permisos
- Sistema de emails

**⏳ Pendiente:**
- Tests unitarios e integración para cada app (en progreso)
- Cobertura de tests >80%

## Testing

Para ejecutar los tests:

```bash
# Tests de una app específica
python manage.py test users
python manage.py test timetracking
python manage.py test requests
python manage.py test audit
python manage.py test admin
python manage.py test dashboard

# Todos los tests
python manage.py test

# Con cobertura
coverage run --source='.' manage.py test
coverage report
```

## Variables de Entorno

```env
DEBUG=True                          # Modo debug
SECRET_KEY=tu-clave-secreta        # Clave secreta de Django
DATABASE_URL=sqlite:///db.sqlite3  # URL de base de datos
ALLOWED_HOSTS=localhost,127.0.0.1  # Hosts permitidos
```

## Notas de Desarrollo

- Los modelos están centralizados en cada app (no en una carpeta de modelos)
- El backend de autenticación está en `core/auth.py` (soporte para soft-delete)
- Los managers centralizados están en `core/managers.py`
- Las migraciones son automáticas (managed=False no se usa)
- Los templates usan Bootstrap 5 a través de `django-bootstrap5`
- El sistema de soft-delete es transparente (queries filtran automáticamente)

## Troubleshooting

### Error de conexión a base de datos PostgreSQL
Asegurate de que PostgreSQL está corriendo y que la URL en `.env` es correcta.

### Usuario no puede registrarse
Verifica que el email es válido y que el servidor de correo está configurado correctamente.

### Soft-delete no funciona
Verifica que estás usando los managers correctos y que los modelos heredan del `SoftDeleteManager`.

## Licencia

Proyecto propietario - Aeptic

## Contacto

Para preguntas o reportar issues, contacta al equipo de desarrollo.
