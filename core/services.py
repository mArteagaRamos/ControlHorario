# ---------- Centralized Services: core/services.py ----------
import uuid
import datetime
from uuid import uuid4
from django.utils import timezone
from django.forms.models import model_to_dict
from django.utils.dateparse import parse_datetime, parse_date
from django.db import transaction

from users.models import Companies, UserCompany, Users
from audit.models import AuditLog
from timetracking.models import TimeEntries, TimeEntryEvent


# ───────────────────────────────────────────────────────────────────────────────
# TIME & DATETIME UTILITIES
# ───────────────────────────────────────────────────────────────────────────────

def combine_local_date_time(date_value, time_value):
    """Combine date and time strings into a timezone-aware datetime."""
    naive_dt = datetime.datetime.strptime(f"{date_value} {time_value}", '%Y-%m-%d %H:%M')
    return timezone.make_aware(naive_dt, timezone.get_current_timezone())


def parse_local_datetime(value):
    """Parse a datetime string and ensure it's timezone-aware."""
    if not value:
        return None
    parsed = parse_datetime(value)
    if parsed is None:
        return None
    if timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed, timezone.get_current_timezone())
    return parsed


def get_display_date(value):
    """Get the date portion of a datetime, respecting timezone."""
    if not value:
        return None
    if timezone.is_naive(value):
        return value.date()
    return timezone.localtime(value).date()


def format_date_spanish(date_obj):
    """Format date as 'D MONTH, YYYY' in Spanish (e.g., '1 ENERO, 2026')."""
    if not date_obj:
        return None
    months = {
        1: 'ENERO', 2: 'FEBRERO', 3: 'MARZO', 4: 'ABRIL',
        5: 'MAYO', 6: 'JUNIO', 7: 'JULIO', 8: 'AGOSTO',
        9: 'SEPTIEMBRE', 10: 'OCTUBRE', 11: 'NOVIEMBRE', 12: 'DICIEMBRE'
    }
    return f"{date_obj.day} {months[date_obj.month]}, {date_obj.year}"


# ───────────────────────────────────────────────────────────────────────────────
# TIME TRACKING UTILITIES
# ───────────────────────────────────────────────────────────────────────────────

def safe_dict(instance):
    """Convert model instance to dict, handling special types (datetime, UUID)."""
    if not instance:
        return None
    d = model_to_dict(instance)
    for k, v in d.items():
        if isinstance(v, (datetime.datetime, datetime.date)):
            d[k] = v.isoformat()
        elif isinstance(v, uuid.UUID):
            d[k] = str(v)
    return d


def compute_worked_seconds(entry):
    """Calculate total worked seconds for a time entry, accounting for pauses."""
    if not entry.clock_in or not entry.clock_out:
        return 0

    clock_in = entry.clock_in
    clock_out = entry.clock_out
    if timezone.is_naive(clock_in):
        clock_in = timezone.make_aware(clock_in, timezone.get_current_timezone())
    if timezone.is_naive(clock_out):
        clock_out = timezone.make_aware(clock_out, timezone.get_current_timezone())

    if clock_out <= clock_in:
        return 0

    elapsed = clock_out - clock_in
    total = int(elapsed.total_seconds())

    # Calculate pauses in seconds
    pause_seconds = 0
    pause_start = None
    for ev in TimeEntryEvent.objects.filter(time_entry=entry).order_by('timestamp'):
        if ev.event_type == TimeEntryEvent.EventType.PAUSE_START:
            pause_start = ev.timestamp
        elif ev.event_type == TimeEntryEvent.EventType.PAUSE_END and pause_start is not None:
            pause_end = ev.timestamp
            if timezone.is_naive(pause_start):
                pause_start = timezone.make_aware(pause_start, timezone.get_current_timezone())
            if timezone.is_naive(pause_end):
                pause_end = timezone.make_aware(pause_end, timezone.get_current_timezone())
            if pause_end > pause_start:
                pause_seconds += int((pause_end - pause_start).total_seconds())
            pause_start = None

    return max(0, total - pause_seconds)


def auto_close_entry_if_expired(entry, company):
    """Auto-close a time entry if it exceeds company's max duration setting."""
    from admin.models import CompanySettings

    settings = CompanySettings.objects.filter(company=company).first()
    max_hours = settings.auto_close_hours if settings and settings.auto_close_hours else 12
    max_duration = datetime.timedelta(hours=max_hours)
    now = timezone.now()

    clock_in = entry.clock_in
    if timezone.is_naive(clock_in):
        clock_in = timezone.make_aware(clock_in, timezone.get_current_timezone())

    if entry and entry.clock_out is None and now - clock_in >= max_duration:
        # Snapshot before change (audit)
        estado_anterior = safe_dict(entry)

        auto_close_time = entry.clock_in + max_duration
        entry.clock_out = auto_close_time
        entry.status = TimeEntries.EntryStatus.AUTO_CLOSED

        # Calculate duration and save
        elapsed = entry.clock_out - entry.clock_in
        pause_seconds = compute_worked_seconds(entry)
        work_seconds = max(0, int(elapsed.total_seconds()) - pause_seconds)
        entry.total_seconds = work_seconds

        entry.save(update_fields=['clock_out', 'status', 'total_seconds'])

        TimeEntryEvent.objects.create(
            id=uuid4(),
            time_entry=entry,
            event_type=TimeEntryEvent.EventType.AUTO_CLOSE,
            timestamp=auto_close_time,
            actor=None,
            note=f'Auto-closed after exceeding {max_hours} hours.',
        )

        # Audit log (auto-close)
        AuditLog.objects.create(
            id=uuid4(),
            table_name='timetracking_registro',
            record_id=entry.id,
            user=entry.user,
            action_type=AuditLog.AuditAction.UPDATE,
            before=estado_anterior,
            after=safe_dict(entry),
            reason=f'Auto-closed by system ({max_hours}h limit)',
            timestamp=timezone.now(),
            source='system' # Añadido
        )

        return True

    return False


