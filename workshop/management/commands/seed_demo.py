"""Наполнение базы реалистичными демонстрационными данными.

Использование:
    python manage.py seed_demo            # наполнить (если пусто)
    python manage.py seed_demo --reset    # очистить данные автосервиса и наполнить заново
"""
import random
from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone

from users.models import User
from workshop.models import (
    Appointment, Client, OrderPart, OrderService, Part,
    Service, ServiceCategory, Supplier, Vehicle, WorkOrder,
)

RU_PLATE_LETTERS = "АВЕКМНОРСТУХ"
VIN_CHARS = "ABCDEFGHJKLMNPRSTUVWXYZ0123456789"
REGIONS = [77, 97, 99, 177, 199, 777, 197, 50, 90, 150, 178, 716]

SURNAMES_M = [
    "Смирнов", "Иванов", "Кузнецов", "Попов", "Соколов", "Лебедев", "Козлов",
    "Новиков", "Морозов", "Петров", "Волков", "Соловьёв", "Васильев", "Зайцев",
    "Павлов", "Семёнов", "Голубев", "Виноградов", "Богданов", "Фёдоров",
]
FIRST_M = ["Александр", "Сергей", "Дмитрий", "Андрей", "Алексей", "Максим",
           "Евгений", "Иван", "Михаил", "Николай", "Владимир", "Павел", "Роман"]
PATR_M = ["Александрович", "Сергеевич", "Дмитриевич", "Андреевич", "Алексеевич",
          "Иванович", "Михайлович", "Николаевич", "Владимирович", "Павлович"]
FIRST_F = ["Елена", "Ольга", "Наталья", "Татьяна", "Ирина", "Мария", "Анна",
           "Екатерина", "Светлана", "Юлия"]
PATR_F = ["Александровна", "Сергеевна", "Дмитриевна", "Андреевна", "Алексеевна",
          "Ивановна", "Михайловна", "Николаевна", "Владимировна", "Павловна"]
COMPANIES = [
    "ООО «Логистик-Транс»", "ООО «СтройГарант»", "ООО «ТехноСервис»",
    "ИП Кузнецов А. А.", "ООО «ГрузАвто»", "ООО «ТаксиПарк»",
    "ООО «Доставка-Экспресс»",
]
MODELS = [
    ("Toyota", "Camry"), ("Toyota", "Corolla"), ("Toyota", "RAV4"),
    ("Kia", "Rio"), ("Kia", "Ceed"), ("Hyundai", "Solaris"), ("Hyundai", "Creta"),
    ("Lada", "Vesta"), ("Lada", "Granta"), ("Lada", "Largus"),
    ("Volkswagen", "Polo"), ("Volkswagen", "Tiguan"), ("Skoda", "Octavia"),
    ("Skoda", "Rapid"), ("Renault", "Logan"), ("Renault", "Duster"),
    ("Nissan", "Qashqai"), ("Nissan", "Almera"), ("Ford", "Focus"),
    ("Mazda", "3"), ("Chevrolet", "Niva"), ("BMW", "320i"), ("Audi", "A4"),
]
COMPANY_MODELS = [("ГАЗ", "ГАЗель Next"), ("Mercedes-Benz", "Sprinter"),
                  ("ГАЗ", "Соболь"), ("Ford", "Transit")]

