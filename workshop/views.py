from datetime import date, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.messages.views import SuccessMessageMixin
from django.db import transaction
from django.db.models import (
    Avg, Count, DecimalField, ExpressionWrapper, F, Q, Sum,
)
from django.db.models.functions import TruncMonth
from django.db.models.deletion import ProtectedError
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.generic import (
    CreateView, DeleteView, DetailView, ListView, UpdateView,
)

from users.access import RoleRequiredMixin, role_required
from users.models import User

from .forms import (
    AppointmentForm, ClientForm, OrderPartForm, OrderServiceForm, PartForm,
    ServiceCategoryForm, ServiceForm, SupplierForm, VehicleForm, WorkOrderForm,
)
from .exports import build_reports_xlsx, render_order_pdf
from .models import (
    Appointment, Client, OrderPart, OrderService, Part, Service,
    ServiceCategory, Supplier, Vehicle, WorkOrder,
)

MANAGER_ROLES = (User.Role.ADMIN, User.Role.RECEIVER)

MONTHS_RU = [
    "янв", "фев", "мар", "апр", "май", "июн",
    "июл", "авг", "сен", "окт", "ноя", "дек",
]


def _months_back(d, n):
    """Первое число месяца, на n месяцев раньше месяца даты d."""
    index = d.year * 12 + (d.month - 1) - n
    year, month = divmod(index, 12)
    return date(year, month + 1, 1)


def _month_label(dt):
    return f"{MONTHS_RU[dt.month - 1]} {dt.year}"


# ======================= Дашборд и заглушка =======================
@login_required
def dashboard(request):
    # Распределение заказ-нарядов по статусам (для диаграммы)
    color_hex = {
        "new": "#6c757d", "diagnostics": "#0dcaf0", "approval": "#ffc107",
        "in_progress": "#0d6efd", "waiting_parts": "#fd7e14",
        "ready": "#198754", "issued": "#212529",
    }
    counts = {
        row["status"]: row["c"]
        for row in WorkOrder.objects.values("status").annotate(c=Count("id"))
    }
    status_chart = {"labels": [], "data": [], "colors": []}
    for value, label in WorkOrder.Status.choices:
        if counts.get(value):
            status_chart["labels"].append(label)
            status_chart["data"].append(counts[value])
            status_chart["colors"].append(color_hex[value])

    # Выручка по месяцам за последние 6 месяцев (по выданным заказам)
    d_from = _months_back(timezone.localdate(), 5)
    by_month = (
        WorkOrder.objects.filter(
            status=WorkOrder.Status.ISSUED, closed_at__date__gte=d_from
        )
        .annotate(m=TruncMonth("closed_at")).values("m")
        .annotate(total=Sum("total")).order_by("m")
    )
    revenue_chart = {
        "labels": [_month_label(r["m"]) for r in by_month],
        "data": [float(r["total"]) for r in by_month],
    }

    context = {
        "clients_count": Client.objects.count(),
        "vehicles_count": Vehicle.objects.count(),
        "active_orders_count": WorkOrder.objects.exclude(
            status=WorkOrder.Status.ISSUED
        ).count(),
        "low_stock_count": Part.objects.filter(stock__lte=5).count(),
        "recent_orders": WorkOrder.objects.select_related("vehicle", "client")[:8],
        "upcoming_appointments": Appointment.objects.exclude(
            status=Appointment.Status.CANCELLED
        ).filter(scheduled_at__gte=timezone.now()).select_related(
            "client", "vehicle"
        )[:5],
        "status_chart": status_chart,
        "revenue_chart": revenue_chart,
    }
    return render(request, "dashboard.html", context)


@login_required
def soon(request):
    return render(request, "soon.html")


# ======================= Базовые классы CRUD =======================
class DirectoryAccess(RoleRequiredMixin):
    """Доступ к справочникам: администратор и мастер-приёмщик."""
    allowed_roles = MANAGER_ROLES


