from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("soon/", views.soon, name="soon"),

    # Аутентификация
    path(
        "login/",
        auth_views.LoginView.as_view(template_name="registration/login.html"),
        name="login",
    ),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),

    # Клиенты
    path("clients/", views.ClientListView.as_view(), name="client_list"),
    path("clients/add/", views.ClientCreateView.as_view(), name="client_create"),
    path("clients/<int:pk>/", views.ClientDetailView.as_view(), name="client_detail"),
    path("clients/<int:pk>/edit/", views.ClientUpdateView.as_view(), name="client_update"),
    path("clients/<int:pk>/delete/", views.ClientDeleteView.as_view(), name="client_delete"),

    # Автомобили
    path("vehicles/", views.VehicleListView.as_view(), name="vehicle_list"),
    path("vehicles/add/", views.VehicleCreateView.as_view(), name="vehicle_create"),
    path("vehicles/<int:pk>/edit/", views.VehicleUpdateView.as_view(), name="vehicle_update"),
    path("vehicles/<int:pk>/delete/", views.VehicleDeleteView.as_view(), name="vehicle_delete"),

    # Категории услуг
    path("categories/", views.CategoryListView.as_view(), name="category_list"),
    path("categories/add/", views.CategoryCreateView.as_view(), name="category_create"),
    path("categories/<int:pk>/edit/", views.CategoryUpdateView.as_view(), name="category_update"),
    path("categories/<int:pk>/delete/", views.CategoryDeleteView.as_view(), name="category_delete"),

    # Услуги
    path("services/", views.ServiceListView.as_view(), name="service_list"),
    path("services/add/", views.ServiceCreateView.as_view(), name="service_create"),
    path("services/<int:pk>/edit/", views.ServiceUpdateView.as_view(), name="service_update"),
    path("services/<int:pk>/delete/", views.ServiceDeleteView.as_view(), name="service_delete"),

    # Поставщики
    path("suppliers/", views.SupplierListView.as_view(), name="supplier_list"),
    path("suppliers/add/", views.SupplierCreateView.as_view(), name="supplier_create"),
    path("suppliers/<int:pk>/edit/", views.SupplierUpdateView.as_view(), name="supplier_update"),
    path("suppliers/<int:pk>/delete/", views.SupplierDeleteView.as_view(), name="supplier_delete"),

    # Заказ-наряды
    path("orders/", views.WorkOrderListView.as_view(), name="order_list"),
    path("orders/add/", views.WorkOrderCreateView.as_view(), name="order_create"),
    path("orders/<int:pk>/", views.WorkOrderDetailView.as_view(), name="order_detail"),
    path("orders/<int:pk>/edit/", views.WorkOrderUpdateView.as_view(), name="order_update"),
    path("orders/<int:pk>/delete/", views.WorkOrderDeleteView.as_view(), name="order_delete"),
    path("orders/<int:pk>/status/", views.order_change_status, name="order_change_status"),
    path("orders/<int:pk>/paid/", views.order_toggle_paid, name="order_toggle_paid"),
    path("orders/<int:pk>/pdf/", views.order_pdf, name="order_pdf"),
    path("orders/<int:pk>/act/", views.order_act_pdf, name="order_act_pdf"),
    path("orders/<int:pk>/services/add/", views.order_add_service, name="order_add_service"),
    path("orders/<int:pk>/services/<int:item_pk>/delete/", views.order_delete_service, name="order_delete_service"),
    path("orders/<int:pk>/parts/add/", views.order_add_part, name="order_add_part"),
    path("orders/<int:pk>/parts/<int:item_pk>/delete/", views.order_delete_part, name="order_delete_part"),

    # Запчасти (склад)
    path("parts/", views.PartListView.as_view(), name="part_list"),
    path("parts/add/", views.PartCreateView.as_view(), name="part_create"),
    path("parts/<int:pk>/edit/", views.PartUpdateView.as_view(), name="part_update"),
    path("parts/<int:pk>/delete/", views.PartDeleteView.as_view(), name="part_delete"),

    # Записи на приём
    path("appointments/", views.AppointmentListView.as_view(), name="appointment_list"),
    path("appointments/add/", views.AppointmentCreateView.as_view(), name="appointment_create"),
    path("appointments/<int:pk>/edit/", views.AppointmentUpdateView.as_view(), name="appointment_update"),
    path("appointments/<int:pk>/delete/", views.AppointmentDeleteView.as_view(), name="appointment_delete"),
    path("appointments/<int:pk>/status/", views.appointment_set_status, name="appointment_set_status"),
    path("appointments/<int:pk>/convert/", views.appointment_convert, name="appointment_convert"),

    # Отчёты
    path("reports/", views.reports, name="reports"),
    path("reports/export.xlsx", views.reports_export_xlsx, name="reports_export_xlsx"),
]
