from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from .forms import RegisterForm
from .models import (
    BuyerDemand, CropRecord, Farm, Notification, Order, ProductListing, Profile,
    StorageRecord, TransportRequest,
)
from .views import find_matches


class AgroConnectTests(TestCase):
    def setUp(self):
        self.farmer_user = User.objects.create_user(username="farmer", password="StrongPass123!")
        self.farmer = Profile.objects.create(user=self.farmer_user, role=Profile.Role.FARMER)
        self.buyer_user = User.objects.create_user(username="buyer", password="StrongPass123!")
        self.buyer = Profile.objects.create(user=self.buyer_user, role=Profile.Role.BUYER)
        self.transporter_user = User.objects.create_user(
            username="transporter", password="StrongPass123!"
        )
        self.transporter = Profile.objects.create(
            user=self.transporter_user,
            role=Profile.Role.TRANSPORTER,
            vehicle_capacity=Decimal("250"),
        )
        self.farm = Farm.objects.create(farmer=self.farmer, name="Green Valley", district="Gasabo")

    def create_listing(self, **overrides):
        values = {
            "farmer": self.farmer,
            "product_name": "Potatoes",
            "quantity": Decimal("800"),
            "quantity_unit": "kg",
            "expected_available_date": timezone.localdate() + timedelta(days=20),
            "district": "Gasabo",
            "negotiable": True,
        }
        values.update(overrides)
        return ProductListing.objects.create(**values)

    def test_registration_creates_role_profile_and_logs_in(self):
        self.client.post("/register/", {
            "username": "newfarmer",
            "first_name": "Aline",
            "last_name": "Uwase",
            "email": "aline@example.com",
            "role": Profile.Role.FARMER,
            "phone": "0780000000",
            "district": "Gasabo",
            "password1": "StrongPass123!",
            "password2": "StrongPass123!",
        })
        self.assertTrue(self.client.session.get("_auth_user_id"))
        self.assertEqual(
            User.objects.get(username="newfarmer").profile.role, Profile.Role.FARMER
        )

    def test_registration_supports_buyer_and_requires_transporter_details(self):
        for role, username, vehicle_fields in (
            (Profile.Role.BUYER, "newbuyer", {}),
            (
                Profile.Role.TRANSPORTER,
                "newtransporter",
                {"vehicle_type": "Pickup", "vehicle_capacity": "1200"},
            ),
        ):
            data = {
                "username": username,
                "first_name": "Aline",
                "last_name": "Uwase",
                "role": role,
                "password1": "StrongPass123!",
                "password2": "StrongPass123!",
                **vehicle_fields,
            }
            response = self.client.post("/register/", data)
            self.assertRedirects(response, "/dashboard/")
            profile = User.objects.get(username=username).profile
            self.assertEqual(profile.role, role)
            if role == Profile.Role.TRANSPORTER:
                self.assertEqual(profile.vehicle_type, "Pickup")
                self.assertEqual(profile.vehicle_capacity, Decimal("1200"))
            self.client.post("/logout/")

        invalid_transporter = RegisterForm(data={
            "username": "missingvehicle",
            "first_name": "Aline",
            "last_name": "Uwase",
            "role": Profile.Role.TRANSPORTER,
            "password1": "StrongPass123!",
            "password2": "StrongPass123!",
        })
        self.assertFalse(invalid_transporter.is_valid())
        self.assertIn("vehicle_type", invalid_transporter.errors)
        self.assertIn("vehicle_capacity", invalid_transporter.errors)

    def test_crop_harvest_date_is_a_calendar_estimate(self):
        crop = CropRecord.objects.create(
            farm=self.farm, crop_name="Beans", planting_date=timezone.localdate(),
            expected_growing_days=90, expected_quantity=Decimal("100"),
        )
        self.assertEqual(
            crop.estimated_harvest_date, timezone.localdate() + timedelta(days=90)
        )
        self.assertIn("estimate", crop.estimate_status.lower())

    def test_matching_requires_crop_quantity_date_and_location(self):
        demand = BuyerDemand.objects.create(
            buyer=self.buyer, product_name="Potatoes", required_quantity=Decimal("500"),
            quantity_unit="kg", needed_by_date=timezone.localdate() + timedelta(days=20),
            district="Gasabo",
        )
        matching = self.create_listing()
        self.create_listing(product_name="Beans")
        self.create_listing(quantity=Decimal("100"))
        self.create_listing(district="Huye")
        self.create_listing(expected_available_date=timezone.localdate() + timedelta(days=60))
        self.assertEqual(find_matches(demand), [matching])

    def test_buyer_cannot_order_more_than_listing_quantity(self):
        listing = self.create_listing(quantity=Decimal("100"))
        self.client.force_login(self.buyer_user)
        response = self.client.post(f"/listings/{listing.pk}/order/", {
            "quantity": "101",
            "proposed_unit_price": "500",
            "collection_date": timezone.localdate().isoformat(),
            "delivery_location": "Gasabo",
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Order.objects.exists())
        self.assertIn("Only 100.00 kg remain available.", response.content.decode())

    def test_farmer_can_accept_and_confirm_agreed_price(self):
        listing = self.create_listing()
        order = Order.objects.create(
            buyer=self.buyer,
            farmer=self.farmer,
            listing=listing,
            quantity=Decimal("100"),
            collection_date=timezone.localdate() + timedelta(days=1),
            delivery_location="Gasabo",
        )
        self.client.force_login(self.farmer_user)
        accept = self.client.post(f"/orders/{order.pk}/accept/")
        self.assertEqual(accept.status_code, 302)
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.ACCEPTED)
        confirm = self.client.post(f"/orders/{order.pk}/confirm/", {"agreed_unit_price": "600"})
        self.assertEqual(confirm.status_code, 302)
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.CONFIRMED)
        self.assertEqual(order.total_amount, Decimal("60000"))
        self.assertTrue(
            Notification.objects.filter(
                user=self.buyer, message__contains="Agreement confirmed"
            ).exists()
        )

    def test_assigned_transporter_updates_order_and_notifies_both_parties(self):
        listing = self.create_listing()
        order = Order.objects.create(
            buyer=self.buyer,
            farmer=self.farmer,
            listing=listing,
            quantity=Decimal("100"),
            agreed_unit_price=Decimal("600"),
            collection_date=timezone.localdate() + timedelta(days=1),
            delivery_location="Gasabo",
            status=Order.Status.READY,
        )
        transport = TransportRequest.objects.create(
            order=order,
            requester=self.buyer,
            transporter=self.transporter,
            pickup_location="Green Valley",
            destination="Gasabo market",
            pickup_date=order.collection_date,
            status=TransportRequest.Status.ASSIGNED,
        )
        self.client.force_login(self.transporter_user)
        pickup = self.client.post(f"/transport/{transport.pk}/pickup/")
        self.assertEqual(pickup.status_code, 302)
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.IN_TRANSIT)
        delivery = self.client.post(f"/transport/{transport.pk}/delivered/")
        self.assertEqual(delivery.status_code, 302)
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.DELIVERED)
        self.assertEqual(
            Notification.objects.filter(
                user=self.buyer, title="Produce delivered"
            ).count(),
            1,
        )
        self.assertEqual(
            Notification.objects.filter(
                user=self.farmer, title="Produce delivered"
            ).count(),
            1,
        )

    def test_transporter_capacity_prevents_claiming_larger_order(self):
        listing = self.create_listing()
        order = Order.objects.create(
            buyer=self.buyer,
            farmer=self.farmer,
            listing=listing,
            quantity=Decimal("300"),
            collection_date=timezone.localdate() + timedelta(days=1),
            delivery_location="Gasabo",
            status=Order.Status.READY,
        )
        transport = TransportRequest.objects.create(
            order=order,
            requester=self.buyer,
            pickup_location="Green Valley",
            destination="Gasabo market",
            pickup_date=order.collection_date,
            vehicle_capacity=Decimal("300"),
        )
        self.client.force_login(self.transporter_user)
        response = self.client.post(f"/transport/{transport.pk}/claim/")
        self.assertRedirects(response, "/transport/")
        transport.refresh_from_db()
        self.assertEqual(transport.status, TransportRequest.Status.OPEN)
        self.assertIsNone(transport.transporter)

    def test_role_permissions_restrict_farm_pages(self):
        self.client.force_login(self.buyer_user)
        self.assertEqual(self.client.get("/farms/").status_code, 403)
        self.assertEqual(self.client.get("/demands/").status_code, 200)

    def test_farmer_cannot_edit_another_farmers_crop(self):
        crop = CropRecord.objects.create(
            farm=self.farm, crop_name="Beans", planting_date=timezone.localdate(),
            expected_growing_days=90, expected_quantity=Decimal("100"),
        )
        other_user = User.objects.create_user(username="other", password="StrongPass123!")
        Profile.objects.create(user=other_user, role=Profile.Role.FARMER)
        self.client.force_login(other_user)
        self.assertEqual(self.client.get(f"/crops/{crop.pk}/edit/").status_code, 404)

    def test_storage_alerts_are_user_configured_reminders(self):
        record = StorageRecord.objects.create(
            farmer=self.farmer,
            crop_name="Potatoes",
            quantity_remaining=Decimal("50"),
            harvest_date=timezone.localdate() - timedelta(days=20),
            storage_start_date=timezone.localdate() - timedelta(days=15),
            storage_location="Store room",
            max_storage_days=14,
        )
        self.assertIn("Past your configured storage reminder period", record.reminders)
        self.assertIn("Storage inspection has not been recorded", record.reminders)

    def test_language_switch_translates_home_and_registration_form(self):
        response = self.client.post(
            "/i18n/setlang/", {"language": "rw", "next": "/"}
        )
        self.assertRedirects(response, "/")

        response = self.client.get("/")
        self.assertContains(response, '<html lang="rw">')
        self.assertContains(response, "Isarura rihuza abantu")

        response = self.client.get("/register/")
        self.assertContains(response, "Fungura konti yawe")
        self.assertContains(response, "Izina rikoreshwa")
        self.assertContains(response, "Ijambo ry&#x27;ibanga rigomba kugira nibura inyuguti 8.")
        self.assertNotContains(response, "Your password must contain at least 8 characters.")

        response = self.client.post(
            "/i18n/setlang/", {"language": "en", "next": "/"}
        )
        self.assertRedirects(response, "/")
        response = self.client.get("/")
        self.assertContains(response, '<html lang="en">')
        self.assertContains(response, "A better-connected harvest")
