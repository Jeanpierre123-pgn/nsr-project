from datetime import timedelta
from decimal import Decimal
from functools import wraps
import os

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q, Sum
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext as _

from .forms import (
    BuyerDemandForm, ConfirmAgreementForm, CropRecordForm, ExpenseForm, FarmForm,
    InspectionForm, ListingForm, PlaceOrderForm, RegisterForm, StorageRecordForm,
    TransportRequestForm,
)
from .models import (
    BuyerDemand, CommunityComment, CommunityPost, CropRecord, Expense, Farm,
    Notification, Order, ProductListing, Profile, StorageRecord, TransportRequest,
)


def current_role(user):
    return Profile.objects.filter(user=user).values_list("role", flat=True).first()


def role_required(*roles):
    def decorator(view_func):
        @login_required
        @wraps(view_func)
        def wrapped(request, *args, **kwargs):
            if current_role(request.user) in roles:
                return view_func(request, *args, **kwargs)
            return HttpResponseForbidden(_("Your account does not have permission to access this page."))
        return wrapped
    return decorator


def notify_order_participants(order, recipients, title, message):
    unique_recipients = {recipient.pk: recipient for recipient in recipients if recipient is not None}
    Notification.objects.bulk_create(
        [
            Notification(user=recipient, title=title, message=message)
            for recipient in unique_recipients.values()
        ]
    )


