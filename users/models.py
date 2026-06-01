from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Сотрудник автосервиса — пользователь системы (приёмщик, механик, администратор)."""

    class Role(models.TextChoices):
        ADMIN = "admin", "Администратор"
        RECEIVER = "receiver", "Мастер-приёмщик"
        MECHANIC = "mechanic", "Механик"

    middle_name = models.CharField("Отчество", max_length=150, blank=True)
    phone = models.CharField("Телефон", max_length=20, blank=True)
    role = models.CharField(
        "Роль", max_length=20, choices=Role.choices, default=Role.RECEIVER
    )

    class Meta:
        verbose_name = "Сотрудник"
        verbose_name_plural = "Сотрудники"

    @property
    def full_name(self):
        parts = [self.last_name, self.first_name, self.middle_name]
        return " ".join(p for p in parts if p) or self.username

    @property
    def is_admin(self):
        return self.is_superuser or self.role == self.Role.ADMIN

    @property
    def is_receiver(self):
        return self.role == self.Role.RECEIVER

    @property
    def is_mechanic(self):
        return self.role == self.Role.MECHANIC

    def __str__(self):
        return f"{self.full_name} ({self.get_role_display()})"