class SearchableListView(DirectoryAccess, ListView):
    """Список с поиском по нескольким полям и постраничным выводом."""
    paginate_by = 15
    search_fields = ()

    def get_queryset(self):
        qs = super().get_queryset()
        query = self.request.GET.get("q", "").strip()
        if query and self.search_fields:
            condition = Q()
            for field in self.search_fields:
                condition |= Q(**{f"{field}__icontains": query})
            qs = qs.filter(condition)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["q"] = self.request.GET.get("q", "")
        return ctx


class PageMixin:
    """Передаёт в шаблон заголовок страницы и ссылку отмены (на список)."""
    list_url_name = None
    page_title = ""

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        if self.page_title:
            ctx.setdefault("page_title", self.page_title)
        if self.list_url_name:
            ctx.setdefault("cancel_url", reverse(self.list_url_name))
        return ctx


class BaseCreate(DirectoryAccess, SuccessMessageMixin, PageMixin, CreateView):
    template_name = "crud/object_form.html"


class BaseUpdate(DirectoryAccess, SuccessMessageMixin, PageMixin, UpdateView):
    template_name = "crud/object_form.html"


class BaseDelete(DirectoryAccess, PageMixin, DeleteView):
    """Удаление с защитой: если запись используется (PROTECT) — сообщение, а не ошибка."""
    template_name = "crud/object_confirm_delete.html"
    protected_message = "Невозможно удалить: запись используется в других данных."
    deleted_message = "Запись удалена."

    def form_valid(self, form):
        try:
            response = super().form_valid(form)
        except ProtectedError:
            messages.error(self.request, self.protected_message)
            return redirect(self.get_success_url())
        messages.success(self.request, self.deleted_message)
        return response


# ======================= Клиенты =======================
class ClientListView(SearchableListView):
    model = Client
    template_name = "clients/client_list.html"
    search_fields = ("full_name", "phone", "email")


class ClientDetailView(DirectoryAccess, DetailView):
    model = Client
    template_name = "clients/client_detail.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["orders"] = self.object.orders.select_related("vehicle").all()[:10]
        return ctx


class ClientCreateView(BaseCreate):
    model = Client
    form_class = ClientForm
    success_url = reverse_lazy("client_list")
    success_message = "Клиент добавлен."
    list_url_name = "client_list"
    page_title = "Новый клиент"


class ClientUpdateView(BaseUpdate):
    model = Client
    form_class = ClientForm
    success_url = reverse_lazy("client_list")
    success_message = "Данные клиента сохранены."
    list_url_name = "client_list"
    page_title = "Редактирование клиента"


class ClientDeleteView(BaseDelete):
    model = Client
    success_url = reverse_lazy("client_list")
    list_url_name = "client_list"
    deleted_message = "Клиент удалён."


# ======================= Автомобили =======================
class VehicleListView(SearchableListView):
    model = Vehicle
    template_name = "vehicles/vehicle_list.html"
    search_fields = ("brand", "model", "plate", "vin")

    def get_queryset(self):
        return super().get_queryset().select_related("client")


class VehicleCreateView(BaseCreate):
    model = Vehicle
    form_class = VehicleForm
    success_url = reverse_lazy("vehicle_list")
    success_message = "Автомобиль добавлен."
    list_url_name = "vehicle_list"
    page_title = "Новый автомобиль"


class VehicleUpdateView(BaseUpdate):
    model = Vehicle
    form_class = VehicleForm
    success_url = reverse_lazy("vehicle_list")
    success_message = "Данные автомобиля сохранены."
    list_url_name = "vehicle_list"
    page_title = "Редактирование автомобиля"


class VehicleDeleteView(BaseDelete):
    model = Vehicle
    success_url = reverse_lazy("vehicle_list")
    list_url_name = "vehicle_list"
    deleted_message = "Автомобиль удалён."


# ======================= Категории услуг =======================
class CategoryListView(SearchableListView):
    model = ServiceCategory
    template_name = "directory/category_list.html"
    search_fields = ("name",)


class CategoryCreateView(BaseCreate):
    model = ServiceCategory
    form_class = ServiceCategoryForm
    success_url = reverse_lazy("category_list")
    success_message = "Категория добавлена."
    list_url_name = "category_list"
    page_title = "Новая категория услуг"


