# aeptic_reports/views.py

import calendar
from datetime import date, timedelta
import os
import uuid
from datetime import datetime
from pathlib import Path

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.utils import timezone
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse, JsonResponse
from django.views import View
from django.core.exceptions import PermissionDenied
from django.utils import timezone
from django.conf import settings
from django.shortcuts import render

from users.models import Users, UserCompany, Companies
from timetracking.models import TimeEntries
from requests.models import LeaveRequest
from admin.models import CompanySettings
from core.services import get_effective_context
from aeptic_reports.models import MonthlyReport
from aeptic_reports.services import ExcelReportGenerator, CSVReportGenerator
from users.models import UserCompany, Companies
from audit.models import AuditLog
from core.decorators import auditor_cannot_access

# ─── Constante: Tax ID de la empresa AEPTIC ────────────────────────────────────
AEPTIC_TAX_ID = 'B90143645'


def _is_aeptic_member(user):
    """Devuelve True si el usuario pertenece a la empresa AEPTIC (o es admin)."""
    if user.is_admin:
        return True
    return UserCompany.objects.filter(
        user=user,
        company__tax_id=AEPTIC_TAX_ID,
        deleted_at__isnull=True
    ).exists()


@login_required
def aeptic_summary(request):
    """
    Resumen mensual para empleados/managers de AEPTIC (y admins).
    Muestra horas trabajadas, vacaciones, ausencias, festivos y horas extra.
    """

    # ── 1. Control de acceso ────────────────────────────────────────────────────
    if request.user.is_auditor:
        return render(request, 'error/403.html', status=403)

    if not _is_aeptic_member(request.user):
        messages.error(request, 'No tienes acceso a esta sección.')
        return redirect('home_timetracking')

    # ── 2. Contexto de delegación (admin puede ver a otro usuario) ──────────────
    delegation_context = get_effective_context(request)

    if delegation_context['is_delegating']:
        target_user = Users.objects.filter(
            id=delegation_context['delegated_user_id']
        ).first()
        company = Companies.objects.filter(
            id=delegation_context['delegated_company_id']
        ).first()
    else:
        target_user = request.user
        # Tomamos la empresa AEPTIC directamente
        membership = UserCompany.objects.filter(
            user=target_user,
            company__tax_id=AEPTIC_TAX_ID,
            deleted_at__isnull=True
        ).select_related('company').first()

        if not membership and not request.user.is_admin:
            messages.error(request, 'No tienes empresa AEPTIC asignada.')
            return redirect('home_timetracking')

        company = membership.company if membership else None

    if not target_user:
        messages.error(request, 'Usuario no encontrado.')
        return redirect('home_timetracking')

    # ── 3. Selector de mes/año ──────────────────────────────────────────────────
    today = timezone.localdate()
    try:
        selected_year  = int(request.GET.get('year',  today.year))
        selected_month = int(request.GET.get('month', today.month))
        # Validación básica
        if not (1 <= selected_month <= 12):
            selected_month = today.month
        if not (2020 <= selected_year <= today.year + 1):
            selected_year = today.year
    except (ValueError, TypeError):
        selected_year  = today.year
        selected_month = today.month

    # Primer y último día del mes seleccionado
    first_day = date(selected_year, selected_month, 1)
    last_day  = date(selected_year, selected_month,
                     calendar.monthrange(selected_year, selected_month)[1])

    # ── 4. Configuración de empresa (jornada + festivos) ───────────────────────
    settings_obj = None
    if company:
        settings_obj = CompanySettings.objects.filter(company=company).first()

    # Jornada diaria en segundos (por defecto 7h si no hay configuración)
    if settings_obj and settings_obj.work_start and settings_obj.work_end:
        ws = settings_obj.work_start
        we = settings_obj.work_end
        jornada_seconds = (
            (we.hour * 3600 + we.minute * 60 + we.second) -
            (ws.hour * 3600 + ws.minute * 60 + ws.second)
        )
        jornada_seconds = max(jornada_seconds, 0)
    else:
        jornada_seconds = 7 * 3600  # 7 horas por defecto

    # Tolerancia en segundos
    if settings_obj and settings_obj.max_tolerance:
        tolerance_seconds = int(settings_obj.max_tolerance.total_seconds())
    else:
        tolerance_seconds = 15 * 60  # 15 min por defecto

    # Festivos del mes
    holidays_in_month = []
    if settings_obj and settings_obj.holidays:
        holidays_in_month = [
            h for h in settings_obj.holidays
            if first_day <= h <= last_day
        ]

    # Días de fin de semana configurados (0=Lunes…6=Domingo en Python weekday)
    weekend_days = list(settings_obj.weekend_days) if settings_obj and settings_obj.weekend_days else [5, 6]

    # ── 5. Días laborables del mes ─────────────────────────────────────────────
    all_days = [first_day + timedelta(days=i)
                for i in range((last_day - first_day).days + 1)]
    working_days = [
        d for d in all_days
        if d.weekday() not in weekend_days and d not in holidays_in_month
    ]
    num_working_days = len(working_days)

    # ── 6. Fichajes del mes ────────────────────────────────────────────────────
    entries_qs = TimeEntries.objects.filter(
        user=target_user,
        date__gte=first_day,
        date__lte=last_day,
        deleted_at__isnull=True,
    ).exclude(status='voided')

    if company:
        entries_qs = entries_qs.filter(company=company)

    total_worked_seconds = sum(e.total_seconds or 0 for e in entries_qs)
    days_with_entry = entries_qs.values('date').distinct().count()

    # Horas extra: segundos trabajados por encima de la jornada + tolerancia
    extra_seconds = 0
    for entry in entries_qs:
        worked = entry.total_seconds or 0
        if worked > jornada_seconds + tolerance_seconds:
            extra_seconds += worked - jornada_seconds

    # ── 7. Vacaciones y ausencias ──────────────────────────────────────────────
    leaves_qs = LeaveRequest.objects.filter(
        user=target_user,
        status=LeaveRequest.LeaveStatus.APPROVED,
        start_date__lte=last_day,
        end_date__gte=first_day,
    )
    if company:
        leaves_qs = leaves_qs.filter(company=company)

    # Contar días de cada tipo recortando al mes seleccionado
    vacation_days  = 0
    absence_days   = 0
    for leave in leaves_qs:
        start = max(leave.start_date, first_day)
        end   = min(leave.end_date,   last_day)
        days  = (end - start).days + 1
        if leave.leave_type == LeaveRequest.LeaveType.VACATION:
            vacation_days += days
        else:
            absence_days += days

    # ── 8. Rol en AEPTIC ───────────────────────────────────────────────────────
    user_role = 'Admin' if target_user.is_admin else 'Empleado'
    if company:
        uc = UserCompany.objects.filter(
            user=target_user, company=company, deleted_at__isnull=True
        ).first()
        if uc:
            user_role = uc.get_role_display().capitalize()

    # ── 9. Helpers de formato ──────────────────────────────────────────────────
    def fmt_time(seconds):
        h = seconds // 3600
        m = (seconds % 3600) // 60
        return f"{h}h {m:02d}m"

    # ── 10. Lista de meses y años para el selector ─────────────────────────────
    month_names = [
        'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
        'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'
    ]
    available_years = list(range(2024, today.year + 1))

    # ── 11. Contexto final ─────────────────────────────────────────────────────
    context = {
        # Empleado
        'target_user':     target_user,
        'user_role':       user_role,
        'company':         company,
        # Periodo
        'selected_year':   selected_year,
        'selected_month':  selected_month,
        'month_name':      month_names[selected_month - 1],
        'month_names':     list(enumerate(month_names, start=1)),
        'available_years': available_years,
        # Métricas
        'total_worked':       fmt_time(total_worked_seconds),
        'total_worked_raw':   total_worked_seconds,
        'extra_time':         fmt_time(extra_seconds),
        'extra_time_raw':     extra_seconds,
        'vacation_days':      vacation_days,
        'absence_days':       absence_days,
        'holidays_count':     len(holidays_in_month),
        'holidays_list':      holidays_in_month,
        'days_with_entry':    days_with_entry,
        'num_working_days':   num_working_days,
        'jornada_daily':      fmt_time(jornada_seconds),
        # Objetivo del mes (solo días laborables sin vacaciones ni ausencias)
        'target_seconds': max(0, (num_working_days - vacation_days - absence_days) * jornada_seconds),
        'target_time':    fmt_time(max(0, (num_working_days - vacation_days - absence_days) * jornada_seconds)),
        # Delegación
        **delegation_context,
    }

    return render(request, 'aeptic_reports/aeptic_summary.html', context)

