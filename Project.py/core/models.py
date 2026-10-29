from datetime import timedelta

from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone


class Location(models.Model):
    class Level(models.TextChoices):
        PROVINCE = "province", _("Province")
        DISTRICT = "district", _("District")
        SECTOR = "sector", _("Sector")
        CELL = "cell", _("Cell")
        VILLAGE = "village", _("Village")

    name = models.CharField(max_length=150)
    code = models.CharField(max_length=50, blank=True)
    level = models.CharField(max_length=20, choices=Level.choices)
    parent = models.ForeignKey(
        "self", on_delete=models.CASCADE, null=True, blank=True,
        related_name="children",
    )

    class Meta:
        ordering = ["level", "name"]
        constraints = [
            models.UniqueConstraint(fields=["level", "parent", "name"], name="unique_location_name_under_parent"),
        ]

    def __str__(self):
        return self.name


class Profile(models.Model):
    class Role(models.TextChoices):
        FARMER = "farmer", _("Farmer")
        BUYER = "buyer", _("Buyer")
        TRANSPORTER = "transporter", _("Transporter")

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    role = models.CharField(max_length=20, choices=Role.choices)
    phone = models.CharField(max_length=30, blank=True)
    district = models.CharField(max_length=100, blank=True)
    sector = models.CharField(max_length=100, blank=True)
    cell = models.CharField(max_length=100, blank=True)
    village = models.CharField(max_length=100, blank=True)
    location = models.ForeignKey(
        Location, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="profiles",
    )
    vehicle_type = models.CharField(max_length=100, blank=True)
    vehicle_capacity = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(0.01)],
    )

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} ({self.get_role_display()})"


class Farm(models.Model):
    farmer = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="farms")
    name = models.CharField(max_length=120)
    district = models.CharField(max_length=100)
    sector = models.CharField(max_length=100, blank=True)
    cell = models.CharField(max_length=100, blank=True)
    village = models.CharField(max_length=100, blank=True)
    location = models.ForeignKey(
        Location, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="farms",
    )
    size_hectares = models.DecimalField(
        max_digits=9, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(0.01)],
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} — {self.district}"


class CropRecord(models.Model):
    class Stage(models.TextChoices):
        GROWING = "growing", _("Growing")
        APPROACHING = "approaching", _("Harvest period approaching")
        INSPECTION = "inspection", _("Ready for field inspection")
        CONFIRMED = "confirmed", _("Readiness confirmed after inspection")
        HARVESTED = "harvested", _("Harvested")

    farm = models.ForeignKey(Farm, on_delete=models.CASCADE, related_name="crops")
    crop_name = models.CharField(max_length=100)
    variety = models.CharField(max_length=100, blank=True)
    planting_date = models.DateField()
    expected_growing_days = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1)],
        help_text="Enter a growing duration supported by local agricultural guidance.",
    )
    expected_quantity = models.DecimalField(
        max_digits=12, decimal_places=2, validators=[MinValueValidator(0.01)]
    )
    quantity_unit = models.CharField(max_length=30, default="kg")
    stage = models.CharField(max_length=20, choices=Stage.choices, default=Stage.GROWING)
    field_observations = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["planting_date"]

    @property
    def estimated_harvest_date(self):
        return self.planting_date + timedelta(days=self.expected_growing_days)

    @property
    def estimate_status(self):
        if self.stage in (self.Stage.CONFIRMED, self.Stage.HARVESTED):
            return self.get_stage_display()
        days_remaining = (self.estimated_harvest_date - timezone.localdate()).days
        if days_remaining < 0:
            return _("Past estimated date — inspect the crop")
        if days_remaining <= 7:
            return _("Estimate approaching — inspect the crop")
        return _("Growing — calendar estimate only")

    def __str__(self):
        return f"{self.crop_name} on {self.farm.name}"


