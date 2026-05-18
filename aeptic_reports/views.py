# aeptic_reports/views.py

import calendar
import os
from pyexpat.errors import messages
import uuid
from datetime import date, datetime
from pathlib import Path

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse, JsonResponse
from django.views import View
from django.core.exceptions import PermissionDenied
from django.utils import timezone
from django.conf import settings
from django.shortcuts import redirect, render

# Create your views here.
from admin.models import CompanySettings
from aeptic_reports.models import MonthlyReport
from aeptic_reports.services import ExcelReportGenerator, PDFReportGenerator
from core.services import get_effective_context
from requests.models import LeaveRequest
from timetracking.models import TimeEntries
from users.models import UserCompany, Companies, Users
from audit.models import AuditLog
from core.decorators import auditor_cannot_access


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

            if format_type not in ['xlsx', 'pdf']:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Formato debe ser "xlsx" o "pdf"'
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
            elif format_type == 'pdf':
                generator = PDFReportGenerator(request.user, company, report_date)
                file_content = generator.generate()
                content_type = 'application/pdf'
                file_ext = 'pdf'

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
            allowed_extensions = ['pdf']
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


def _check_aeptic_selected(request, aeptic_company):
    """Verificar que AePTIC está seleccionada en el navbar"""
    selected_company_id = request.session.get('company_id')

    if not selected_company_id:
        raise PermissionDenied("No hay empresa seleccionada en la sesión")

    if str(aeptic_company.id) != str(selected_company_id):
        raise PermissionDenied("Debes tener AePTIC seleccionada en el navbar")

    return True


# --- Vista: Resumen de Reportes AePTIC ---

