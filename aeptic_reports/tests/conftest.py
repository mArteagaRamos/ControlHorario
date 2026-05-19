"""
Fixtures and helpers for aeptic_reports tests.

Imports helpers from users.tests.conftest and adds app-specific fixtures.
"""

from datetime import datetime, timedelta, date
from users.tests.conftest import make_user, make_company, make_membership
from timetracking.models import TimeEntries, TimeEntryEvent
from requests.models import LeaveRequest
from django.utils import timezone


def make_time_entry(user, company, date_obj, clock_in=None, clock_out=None, status='normal'):
    """
    Create a TimeEntry for testing.

    Args:
        user: Users instance
        company: Companies instance
        date_obj: date object
        clock_in: datetime (optional, defaults to 09:00)
        clock_out: datetime (optional, defaults to 17:00)
        status: 'normal' or 'voided'

    Returns:
        TimeEntries instance
    """
    if clock_in is None:
        clock_in = timezone.make_aware(
            datetime.combine(date_obj, datetime.strptime('09:00', '%H:%M').time())
        )

    if clock_out is None:
        clock_out = timezone.make_aware(
            datetime.combine(date_obj, datetime.strptime('17:00', '%H:%M').time())
        )

    entry = TimeEntries.objects.create(
        user=user,
        company=company,
        date=date_obj,
        clock_in=clock_in,
        clock_out=clock_out,
        status=status,
        total_seconds=(clock_out - clock_in).total_seconds()
    )

    return entry


def make_leave_request(user, company, leave_type, start_date, end_date,
                       reason='other', status='approved', start_time=None, end_time=None):
    """
    Create a LeaveRequest for testing.

    Args:
        user: Users instance
        company: Companies instance
        leave_type: 'vacation' or 'absence'
        start_date: date object
        end_date: date object
        reason: 'sick', 'maternity', 'wedding', 'bereavement', 'medical_appointment', 'legal_duty', 'personal', 'other'
        status: 'pending', 'approved', 'rejected'
        start_time: time object (optional)
        end_time: time object (optional)

    Returns:
        LeaveRequest instance
    """
    leave = LeaveRequest.objects.create(
        user=user,
        company=company,
        leave_type=leave_type,
        start_date=start_date,
        end_date=end_date,
        leave_reason=reason,
        status=status,
        start_time=start_time,
        end_time=end_time
    )

    return leave
