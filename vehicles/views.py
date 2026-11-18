from django.contrib import messages
from django.shortcuts import redirect, render

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
