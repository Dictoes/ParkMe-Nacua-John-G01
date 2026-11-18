import csv
import mimetypes

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, ProtectedError, Q
from django.db.models.functions import TruncMonth
from django.http import FileResponse, Http404, HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.decorators import role_required
from accounts.models import Role
from .filters import ParkingSessionFilterForm
from .forms import (
    FacilityForm,
    LocationForm,
    ParkingReferenceForm,
    ParkingSessionForm,
    VehicleForm,
)
from .models import (
    ParkingFacility,
    ParkingLocation,
    ParkingReference,
    ParkingSession,
    ParkingStatus,
    Vehicle,
)


PAGE_SIZE = 12


def _owner_vehicle(request, pk):
    return get_object_or_404(Vehicle, pk=pk, owner=request.user)


def _owner_session(request, pk):
    return get_object_or_404(
        ParkingSession.objects.select_related(
            "vehicle", "location__facility"
        ).prefetch_related("references"),
        pk=pk,
        vehicle__owner=request.user,
    )


def _delete_photo_if_orphaned(storage, photo_name):
    if photo_name and not ParkingReference.objects.filter(photo=photo_name).exists():
        storage.delete(photo_name)


def _schedule_orphaned_photo_cleanup(storage, photo_names):
    for photo_name in photo_names:
        transaction.on_commit(
            lambda name=photo_name: _delete_photo_if_orphaned(storage, name)
        )


def _delete_record_and_photos(record, references):
    photo_names = [reference.photo.name for reference in references if reference.photo]
    storage = references[0].photo.storage if references else None
    with transaction.atomic():
        record.delete()
    if storage:
        _schedule_orphaned_photo_cleanup(storage, photo_names)


def _paginate(request, queryset):
    return Paginator(queryset, PAGE_SIZE).get_page(request.GET.get("page"))


def _apply_report_filters(sessions, filters):
    if filters.get("date_from"):
        sessions = sessions.filter(parked_at__date__gte=filters["date_from"])
    if filters.get("date_to"):
        sessions = sessions.filter(parked_at__date__lte=filters["date_to"])
    if filters.get("vehicle"):
        sessions = sessions.filter(vehicle=filters["vehicle"])
    if filters.get("facility"):
        sessions = sessions.filter(location__facility=filters["facility"])
    if filters.get("status"):
        sessions = sessions.filter(status=filters["status"])
    if filters.get("floor"):
        sessions = sessions.filter(location__floor_level__icontains=filters["floor"].strip())
    if filters.get("zone"):
        sessions = sessions.filter(location__zone__icontains=filters["zone"].strip())
    query = filters.get("q", "").strip()
    if query:
        sessions = sessions.filter(
            Q(vehicle__plate_number__icontains=query)
            | Q(vehicle__brand_model__icontains=query)
            | Q(location__facility__name__icontains=query)
            | Q(location__floor_level__icontains=query)
            | Q(location__zone__icontains=query)
            | Q(location__stall_number__icontains=query)
        )
    return sessions


@login_required
def vehicle_list(request):
    vehicles = Vehicle.objects.filter(owner=request.user).annotate(
        session_count=Count("parking_sessions")
    ).order_by("plate_number", "pk")
    query = request.GET.get("q", "").strip()
    if query:
        vehicles = vehicles.filter(
            Q(plate_number__icontains=query)
            | Q(brand_model__icontains=query)
            | Q(color__icontains=query)
        )
    return render(
        request,
        "parking/vehicle_list.html",
        {"page_obj": _paginate(request, vehicles), "query": query},
    )


@login_required
def vehicle_create(request):
    form = VehicleForm(request.POST or None, owner=request.user)
    if request.method == "POST" and form.is_valid():
        vehicle = form.save(commit=False)
        vehicle.owner = request.user
        vehicle.save()
        messages.success(request, "Vehicle added to your account.")
        return redirect("parking:vehicle_list")
    return render(
        request, "parking/vehicle_form.html", {"form": form, "is_create": True}
    )


@login_required
def vehicle_detail(request, pk):
    vehicle = _owner_vehicle(request, pk)
    sessions = vehicle.parking_sessions.select_related("location__facility")
    return render(
        request,
        "parking/vehicle_detail.html",
        {"vehicle": vehicle, "page_obj": _paginate(request, sessions)},
    )