# --- Funciones de validación auxiliares ---

def _validate_user_company_access(user, company_id):
    """Verificar que user pertenece a company y retornar membership"""
    membership = UserCompany.objects.filter(
        user=user,
        company_id=company_id,
        deleted_at__isnull=True
    ).first()

    if not membership:
        raise PermissionDenied("Usuario no pertenece a esta empresa")

    return membership


def _validate_month_format(month_str):
    """Validar formato YYYY-MM-DD y que sea primer día del mes"""
    try:
        date_obj = datetime.strptime(month_str, '%Y-%m-%d').date()
        if date_obj.day != 1:
            raise ValueError("Debe ser el primer día del mes")
        return date_obj
    except (ValueError, TypeError):
        raise ValueError("Formato de mes inválido. Use YYYY-MM-DD")


def _get_company_from_session(request):
    """Obtener company_id de la sesión del request"""
    company_id = request.session.get('company_id')
    if not company_id:
        raise PermissionDenied("No hay empresa seleccionada en la sesión")
    return company_id


def _create_audit_log(user, table_name, record_id, action_type, reason, before=None, after=None):
    """Helper para crear entrada en audit_log"""
    try:
        audit = AuditLog.objects.create(
            id=uuid.uuid4(),
            table_name=table_name,
            record_id=record_id,
            user=user,
            action_type=action_type,
            reason=reason,
            before=before,
            after=after,
            source='web'
        )
        return audit
    except Exception as e:
        # Log pero no fallar la vista si auditoría falla
        print(f"Error creando audit log: {e}")
        return None


