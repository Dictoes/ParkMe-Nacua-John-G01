from django.urls import path

from . import views


app_name = "parking"

urlpatterns = [
    path("vehicles/", views.vehicle_list, name="vehicle_list"),
    path("vehicles/add/", views.vehicle_create, name="vehicle_create"),
    path("vehicles/<int:pk>/", views.vehicle_detail, name="vehicle_detail"),
    path("vehicles/<int:pk>/edit/", views.vehicle_update, name="vehicle_update"),
    path("vehicles/<int:pk>/delete/", views.vehicle_delete, name="vehicle_delete"),
    path("facilities/", views.facility_list, name="facility_list"),
    path("facilities/add/", views.facility_create, name="facility_create"),
    path("facilities/<int:pk>/", views.facility_detail, name="facility_detail"),
    path("facilities/<int:pk>/edit/", views.facility_update, name="facility_update"),
    path("facilities/<int:pk>/delete/", views.facility_delete, name="facility_delete"),
    path("locations/", views.location_list, name="location_list"),
    path("locations/add/", views.location_create, name="location_create"),
    path("locations/<int:pk>/", views.location_detail, name="location_detail"),
    path("locations/<int:pk>/edit/", views.location_update, name="location_update"),
    path("locations/<int:pk>/delete/", views.location_delete, name="location_delete"),
    path("sessions/", views.session_list, name="session_list"),
    path("sessions/add/", views.session_create, name="session_create"),
    path("sessions/<int:pk>/", views.session_detail, name="session_detail"),
    path("sessions/<int:pk>/edit/", views.session_update, name="session_update"),
    path("sessions/<int:pk>/delete/", views.session_delete, name="session_delete"),
    path("sessions/<int:pk>/complete/", views.session_complete, name="session_complete"),
    path(
        "sessions/<int:session_pk>/references/add/",
        views.reference_create,
        name="reference_create",
    ),
    path("references/<int:pk>/edit/", views.reference_update, name="reference_update"),
    path("references/<int:pk>/delete/", views.reference_delete, name="reference_delete"),
    path("references/<int:pk>/photo/", views.reference_photo, name="reference_photo"),
    path("sessions/<int:session_pk>/timer/", views.timer_update, name="timer_update"),
    path("sessions/<int:session_pk>/timer/delete/", views.timer_delete, name="timer_delete"),
    path("reports/", views.reports, name="reports"),
    path("reports/export.csv", views.report_csv, name="report_csv"),
]