class AepticSummaryView(LoginRequiredMixin, View):
    """
    GET /aeptic_reports/summary/
    Mostrar resumen de reportes mensuales para AePTIC incluyendo control de incurrido.
    """

    def get(self, request):
        try:
            # ── 1. Control de acceso inicial ──
            if request.user.is_auditor:
                return render(request, 'error/403.html', status=403)

            # Usamos tu función actual para asegurar el acceso y obtener la empresa
            company = _check_aeptic_access(request.user)
            _check_aeptic_selected(request, company)

            # ── 2. Contexto de Delegación (Admin / User) ──
            # Reutilizamos la lógica del FBV antiguo para determinar a quién miramos
            delegation_context = get_effective_context(request)
            
            if delegation_context.get('is_delegating'):
                target_user = Users.objects.filter(id=delegation_context['delegated_user_id']).first()
                # Si está delegando, puede que esté viendo otra empresa. Si no, usamos la devuelta arriba.
                company = Companies.objects.filter(id=delegation_context['delegated_company_id']).first() or company
            else:
                target_user = request.user

            if not target_user:
                messages.error(request, 'Usuario no encontrado.')
                return redirect('home_timetracking')

            # ── 3. Fechas del Mes Actual ──
            # Como el selector en HTML está comentado, forzamos el mes actual
            today = timezone.localdate()
            first_day = date(today.year, today.month, 1)
            last_day = date(today.year, today.month, calendar.monthrange(today.year, today.month)[1])

            month_names = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
                           'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']

            # ── 4. Configuración de Empresa (Jornada y Festivos) ──
            settings_obj = CompanySettings.objects.filter(company=company).first() if company else None

            # Jornada diaria en segundos (7h por defecto)
            if settings_obj and settings_obj.work_start and settings_obj.work_end:
                ws, we = settings_obj.work_start, settings_obj.work_end
                jornada_seconds = max(((we.hour * 3600 + we.minute * 60 + we.second) -
                                       (ws.hour * 3600 + ws.minute * 60 + ws.second)), 0)
            else:
                jornada_seconds = 7 * 3600  

            # Tolerancia (15 min por defecto)
            tolerance_seconds = int(settings_obj.max_tolerance.total_seconds()) if (settings_obj and settings_obj.max_tolerance) else 15 * 60

            # Festivos y fines de semana
            holidays_in_month = [h for h in settings_obj.holidays if first_day <= h <= last_day] if (settings_obj and settings_obj.holidays) else []
            weekend_days = list(settings_obj.weekend_days) if (settings_obj and settings_obj.weekend_days) else [5, 6]

            # Días laborables del mes
            all_days = [first_day + timezone.timedelta(days=i) for i in range((last_day - first_day).days + 1)]
            working_days = [d for d in all_days if d.weekday() not in weekend_days and d not in holidays_in_month]
            num_working_days = len(working_days)

            # ── 5. Fichajes y Horas Extra ──
            entries_qs = TimeEntries.objects.filter(
                user=target_user,
                company=company,
                date__gte=first_day,
                date__lte=last_day,
                deleted_at__isnull=True,
            ).exclude(status='voided')

            total_worked_seconds = sum(e.total_seconds or 0 for e in entries_qs)
            days_with_entry = entries_qs.values('date').distinct().count()

            extra_seconds = sum(
                (e.total_seconds - jornada_seconds) 
                for e in entries_qs 
                if (e.total_seconds or 0) > (jornada_seconds + tolerance_seconds)
            )

            # ── 6. Vacaciones y Ausencias ──
            leaves_qs = LeaveRequest.objects.filter(
                user=target_user,
                company=company,
                status=LeaveRequest.LeaveStatus.APPROVED,
                start_date__lte=last_day,
                end_date__gte=first_day,
            )

            vacation_days = absence_days = 0
            for leave in leaves_qs:
                start = max(leave.start_date, first_day)
                end = min(leave.end_date, last_day)
                days = (end - start).days + 1
                if leave.leave_type == LeaveRequest.LeaveType.VACATION:
                    vacation_days += days
                else:
                    absence_days += days

            # ── 7. Rol del Usuario ──
            user_role = 'Admin' if target_user.is_admin else 'Empleado'
            if company:
                uc = UserCompany.objects.filter(user=target_user, company=company, deleted_at__isnull=True).first()
                if uc:
                    user_role = uc.get_role_display().capitalize()

            # ── 8. Formateo y Contexto ──
            def fmt_time(seconds):
                h = int(seconds // 3600)
                m = int((seconds % 3600) // 60)
                return f"{h}h {m:02d}m"

            target_seconds = max(0, (num_working_days - vacation_days - absence_days) * jornada_seconds)

            context = {
                # Cabecera
                'target_user': target_user,
                'company': company,
                'user_role': user_role,
                'month_name': month_names[today.month - 1],
                
                # Datos subida PDFs (requeridos por tu nuevo diseño)
                'current_month_date': first_day.strftime('%Y-%m-%d'),
                'current_month_name': f"{month_names[today.month - 1]} {today.year}",
                
                # Columna Tiempo
                'total_worked': fmt_time(total_worked_seconds),
                'target_time': fmt_time(target_seconds),
                'extra_time': fmt_time(extra_seconds),
                'extra_time_raw': extra_seconds,
                
                # Columna Asistencia
                'days_with_entry': days_with_entry,
                'num_working_days': num_working_days,
                'vacation_days': vacation_days,
                'absence_days': absence_days,
                'holidays_count': len(holidays_in_month),
                
                # Contexto de delegación por si otras partes de la UI lo necesitan
                **delegation_context,
            }

            return render(request, 'aeptic_reports/aeptic_summary.html', context)

        except PermissionDenied:
            return render(request, 'error/403.html', status=403)


# --- Vista: Histórico de Reportes AePTIC ---

class AepticHistoryView(LoginRequiredMixin, View):
    """
    GET /aeptic_reports/history/
    Mostrar histórico de reportes mensuales para AePTIC con filtros.
    """

    def get(self, request):
        try:
            if request.user.is_auditor:
                return render(request, 'error/403.html', status=403)

            company = _check_aeptic_access(request.user)
            _check_aeptic_selected(request, company)

            # ── Filtros ────────────────────────────────────────────────
            filter_year   = request.GET.get('year',   '').strip()
            filter_month  = request.GET.get('month',  '').strip()
            filter_status = request.GET.get('status', '').strip()

            # Totales sin filtrar (para los badges de cabecera)
            all_reports = MonthlyReport.objects.filter(
                user=request.user,
                company=company
            )
            total_reports    = all_reports.count()
            archived_reports = all_reports.filter(
                status=MonthlyReport.ReportStatus.ARCHIVED
            ).count()

            # QuerySet filtrado para la tabla
            reports = all_reports.order_by('-report_date')

            if filter_year:
                reports = reports.filter(report_date__year=filter_year)
            if filter_month:
                reports = reports.filter(report_date__month=filter_month)
            if filter_status:
                reports = reports.filter(status=filter_status)

            # ── Datos para los selectores ──────────────────────────────
            today = timezone.localdate()
            available_years = list(range(2024, today.year + 1))
            month_names = [
                (1, 'Enero'),    (2, 'Febrero'),   (3, 'Marzo'),
                (4, 'Abril'),    (5, 'Mayo'),       (6, 'Junio'),
                (7, 'Julio'),    (8, 'Agosto'),     (9, 'Septiembre'),
                (10, 'Octubre'), (11, 'Noviembre'), (12, 'Diciembre'),
            ]

            context = {
                'company':         company,
                'reports':         reports,
                'total_reports':   total_reports,
                'archived_reports': archived_reports,
                'available_years': available_years,
                'month_names':     month_names,
            }

            return render(request, 'aeptic_reports/aeptic_history.html', context)

        except PermissionDenied:
            return render(request, 'error/403.html', status=403)
