from django.conf import settings
from django.db import models
from django.utils import timezone


class Client(models.Model):
    """Клиент автосервиса."""

    class Type(models.TextChoices):
        INDIVIDUAL = "individual", "Физическое лицо"
        COMPANY = "company", "Юридическое лицо"

    full_name = models.CharField("ФИО / Название", max_length=255)
    phone = models.CharField("Телефон", max_length=20)
    email = models.EmailField("Email", blank=True)
    type = models.CharField(
        "Тип", max_length=20, choices=Type.choices, default=Type.INDIVIDUAL
    )
    created_at = models.DateTimeField("Дата регистрации", auto_now_add=True)

    class Meta:
        verbose_name = "Клиент"
        verbose_name_plural = "Клиенты"
        ordering = ["full_name"]

    def __str__(self):
        return self.full_name


class Vehicle(models.Model):
    """Автомобиль клиента."""

    client = models.ForeignKey(
        Client, on_delete=models.CASCADE, related_name="vehicles",
        verbose_name="Клиент",
    )
    brand = models.CharField("Марка", max_length=100)
    model = models.CharField("Модель", max_length=100)
    plate = models.CharField("Гос. номер", max_length=20)
    vin = models.CharField("VIN", max_length=17, blank=True)
    year = models.PositiveIntegerField("Год выпуска", null=True, blank=True)
    mileage = models.PositiveIntegerField("Пробег, км", null=True, blank=True)

    class Meta:
        verbose_name = "Автомобиль"
        verbose_name_plural = "Автомобили"
        ordering = ["brand", "model"]

    def __str__(self):
        return f"{self.brand} {self.model} ({self.plate})"


class ServiceCategory(models.Model):
    """Категория услуг (ТО, двигатель, ходовая, электрика и т. д.)."""

    name = models.CharField("Название", max_length=120, unique=True)

    class Meta:
        verbose_name = "Категория услуг"
        verbose_name_plural = "Категории услуг"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Service(models.Model):
    """Услуга (вид работ) с нормо-часами и ценой."""

    category = models.ForeignKey(
        ServiceCategory, on_delete=models.PROTECT, related_name="services",
        verbose_name="Категория",
    )
    name = models.CharField("Наименование", max_length=255)
    labor_hours = models.DecimalField(
        "Нормо-часы", max_digits=5, decimal_places=2, default=1
    )
    price = models.DecimalField("Цена, ₽", max_digits=10, decimal_places=2)

    class Meta:
        verbose_name = "Услуга"
        verbose_name_plural = "Услуги"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Supplier(models.Model):
    """Поставщик запчастей."""

    name = models.CharField("Название", max_length=255)
    contacts = models.CharField("Контакты", max_length=255, blank=True)

    class Meta:
        verbose_name = "Поставщик"
        verbose_name_plural = "Поставщики"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Part(models.Model):
    """Запчасть на складе."""

    supplier = models.ForeignKey(
        Supplier, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="parts", verbose_name="Поставщик",
    )
    name = models.CharField("Наименование", max_length=255)
    article = models.CharField("Артикул", max_length=100, blank=True)
    stock = models.PositiveIntegerField("Остаток на складе", default=0)
    price = models.DecimalField("Цена продажи, ₽", max_digits=10, decimal_places=2)

    class Meta:
        verbose_name = "Запчасть"
        verbose_name_plural = "Запчасти"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.article})" if self.article else self.name


class WorkOrder(models.Model):
    """Заказ-наряд — центральная сущность системы."""

    class Status(models.TextChoices):
        NEW = "new", "Принят"
        DIAGNOSTICS = "diagnostics", "Диагностика"
        APPROVAL = "approval", "Согласование"
        IN_PROGRESS = "in_progress", "В работе"
        WAITING_PARTS = "waiting_parts", "Ожидание запчастей"
        READY = "ready", "Готов"
        ISSUED = "issued", "Выдан"

    client = models.ForeignKey(
        Client, on_delete=models.PROTECT, related_name="orders",
        verbose_name="Клиент",
    )
    vehicle = models.ForeignKey(
        Vehicle, on_delete=models.PROTECT, related_name="orders",
        verbose_name="Автомобиль",
    )
    receiver = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name="received_orders", verbose_name="Мастер-приёмщик",
    )
    status = models.CharField(
        "Статус", max_length=20, choices=Status.choices, default=Status.NEW
    )
    complaint = models.TextField("Жалоба клиента", blank=True)
    mileage_in = models.PositiveIntegerField(
        "Пробег при приёме, км", null=True, blank=True
    )
    total = models.DecimalField(
        "Итоговая сумма, ₽", max_digits=12, decimal_places=2,
        default=0, editable=False,
    )
    is_paid = models.BooleanField("Оплачен", default=False)
    created_at = models.DateTimeField("Дата приёма", auto_now_add=True)
    closed_at = models.DateTimeField("Дата выдачи", null=True, blank=True)

    class Meta:
        verbose_name = "Заказ-наряд"
        verbose_name_plural = "Заказ-наряды"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Заказ-наряд №{self.pk} — {self.vehicle}"

    @property
    def services_total(self):
        return sum((item.cost for item in self.order_services.all()), 0)

    @property
    def parts_total(self):
        return sum((item.line_sum for item in self.order_parts.all()), 0)

    def recalculate_total(self, save=True):
        """Пересчитать итоговую сумму: работы + запчасти."""
        self.total = self.services_total + self.parts_total
        if save:
            self.save(update_fields=["total"])
        return self.total

    @property
    def status_color(self):
        """Bootstrap-класс для бейджа статуса."""
        return {
            "new": "secondary",
            "diagnostics": "info",
            "approval": "warning",
            "in_progress": "primary",
            "waiting_parts": "warning",
            "ready": "success",
            "issued": "dark",
        }.get(self.status, "secondary")

    def allowed_next_statuses(self):
        """Допустимые переходы статуса (жизненный цикл заказ-наряда)."""
        S = WorkOrder.Status
        transitions = {
            S.NEW: [S.DIAGNOSTICS, S.IN_PROGRESS],
            S.DIAGNOSTICS: [S.APPROVAL, S.IN_PROGRESS],
            S.APPROVAL: [S.IN_PROGRESS, S.WAITING_PARTS],
            S.IN_PROGRESS: [S.WAITING_PARTS, S.READY],
            S.WAITING_PARTS: [S.IN_PROGRESS],
            S.READY: [S.ISSUED, S.IN_PROGRESS],
            S.ISSUED: [],
        }
        return transitions.get(self.status, [])