def home(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    return render(request, "core/home.html")


def register(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    form = RegisterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            user = form.save()
        login(request, user)
        messages.success(request, _("Your account is ready. Welcome to Smart AgroConnect Rwanda."))
        return redirect("dashboard")
    return render(request, "core/form.html", {
        "form": form, "title": _("Create your account"),
        "intro": _("Join as a farmer, buyer or transporter."), "submit_label": _("Create account"),
    })


def demo_login(request):
    """Create a safe local demo account so judges can explore without registration."""
    if not settings.DEMO_LOGIN_ENABLED:
        return HttpResponseForbidden(_("Demo access is disabled in this environment."))
    role = request.GET.get("role", Profile.Role.FARMER)
    if role not in Profile.Role.values:
        role = Profile.Role.FARMER
    account = {
        Profile.Role.FARMER: ("demo_farmer", "Demo Farmer"),
        Profile.Role.BUYER: ("demo_buyer", "Demo Buyer"),
        Profile.Role.TRANSPORTER: ("demo_transporter", "Demo Transporter"),
    }[role]
    username, display_name = account
    user, created = User.objects.get_or_create(
        username=username,
        defaults={"first_name": display_name.split()[1], "last_name": "Account"},
    )
    user.set_password("AgroConnectDemo2026!")
    user.save(update_fields=["password", "first_name", "last_name"])
    Profile.objects.get_or_create(
        user=user,
        defaults={
            "role": role,
            "phone": "+250 700 000 000",
            "district": "Demo district",
            "sector": "Demo sector",
            "cell": "Demo cell",
            "village": "Demo village",
            "vehicle_type": "Demo truck" if role == Profile.Role.TRANSPORTER else "",
            "vehicle_capacity": 1000 if role == Profile.Role.TRANSPORTER else None,
        },
    )
    login(request, user, backend="django.contrib.auth.backends.ModelBackend")
    messages.success(request, _(f"You are signed in as the demo {role} account."))
    return redirect("dashboard")


@login_required
def dashboard(request):
    role = current_role(request.user)
    if request.user.is_staff and role is None:
        context = {
            "role": "administrator", "profile": None,
            "admin_counts": {
                "farmers": Profile.objects.filter(role=Profile.Role.FARMER).count(),
                "buyers": Profile.objects.filter(role=Profile.Role.BUYER).count(),
                "transporters": Profile.objects.filter(role=Profile.Role.TRANSPORTER).count(),
                "listings": ProductListing.objects.filter(status=ProductListing.Status.AVAILABLE).count(),
                "orders": Order.objects.count(),
            },
        }
    elif role == Profile.Role.FARMER:
        profile = request.user.profile
        crops = CropRecord.objects.filter(farm__farmer=profile).select_related("farm")
        storage = StorageRecord.objects.filter(farmer=profile)
        context = {
            "role": role, "profile": profile,
            "farm_count": Farm.objects.filter(farmer=profile).count(),
            "crop_count": crops.count(),
            "listing_count": ProductListing.objects.filter(
                farmer=profile, status=ProductListing.Status.AVAILABLE
            ).count(),
            "orders": Order.objects.filter(farmer=profile).select_related("listing", "buyer__user")[:5],
            "crops": crops[:5],
            "storage_alerts": [(record, record.reminders) for record in storage if record.reminders],
            "notifications": profile.notifications.filter(is_read=False)[:5],
        }
    elif role == Profile.Role.BUYER:
        profile = request.user.profile
        context = {
            "role": role, "profile": profile,
            "open_demands": BuyerDemand.objects.filter(
                buyer=profile, status=BuyerDemand.Status.OPEN
            ).count(),
            "orders": Order.objects.filter(buyer=profile).select_related("listing", "farmer__user")[:5],
            "listings": ProductListing.objects.filter(
                status=ProductListing.Status.AVAILABLE
            ).select_related("farmer__user")[:5],
            "notifications": profile.notifications.filter(is_read=False)[:5],
        }
    elif role == Profile.Role.TRANSPORTER:
        profile = request.user.profile
        context = {
            "role": role, "profile": profile,
            "open_transport": TransportRequest.objects.filter(
                status=TransportRequest.Status.OPEN
            ).count(),
            "assignments": TransportRequest.objects.filter(
                transporter=profile
            ).select_related("order", "requester__user")[:5],
        }
    else:
        return HttpResponseForbidden(_("This account has no active application role."))
    return render(request, "core/dashboard.html", context)


@role_required(Profile.Role.FARMER)
def farms(request):
    return render(request, "core/list.html", {
        "title": _("Your farms"), "intro": _("Keep your farm locations and crop records together."),
        "records": Farm.objects.filter(farmer=request.user.profile),
        "create_url": "farm_create", "empty_text": _("Add a farm to start recording crops."),
        "record_type": "farm", "edit_url": "farm_edit",
    })


@role_required(Profile.Role.FARMER)
def farm_create(request):
    form = FarmForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        farm = form.save(commit=False)
        farm.farmer = request.user.profile
        farm.save()
        messages.success(request, _("Farm added."))
        return redirect("farms")
    return render(request, "core/form.html", {
        "form": form, "title": _("Add a farm"), "submit_label": _("Save farm"),
    })


@role_required(Profile.Role.FARMER)
def farm_edit(request, farm_id):
    farm = get_object_or_404(Farm, pk=farm_id, farmer=request.user.profile)
    form = FarmForm(request.POST or None, instance=farm)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, _("Farm details updated."))
        return redirect("farms")
    return render(request, "core/form.html", {
        "form": form, "title": _("Update farm"), "submit_label": _("Save changes"),
    })


@role_required(Profile.Role.FARMER)
def crops(request):
    return render(request, "core/list.html", {
        "title": _("Crop calendar"),
        "intro": _("Harvest dates are calendar estimates. Inspect crops in the field before confirming readiness."),
        "records": CropRecord.objects.filter(
            farm__farmer=request.user.profile
        ).select_related("farm"),
        "create_url": "crop_create", "empty_text": _("Add a farm before creating a crop record."),
        "record_type": "crop", "edit_url": "crop_edit",
    })


@role_required(Profile.Role.FARMER)
def crop_create(request):
    form = CropRecordForm(request.POST or None, farmer=request.user.profile)
    if request.method == "POST" and form.is_valid():
        crop = form.save()
        messages.success(
            request,
            _("Crop saved. Estimated harvest date: %(date)s.") % {
                "date": f"{crop.estimated_harvest_date:%d %b %Y}"
            },
        )
        return redirect("crops")
    return render(request, "core/form.html", {
        "form": form, "title": _("Record a crop"),
        "intro": _("Use a growing duration supported by local crop guidance; the estimate does not confirm readiness."),
        "submit_label": _("Save crop"),
    })


@role_required(Profile.Role.FARMER)
def crop_edit(request, crop_id):
    crop = get_object_or_404(CropRecord, pk=crop_id, farm__farmer=request.user.profile)
    form = CropRecordForm(request.POST or None, instance=crop, farmer=request.user.profile)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, _("Crop details updated."))
        return redirect("crops")
    return render(request, "core/form.html", {
        "form": form, "title": _("Update crop record"), "submit_label": _("Save changes"),
    })


