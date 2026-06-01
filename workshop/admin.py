from django.contrib import admin

from .models import (
    Appointment, Client, OrderPart, OrderService, Part,
    Service, ServiceCategory, Supplier, Vehicle, WorkOrder,
)


class VehicleInline(admin.TabularInline):
    model = Vehicle
    extra = 0


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ["full_name", "phone", "type", "created_at"]
    list_filter = ["type"]
    search_fields = ["full_name", "phone", "email"]
    inlines = [VehicleInline]


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ["brand", "model", "plate", "client", "year", "mileage"]
    list_filter = ["brand"]
    search_fields = ["brand", "model", "plate", "vin"]
    autocomplete_fields = ["client"]


@admin.register(ServiceCategory)
class ServiceCategoryAdmin(admin.ModelAdmin):
    list_display = ["name"]
    search_fields = ["name"]


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ["name", "category", "labor_hours", "price"]
    list_filter = ["category"]
    search_fields = ["name"]


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ["name", "contacts"]
    search_fields = ["name"]


@admin.register(Part)
class PartAdmin(admin.ModelAdmin):
    list_display = ["name", "article", "stock", "price", "supplier"]
    list_filter = ["supplier"]
    search_fields = ["name", "article"]


class OrderServiceInline(admin.TabularInline):
    model = OrderService
    extra = 1
    autocomplete_fields = ["service", "mechanic"]


class OrderPartInline(admin.TabularInline):
    model = OrderPart
    extra = 1
    autocomplete_fields = ["part"]


@admin.register(WorkOrder)
class WorkOrderAdmin(admin.ModelAdmin):
    list_display = ["id", "vehicle", "client", "status", "total", "is_paid", "created_at"]
    list_filter = ["status", "is_paid"]
    search_fields = ["vehicle__plate", "client__full_name"]
    autocomplete_fields = ["client", "vehicle", "receiver"]
    readonly_fields = ["total", "created_at"]
    inlines = [OrderServiceInline, OrderPartInline]


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ["client", "vehicle", "scheduled_at", "status"]
    list_filter = ["status"]
    search_fields = ["client__full_name", "vehicle__plate"]
    autocomplete_fields = ["client", "vehicle"]
