from django.contrib import admin

from .models import ParkingFacility, ParkingLocation


class ParkingLocationInline(admin.TabularInline):
    model = ParkingLocation
    extra = 0


@admin.register(ParkingFacility)
class ParkingFacilityAdmin(admin.ModelAdmin):
    list_display = ("name", "facility_type")
    list_filter = ("facility_type",)
    search_fields = ("name",)
    inlines = [ParkingLocationInline]


@admin.register(ParkingLocation)
class ParkingLocationAdmin(admin.ModelAdmin):
    list_display = ("facility", "floor_level", "zone", "stall_number")
    list_filter = ("facility",)
    search_fields = ("facility__name", "floor_level", "zone", "stall_number")