@role_required(Profile.Role.FARMER)
def listings(request):
    return render(request, "core/list.html", {
        "title": _("Your produce listings"),
        "intro": _("Publish expected or available produce for buyers to discover."),
        "records": ProductListing.objects.filter(
            farmer=request.user.profile
        ).select_related("crop_record"),
        "create_url": "listing_create", "empty_text": _("You have not published produce yet."),
        "record_type": "listing", "edit_url": "listing_edit",
    })


@role_required(Profile.Role.FARMER)
def listing_create(request):
    form = ListingForm(request.POST or None, farmer=request.user.profile)
    if request.method == "POST" and form.is_valid():
        listing = form.save(commit=False)
        listing.farmer = request.user.profile
        listing.save()
        messages.success(request, _("Your produce listing is now visible to buyers."))
        return redirect("listings")
    return render(request, "core/form.html", {
        "form": form, "title": _("Publish produce"), "submit_label": _("Publish listing"),
    })


@role_required(Profile.Role.FARMER)
def listing_edit(request, listing_id):
    listing = get_object_or_404(ProductListing, pk=listing_id, farmer=request.user.profile)
    form = ListingForm(request.POST or None, instance=listing, farmer=request.user.profile)
    if request.method == "POST" and form.is_valid():
        reserved = listing.orders.exclude(
            status__in=[Order.Status.REJECTED, Order.Status.CANCELLED]
        ).aggregate(total=Sum("quantity"))["total"] or Decimal("0")
        if form.cleaned_data["quantity"] < reserved:
            form.add_error("quantity", f"Quantity cannot be lower than {reserved} already committed to orders.")
        else:
            form.save()
            messages.success(request, _("Produce listing updated."))
            return redirect("listings")
    return render(request, "core/form.html", {
        "form": form, "title": _("Update produce listing"), "submit_label": _("Save changes"),
    })


def market(request):
    listings = ProductListing.objects.filter(
        status=ProductListing.Status.AVAILABLE,
        expected_available_date__gte=timezone.localdate() - timedelta(days=14),
    ).select_related("farmer__user")
    available = [listing for listing in listings if listing.available_quantity > 0]
    return render(request, "core/market.html", {"listings": available})


@role_required(Profile.Role.BUYER)
def place_order(request, listing_id):
    with transaction.atomic():
        listing = get_object_or_404(
            ProductListing.objects.select_for_update().select_related("farmer__user"),
            pk=listing_id, status=ProductListing.Status.AVAILABLE,
        )
        reserved = listing.orders.exclude(
            status__in=[Order.Status.REJECTED, Order.Status.CANCELLED]
        ).aggregate(total=Sum("quantity"))["total"] or Decimal("0")
        remaining = listing.quantity - reserved
        form = PlaceOrderForm(request.POST or None)
        if request.method == "POST" and form.is_valid():
            quantity = form.cleaned_data["quantity"]
            if quantity > remaining:
                message = _("Only %(quantity)s %(unit)s remain available.") % {
                    "quantity": remaining, "unit": listing.quantity_unit
                }
                form.add_error("quantity", message)
            else:
                order = form.save(commit=False)
                order.buyer = request.user.profile
                order.farmer = listing.farmer
                order.listing = listing
                order.save()
                Notification.objects.create(
                    user=listing.farmer, title="New buyer order",
                    message=f"{request.user.get_full_name() or request.user.username} requested "
                    f"{quantity} {listing.quantity_unit} of {listing.product_name}.",
                )
                messages.success(request, _("Order request sent to the farmer for review."))
                return redirect("orders")
    return render(request, "core/form.html", {
        "form": form, "title": _("Request %(product)s") % {"product": listing.product_name},
        "intro": _("Set the requested quantity, proposed price, collection date, and delivery location. Prices are proposals until agreed."),
        "submit_label": _("Send order request"),
    })