class CategoryUpdateView(BaseUpdate):
    model = ServiceCategory
    form_class = ServiceCategoryForm
    success_url = reverse_lazy("category_list")
    success_message = "Категория сохранена."
    list_url_name = "category_list"
    page_title = "Редактирование категории"


class CategoryDeleteView(BaseDelete):
    model = ServiceCategory
    success_url = reverse_lazy("category_list")
    list_url_name = "category_list"
    deleted_message = "Категория удалена."
    protected_message = "Нельзя удалить категорию: к ней привязаны услуги."


# ======================= Услуги =======================
class ServiceListView(SearchableListView):
    model = Service
    template_name = "directory/service_list.html"
    search_fields = ("name",)

    def get_queryset(self):
        return super().get_queryset().select_related("category")


class ServiceCreateView(BaseCreate):
    model = Service
    form_class = ServiceForm
    success_url = reverse_lazy("service_list")
    success_message = "Услуга добавлена."
    list_url_name = "service_list"
    page_title = "Новая услуга"


class ServiceUpdateView(BaseUpdate):
    model = Service
    form_class = ServiceForm
    success_url = reverse_lazy("service_list")
    success_message = "Услуга сохранена."
    list_url_name = "service_list"
    page_title = "Редактирование услуги"


class ServiceDeleteView(BaseDelete):
    model = Service
    success_url = reverse_lazy("service_list")
    list_url_name = "service_list"
    deleted_message = "Услуга удалена."
    protected_message = "Нельзя удалить услугу: она используется в заказ-нарядах."


# ======================= Поставщики =======================
class SupplierListView(SearchableListView):
    model = Supplier
    template_name = "directory/supplier_list.html"
    search_fields = ("name", "contacts")


class SupplierCreateView(BaseCreate):
    model = Supplier
    form_class = SupplierForm
    success_url = reverse_lazy("supplier_list")
    success_message = "Поставщик добавлен."
    list_url_name = "supplier_list"
    page_title = "Новый поставщик"


class SupplierUpdateView(BaseUpdate):
    model = Supplier
    form_class = SupplierForm
    success_url = reverse_lazy("supplier_list")
    success_message = "Поставщик сохранён."
    list_url_name = "supplier_list"
    page_title = "Редактирование поставщика"


class SupplierDeleteView(BaseDelete):
    model = Supplier
    success_url = reverse_lazy("supplier_list")
    list_url_name = "supplier_list"
    deleted_message = "Поставщик удалён."


# ======================= Запчасти (склад) =======================
class PartListView(SearchableListView):
    model = Part
    template_name = "directory/part_list.html"
    search_fields = ("name", "article")

    def get_queryset(self):
        return super().get_queryset().select_related("supplier")


class PartCreateView(BaseCreate):
    model = Part
    form_class = PartForm
    success_url = reverse_lazy("part_list")
    success_message = "Запчасть добавлена."
    list_url_name = "part_list"
    page_title = "Новая запчасть"


class PartUpdateView(BaseUpdate):
    model = Part
    form_class = PartForm
    success_url = reverse_lazy("part_list")
    success_message = "Запчасть сохранена."
    list_url_name = "part_list"
    page_title = "Редактирование запчасти"


class PartDeleteView(BaseDelete):
    model = Part
    success_url = reverse_lazy("part_list")
    list_url_name = "part_list"
    deleted_message = "Запчасть удалена."
    protected_message = "Нельзя удалить запчасть: она используется в заказ-нарядах."


# ======================= Заказ-наряды =======================
class OrderAccess(RoleRequiredMixin):
    """Просмотр заказ-нарядов: все роли (включая механика)."""
    allowed_roles = (User.Role.ADMIN, User.Role.RECEIVER, User.Role.MECHANIC)


class OrderManageAccess(RoleRequiredMixin):
    """Управление заказ-нарядами: администратор и приёмщик."""
    allowed_roles = MANAGER_ROLES


class WorkOrderListView(OrderAccess, ListView):
    model = WorkOrder
    template_name = "orders/order_list.html"
    paginate_by = 15

    def get_queryset(self):
        qs = WorkOrder.objects.select_related("client", "vehicle", "receiver")
        status = self.request.GET.get("status", "").strip()
        query = self.request.GET.get("q", "").strip()
        if status:
            qs = qs.filter(status=status)
        if query:
            qs = qs.filter(
                Q(vehicle__plate__icontains=query)
                | Q(client__full_name__icontains=query)
            )
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["q"] = self.request.GET.get("q", "")
        ctx["status"] = self.request.GET.get("status", "")
        ctx["status_choices"] = WorkOrder.Status.choices
        return ctx


