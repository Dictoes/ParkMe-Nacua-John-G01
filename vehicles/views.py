from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from accounts.decorators import role_required
from accounts.models import Role

from .forms import VehicleForm
from .models import Vehicle


@role_required(Role.DRIVER)
def vehicle_list(request):
    vehicles = Vehicle.objects.filter(owner=request.user)
    return render(request, "vehicles/vehicle_list.html", {"vehicles": vehicles})


@role_required(Role.DRIVER)
def vehicle_create(request):
    form = VehicleForm(request.POST or None, owner=request.user)
    if request.method == "POST" and form.is_valid():
        vehicle = form.save(commit=False)
        vehicle.owner = request.user
        vehicle.save()
        messages.success(request, "Vehicle added to your account.")
        return redirect("vehicles:list")
    return render(request, "vehicles/vehicle_form.html", {"form": form})


@role_required(Role.DRIVER)
@require_http_methods(["GET", "POST"])
def vehicle_edit(request, pk):
    vehicle = get_object_or_404(Vehicle, pk=pk, owner=request.user)
    form = VehicleForm(
        request.POST or None,
        instance=vehicle,
        owner=request.user,
    )
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Vehicle details updated.")
        return redirect("vehicles:list")
    return render(
        request,
        "vehicles/vehicle_form.html",
        {"form": form, "vehicle": vehicle},
    )


@role_required(Role.DRIVER)
@require_http_methods(["GET", "POST"])
def vehicle_delete(request, pk):
    vehicle = get_object_or_404(Vehicle, pk=pk, owner=request.user)
    if request.method == "POST":
        vehicle.delete()
        messages.success(request, "Vehicle deleted.")
        return redirect("vehicles:list")
    return render(
        request,
        "vehicles/vehicle_confirm_delete.html",
        {"vehicle": vehicle},
    )