@login_required
def vehicle_update(request, pk):
    vehicle = _owner_vehicle(request, pk)
    form = VehicleForm(request.POST or None, instance=vehicle, owner=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Vehicle details updated.")
        return redirect("parking:vehicle_detail", pk=vehicle.pk)
    return render(
        request, "parking/vehicle_form.html", {"form": form, "vehicle": vehicle}
    )


@login_required
def vehicle_delete(request, pk):
    vehicle = _owner_vehicle(request, pk)
    references = ParkingReference.objects.filter(session__vehicle=vehicle).select_related(
        "session"
    )
    if request.method == "POST":
        _delete_record_and_photos(vehicle, references)
        messages.success(request, "Vehicle and its parking history were deleted.")
        return redirect("parking:vehicle_list")
    return render(
        request,
        "parking/confirm_delete.html",
        {"object": vehicle, "cancel_url": "parking:vehicle_detail", "cancel_pk": pk},
    )


@login_required
def facility_list(request):
    facilities = ParkingFacility.objects.annotate(
        location_count=Count("locations")
    ).order_by("name", "pk")
    query = request.GET.get("q", "").strip()
    if query:
        facilities = facilities.filter(
            Q(name__icontains=query) | Q(facility_type__icontains=query)
        )
    return render(
        request,
        "parking/facility_list.html",
        {"page_obj": _paginate(request, facilities), "query": query},
    )


@login_required
def facility_detail(request, pk):
    facility = get_object_or_404(
        ParkingFacility.objects.annotate(location_count=Count("locations")), pk=pk
    )
    locations = facility.locations.select_related("facility")
    return render(
        request,
        "parking/facility_detail.html",
        {"facility": facility, "page_obj": _paginate(request, locations)},
    )


@role_required(Role.ADMINISTRATOR)
def facility_create(request):
    form = FacilityForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Parking facility created.")
        return redirect("parking:facility_list")
    return render(
        request, "parking/facility_form.html", {"form": form, "is_create": True}
    )


@role_required(Role.ADMINISTRATOR)
def facility_update(request, pk):
    facility = get_object_or_404(ParkingFacility, pk=pk)
    form = FacilityForm(request.POST or None, instance=facility)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Parking facility updated.")
        return redirect("parking:facility_detail", pk=facility.pk)
    return render(
        request, "parking/facility_form.html", {"form": form, "facility": facility}
    )


@role_required(Role.ADMINISTRATOR)
def facility_delete(request, pk):
    facility = get_object_or_404(ParkingFacility, pk=pk)
    if request.method == "POST":
        try:
            facility.delete()
        except ProtectedError:
            messages.error(
                request,
                "This facility has a parking location used by a parking session and cannot be deleted.",
            )
            return redirect("parking:facility_detail", pk=facility.pk)
        messages.success(request, "Parking facility deleted.")
        return redirect("parking:facility_list")
    return render(
        request,
        "parking/confirm_delete.html",
        {"object": facility, "cancel_url": "parking:facility_detail", "cancel_pk": pk},
    )


@login_required
def location_list(request):
    locations = ParkingLocation.objects.select_related("facility")
    query = request.GET.get("q", "").strip()
    if query:
        locations = locations.filter(
            Q(facility__name__icontains=query)
            | Q(floor_level__icontains=query)
            | Q(zone__icontains=query)
            | Q(stall_number__icontains=query)
        )
    facility_id = request.GET.get("facility", "")
    if facility_id.isdigit():
        locations = locations.filter(facility_id=int(facility_id))
    return render(
        request,
        "parking/location_list.html",
        {
            "page_obj": _paginate(request, locations),
            "query": query,
            "facilities": ParkingFacility.objects.all(),
            "selected_facility": facility_id,
        },
    )


@login_required
def location_detail(request, pk):
    location = get_object_or_404(
        ParkingLocation.objects.select_related("facility"), pk=pk
    )
    return render(request, "parking/location_detail.html", {"location": location})


@role_required(Role.ADMINISTRATOR)
def location_create(request):
    form = LocationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Parking location added.")
        return redirect("parking:location_list")
    return render(
        request, "parking/location_form.html", {"form": form, "is_create": True}
    )


@role_required(Role.ADMINISTRATOR)
def location_update(request, pk):
    location = get_object_or_404(
        ParkingLocation.objects.select_related("facility"), pk=pk
    )
    form = LocationForm(request.POST or None, instance=location)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Parking location updated.")
        return redirect("parking:location_list")
    return render(
        request,
        "parking/location_form.html",
        {"form": form, "location": location},
    )


@role_required(Role.ADMINISTRATOR)
def location_delete(request, pk):
    location = get_object_or_404(
        ParkingLocation.objects.select_related("facility"), pk=pk
    )
    if request.method == "POST":
        try:
            location.delete()
        except ProtectedError:
            messages.error(
                request,
                "This location is part of a parking session and cannot be deleted.",
            )
            return redirect("parking:location_list")
        messages.success(request, "Parking location deleted.")
        return redirect("parking:location_list")
    return render(
        request,
        "parking/confirm_delete.html",
        {"object": location, "cancel_url": "parking:location_list"},
    )


@login_required
def session_list(request):
    form = ParkingSessionFilterForm(request.GET or None, owner=request.user)
    sessions = (
        ParkingSession.objects.filter(vehicle__owner=request.user)
        .select_related("vehicle", "location__facility")
        .prefetch_related("references")
    )
    if form.is_valid():
        filters = form.cleaned_data
        query = filters.get("q")
        if query:
            sessions = sessions.filter(
                Q(vehicle__plate_number__icontains=query)
                | Q(vehicle__brand_model__icontains=query)
                | Q(location__facility__name__icontains=query)
                | Q(location__floor_level__icontains=query)
                | Q(location__zone__icontains=query)
                | Q(location__stall_number__icontains=query)
            )
        if filters.get("status"):
            sessions = sessions.filter(status=filters["status"])
        if filters.get("vehicle"):
            sessions = sessions.filter(vehicle=filters["vehicle"])
        if filters.get("facility"):
            sessions = sessions.filter(location__facility=filters["facility"])
        if filters.get("date_from"):
            sessions = sessions.filter(parked_at__date__gte=filters["date_from"])
        if filters.get("date_to"):
            sessions = sessions.filter(parked_at__date__lte=filters["date_to"])
        if filters.get("floor"):
            sessions = sessions.filter(
                location__floor_level__icontains=filters["floor"].strip()
            )
        if filters.get("zone"):
            sessions = sessions.filter(location__zone__icontains=filters["zone"].strip())
    return render(
        request,
        "parking/session_list.html",
        {"form": form, "page_obj": _paginate(request, sessions)},
    )


@login_required
def session_create(request):
    form = ParkingSessionForm(request.POST or None, owner=request.user)
    if request.method == "POST" and form.is_valid():
        session = form.save()
        messages.success(request, "Parking session recorded.")
        return redirect("parking:session_detail", pk=session.pk)
    return render(
        request, "parking/session_form.html", {"form": form, "is_create": True}
    )


@login_required
def session_detail(request, pk):
    session = _owner_session(request, pk)
    return render(
        request,
        "parking/session_detail.html",
        {"parking_session": session},
    )


@login_required
def session_update(request, pk):
    session = _owner_session(request, pk)
    form = ParkingSessionForm(request.POST or None, instance=session, owner=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Parking session updated.")
        return redirect("parking:session_detail", pk=session.pk)
    return render(
        request,
        "parking/session_form.html",
        {"form": form, "parking_session": session},
    )


@login_required
def session_delete(request, pk):
    session = _owner_session(request, pk)
    references = session.references.all()
    if request.method == "POST":
        _delete_record_and_photos(session, references)
        messages.success(request, "Parking session and its references were deleted.")
        return redirect("parking:session_list")
    return render(
        request,
        "parking/confirm_delete.html",
        {
            "object": session,
            "cancel_url": "parking:session_detail",
            "cancel_pk": pk,
        },
    )


@login_required
@require_POST
def session_complete(request, pk):
    session = _owner_session(request, pk)
    if session.status != ParkingStatus.COMPLETED:
        session.status = ParkingStatus.COMPLETED
        session.save(update_fields=["status"])
        messages.success(request, "Parking session marked as completed.")
    else:
        messages.info(request, "This parking session is already completed.")
    return redirect("parking:session_detail", pk=session.pk)


@login_required
def reference_create(request, session_pk):
    session = _owner_session(request, session_pk)
    form = ParkingReferenceForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        reference = form.save(commit=False)
        reference.session = session
        reference.save()
        messages.success(request, "Parking reference added.")
        return redirect("parking:session_detail", pk=session.pk)
    return render(
        request,
        "parking/reference_form.html",
        {"form": form, "parking_session": session, "is_create": True},
    )


@login_required
def reference_update(request, pk):
    reference = get_object_or_404(
        ParkingReference.objects.select_related("session__vehicle"),
        pk=pk,
        session__vehicle__owner=request.user,
    )
    form = ParkingReferenceForm(
        request.POST or None, request.FILES or None, instance=reference
    )
    if request.method == "POST" and form.is_valid():
        old_photo_name = reference.photo.name if reference.photo else ""
        storage = reference.photo.storage
        form.save()
        new_photo_name = reference.photo.name if reference.photo else ""
        if old_photo_name and old_photo_name != new_photo_name:
            _schedule_orphaned_photo_cleanup(storage, [old_photo_name])
        messages.success(request, "Parking reference updated.")
        return redirect("parking:session_detail", pk=reference.session_id)
    return render(
        request,
        "parking/reference_form.html",
        {"form": form, "parking_session": reference.session, "reference": reference},
    )


@login_required
def reference_delete(request, pk):
    reference = get_object_or_404(
        ParkingReference.objects.select_related("session__vehicle"),
        pk=pk,
        session__vehicle__owner=request.user,
    )
    if request.method == "POST":
        session_id = reference.session_id
        if reference.photo:
            photo_name = reference.photo.name
            storage = reference.photo.storage
            reference.delete()
            _schedule_orphaned_photo_cleanup(storage, [photo_name])
        else:
            reference.delete()
        messages.success(request, "Parking reference deleted.")
        return redirect("parking:session_detail", pk=session_id)
    return render(
        request,
        "parking/confirm_delete.html",
        {
            "object": reference,
            "cancel_url": "parking:session_detail",
            "cancel_pk": reference.session_id,
        },
    )


@login_required
def reference_photo(request, pk):
    reference = get_object_or_404(
        ParkingReference.objects.select_related("session__vehicle"),
        pk=pk,
        session__vehicle__owner=request.user,
    )
    if not reference.photo:
        raise Http404("This reference has no photo.")
    try:
        file_handle = reference.photo.open("rb")
    except (OSError, ValueError) as exc:
        raise Http404("The reference photo is unavailable.") from exc
    content_type = mimetypes.guess_type(reference.photo.name)[0] or "application/octet-stream"
    response = FileResponse(file_handle, content_type=content_type)
    response["X-Content-Type-Options"] = "nosniff"
    response["Cache-Control"] = "private, no-store"
    return response


@login_required
def reports(request):
    form = ParkingSessionFilterForm(request.GET or None, owner=request.user)
    sessions = (
        ParkingSession.objects.filter(vehicle__owner=request.user)
        .select_related("vehicle", "location__facility")
    )
    if form.is_valid():
        sessions = _apply_report_filters(sessions, form.cleaned_data)
    summary = {
        "total": sessions.count(),
        "active": sessions.filter(status=ParkingStatus.ACTIVE).count(),
        "completed": sessions.filter(status=ParkingStatus.COMPLETED).count(),
    }
    per_vehicle = (
        sessions.values("vehicle__plate_number", "vehicle__brand_model")
        .annotate(total=Count("pk"))
        .order_by("vehicle__plate_number")
    )
    per_facility = (
        sessions.values("location__facility__name")
        .annotate(total=Count("pk"))
        .order_by("location__facility__name")
    )
    per_month = (
        sessions.annotate(month=TruncMonth("parked_at"))
        .values("month")
        .annotate(total=Count("pk"))
        .order_by("month")
    )
    return render(
        request,
        "parking/reports.html",
        {
            "form": form,
            "summary": summary,
            "per_vehicle": per_vehicle,
            "per_facility": per_facility,
            "per_month": per_month,
            "page_obj": _paginate(request, sessions),
        },
    )


@login_required
def report_csv(request):
    form = ParkingSessionFilterForm(request.GET or None, owner=request.user)
    if form.is_bound and not form.is_valid():
        return HttpResponseBadRequest("Correct the report filters before exporting.")
    sessions = ParkingSession.objects.filter(vehicle__owner=request.user).select_related(
        "vehicle", "location__facility"
    )
    if form.is_valid():
        sessions = _apply_report_filters(sessions, form.cleaned_data)
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="parkme-parking-report.csv"'
    writer = csv.writer(response)
    writer.writerow(
        ["Vehicle", "Facility", "Floor / level", "Zone", "Stall", "Parked at", "Status"]
    )
    for session in sessions.iterator():
        values = [
        session.vehicle.plate_number,
        session.location.facility.name,
        session.location.floor_level,
        session.location.zone,
        session.location.stall_number,
        timezone.localtime(session.parked_at).isoformat(),
        session.get_status_display(),
        ]
        writer.writerow(
        [f"'{value}" if str(value).startswith(("=", "+", "-", "@")) else value for value in values]
        )
    return response