class OrderService(models.Model):
    """Позиция работ в заказ-наряде (связка заказ ↔ услуга)."""

    order = models.ForeignKey(
        WorkOrder, on_delete=models.CASCADE, related_name="order_services",
        verbose_name="Заказ-наряд",
    )
    service = models.ForeignKey(
        Service, on_delete=models.PROTECT, verbose_name="Услуга",
    )
    mechanic = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="performed_works",
        verbose_name="Механик-исполнитель",
    )
    quantity = models.PositiveIntegerField("Количество", default=1)
    cost = models.DecimalField("Стоимость, ₽", max_digits=10, decimal_places=2)

    class Meta:
        verbose_name = "Работа в заказе"
        verbose_name_plural = "Работы в заказе"

    def __str__(self):
        return f"{self.service} × {self.quantity}"


class OrderPart(models.Model):
    """Позиция запчастей в заказ-наряде (связка заказ ↔ запчасть)."""

    order = models.ForeignKey(
        WorkOrder, on_delete=models.CASCADE, related_name="order_parts",
        verbose_name="Заказ-наряд",
    )
    part = models.ForeignKey(
        Part, on_delete=models.PROTECT, verbose_name="Запчасть",
    )
    quantity = models.PositiveIntegerField("Количество", default=1)
    price = models.DecimalField(
        "Цена за ед. на момент продажи, ₽", max_digits=10, decimal_places=2
    )

    class Meta:
        verbose_name = "Запчасть в заказе"
        verbose_name_plural = "Запчасти в заказе"

    def __str__(self):
        return f"{self.part} × {self.quantity}"

    @property
    def line_sum(self):
        return self.price * self.quantity


class Appointment(models.Model):
    """Предварительная запись на приём."""

    class Status(models.TextChoices):
        PLANNED = "planned", "Запланирована"
        CONFIRMED = "confirmed", "Подтверждена"
        DONE = "done", "Завершена"
        CANCELLED = "cancelled", "Отменена"

    client = models.ForeignKey(
        Client, on_delete=models.CASCADE, related_name="appointments",
        verbose_name="Клиент",
    )
    vehicle = models.ForeignKey(
        Vehicle, on_delete=models.CASCADE, related_name="appointments",
        verbose_name="Автомобиль",
    )
    scheduled_at = models.DateTimeField("Дата и время")
    status = models.CharField(
        "Статус", max_length=20, choices=Status.choices, default=Status.PLANNED
    )
    comment = models.CharField("Комментарий", max_length=255, blank=True)

    class Meta:
        verbose_name = "Запись на приём"
        verbose_name_plural = "Записи на приём"
        ordering = ["scheduled_at"]

    # Длительность одного слота приёма (для контроля занятости), мин.
    SLOT_MINUTES = 60

    def __str__(self):
        return f"{self.client} — {self.scheduled_at:%d.%m.%Y %H:%M}"

    @property
    def status_color(self):
        """Bootstrap-класс для бейджа статуса записи."""
        return {
            "planned": "secondary",
            "confirmed": "primary",
            "done": "success",
            "cancelled": "danger",
        }.get(self.status, "secondary")

    @property
    def is_past(self):
        return self.scheduled_at < timezone.now()

    @property
    def is_overdue(self):
        """Время приёма прошло, а запись ещё не завершена и не отменена."""
        return self.is_past and self.status in (
            self.Status.PLANNED, self.Status.CONFIRMED
        )