# --- Vista: Obtener datos del mes en JSON (para preview) ---

class MonthlyReportDataView(LoginRequiredMixin, View):
    """
    GET /monthly-reports/data/
    Params: ?month=2026-05-01
    Retorna datos del mes en JSON para mostrar en preview de la tabla
    """

    def get(self, request):
        try:
            if request.user.is_auditor:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Auditors cannot access this'
                }, status=403)

            # 1. Leer parámetros
            month_str = request.GET.get('month')

            if not month_str:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Parámetro "month" requerido'
                }, status=400)

            # 2. Validar formato de mes
            try:
                report_date = _validate_month_format(month_str)
            except ValueError as e:
                return JsonResponse({
                    'status': 'error',
                    'message': str(e)
                }, status=400)

            # 3. Obtener company_id de sesión
            company_id = _get_company_from_session(request)

            # 4. Validar que user pertenece a company
            try:
                _validate_user_company_access(request.user, company_id)
            except PermissionDenied as e:
                return JsonResponse({
                    'status': 'error',
                    'message': str(e)
                }, status=403)

            # 5. Obtener company
            company = Companies.objects.filter(id=company_id).first()
            if not company:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Empresa no encontrada'
                }, status=404)

            # 6. Generar datos del mes usando ExcelReportGenerator
            generator = ExcelReportGenerator(
                request.user,
                company,
                report_date
            )
            report_data = generator.get_report_data()

            # 7. Retornar JSON
            return JsonResponse({
                'status': 'success',
                'month': report_date.strftime('%Y-%m'),
                'month_name': report_date.strftime('%B %Y'),
                'data': report_data
            }, status=200)

        except PermissionDenied as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=403)

        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': f'Error al obtener datos: {str(e)}'
            }, status=500)


# --- Vista: Descargar reporte (GET) ---