@role_required(Profile.Role.BUYER)
def demands(request):
    return render(request, "core/list.html", {
        "title": _("Your buyer demands"),
        "intro": _("Post current or future produce requirements to find potential suppliers."),
        "records": BuyerDemand.objects.filter(buyer=request.user.profile),
        "create_url": "demand_create",
        "empty_text": _("Create a demand to compare your needs with farmer listings."),
        "record_type": "demand", "edit_url": "demand_edit",
    })


@role_required(Profile.Role.BUYER)
def demand_create(request):
    form = BuyerDemandForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        demand = form.save(commit=False)
        demand.buyer = request.user.profile
        demand.save()
        messages.success(request, _("Demand saved. Potential matches are ready to review."))
        return redirect("matches")
    return render(request, "core/form.html", {
        "form": form, "title": _("Post a buyer demand"), "submit_label": _("Save demand"),
    })


@role_required(Profile.Role.BUYER)
def demand_edit(request, demand_id):
    demand = get_object_or_404(BuyerDemand, pk=demand_id, buyer=request.user.profile)
    form = BuyerDemandForm(request.POST or None, instance=demand)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, _("Buyer demand updated."))
        return redirect("demands")
    return render(request, "core/form.html", {
        "form": form, "title": _("Update buyer demand"), "submit_label": _("Save changes"),
    })


def find_matches(demand):
    listings = ProductListing.objects.filter(
        status=ProductListing.Status.AVAILABLE,
        product_name__iexact=demand.product_name,
        quantity_unit__iexact=demand.quantity_unit,
        quantity__gte=demand.required_quantity,
        expected_available_date__range=(
            demand.needed_by_date - timedelta(days=14),
            demand.needed_by_date + timedelta(days=14),
        ),
    ).select_related("farmer__user")
    if demand.district:
        listings = listings.filter(district__iexact=demand.district)
    matches = []
    for listing in listings:
        if listing.available_quantity < demand.required_quantity:
            continue
        if demand.target_price_per_unit is not None and listing.price_per_unit is not None:
            if listing.price_per_unit > demand.target_price_per_unit and not listing.negotiable:
                continue
        matches.append(listing)
    return matches


@role_required(Profile.Role.BUYER)
def matches(request):
    open_demands = BuyerDemand.objects.filter(
        buyer=request.user.profile, status=BuyerDemand.Status.OPEN
    )
    return render(request, "core/matches.html", {
        "demand_matches": [(demand, find_matches(demand)) for demand in open_demands],
    })


@login_required
def orders(request):
    profile = Profile.objects.filter(user=request.user).first()
    if request.user.is_staff and profile is None:
        records = Order.objects.select_related("listing", "buyer__user", "farmer__user")
    elif profile and profile.role == Profile.Role.FARMER:
        records = Order.objects.filter(farmer=profile).select_related("listing", "buyer__user")
    elif profile and profile.role == Profile.Role.BUYER:
        records = Order.objects.filter(buyer=profile).select_related("listing", "farmer__user")
    else:
        return HttpResponseForbidden(_("Only farmers and buyers can view order agreements."))
    return render(request, "core/orders.html", {"orders": records})