class WorkOrderDetailView(OrderAccess, DetailView):
    model = WorkOrder
    template_name = "orders/order_detail.html"
    context_object_name = "order"

    def get_queryset(self):
        return WorkOrder.objects.select_related("client", "vehicle", "receiver")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["services"] = self.object.order_services.select_related(
            "service", "mechanic"
        )
        ctx["parts"] = self.object.order_parts.select_related("part")
        ctx["service_form"] = OrderServiceForm()
        ctx["part_form"] = OrderPartForm()
        ctx["can_manage"] = (
            self.request.user.is_superuser
            or self.request.user.role in MANAGER_ROLES
        )
        return ctx


class WorkOrderCreateView(OrderManageAccess, SuccessMessageMixin, PageMixin, CreateView):
    model = WorkOrder
    form_class = WorkOrderForm
    template_name = "crud/object_form.html"
    success_message = "Заказ-наряд создан."
    list_url_name = "order_list"
    page_title = "Новый заказ-наряд"

    def form_valid(self, form):
        form.instance.receiver = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("order_detail", kwargs={"pk": self.object.pk})


class WorkOrderUpdateView(OrderManageAccess, SuccessMessageMixin, PageMixin, UpdateView):
    model = WorkOrder
    form_class = WorkOrderForm
    template_name = "crud/object_form.html"
    success_message = "Заказ-наряд обновлён."
    list_url_name = "order_list"
    page_title = "Редактирование заказ-наряда"

    def get_success_url(self):
        return reverse("order_detail", kwargs={"pk": self.object.pk})


class WorkOrderDeleteView(OrderManageAccess, PageMixin, DeleteView):
    model = WorkOrder
    template_name = "crud/object_confirm_delete.html"
    success_url = reverse_lazy("order_list")
    list_url_name = "order_list"

    def form_valid(self, form):
        # Возвращаем запчасти на склад перед удалением заказа
        with transaction.atomic():
            for item in self.object.order_parts.select_related("part"):
                part = Part.objects.select_for_update().get(pk=item.part_id)
                part.stock += item.quantity
                part.save(update_fields=["stock"])
            response = super().form_valid(form)
        messages.success(
            self.request, "Заказ-наряд удалён, запчасти возвращены на склад."
        )
        return response


# ---------- Операции над заказ-нарядом (function views) ----------
@role_required(*MANAGER_ROLES)
@require_POST
def order_add_service(request, pk):
    order = get_object_or_404(WorkOrder, pk=pk)
    form = OrderServiceForm(request.POST)
    if form.is_valid():
        item = form.save(commit=False)
        item.order = order
        item.cost = item.service.price * item.quantity
        item.save()
        order.recalculate_total()
        messages.success(request, "Работа добавлена в заказ.")
    else:
        messages.error(request, "Проверьте данные формы работы.")
    return redirect("order_detail", pk=pk)


@role_required(*MANAGER_ROLES)
@require_POST
def order_delete_service(request, pk, item_pk):
    order = get_object_or_404(WorkOrder, pk=pk)
    item = get_object_or_404(OrderService, pk=item_pk, order=order)
    item.delete()
    order.recalculate_total()
    messages.success(request, "Работа удалена из заказа.")
    return redirect("order_detail", pk=pk)


@role_required(*MANAGER_ROLES)
@require_POST
def order_add_part(request, pk):
    order = get_object_or_404(WorkOrder, pk=pk)
    form = OrderPartForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Проверьте данные формы запчасти.")
        return redirect("order_detail", pk=pk)

    quantity = form.cleaned_data["quantity"]
    with transaction.atomic():
        # Блокируем строку склада, чтобы избежать гонок при списании
        part = Part.objects.select_for_update().get(pk=form.cleaned_data["part"].pk)
        if quantity > part.stock:
            messages.error(
                request,
                f"Недостаточно на складе: «{part.name}» (остаток {part.stock}).",
            )
        else:
            part.stock -= quantity
            part.save(update_fields=["stock"])
            OrderPart.objects.create(
                order=order, part=part, quantity=quantity, price=part.price
            )
            order.recalculate_total()
            messages.success(request, "Запчасть добавлена в заказ, списана со склада.")
    return redirect("order_detail", pk=pk)


