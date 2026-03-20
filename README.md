# control_horario
Aplicación de control horario para empresas

## Descripción del proyecto
Control Horario es una aplicación web desarrollada en Django para gestionar el registro de entradas/salidas de empleados, el control de jornadas, y la gestión de solicitudes de corrección.

### Funcionalidades principales
- Autenticación de usuarios (login/registro)
- Administración de empresas y miembros
- Registro de entradas y salidas (time tracking)
- Estados de entrada: en curso, confirmado, auto-cerrado, corregido, anulado
- Solicitudes de corrección con aprobación/rechazo
- Panel de administración para usuarios con permisos

## Estructura del proyecto
- `core/`: configuración principal (settings, urls, wsgi/asgi)
- `users/`: modelos de usuario, formularios, vistas de autenticación
- `timetracking/`: modelos y lógica de control horario
- `dashboard/`: vistas de la página principal y panel
- `audit/`: logger/auditoría del sistema
- `templates/`: plantillas HTML con Bootstrap
- `static/`: archivos CSS, JS y recursos estáticos

## Requisitos
- Python 3.11+
- Django 4.x
- SQLite (por defecto)
- Dependencias en `requirements.txt`

## Instalación
```bash
python -m venv .venv
# Windows
.\.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## Uso
1. Abre `http://127.0.0.1:8000/`
2. Regístrate o inicia sesión con un administrador
3. Usa el panel para crear empresas, usuarios y registrar entradas de tiempo
4. Para revisar solicitudes de corrección, ve la sección correspondiente en el panel

## Notas de desarrollo
- Los modelos principales están en `users/models.py` y `timetracking/models.py`.
- Las vistas de autenticación están en `users/views.py`.
- URL principal y rutas se configuran en `core/urls.py`.
- El estilo base usa Bootstrap 5 y plantillas en `templates/login`.

## Contribuciones
1. Haz un fork del repositorio
2. Crea una rama feature: `git checkout -b feature/nombre`
3. Realiza cambios y pruebas
4. Abre un pull request

## Estado
Proyecto en desarrollo con funcionalidades base de control horario y registro de correcciones.