@login_required
def order_action(request, order_id, action):
    if request.method != "POST":
        return HttpResponseForbidden(_("Order changes must be submitted with POST."))
    profile = Profile.objects.filter(user=request.user).first()
    with transaction.atomic():
        order = get_object_or_404(
            Order.objects.select_for_update().select_related("buyer__user", "farmer__user"),
            pk=order_id,
        )
        is_farmer = profile is not None and order.farmer_id == profile.pk
        is_buyer = profile is not None and order.buyer_id == profile.pk
        is_assigned_transporter = profile is not None and order.transport_requests.filter(
            transporter=profile
        ).exists()

        if action == "accept" and is_farmer and order.status == Order.Status.PENDING:
            order.status = Order.Status.ACCEPTED
        elif action == "reject" and is_farmer and order.status == Order.Status.PENDING:
            order.status = Order.Status.REJECTED
        elif action == "confirm" and is_farmer and order.status == Order.Status.ACCEPTED:
            form = ConfirmAgreementForm(request.POST)
            if not form.is_valid():
                messages.error(request, _("Enter a valid agreed price before confirming."))
                return redirect("orders")
            order.agreed_unit_price = form.cleaned_data["agreed_unit_price"]
            order.status = Order.Status.CONFIRMED
        elif action == "ready" and is_farmer and order.status == Order.Status.CONFIRMED:
            order.status = Order.Status.READY
        elif action == "cancel" and is_buyer and order.status in (
            Order.Status.PENDING, Order.Status.ACCEPTED, Order.Status.CONFIRMED,
        ):
            order.status = Order.Status.CANCELLED
            order.transport_requests.exclude(
                status__in=[TransportRequest.Status.PICKED_UP, TransportRequest.Status.DELIVERED]
            ).update(status=TransportRequest.Status.CANCELLED)
        elif action == "transit" and is_assigned_transporter and order.status == Order.Status.READY:
            order.status = Order.Status.IN_TRANSIT
            order.transport_requests.filter(
                transporter=profile, status=TransportRequest.Status.ASSIGNED
            ).update(status=TransportRequest.Status.PICKED_UP)
        elif action == "delivered" and is_assigned_transporter and order.status == Order.Status.IN_TRANSIT:
            order.status = Order.Status.DELIVERED
            order.transport_requests.filter(
                transporter=profile, status=TransportRequest.Status.PICKED_UP
            ).update(status=TransportRequest.Status.DELIVERED)
        else:
            return HttpResponseForbidden(_("That order transition is not permitted."))
        order.save()
        actor_name = request.user.get_full_name() or request.user.username
        message = (
            f"Order #{order.pk} for {order.listing.product_name} was updated to "
            f"{order.get_status_display()} by {actor_name}."
        )
        if is_farmer:
            recipients = [order.buyer]
        elif is_buyer:
            recipients = [order.farmer]
        else:
            recipients = [order.buyer, order.farmer]
        notify_order_participants(
            order, recipients, f"Order #{order.pk} update", message
        )
    messages.success(
        request,
        _("Order #%(number)s updated to %(status)s.") % {
            "number": order.pk,
            "status": order.get_status_display(),
        },
    )
    return redirect("orders")


@login_required
def transport(request):
    profile = Profile.objects.filter(user=request.user).first()
    if request.user.is_staff and profile is None:
        records = TransportRequest.objects.select_related(
            "order", "requester__user", "transporter__user"
        )
    elif profile and profile.role == Profile.Role.TRANSPORTER:
        records = TransportRequest.objects.filter(
            Q(status=TransportRequest.Status.OPEN) | Q(transporter=profile)
        ).select_related("order", "requester__user", "transporter__user")
    elif profile:
        records = TransportRequest.objects.filter(
            requester=profile
        ).select_related("order", "transporter__user")
    else:
        return HttpResponseForbidden(_("Transport requests require a registered platform role."))
    return render(request, "core/transport.html", {"requests": records})


@login_required
def transport_create(request, order_id):
    profile = Profile.objects.filter(user=request.user).first()
    order = get_object_or_404(Order, pk=order_id)
    if profile is None or profile.pk not in (order.buyer_id, order.farmer_id):
        return HttpResponseForbidden(_("Only the buyer or farmer in this order can request transport."))
    if order.status not in (Order.Status.CONFIRMED, Order.Status.READY):
        messages.error(request, _("Confirm the order agreement before arranging transport."))
        return redirect("orders")
    if order.transport_requests.exclude(status=TransportRequest.Status.CANCELLED).exists():
        messages.info(request, _("A transport request already exists for this order."))
        return redirect("transport")
    form = TransportRequestForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        transport_request = form.save(commit=False)
        transport_request.order = order
        transport_request.requester = profile
        transport_request.save()
        messages.success(request, _("Transport request posted for registered transporters."))
        return redirect("transport")
    return render(request, "core/form.html", {
        "form": form, "title": _("Arrange transport"),
        "intro": _("Provide the pickup location, destination, pickup date, and optional cost."),
        "submit_label": _("Post transport request"),
    })