@role_required(*MANAGER_ROLES)
@require_POST
def order_delete_part(request, pk, item_pk):
    order = get_object_or_404(WorkOrder, pk=pk)
    item = get_object_or_404(OrderPart, pk=item_pk, order=order)
    with transaction.atomic():
        part = Part.objects.select_for_update().get(pk=item.part_id)
        part.stock += item.quantity
        part.save(update_fields=["stock"])
        item.delete()
        order.recalculate_total()
    messages.success(request, "Запчасть удалена, остаток возвращён на склад.")
    return redirect("order_detail", pk=pk)


@role_required(User.Role.ADMIN, User.Role.RECEIVER, User.Role.MECHANIC)
@require_POST
def order_change_status(request, pk):
    order = get_object_or_404(WorkOrder, pk=pk)
    new_status = request.POST.get("status", "")
    allowed = [s.value for s in order.allowed_next_statuses()]
    if new_status in allowed:
        order.status = new_status
        fields = ["status"]
        if new_status == WorkOrder.Status.ISSUED:
            order.closed_at = timezone.now()
            fields.append("closed_at")
        order.save(update_fields=fields)
        messages.success(request, f"Статус изменён: {order.get_status_display()}.")
    else:
        messages.error(request, "Недопустимый переход статуса.")
    return redirect("order_detail", pk=pk)


@role_required(*MANAGER_ROLES)
@require_POST
def order_toggle_paid(request, pk):
    order = get_object_or_404(WorkOrder, pk=pk)
    order.is_paid = not order.is_paid
    order.save(update_fields=["is_paid"])
    messages.success(request, "Статус оплаты обновлён.")
    return redirect("order_detail", pk=pk)


# ======================= Записи на приём =======================
class AppointmentListView(DirectoryAccess, ListView):
    model = Appointment
    template_name = "appointments/appointment_list.html"
    paginate_by = 15

    def get_queryset(self):
        qs = Appointment.objects.select_related("client", "vehicle")
        status = self.request.GET.get("status", "").strip()
        query = self.request.GET.get("q", "").strip()
        if status:
            qs = qs.filter(status=status)
        if query:
            qs = qs.filter(
                Q(client__full_name__icontains=query)
                | Q(vehicle__plate__icontains=query)
            )
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["q"] = self.request.GET.get("q", "")
        ctx["status"] = self.request.GET.get("status", "")
        ctx["status_choices"] = Appointment.Status.choices
        return ctx


class AppointmentCreateView(BaseCreate):
    model = Appointment
    form_class = AppointmentForm
    success_url = reverse_lazy("appointment_list")
    success_message = "Запись создана."
    list_url_name = "appointment_list"
    page_title = "Новая запись на приём"


class AppointmentUpdateView(BaseUpdate):
    model = Appointment
    form_class = AppointmentForm
    success_url = reverse_lazy("appointment_list")
    success_message = "Запись сохранена."
    list_url_name = "appointment_list"
    page_title = "Редактирование записи"


class AppointmentDeleteView(BaseDelete):
    model = Appointment
    success_url = reverse_lazy("appointment_list")
    list_url_name = "appointment_list"
    deleted_message = "Запись удалена."


@role_required(*MANAGER_ROLES)
@require_POST
def appointment_set_status(request, pk):
    appointment = get_object_or_404(Appointment, pk=pk)
    new_status = request.POST.get("status", "")
    valid = {
        Appointment.Status.CONFIRMED,
        Appointment.Status.CANCELLED,
        Appointment.Status.DONE,
    }
    if new_status in valid:
        appointment.status = new_status
        appointment.save(update_fields=["status"])
        messages.success(
            request, f"Статус записи: {appointment.get_status_display()}."
        )
    else:
        messages.error(request, "Недопустимый статус записи.")
    return redirect("appointment_list")