class MonthlyReportDownloadView(LoginRequiredMixin, View):
    """
    GET /monthly-reports/download/
    Params: ?month=2026-05-01&format=xlsx|csv
    """

    def get(self, request):
        try:
            if request.user.is_auditor:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Auditors cannot access this'
                }, status=403)

            # 1. Leer parámetros
            month_str = request.GET.get('month')
            format_type = request.GET.get('format', 'xlsx').lower()

            if not month_str:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Parámetro "month" requerido'
                }, status=400)

            if format_type not in ['xlsx', 'csv']:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Formato debe ser "xlsx" o "csv"'
                }, status=400)

            # 2. Validar formato de mes
            try:
                report_date = _validate_month_format(month_str)
            except ValueError as e:
                return JsonResponse({
                    'status': 'error',
                    'message': str(e)
                }, status=400)

            # 3. Obtener company_id de sesión
            company_id = _get_company_from_session(request)

            # 4. Validar que user pertenece a company
            try:
                _validate_user_company_access(request.user, company_id)
            except PermissionDenied as e:
                return JsonResponse({
                    'status': 'error',
                    'message': str(e)
                }, status=403)

            # 5. Obtener company
            company = Companies.objects.filter(id=company_id).first()
            if not company:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Empresa no encontrada'
                }, status=404)

            # 6. Obtener o crear MonthlyReport con status=draft
            monthly_report, created = MonthlyReport.objects.get_or_create(
                user=request.user,
                company=company,
                report_date=report_date,
                defaults={'status': MonthlyReport.ReportStatus.DRAFT}
            )

            # 7. Generar archivo
            if format_type == 'xlsx':
                generator = ExcelReportGenerator(
                    request.user,
                    company,
                    report_date
                )
                file_content = generator.generate()
                content_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                file_ext = 'xlsx'
            else:  # csv
                generator = CSVReportGenerator(
                    request.user,
                    company,
                    report_date
                )
                file_content = generator.generate()
                # Convertir string CSV a BytesIO
                from io import BytesIO
                file_bytes = BytesIO(file_content.encode('utf-8-sig'))
                file_content = file_bytes
                content_type = 'text/csv'
                file_ext = 'csv'

            # 8. Actualizar MonthlyReport con status=generated
            monthly_report.status = MonthlyReport.ReportStatus.GENERATED
            monthly_report.generated_at = timezone.now()
            monthly_report.save(update_fields=['status', 'generated_at'])

            # 9. Auditar
            _create_audit_log(
                user=request.user,
                table_name='monthly_reports',
                record_id=monthly_report.id,
                action_type=AuditLog.AuditAction.CREATE,
                reason=f'Descarga reporte {report_date.strftime("%B %Y")} en formato {format_type.upper()}',
                after={
                    'report_id': str(monthly_report.id),
                    'user': request.user.email,
                    'company': company.name,
                    'month': report_date.strftime('%Y-%m'),
                    'status': monthly_report.status,
                    'format': format_type,
                }
            )

            # 10. Preparar respuesta de descarga
            response = HttpResponse(
                file_content,
                content_type=content_type
            )

            filename = f"report_{request.user.email}_{report_date.strftime('%Y-%m-%d')}.{file_ext}"
            response['Content-Disposition'] = f'attachment; filename="{filename}"'

            return response

        except PermissionDenied as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=403)

        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': f'Error al generar reporte: {str(e)}'
            }, status=500)


# --- Vista: Subir documento firmado (POST) ---

