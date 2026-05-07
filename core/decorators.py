# ---------- Centralized Decorators: core/decorators.py ----------
from functools import wraps
from django.shortcuts import render, redirect
from users.models import UserCompany, Users, Companies
from core.services import get_effective_context


def admin_only_required(view_func):
    """Decorator to ensure only admin users can access the view"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return render(request, 'error/401.html', status=401)

        if not request.user.is_admin:
            return render(request, 'error/403.html', status=403)

        return view_func(request, *args, **kwargs)
    return _wrapped_view


def manager_or_admin_required(view_func):
    """Decorator to verify that the user is a manager or admin before accessing certain views"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        # If not even logged in, get out
        if not request.user.is_authenticated:
            return render(request, 'error/401.html', status=401)

        is_admin = request.user.is_admin
        is_manager = UserCompany.objects.all_with_deleted().filter(
            user=request.user,
            role=UserCompany.RoleChoices.MANAGER,
            deleted_at__isnull=True
        ).exists()

        if is_admin or is_manager:
            return view_func(request, *args, **kwargs)
        else:
            return render(request, 'error/403.html', status=403)

    return _wrapped_view


def auditor_cannot_access(view_func):
    """Decorator to prevent auditors from accessing certain views."""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        # If not logged in, redirect to login
        if not request.user.is_authenticated:
            return redirect('login')

        # Block auditors
        if request.user.is_auditor:
            return render(request, 'error/403.html', status=403)

        return view_func(request, *args, **kwargs)

    return _wrapped_view


def auditor_or_admin_required(view_func):
    """Decorator to ensure only auditors or admin users can access audit views"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return render(request, 'error/401.html', status=401)

        # Allow only auditors and admins
        if request.user.is_auditor or request.user.is_admin:
            return view_func(request, *args, **kwargs)
        else:
            return render(request, 'error/403.html', status=403)

    return _wrapped_view


def login_required_with_delegation_support(view_func):
    """
    Decorator that validates access for admin, manager, and employee users.

    Allows delegation to ANY user (admin, manager, employee). Auditors are excluded.
    Security is handled at the view/template level based on the user's role.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        # Step 1: Validate authentication
        if not request.user.is_authenticated:
            return render(request, 'error/401.html', status=401)

        # Step 2: Exclude auditors only
        if request.user.is_auditor:
            return render(request, 'error/403.html', status=403)

        is_admin = request.user.is_admin

        # Step 3: If admin is delegating, clear invalid delegations
        if is_admin:
            from core.services import get_effective_context
            delegation_context = get_effective_context(request)

            if delegation_context.get('is_delegating'):
                delegated_user_id = delegation_context.get('delegated_user_id')
                delegated_company_id = delegation_context.get('delegated_company_id')

                # Fetch delegated user
                delegated_user = Users.objects.filter(id=delegated_user_id).first()
                if not delegated_user:
                    # Invalid delegated user: clear delegation
                    request.session.pop('delegated_user_id', None)
                    request.session.pop('delegated_user_name', None)
                    request.session.pop('delegated_company_id', None)
                    request.session.pop('delegated_user_role', None)
                    request.session.modified = True
                    return view_func(request, *args, **kwargs)

                # Fetch delegated company
                delegated_company = Companies.objects.filter(id=delegated_company_id).first()
                if not delegated_company:
                    # Invalid delegated company: clear delegation
                    request.session.pop('delegated_user_id', None)
                    request.session.pop('delegated_user_name', None)
                    request.session.pop('delegated_company_id', None)
                    request.session.pop('delegated_user_role', None)
                    request.session.modified = True
                    return view_func(request, *args, **kwargs)

        return view_func(request, *args, **kwargs)

    return _wrapped_view