SERVICES = [
    ("ТО", "Замена масла ДВС и фильтра", "1.0", "1500"),
    ("ТО", "Замена воздушного фильтра", "0.3", "500"),
    ("ТО", "Замена салонного фильтра", "0.4", "600"),
    ("ТО", "Замена топливного фильтра", "0.8", "1200"),
    ("ТО", "Комплексное ТО-1", "2.0", "4000"),
    ("ТО", "Комплексное ТО-2", "3.5", "7000"),
    ("Двигатель", "Замена ремня ГРМ", "3.5", "6000"),
    ("Двигатель", "Замена свечей зажигания", "0.8", "1200"),
    ("Двигатель", "Промывка инжектора", "1.5", "2500"),
    ("Двигатель", "Замена помпы", "2.5", "4500"),
    ("Ходовая часть", "Замена передних амортизаторов", "2.0", "3500"),
    ("Ходовая часть", "Замена задних амортизаторов", "1.8", "3200"),
    ("Ходовая часть", "Замена шаровой опоры", "1.2", "2000"),
    ("Ходовая часть", "Замена сайлентблоков", "2.5", "4000"),
    ("Ходовая часть", "Развал-схождение", "1.0", "2500"),
    ("Тормозная система", "Замена тормозных колодок (перёд)", "1.0", "1800"),
    ("Тормозная система", "Замена тормозных колодок (зад)", "1.2", "2000"),
    ("Тормозная система", "Замена тормозных дисков", "1.5", "2800"),
    ("Тормозная система", "Замена тормозной жидкости", "0.8", "1200"),
    ("Электрика", "Диагностика электрооборудования", "1.0", "1200"),
    ("Электрика", "Замена генератора", "2.0", "3500"),
    ("Электрика", "Замена стартера", "2.0", "3500"),
    ("Диагностика", "Компьютерная диагностика", "1.0", "1500"),
    ("Диагностика", "Диагностика подвески", "0.8", "1000"),
    ("Шиномонтаж", "Шиномонтаж (4 колеса)", "1.0", "2000"),
    ("Шиномонтаж", "Балансировка колёс", "0.8", "1200"),
    ("Кузовной ремонт", "Покраска элемента", "4.0", "8000"),
    ("Кузовной ремонт", "Полировка кузова", "3.0", "5000"),
]
PARTS = [
    ("Масляный фильтр", "W712/52", 35, "450"),
    ("Воздушный фильтр", "C2433", 28, "700"),
    ("Салонный фильтр", "CU2433", 22, "650"),
    ("Топливный фильтр", "KL248", 15, "900"),
    ("Свеча зажигания NGK", "BKR6E", 80, "320"),
    ("Ремень ГРМ", "CT1028", 12, "1900"),
    ("Комплект ГРМ", "KTB295", 6, "5500"),
    ("Помпа водяная", "GWP-123", 8, "2400"),
    ("Тормозные колодки перёд", "GDB1330", 18, "2800"),
    ("Тормозные колодки зад", "GDB1450", 14, "2400"),
    ("Тормозной диск", "DF4045", 10, "3200"),
    ("Тормозная жидкость DOT4", "BF-1L", 40, "450"),
    ("Амортизатор передний", "G8-1234", 9, "4200"),
    ("Амортизатор задний", "G8-5678", 7, "3800"),
    ("Шаровая опора", "SB-2201", 16, "1500"),
    ("Сайлентблок", "SB-3302", 30, "600"),
    ("Аккумулятор 60Ah", "AKB-60", 11, "6500"),
    ("Генератор", "GEN-110", 4, "8500"),
    ("Стартер", "STR-220", 3, "7500"),
    ("Антифриз G12 (5л)", "AF-5L", 25, "1100"),
    ("Моторное масло 5W-40 (4л)", "OIL-5W40", 50, "2800"),
    ("Лампа H4", "H4-12V", 60, "250"),
    ("Щётки стеклоочистителя", "WB-600", 35, "800"),
    ("Подшипник ступицы", "HB-4401", 13, "2200"),
    ("Наконечник рулевой", "TR-5501", 17, "1300"),
    ("Стойка стабилизатора", "SL-6601", 24, "900"),
    ("Радиатор охлаждения", "RAD-101", 5, "7200"),
    ("Термостат", "TH-88", 14, "950"),
    ("Датчик кислорода", "OX-220", 9, "3400"),
    ("Фильтр АКПП", "ATF-F1", 8, "1600"),
]
SUPPLIERS = [
    ("АвтоЗапчасть Опт", "+7 495 123-45-67"),
    ("Дилер-Партс", "+7 495 222-11-00"),
    ("ЕвроАвто", "+7 812 333-22-44"),
    ("Профи-Деталь", "+7 495 777-88-99"),
    ("МастерКомплект", "+7 343 555-66-77"),
]