class MonthlyReportUploadView(LoginRequiredMixin, View):
    """
    POST /monthly-reports/upload/
    Body: multipart/form-data con file y month
    """

    def post(self, request):
        try:
            if request.user.is_auditor:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Auditors cannot access this'
                }, status=403)

            # 1. Validar que file está presente
            if 'file' not in request.FILES:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Archivo no proporcionado'
                }, status=400)

            uploaded_file = request.FILES['file']

            # 2. Validar extensión
            allowed_extensions = ['xlsx', 'csv']
            file_ext = uploaded_file.name.split('.')[-1].lower()

            if file_ext not in allowed_extensions:
                return JsonResponse({
                    'status': 'error',
                    'message': f'Extensión no permitida. Use {", ".join(allowed_extensions)}'
                }, status=400)

            # 3. Validar tamaño (máx 10MB)
            max_size = 10 * 1024 * 1024  # 10MB
            if uploaded_file.size > max_size:
                return JsonResponse({
                    'status': 'error',
                    'message': f'Archivo demasiado grande. Máximo: 10MB'
                }, status=400)

            # 4. Validar mes
            month_str = request.POST.get('month')
            if not month_str:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Parámetro "month" requerido'
                }, status=400)

            try:
                report_date = _validate_month_format(month_str)
            except ValueError as e:
                return JsonResponse({
                    'status': 'error',
                    'message': str(e)
                }, status=400)

            # 5. Obtener company_id de sesión
            company_id = _get_company_from_session(request)

            # 6. Validar pertenencia a company
            try:
                _validate_user_company_access(request.user, company_id)
            except PermissionDenied as e:
                return JsonResponse({
                    'status': 'error',
                    'message': str(e)
                }, status=403)

            # 7. Obtener company
            company = Companies.objects.filter(id=company_id).first()
            if not company:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Empresa no encontrada'
                }, status=404)

            # 8. Crear carpeta si no existe
            media_root = Path(settings.MEDIA_ROOT)
            report_dir = media_root / 'monthly_reports' / str(request.user.id) / str(company.id)
            report_dir.mkdir(parents=True, exist_ok=True)

            # 9. Guardar archivo
            filename = f"{request.user.email}_{report_date.strftime('%Y-%m-%d')}.{file_ext}"
            file_path = report_dir / filename

            with open(file_path, 'wb') as f:
                for chunk in uploaded_file.chunks():
                    f.write(chunk)

            # Ruta relativa para BD
            relative_path = os.path.join(
                'monthly_reports',
                str(request.user.id),
                str(company.id),
                filename
            )

            # 10. Obtener o crear MonthlyReport
            monthly_report, created = MonthlyReport.objects.get_or_create(
                user=request.user,
                company=company,
                report_date=report_date,
                defaults={'status': MonthlyReport.ReportStatus.DRAFT}
            )

            # 11. Actualizar MonthlyReport
            old_status = monthly_report.status
            old_path = monthly_report.document_path

            monthly_report.status = MonthlyReport.ReportStatus.SIGNED
            monthly_report.signed_at = timezone.now()
            monthly_report.document_path = relative_path
            monthly_report.save()

            # 12. Auditar
            _create_audit_log(
                user=request.user,
                table_name='monthly_reports',
                record_id=monthly_report.id,
                action_type=AuditLog.AuditAction.UPDATE,
                reason=f'Carga de documento firmado para {report_date.strftime("%B %Y")}',
                before={
                    'status': old_status,
                    'document_path': old_path,
                    'signed_at': None,
                },
                after={
                    'report_id': str(monthly_report.id),
                    'user': request.user.email,
                    'company': company.name,
                    'month': report_date.strftime('%Y-%m'),
                    'status': monthly_report.status,
                    'document_path': relative_path,
                    'signed_at': monthly_report.signed_at.isoformat(),
                }
            )

            # 13. Retornar respuesta exitosa
            return JsonResponse({
                'status': 'success',
                'message': 'Documento subido correctamente',
                'report_id': str(monthly_report.id),
                'signed_at': monthly_report.signed_at.isoformat(),
            }, status=200)

        except PermissionDenied as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=403)

        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': f'Error al subir documento: {str(e)}'
            }, status=500)


# --- Vista: Listar reportes del usuario (GET) ---

