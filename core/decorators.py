# ---------- Centralized Decorators: core/decorators.py ----------
from functools import wraps
from django.shortcuts import render, redirect
from users.models import UserCompany


def admin_only_required(view_func):
    """Decorator to ensure only admin users can access the view"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return render(request, 'error/sin_loguear.html', status=401)

        if not request.user.is_admin:
            return render(request, 'error/sin_permisos.html', status=403)

        return view_func(request, *args, **kwargs)
    return _wrapped_view


def manager_or_admin_required(view_func):
    """Decorator to verify that the user is a manager or admin before accessing certain views"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        # If not even logged in, get out
        if not request.user.is_authenticated:
            return render(request, 'error/sin_loguear.html', status=401)

        is_admin = request.user.is_admin
        is_manager = UserCompany.objects.all_with_deleted().filter(
            user=request.user,
            role=UserCompany.RoleChoices.MANAGER,
            deleted_at__isnull=True
        ).exists()

        if is_admin or is_manager:
            return view_func(request, *args, **kwargs)
        else:
            return render(request, 'error/sin_permisos.html', status=403)

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
            return render(request, 'error/sin_permisos.html', status=403)

        return view_func(request, *args, **kwargs)

    return _wrapped_view