class Command(BaseCommand):
    help = "Заполняет базу демонстрационными данными (как в рабочем автосервисе)"

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true",
                            help="Очистить данные автосервиса перед наполнением")
        parser.add_argument("--orders", type=int, default=90,
                            help="Сколько заказ-нарядов сгенерировать (по умолчанию 90)")

    def handle(self, *args, **options):
        rnd = random.Random(2024)  # фиксированное зерно — данные воспроизводимы

        if options["reset"]:
            OrderPart.objects.all().delete()
            OrderService.objects.all().delete()
            WorkOrder.objects.all().delete()
            Appointment.objects.all().delete()
            Vehicle.objects.all().delete()
            Client.objects.all().delete()
            Part.objects.all().delete()
            Service.objects.all().delete()
            ServiceCategory.objects.all().delete()
            Supplier.objects.all().delete()
            self.stdout.write(self.style.WARNING("Данные автосервиса очищены."))

        # --- Пользователи ---
        if not User.objects.filter(username="admin").exists():
            User.objects.create_superuser(
                "admin", password="admin12345",
                first_name="Администратор", role=User.Role.ADMIN)
            self.stdout.write("Создан администратор: admin / admin12345")
        # Пароль для всех демонстрационных сотрудников (для входа под разными ролями)
        DEMO_PASSWORD = "demo12345"
        for uname, last, first, role in [
            ("priemka", "Петров", "Иван", User.Role.RECEIVER),
            ("priemka2", "Орлов", "Денис", User.Role.RECEIVER),
            ("mehanik", "Сидоров", "Сергей", User.Role.MECHANIC),
            ("mehanik2", "Кузнецов", "Андрей", User.Role.MECHANIC),
            ("mehanik3", "Васильев", "Пётр", User.Role.MECHANIC),
        ]:
            user, created = User.objects.get_or_create(
                username=uname,
                defaults=dict(last_name=last, first_name=first, role=role))
            # Всегда задаём демонстрационный пароль (надёжно для входа под ролью).
            # has_usable_password() не отличает "нет пароля" от "пароль есть",
            # поэтому пароль выставляем безусловно при каждом сидинге.
            user.set_password(DEMO_PASSWORD)
            user.save(update_fields=["password"])

        receivers = list(User.objects.filter(role=User.Role.RECEIVER))
        mechanics = list(User.objects.filter(role=User.Role.MECHANIC))

        # --- Справочники ---
        cats = {}
        for _, name, *_ in [("", s[0]) for s in SERVICES]:
            if name not in cats:
                cats[name], _ = ServiceCategory.objects.get_or_create(name=name)
        services = []
        for cat, name, hours, price in SERVICES:
            srv, _ = Service.objects.get_or_create(
                name=name,
                defaults=dict(category=cats[cat], labor_hours=Decimal(hours),
                              price=Decimal(price)))
            services.append(srv)

        suppliers = []
        for name, contacts in SUPPLIERS:
            sup, _ = Supplier.objects.get_or_create(
                name=name, defaults=dict(contacts=contacts))
            suppliers.append(sup)

        parts = []
        for name, art, stock, price in PARTS:
            prt, _ = Part.objects.get_or_create(
                article=art,
                defaults=dict(name=name, stock=stock, price=Decimal(price),
                              supplier=rnd.choice(suppliers)))
            parts.append(prt)

        # --- Клиенты и автомобили ---
        used_plates = set(Vehicle.objects.values_list("plate", flat=True))

        def gen_plate():
            while True:
                p = (rnd.choice(RU_PLATE_LETTERS)
                     + f"{rnd.randint(0, 999):03d}"
                     + "".join(rnd.choice(RU_PLATE_LETTERS) for _ in range(2))
                     + str(rnd.choice(REGIONS)))
                if p not in used_plates:
                    used_plates.add(p)
                    return p

        def gen_vin():
            return "".join(rnd.choice(VIN_CHARS) for _ in range(17))

        if Client.objects.count() < 5:
            # Физлица
            for _ in range(18):
                if rnd.random() < 0.5:
                    fio = f"{rnd.choice(SURNAMES_M)} {rnd.choice(FIRST_M)} {rnd.choice(PATR_M)}"
                else:
                    fio = f"{rnd.choice(SURNAMES_M)}а {rnd.choice(FIRST_F)} {rnd.choice(PATR_F)}"
                client = Client.objects.create(
                    full_name=fio,
                    phone=f"+7 9{rnd.randint(0,9)}{rnd.randint(0,9)} "
                          f"{rnd.randint(100,999)}-{rnd.randint(10,99)}-{rnd.randint(10,99)}",
                    type=Client.Type.INDIVIDUAL)
                for _ in range(rnd.choice([1, 1, 2])):
                    brand, model = rnd.choice(MODELS)
                    Vehicle.objects.create(
                        client=client, brand=brand, model=model, plate=gen_plate(),
                        vin=gen_vin(), year=rnd.randint(2010, 2023),
                        mileage=rnd.randint(15, 250) * 1000)
            # Юрлица (автопарки)
            for name in COMPANIES:
                client = Client.objects.create(
                    full_name=name,
                    phone=f"+7 495 {rnd.randint(100,999)}-{rnd.randint(10,99)}-{rnd.randint(10,99)}",
                    type=Client.Type.COMPANY)
                for _ in range(rnd.choice([2, 3, 4])):
                    brand, model = rnd.choice(COMPANY_MODELS + MODELS)
                    Vehicle.objects.create(
                        client=client, brand=brand, model=model, plate=gen_plate(),
                        vin=gen_vin(), year=rnd.randint(2012, 2023),
                        mileage=rnd.randint(30, 300) * 1000)

        clients = list(Client.objects.all())
        vehicles_by_client = {c.id: list(c.vehicles.all()) for c in clients}

        # --- Заказ-наряды за последние ~180 дней ---
        complaints = [
            "Посторонний шум при движении", "Плановое ТО",
            "Вибрация на скорости", "Скрип при торможении",
            "Загорелся Check Engine", "Не заводится двигатель",
            "Стук в подвеске", "Течь масла", "Замена расходников",
            "Подготовка к сезону", "Проверка перед поездкой",
        ]
        now = timezone.now()
        S = WorkOrder.Status

        if WorkOrder.objects.count() == 0:
            n_orders = options["orders"]
            for _ in range(n_orders):
                client = rnd.choice(clients)
                vlist = vehicles_by_client.get(client.id) or []
                if not vlist:
                    continue
                vehicle = rnd.choice(vlist)
                offset_days = rnd.randint(0, 180)
                created = now - timedelta(days=offset_days,
                                          hours=rnd.randint(0, 8), minutes=rnd.randint(0, 59))

                # Статус в зависимости от давности
                if offset_days >= 12:
                    status = S.ISSUED
                elif offset_days >= 4:
                    status = rnd.choice([S.ISSUED, S.READY, S.IN_PROGRESS, S.WAITING_PARTS])
                else:
                    status = rnd.choice([S.NEW, S.DIAGNOSTICS, S.IN_PROGRESS, S.APPROVAL, S.READY])

                order = WorkOrder.objects.create(
                    client=client, vehicle=vehicle,
                    receiver=rnd.choice(receivers),
                    status=status,
                    complaint=rnd.choice(complaints),
                    mileage_in=(vehicle.mileage or 100000) + rnd.randint(0, 5000),
                    is_paid=(status == S.ISSUED and rnd.random() < 0.85),
                )
                # Работы (1-3)
                for srv in rnd.sample(services, rnd.randint(1, 3)):
                    OrderService.objects.create(
                        order=order, service=srv,
                        mechanic=rnd.choice(mechanics),
                        quantity=1, cost=srv.price)
                # Запчасти (0-3) — без списания склада (исторические данные)
                if rnd.random() < 0.7:
                    for prt in rnd.sample(parts, rnd.randint(1, 3)):
                        qty = rnd.choice([1, 1, 2, 4])
                        OrderPart.objects.create(
                            order=order, part=prt, quantity=qty, price=prt.price)
                order.recalculate_total()

                # Проставляем даты
                fields = {"created_at": created}
                if status == S.ISSUED:
                    fields["closed_at"] = created + timedelta(
                        days=rnd.randint(1, 5), hours=rnd.randint(0, 12))
                WorkOrder.objects.filter(pk=order.pk).update(**fields)

        # --- Записи на приём ---
        if Appointment.objects.count() == 0:
            base = now.replace(minute=0, second=0, microsecond=0)
            slots = set()
            # будущие
            for i in range(8):
                c = rnd.choice(clients)
                vl = vehicles_by_client.get(c.id) or []
                if not vl:
                    continue
                day = rnd.randint(1, 12)
                hour = rnd.choice([9, 10, 11, 13, 14, 15, 16])
                key = (day, hour)
                if key in slots:
                    continue
                slots.add(key)
                Appointment.objects.create(
                    client=c, vehicle=rnd.choice(vl),
                    scheduled_at=base + timedelta(days=day, hours=hour - base.hour),
                    status=rnd.choice([Appointment.Status.PLANNED,
                                       Appointment.Status.CONFIRMED]),
                    comment=rnd.choice(complaints))
            # прошедшие
            for i in range(5):
                c = rnd.choice(clients)
                vl = vehicles_by_client.get(c.id) or []
                if not vl:
                    continue
                Appointment.objects.create(
                    client=c, vehicle=rnd.choice(vl),
                    scheduled_at=base - timedelta(days=rnd.randint(1, 20), hours=rnd.randint(0, 6)),
                    status=rnd.choice([Appointment.Status.DONE,
                                       Appointment.Status.CANCELLED]),
                    comment=rnd.choice(complaints))

        self.stdout.write(self.style.SUCCESS(
            f"Готово. Клиентов: {Client.objects.count()}, "
            f"автомобилей: {Vehicle.objects.count()}, "
            f"услуг: {Service.objects.count()}, запчастей: {Part.objects.count()}, "
            f"заказ-нарядов: {WorkOrder.objects.count()}, "
            f"записей: {Appointment.objects.count()}."))

        self.stdout.write("")
        self.stdout.write("Учётные записи для входа:")
        self.stdout.write("  Администратор:    admin    / admin12345")
        self.stdout.write("  Мастер-приёмщик:  priemka  / demo12345")
        self.stdout.write("  Механик:          mehanik  / demo12345")
        self.stdout.write("  (также priemka2, mehanik2, mehanik3 — пароль demo12345)")