class MonthlyReportListView(LoginRequiredMixin, View):
    """
    GET /monthly-reports/list/
    Retorna lista de MonthlyReports del user actual
    """

    def get(self, request):
        try:
            if request.user.is_auditor:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Auditors cannot access this'
                }, status=403)

            # 1. Obtener company_id de sesión (opcional, si no hay listar todas)
            company_id = request.session.get('company_id')

            # 2. Obtener reportes
            if company_id:
                # Validar pertenencia a company
                try:
                    _validate_user_company_access(request.user, company_id)
                except PermissionDenied:
                    return JsonResponse({
                        'status': 'error',
                        'message': 'No tiene acceso a esta empresa'
                    }, status=403)

                reports = MonthlyReport.objects.filter(
                    user=request.user,
                    company_id=company_id
                ).order_by('-report_date')
            else:
                # Listar todos los reportes del usuario (de empresas a las que pertenece)
                user_companies = UserCompany.objects.filter(
                    user=request.user,
                    deleted_at__isnull=True
                ).values_list('company_id', flat=True)

                reports = MonthlyReport.objects.filter(
                    user=request.user,
                    company_id__in=user_companies
                ).order_by('-report_date')

            # 3. Formatear respuesta
            month_names = [
                'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
                'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'
            ]

            reports_data = []
            for report in reports:
                reports_data.append({
                    'id': str(report.id),
                    'report_date': report.report_date.isoformat(),
                    'month': report.month,
                    'year': report.year,
                    'month_name': month_names[report.month - 1],
                    'status': report.status,
                    'is_signed': report.is_signed,
                    'signed_at': report.signed_at.isoformat() if report.signed_at else None,
                    'generated_at': report.generated_at.isoformat() if report.generated_at else None,
                    'document_path': report.document_path,
                    'company_id': str(report.company.id),
                    'company_name': report.company.name,
                })

            return JsonResponse({
                'status': 'success',
                'reports': reports_data,
                'count': len(reports_data)
            }, status=200)

        except PermissionDenied as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=403)

        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': f'Error al listar reportes: {str(e)}'
            }, status=500)


# --- Helper: Verificar acceso a AePTIC ---

def _check_aeptic_access(user):
    """Verificar que el usuario pertenece a empresa AePTIC (CIF B90143645)"""
    aeptic_company = Companies.objects.filter(
        tax_id='B90143645'
    ).first()

    if not aeptic_company:
        raise PermissionDenied("Empresa AePTIC no encontrada")

    membership = UserCompany.objects.filter(
        user=user,
        company=aeptic_company,
        deleted_at__isnull=True
    ).first()

    if not membership:
        raise PermissionDenied("No tienes acceso a esta sección")

    return aeptic_company


# --- Vista: Resumen de Reportes AePTIC ---

class AepticSummaryView(LoginRequiredMixin, View):
    """
    GET /aeptic_reports/summary/
    Mostrar resumen de reportes mensuales para AePTIC
    """

    def get(self, request):
        try:
            if request.user.is_auditor:
                return render(request, 'error/403.html', status=403)

            company = _check_aeptic_access(request.user)

            # Obtener reportes del usuario en AePTIC
            reports = MonthlyReport.objects.filter(
                user=request.user,
                company=company
            ).order_by('-report_date')

            # Calcular meses actual y anterior
            today = timezone.now()
            current_month = today.replace(day=1)
            previous_month = (current_month - timezone.timedelta(days=1)).replace(day=1)

            month_names = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
                          'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']

            context = {
                'company': company,
                'reports': reports,
                'total_reports': reports.count(),
                'signed_reports': reports.filter(status=MonthlyReport.ReportStatus.SIGNED).count(),
                'prev_month_date': previous_month.strftime('%Y-%m-%d'),
                'prev_month_name': f"{month_names[previous_month.month - 1]} {previous_month.year}",
                'current_month_date': current_month.strftime('%Y-%m-%d'),
                'current_month_name': f"{month_names[current_month.month - 1]} {current_month.year}",
            }

            return render(request, 'aeptic_reports/aeptic_summary.html', context)

        except PermissionDenied:
            return render(request, 'error.html', {
                'error': 'No tienes acceso a esta sección'
            }, status=403)


# --- Vista: Histórico de Reportes AePTIC ---

class AepticHistoryView(LoginRequiredMixin, View):
    """
    GET /aeptic_reports/history/
    Mostrar histórico de reportes mensuales para AePTIC
    """

    def get(self, request):
        try:
            if request.user.is_auditor:
                return render(request, 'error/403.html', status=403)

            company = _check_aeptic_access(request.user)

            # Obtener todos los reportes (incluyendo archivados)
            reports = MonthlyReport.objects.filter(
                user=request.user,
                company=company
            ).order_by('-report_date')

            context = {
                'company': company,
                'reports': reports,
                'total_reports': reports.count(),
                'archived_reports': reports.filter(status=MonthlyReport.ReportStatus.ARCHIVED).count(),
            }

            return render(request, 'aeptic_reports/aeptic_history.html', context)

        except PermissionDenied:
            return render(request, 'error.html', {
                'error': 'No tienes acceso a esta sección'
            }, status=403)