@role_required(Profile.Role.TRANSPORTER)
def transport_action(request, request_id, action):
    if request.method != "POST":
        return HttpResponseForbidden(_("Transport changes must be submitted with POST."))
    profile = request.user.profile
    with transaction.atomic():
        item = get_object_or_404(
            TransportRequest.objects.select_for_update().select_related("order"),
            pk=request_id,
        )
        if action == "claim" and item.status == TransportRequest.Status.OPEN:
            if profile.vehicle_capacity and profile.vehicle_capacity < item.order.quantity:
                messages.error(request, _("Your registered vehicle capacity is below this order quantity."))
                return redirect("transport")
            item.transporter = profile
            item.status = TransportRequest.Status.ASSIGNED
            notify_order_participants(
                item.order,
                [item.requester],
                "Transporter assigned",
                f"A transporter accepted the collection request for order #{item.order_id}.",
            )
        elif (
            item.transporter_id == profile.pk
            and item.status == TransportRequest.Status.ASSIGNED
            and item.order.status == Order.Status.READY
            and action == "pickup"
        ):
            item.status = TransportRequest.Status.PICKED_UP
            item.order.status = Order.Status.IN_TRANSIT
            item.order.save(update_fields=["status"])
            notify_order_participants(
                item.order,
                [item.order.buyer, item.order.farmer],
                "Produce picked up",
                f"Produce for order #{item.order_id} has been picked up and is in transit.",
            )
        elif (
            item.transporter_id == profile.pk
            and item.status == TransportRequest.Status.PICKED_UP
            and item.order.status == Order.Status.IN_TRANSIT
            and action == "delivered"
        ):
            item.status = TransportRequest.Status.DELIVERED
            item.order.status = Order.Status.DELIVERED
            item.order.save(update_fields=["status"])
            notify_order_participants(
                item.order,
                [item.order.buyer, item.order.farmer],
                "Produce delivered",
                f"Delivery for order #{item.order_id} has been marked complete.",
            )
        else:
            return HttpResponseForbidden(_("That transport action is not permitted."))
        item.save()
    messages.success(request, _("Transport request updated."))
    return redirect("transport")


@role_required(Profile.Role.FARMER)
def storage(request):
    records = StorageRecord.objects.filter(
        farmer=request.user.profile
    ).select_related("crop_record")
    return render(request, "core/storage.html", {
        "records": records,
        "alerts": [(record, record.reminders) for record in records if record.reminders],
    })


@role_required(Profile.Role.FARMER)
def storage_create(request):
    form = StorageRecordForm(request.POST or None, farmer=request.user.profile)
    if request.method == "POST" and form.is_valid():
        record = form.save(commit=False)
        record.farmer = request.user.profile
        record.save()
        messages.success(request, _("Storage record saved."))
        return redirect("storage")
    return render(request, "core/form.html", {
        "form": form, "title": _("Record harvested produce"),
        "intro": _("Reminders use your configured dates and are not food-safety or spoilage assessments."),
        "submit_label": _("Save storage record"),
    })


@role_required(Profile.Role.FARMER)
def storage_inspect(request, record_id):
    record = get_object_or_404(StorageRecord, pk=record_id, farmer=request.user.profile)
    form = InspectionForm(request.POST or None, instance=record)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, _("Storage inspection recorded."))
        return redirect("storage")
    return render(request, "core/form.html", {
        "form": form, "title": _("Record storage inspection"),
        "submit_label": _("Save inspection"),
    })


@role_required(Profile.Role.FARMER)
def finance(request):
    profile = request.user.profile
    costs = Expense.objects.filter(farmer=profile).aggregate(total=Sum("amount"))["total"] or Decimal("0")
    revenue = Decimal("0")
    for order in Order.objects.filter(farmer=profile, status=Order.Status.DELIVERED):
        if order.total_amount is not None:
            revenue += order.total_amount
    form = ExpenseForm(request.POST or None, farmer=profile)
    if request.method == "POST" and form.is_valid():
        expense = form.save(commit=False)
        expense.farmer = profile
        expense.save()
        messages.success(request, _("Farm expense recorded."))
        return redirect("finance")
    return render(request, "core/finance.html", {
        "costs": costs, "revenue": revenue, "profit": revenue - costs,
        "expenses": Expense.objects.filter(farmer=profile)[:20], "form": form,
    })


