from datetime import timedelta

from django import forms
from django.forms.widgets import CheckboxInput, Select, SelectMultiple, Textarea

from users.models import User

from .models import (
    Appointment, Client, OrderPart, OrderService, Part, Service,
    ServiceCategory, Supplier, Vehicle, WorkOrder,
)


class BootstrapFormMixin:
    """Добавляет Bootstrap-классы виджетам формы без сторонних библиотек."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, CheckboxInput):
                widget.attrs.setdefault("class", "form-check-input")
            elif isinstance(widget, (Select, SelectMultiple)):
                widget.attrs.setdefault("class", "form-select")
            else:
                css = widget.attrs.get("class", "")
                widget.attrs["class"] = (css + " form-control").strip()
            if isinstance(widget, Textarea):
                widget.attrs.setdefault("rows", 3)


# ---------- Справочники ----------
class ClientForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Client
        fields = ["full_name", "phone", "email", "type"]


class VehicleForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Vehicle
        fields = ["client", "brand", "model", "plate", "vin", "year", "mileage"]


class ServiceCategoryForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = ServiceCategory
        fields = ["name"]


class ServiceForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Service
        fields = ["category", "name", "labor_hours", "price"]


class SupplierForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Supplier
        fields = ["name", "contacts"]


class PartForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Part
        fields = ["supplier", "name", "article", "stock", "price"]


# ---------- Заказ-наряд ----------
class WorkOrderForm(BootstrapFormMixin, forms.ModelForm):
    """Шапка заказ-наряда. Приёмщик и статус назначаются системой."""

    class Meta:
        model = WorkOrder
        fields = ["client", "vehicle", "complaint", "mileage_in"]

    def clean(self):
        cleaned = super().clean()
        client = cleaned.get("client")
        vehicle = cleaned.get("vehicle")
        if client and vehicle and vehicle.client_id != client.id:
            self.add_error("vehicle", "Этот автомобиль принадлежит другому клиенту.")
        return cleaned


class OrderServiceForm(BootstrapFormMixin, forms.ModelForm):
    """Добавление работы в заказ. Стоимость рассчитывается в представлении."""

    class Meta:
        model = OrderService
        fields = ["service", "mechanic", "quantity"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["mechanic"].queryset = User.objects.filter(
            role=User.Role.MECHANIC
        )
        self.fields["mechanic"].required = False
        self.fields["mechanic"].empty_label = "— механик —"
        self.fields["quantity"].initial = 1
        self.fields["service"].label_from_instance = (
            lambda obj: f"{obj.name} — {obj.price} ₽"
        )


class OrderPartForm(BootstrapFormMixin, forms.ModelForm):
    """Добавление запчасти в заказ. Цена и списание со склада — в представлении."""

    class Meta:
        model = OrderPart
        fields = ["part", "quantity"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["quantity"].initial = 1
        self.fields["part"].label_from_instance = (
            lambda obj: f"{obj.name} — {obj.price} ₽ (остаток: {obj.stock})"
        )


class AppointmentForm(BootstrapFormMixin, forms.ModelForm):
    """Запись на приём. Проверяет занятость временного слота."""

    scheduled_at = forms.DateTimeField(
        label="Дата и время",
        widget=forms.DateTimeInput(
            attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"
        ),
        input_formats=["%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"],
    )

    class Meta:
        model = Appointment
        fields = ["client", "vehicle", "scheduled_at", "status", "comment"]

    def clean(self):
        cleaned = super().clean()
        client = cleaned.get("client")
        vehicle = cleaned.get("vehicle")
        scheduled_at = cleaned.get("scheduled_at")
        status = cleaned.get("status")

        if client and vehicle and vehicle.client_id != client.id:
            self.add_error("vehicle", "Этот автомобиль принадлежит другому клиенту.")

        # Контроль занятости: в пределах слота не должно быть других активных записей
        if scheduled_at and status != Appointment.Status.CANCELLED:
            window = timedelta(minutes=Appointment.SLOT_MINUTES)
            conflicts = Appointment.objects.exclude(
                status=Appointment.Status.CANCELLED
            ).filter(
                scheduled_at__gt=scheduled_at - window,
                scheduled_at__lt=scheduled_at + window,
            )
            if self.instance.pk:
                conflicts = conflicts.exclude(pk=self.instance.pk)
            other = conflicts.first()
            if other:
                self.add_error(
                    "scheduled_at",
                    f"Это время занято: уже есть запись на "
                    f"{other.scheduled_at:%d.%m.%Y %H:%M} "
                    f"(интервал {Appointment.SLOT_MINUTES} мин).",
                )
        return cleaned
