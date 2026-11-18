from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseNotAllowed
from django.shortcuts import redirect, render
from django.views.decorators.cache import never_cache

from vehicles.models import Vehicle

from .decorators import dashboard_for_user, role_required
from .forms import LoginForm, ProfileForm, RegistrationForm
from .models import Role, User


def register_view(request):
    if request.user.is_authenticated:
        return dashboard_for_user(request.user)

    form = RegistrationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Your ParkMe account is ready. You can now log in.")
        return redirect("accounts:login")
    return render(request, "accounts/register.html", {"form": form})


@never_cache
def login_view(request):
    if request.user.is_authenticated:
        return dashboard_for_user(request.user)

    form = LoginForm(request, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        login(request, form.get_user())
        messages.success(request, "You are now logged in.")
        return dashboard_for_user(request.user)
    return render(request, "accounts/login.html", {"form": form})


def logout_view(request):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    logout(request)
    messages.success(request, "You have been logged out.")
    return redirect("home")


@login_required
def dashboard_view(request):
    return dashboard_for_user(request.user)


@role_required(Role.ADMINISTRATOR)
def admin_dashboard(request):
    return render(
        request,
        "dashboards/admin_dashboard.html",
        {
            "driver_count": User.objects.filter(role=Role.DRIVER).count(),
        },
    )


@role_required(Role.DRIVER)
def driver_dashboard(request):
    return render(
        request,
        "dashboards/driver_dashboard.html",
        {
            "profile_complete": bool(
                request.user.first_name
                and request.user.last_name
                and request.user.email
            ),
            "vehicle_count": Vehicle.objects.filter(owner=request.user).count(),
        },
    )


@login_required
def profile_view(request):
    return render(request, "accounts/profile.html", {"profile_user": request.user})


@login_required
def edit_profile_view(request):
    form = ProfileForm(request.POST or None, instance=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Your profile has been updated.")
        return redirect("accounts:profile")
    return render(request, "accounts/edit_profile.html", {"form": form})