@role_required(*MANAGER_ROLES)
@require_POST
def appointment_convert(request, pk):
    """Создать заказ-наряд на основе записи (интеграция модулей)."""
    appointment = get_object_or_404(Appointment, pk=pk)
    if appointment.status in (Appointment.Status.CANCELLED, Appointment.Status.DONE):
        messages.error(request, "Из этой записи нельзя создать заказ-наряд.")
        return redirect("appointment_list")
    order = WorkOrder.objects.create(
        client=appointment.client,
        vehicle=appointment.vehicle,
        receiver=request.user,
        complaint=appointment.comment,
    )
    appointment.status = Appointment.Status.DONE
    appointment.save(update_fields=["status"])
    messages.success(request, f"Создан заказ-наряд №{order.id} по записи.")
    return redirect("order_detail", pk=order.pk)


# ======================= Отчёты =======================
def _compute_reports(request):
    """Считает все данные отчёта за период. Используется и страницей, и Excel-выгрузкой.

    Финансовые показатели — по выданным (закрытым) заказам, дата по closed_at.
    Список «все заказ-наряды» — по дате приёма (created_at), любой статус.
    """
    today = timezone.localdate()
    default_from = _months_back(today, 5)  # последние 6 месяцев

    def parse(name, default):
        try:
            return date.fromisoformat(request.GET.get(name, ""))
        except ValueError:
            return default

    date_from = parse("date_from", default_from)
    date_to = parse("date_to", today)

    issued = WorkOrder.objects.filter(
        status=WorkOrder.Status.ISSUED,
        closed_at__date__gte=date_from,
        closed_at__date__lte=date_to,
    )

    line_sum = ExpressionWrapper(
        F("price") * F("quantity"),
        output_field=DecimalField(max_digits=12, decimal_places=2),
    )
    labor_expr = ExpressionWrapper(
        F("service__labor_hours") * F("quantity"),
        output_field=DecimalField(max_digits=10, decimal_places=2),
    )

    agg = issued.aggregate(revenue=Sum("total"), orders=Count("id"), avg=Avg("total"))
    works_amount = OrderService.objects.filter(order__in=issued).aggregate(
        s=Sum("cost"))["s"] or 0
    labor_hours = OrderService.objects.filter(order__in=issued).aggregate(
        h=Sum(labor_expr))["h"] or 0
    parts_amount = OrderPart.objects.filter(order__in=issued).aggregate(
        s=Sum(line_sum))["s"] or 0
    clients_served = issued.values("client").distinct().count()
    cars_served = issued.values("vehicle").distinct().count()
    new_clients = Client.objects.filter(
        created_at__date__gte=date_from, created_at__date__lte=date_to
    ).count()

    # Средний срок ремонта (дней) — по парам created_at/closed_at
    pairs = issued.exclude(closed_at__isnull=True).values_list("created_at", "closed_at")
    if pairs:
        days = [(c - cr).total_seconds() / 86400 for cr, c in pairs]
        avg_repair_days = sum(days) / len(days)
    else:
        avg_repair_days = 0

    summary = {
        "revenue": agg["revenue"] or 0,
        "orders": agg["orders"] or 0,
        "avg": agg["avg"] or 0,
        "works_amount": works_amount,
        "parts_amount": parts_amount,
        "labor_hours": labor_hours,
        "clients_served": clients_served,
        "cars_served": cars_served,
        "new_clients": new_clients,
        "avg_repair_days": avg_repair_days,
    }

    # Выручка по месяцам
    by_month = list(
        issued.annotate(m=TruncMonth("closed_at")).values("m")
        .annotate(total=Sum("total")).order_by("m")
    )
    revenue_chart = {
        "labels": [_month_label(r["m"]) for r in by_month],
        "data": [float(r["total"]) for r in by_month],
    }

    # Структура выручки: работы vs запчасти
    structure_chart = {
        "labels": ["Работы", "Запчасти"],
        "data": [float(works_amount), float(parts_amount)],
    }

    # Топ клиентов по выручке
    top_clients = list(
        issued.values("client__full_name")
        .annotate(revenue=Sum("total"), cnt=Count("id"))
        .order_by("-revenue")[:10]
    )
    clients_chart = {
        "labels": [r["client__full_name"] for r in top_clients[:8]],
        "data": [float(r["revenue"] or 0) for r in top_clients[:8]],
    }

    # Загрузка механиков
    mechanic_rows = list(
        OrderService.objects.filter(order__in=issued)
        .values("mechanic", "mechanic__last_name", "mechanic__first_name")
        .annotate(works=Count("id"), amount=Sum("cost"))
        .order_by("-amount")
    )
    for r in mechanic_rows:
        if r["mechanic"] is None:
            r["name"] = "Не назначен"
        else:
            last = r["mechanic__last_name"] or ""
            first = (r["mechanic__first_name"] or "")[:1]
            r["name"] = (f"{last} {first}." if first else last) or "Механик"
    mechanic_chart = {
        "labels": [r["name"] for r in mechanic_rows],
        "data": [float(r["amount"] or 0) for r in mechanic_rows],
    }

    # Востребованные услуги
    service_rows = list(
        OrderService.objects.filter(order__in=issued)
        .values("service__name")
        .annotate(cnt=Sum("quantity"), revenue=Sum("cost"))
        .order_by("-cnt")[:10]
    )
    services_chart = {
        "labels": [r["service__name"] for r in service_rows],
        "data": [int(r["cnt"]) for r in service_rows],
    }

    # Движение запчастей
    parts_rows = list(
        OrderPart.objects.filter(order__in=issued)
        .values("part__name")
        .annotate(qty=Sum("quantity"), amount=Sum(line_sum))
        .order_by("-qty")[:10]
    )

    # Запчасти, заканчивающиеся на складе (операционный показатель)
    low_stock = list(Part.objects.filter(stock__lte=5).order_by("stock")[:15])

    # Все заказ-наряды за период (по дате приёма, любой статус)
    all_orders = list(
        WorkOrder.objects.select_related("client", "vehicle")
        .filter(created_at__date__gte=date_from, created_at__date__lte=date_to)
        .order_by("-created_at")
    )

    return {
        "date_from": date_from,
        "date_to": date_to,
        "summary": summary,
        "revenue_chart": revenue_chart,
        "structure_chart": structure_chart,
        "top_clients": top_clients,
        "clients_chart": clients_chart,
        "mechanic_rows": mechanic_rows,
        "mechanic_chart": mechanic_chart,
        "service_rows": service_rows,
        "services_chart": services_chart,
        "parts_rows": parts_rows,
        "low_stock": low_stock,
        "all_orders": all_orders,
    }