@login_required
def notifications(request):
    profile = Profile.objects.filter(user=request.user).first()
    if profile is None:
        return HttpResponseForbidden(_("Notifications are available to registered platform roles."))
    records = profile.notifications.all()
    if request.method == "POST":
        records.filter(is_read=False).update(is_read=True)
        messages.success(request, _("Notifications marked as read."))
        return redirect("notifications")
    return render(request, "core/notifications.html", {"records": records})


@login_required
def weather(request):
    return render(request, "core/weather.html")


@login_required
def community(request):
    profile = Profile.objects.filter(user=request.user).first()
    if profile is None:
        return HttpResponseForbidden(_("Community access is available to registered platform roles."))
    if request.method == "POST":
        post_id = request.POST.get("post_id")
        comment_body = request.POST.get("comment_body", "").strip()
        if post_id and comment_body:
            post = get_object_or_404(CommunityPost, pk=post_id)
            CommunityComment.objects.create(post=post, author=profile, body=comment_body[:1000])
            messages.success(request, _("Your comment was added."))
            return redirect("community")
        body = request.POST.get("body", "").strip()
        if body:
            CommunityPost.objects.create(author=profile, body=body[:2000])
            messages.success(request, _("Your community post was shared."))
        return redirect("community")
    posts = CommunityPost.objects.select_related("author__user", "location").prefetch_related("comments__author__user")[:50]
    return render(request, "core/community.html", {"posts": posts, "profile": profile})


def _assistant_answer(question):
    question = question.lower().strip()
    if any(word in question for word in ("harvest", "planting", "crop calendar")):
        return _("Record the planting date and the locally recommended growing duration. Treat the calculated harvest date as an estimate and confirm crop readiness in the field.")
    if any(word in question for word in ("market", "sell", "buyer", "price")):
        return _("Publish a clear listing with crop, quantity, unit, expected availability, district, quality and delivery preference. Compare buyer demands before agreeing on a price.")
    if any(word in question for word in ("storage", "store", "warehouse")):
        return _("Record the harvest date, storage location, remaining quantity and inspection schedule. The reminders support record-keeping; they do not certify food safety.")
    if any(word in question for word in ("transport", "delivery", "truck")):
        return _("Create a transport request with pickup location, destination, pickup date, capacity and estimated cost so a compatible transporter can claim it.")
    if any(word in question for word in ("fertilizer", "seed", "irrigation", "disease")):
        return _("Use local agricultural extension guidance for input rates and disease treatment. This assistant gives general planning guidance, not a substitute for a qualified agronomist.")
    return _("I can help with crop planning, harvest records, market listings, storage reminders and transport coordination. Ask me about one of those topics.")


def _ai_assistant_answer(question):
    """Use an optional OpenAI Responses API provider without exposing credentials in code."""
    api_key = os.environ.get("OPENAI_API_KEY")
    model = os.environ.get("OPENAI_MODEL")
    if not api_key or not model:
        return None
    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key)
        response = client.responses.create(
            model=model,
            instructions=(
                "You are Smart AgroConnect's agricultural planning assistant. "
                "Give concise, practical guidance for Rwanda. Do not diagnose disease, "
                "prescribe chemicals, guarantee prices, or claim causal evidence. "
                "Recommend a qualified local extension officer for safety-critical decisions."
            ),
            input=question,
        )
        return response.output_text.strip()
    except Exception:
        return None


@login_required
def assistant(request):
    answer = None
    question = ""
    if request.method == "POST":
        question = request.POST.get("question", "").strip()
        if question:
            answer = _ai_assistant_answer(question) or _assistant_answer(question)
    return render(request, "core/assistant.html", {"answer": answer, "question": question})
