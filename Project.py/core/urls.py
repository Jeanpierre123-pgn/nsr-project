from django.contrib.auth import views as auth_views
from django.urls import path

from .forms import LocalizedAuthenticationForm
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("register/", views.register, name="register"),
    path(
        "login/",
        auth_views.LoginView.as_view(
            template_name="core/login.html",
            authentication_form=LocalizedAuthenticationForm,
        ),
        name="login",
    ),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("market/", views.market, name="market"),
    path("farms/", views.farms, name="farms"),
    path("farms/new/", views.farm_create, name="farm_create"),
    path("farms/<int:farm_id>/edit/", views.farm_edit, name="farm_edit"),
    path("crops/", views.crops, name="crops"),
    path("crops/new/", views.crop_create, name="crop_create"),
    path("crops/<int:crop_id>/edit/", views.crop_edit, name="crop_edit"),
    path("listings/", views.listings, name="listings"),
    path("listings/new/", views.listing_create, name="listing_create"),
    path("listings/<int:listing_id>/edit/", views.listing_edit, name="listing_edit"),
    path("listings/<int:listing_id>/order/", views.place_order, name="place_order"),
    path("demands/", views.demands, name="demands"),
    path("demands/new/", views.demand_create, name="demand_create"),
    path("demands/<int:demand_id>/edit/", views.demand_edit, name="demand_edit"),
    path("matches/", views.matches, name="matches"),
    path("orders/", views.orders, name="orders"),
    path("orders/<int:order_id>/transport/", views.transport_create, name="transport_create"),
    path("orders/<int:order_id>/<str:action>/", views.order_action, name="order_action"),
    path("transport/", views.transport, name="transport"),
    path(
        "transport/<int:request_id>/<str:action>/",
        views.transport_action,
        name="transport_action",
    ),
    path("storage/", views.storage, name="storage"),
    path("storage/new/", views.storage_create, name="storage_create"),
    path("storage/<int:record_id>/inspect/", views.storage_inspect, name="storage_inspect"),
    path("finances/", views.finance, name="finance"),
    path("notifications/", views.notifications, name="notifications"),
    path("weather/", views.weather, name="weather"),
]