@role_required(User.Role.ADMIN)
def reports(request):
    data = _compute_reports(request)
    context = dict(data)
    context["date_from"] = data["date_from"].isoformat()
    context["date_to"] = data["date_to"].isoformat()
    return render(request, "reports/reports.html", context)


@role_required(User.Role.ADMIN)
def reports_export_xlsx(request):
    data = _compute_reports(request)
    return build_reports_xlsx(data)


# ======================= Печатные формы (PDF) =======================
@role_required(User.Role.ADMIN, User.Role.RECEIVER, User.Role.MECHANIC)
def order_pdf(request, pk):
    """Печатная форма заказ-наряда."""
    order = get_object_or_404(
        WorkOrder.objects.select_related("client", "vehicle", "receiver"), pk=pk
    )
    return render_order_pdf(
        order=order,
        services=order.order_services.select_related("service", "mechanic"),
        parts=order.order_parts.select_related("part"),
        doc_type="order",
        filename=f"order-{order.pk}.pdf",
    )


@role_required(User.Role.ADMIN, User.Role.RECEIVER)
def order_act_pdf(request, pk):
    """Акт выполненных работ (только для выданных заказов)."""
    order = get_object_or_404(
        WorkOrder.objects.select_related("client", "vehicle", "receiver"), pk=pk
    )
    return render_order_pdf(
        order=order,
        services=order.order_services.select_related("service", "mechanic"),
        parts=order.order_parts.select_related("part"),
        doc_type="act",
        filename=f"act-{order.pk}.pdf",
    )
