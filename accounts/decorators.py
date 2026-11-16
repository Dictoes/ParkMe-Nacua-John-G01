from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect


def role_required(role):
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapped(request, *args, **kwargs):
            if request.user.role != role:
                messages.error(request, "You do not have permission to view that page.")
                return dashboard_for_user(request.user)
            return view_func(request, *args, **kwargs)

        return wrapped

    return decorator


def dashboard_for_user(user):
    from .models import Role

    if user.role == Role.ADMINISTRATOR:
        return redirect("accounts:admin_dashboard")
    if user.role == Role.DRIVER:
        return redirect("accounts:driver_dashboard")
    raise PermissionDenied("This account does not have an assigned dashboard role.")