class ProductListing(models.Model):
    class Status(models.TextChoices):
        AVAILABLE = "available", _("Available")
        RESERVED = "reserved", _("Reserved")
        SOLD = "sold", _("Sold")
        CANCELLED = "cancelled", _("Cancelled")

    class DeliveryPreference(models.TextChoices):
        COLLECTION = "collection", _("Buyer collection")
        DELIVERY = "delivery", _("Delivery preferred")
        FLEXIBLE = "flexible", _("Flexible")

    farmer = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="listings")
    crop_record = models.ForeignKey(
        CropRecord, on_delete=models.SET_NULL, null=True, blank=True, related_name="listings"
    )
    product_name = models.CharField(max_length=100)
    quantity = models.DecimalField(
        max_digits=12, decimal_places=2, validators=[MinValueValidator(0.01)]
    )
    quantity_unit = models.CharField(max_length=30, default="kg")
    price_per_unit = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(0)],
        help_text="Price in FRW per unit; leave blank if negotiable.",
    )
    negotiable = models.BooleanField(default=True)
    expected_available_date = models.DateField()
    district = models.CharField(max_length=100)
    quality_description = models.TextField(blank=True)
    delivery_preference = models.CharField(
        max_length=20, choices=DeliveryPreference.choices, default=DeliveryPreference.FLEXIBLE
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.AVAILABLE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["expected_available_date", "-created_at"]

    @property
    def available_quantity(self):
        reserved = self.orders.exclude(
            status__in=[Order.Status.REJECTED, Order.Status.CANCELLED]
        ).aggregate(total=models.Sum("quantity"))["total"] or 0
        return max(self.quantity - reserved, 0)

    def __str__(self):
        return f"{self.product_name} ({self.quantity} {self.quantity_unit})"


class BuyerDemand(models.Model):
    class Status(models.TextChoices):
        OPEN = "open", _("Open")
        FULFILLED = "fulfilled", _("Fulfilled")
        CANCELLED = "cancelled", _("Cancelled")

    buyer = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="demands")
    product_name = models.CharField(max_length=100)
    required_quantity = models.DecimalField(
        max_digits=12, decimal_places=2, validators=[MinValueValidator(0.01)]
    )
    quantity_unit = models.CharField(max_length=30, default="kg")
    target_price_per_unit = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(0)],
    )
    needed_by_date = models.DateField()
    district = models.CharField(max_length=100, blank=True)
    quality_requirements = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["needed_by_date", "-created_at"]

    def __str__(self):
        return f"{self.product_name} demand by {self.buyer.user.username}"


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", _("Pending farmer response")
        ACCEPTED = "accepted", _("Accepted — confirm agreement")
        CONFIRMED = "confirmed", _("Agreement confirmed")
        READY = "ready", _("Ready for collection")
        IN_TRANSIT = "in_transit", _("In transit")
        DELIVERED = "delivered", _("Delivered")
        REJECTED = "rejected", _("Rejected")
        CANCELLED = "cancelled", _("Cancelled")

    buyer = models.ForeignKey(Profile, on_delete=models.PROTECT, related_name="orders_as_buyer")
    farmer = models.ForeignKey(Profile, on_delete=models.PROTECT, related_name="orders_as_farmer")
    listing = models.ForeignKey(ProductListing, on_delete=models.PROTECT, related_name="orders")
    quantity = models.DecimalField(
        max_digits=12, decimal_places=2, validators=[MinValueValidator(0.01)]
    )
    proposed_unit_price = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0)]
    )
    agreed_unit_price = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0)]
    )
    collection_date = models.DateField()
    delivery_location = models.CharField(max_length=200)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    @property
    def total_amount(self):
        if self.agreed_unit_price is None:
            return None
        return self.quantity * self.agreed_unit_price

    def __str__(self):
        return f"Order #{self.pk}: {self.listing.product_name}"


class TransportRequest(models.Model):
    class Status(models.TextChoices):
        OPEN = "open", _("Seeking transporter")
        ASSIGNED = "assigned", _("Transporter assigned")
        PICKED_UP = "picked_up", _("Picked up")
        DELIVERED = "delivered", _("Delivered")
        CANCELLED = "cancelled", _("Cancelled")

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="transport_requests")
    requester = models.ForeignKey(Profile, on_delete=models.PROTECT, related_name="transport_requests")
    transporter = models.ForeignKey(
        Profile, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="assigned_transport",
    )
    pickup_location = models.CharField(max_length=200)
    destination = models.CharField(max_length=200)
    pickup_date = models.DateField()
    vehicle_capacity = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(0.01)],
    )
    estimated_cost = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(0)],
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["pickup_date"]


class StorageRecord(models.Model):
    farmer = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="storage_records")
    crop_record = models.ForeignKey(
        CropRecord, on_delete=models.SET_NULL, null=True, blank=True, related_name="storage_records"
    )
    crop_name = models.CharField(max_length=100)
    quantity_remaining = models.DecimalField(
        max_digits=12, decimal_places=2, validators=[MinValueValidator(0)]
    )
    quantity_unit = models.CharField(max_length=30, default="kg")
    harvest_date = models.DateField()
    storage_start_date = models.DateField()
    storage_location = models.CharField(max_length=150)
    inspection_interval_days = models.PositiveSmallIntegerField(default=7)
    max_storage_days = models.PositiveSmallIntegerField(
        default=14,
        help_text="Reminder threshold chosen by you; it is not a food-safety assessment.",
    )
    last_inspection_date = models.DateField(null=True, blank=True)
    inspection_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["storage_start_date"]

    @property
    def reminders(self):
        today = timezone.localdate()
        reminders = []
        if (today - self.storage_start_date).days >= self.max_storage_days:
            reminders.append(_("Past your configured storage reminder period"))
        if self.last_inspection_date is None:
            reminders.append(_("Storage inspection has not been recorded"))
        elif (today - self.last_inspection_date).days >= self.inspection_interval_days:
            reminders.append(_("Storage inspection is due"))
        return reminders


class Expense(models.Model):
    farmer = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="expenses")
    farm = models.ForeignKey(Farm, on_delete=models.SET_NULL, null=True, blank=True)
    category = models.CharField(max_length=100)
    amount = models.DecimalField(
        max_digits=12, decimal_places=2, validators=[MinValueValidator(0.01)]
    )
    expense_date = models.DateField()
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["-expense_date"]


class Notification(models.Model):
    user = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="notifications")
    title = models.CharField(max_length=120)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class CommunityPost(models.Model):
    author = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="community_posts")
    location = models.ForeignKey(
        Location, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="community_posts",
    )
    body = models.TextField(max_length=2000)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Post by {self.author.user.username}"


class CommunityComment(models.Model):
    post = models.ForeignKey(CommunityPost, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="community_comments")
    body = models.CharField(max_length=1000)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