# ───────────────────────────────────────────────────────────────────────────────
# DELEGATION CONTEXT
# ───────────────────────────────────────────────────────────────────────────────

def get_effective_context(request):
    """
    Get unified delegation context for request.

    Returns dict with delegation info if admin user has delegated worker,
    otherwise returns empty delegation context.

    Returns:
        dict: {
            'delegated_user_id': str(UUID) or None,
            'delegated_user_name': str or None,
            'delegated_company_id': str(UUID) or None,
            'delegated_company_name': str or None,
            'delegated_user_role': str or None,
            'is_delegating': bool,
        }
    """
    context = {
        'delegated_user_id': None,
        'delegated_user_name': None,
        'delegated_company_id': None,
        'delegated_company_name': None,
        'delegated_user_role': None,
        'is_delegating': False,
    }

    # Only admins can have delegated users
    if not request.user.is_admin:
        return context

    delegated_user_id = request.session.get('delegated_user_id')
    if not delegated_user_id:
        return context

    context.update({
        'delegated_user_id': delegated_user_id,
        'delegated_user_name': request.session.get('delegated_user_name'),
        'delegated_company_id': request.session.get('delegated_company_id'),
        'delegated_company_name': request.session.get('delegated_company_name'),
        'delegated_user_role': request.session.get('delegated_user_role'),
        'is_delegating': True,
    })

    return context


# ───────────────────────────────────────────────────────────────────────────────
# COMPANY & USER CONTEXT
# ───────────────────────────────────────────────────────────────────────────────

def get_company(request):
    """Get the current company from session."""
    company_id = request.session.get('company_id')
    return Companies.objects.filter(id=company_id).first()


def is_manager(request, company):
    """Check if user is manager or admin of the given company."""
    if request.user.is_admin:
        return True
    uc = UserCompany.objects.filter(user=request.user, company=company).first()
    return uc and uc.role == UserCompany.RoleChoices.MANAGER


def ensure_membership(user):
    """Ensure user has at least one membership. Create default if none exists."""
    membership = UserCompany.objects.filter(user=user).order_by('-joined_at').first()
    if not membership:
        company = Companies.objects.first()
        if not company:
            company = Companies.objects.create(
                id=uuid4(), name='DemoCorp', legal_name='Demo Corporation'
            )
        membership = UserCompany.objects.create(
            id=uuid4(), user=user, company=company,
            role=UserCompany.RoleChoices.EMPLOYEE
        )
    return membership


def validate_manager_role_change(user, company, new_role):
    """
    Validate that changing a user's role won't leave company without managers.

    Args:
        user: Users instance being edited
        company: Companies instance context
        new_role: The new role being assigned (RoleChoices value)

    Returns:
        Tuple: (is_valid: bool, message: str or None)
        If valid, returns (True, None)
        If invalid, returns (False, error_message)
    """
    try:
        with transaction.atomic():
            # Only validate if changing TO something other than manager
            if new_role == UserCompany.RoleChoices.MANAGER:
                return (True, None)

            # Get current membership (lock the row to avoid race conditions)
            current_membership = (
                UserCompany.objects
                .select_for_update()
                .filter(user=user, company=company)
                .first()
            )

            # If no membership or not currently a manager, no restriction
            if not current_membership or current_membership.role == UserCompany.RoleChoices.EMPLOYEE:
                return (True, None)

            # User IS a manager and wants to change to employee
            # Count other managers in the company (excluding this user)
            other_managers_count = (
                UserCompany.objects
                .filter(
                    company=company,
                    role=UserCompany.RoleChoices.MANAGER
                )
                .exclude(user=user)
                .count()
            )

            if other_managers_count == 0:
                return (False, 'No se puede cambiar el rol: es el único Manager de la empresa.')

            return (True, None)
    except Exception as e:
        # If transaction fails, fail safely and log
        return (False, f'Error al validar el rol: {str(e)}')


def get_or_create_demo_user():
    """Get or create the demo user."""
    user = Users.objects.first()
    if not user:
        user = Users.objects.create(
            id=uuid4(), username='demo', email='demo@example.com',
            surname='Demo', password='demo'
        )
    return user


# ───────────────────────────────────────────────────────────────────────────────
# LEAVE REQUEST UTILITIES
# ───────────────────────────────────────────────────────────────────────────────

def serialize_leave(leave):
    """Serialize a LeaveRequest instance for JSON/API use."""
    def safe(val):
        if val is None:
            return None
        if hasattr(val, 'isoformat'):
            return val.isoformat()
        return str(val)
    return {
        'leave_type':      leave.leave_type,
        'leave_reason':    leave.leave_reason,
        'reason_note':     leave.reason_note,
        'start_date':      safe(leave.start_date),
        'end_date':        safe(leave.end_date),
        'status':          leave.status,
        'reviewed_by_id':  safe(leave.reviewed_by_id),
        'reviewed_at':     safe(leave.reviewed_at),
        'review_note':     leave.review_note,
        'user_full_name': f"{leave.user.username.title()} {leave.user.surname.title()}".strip(),        'user_id':         str(leave.user_id),
    }


def log_leave(leave, actor, action_type, before=None, reason=None, source='web'):
    """Create an audit log entry for a leave request change."""
    AuditLog.objects.create(
        id          = uuid.uuid4(),
        table_name  = 'leave_requests',
        record_id   = leave.pk,
        user        = actor,
        action_type = action_type,
        before      = before,
        after       = serialize_leave(leave),
        reason      = reason,
        source      = source, # Añadido
    )