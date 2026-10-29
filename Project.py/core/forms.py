from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User
from django.utils.translation import get_language, gettext_lazy as _

from .models import (
    BuyerDemand,
    CropRecord,
    Expense,
    Farm,
    Order,
    ProductListing,
    Profile,
    StorageRecord, Location,
    TransportRequest,
)


class RegisterForm(UserCreationForm):
    first_name = forms.CharField(max_length=150, label=_("First name"))
    last_name = forms.CharField(max_length=150, label=_("Last name"))
    email = forms.EmailField(required=False, label=_("Email"))
    role = forms.ChoiceField(choices=Profile.Role.choices, label=_("Role"))
    phone = forms.CharField(max_length=30, required=False, label=_("Phone"))
    district = forms.CharField(max_length=100, required=False, label=_("District"))
    sector = forms.CharField(max_length=100, required=False, label=_("Sector"))
    cell = forms.CharField(max_length=100, required=False, label=_("Cell"))
    village = forms.CharField(max_length=100, required=False, label=_("Village"))
    location = forms.ModelChoiceField(
        queryset=Location.objects.all(), required=False, label=_("Official location"),
        help_text=_("Select an imported NISR location when available."),
    )
    vehicle_type = forms.CharField(max_length=100, required=False, label=_("Vehicle type"))
    vehicle_capacity = forms.DecimalField(
        max_digits=10, decimal_places=2, min_value=0.01, required=False,
        label=_("Vehicle capacity (kg)"),
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = (
            "username", "first_name", "last_name", "email", "role",
            "phone", "district", "sector", "cell", "village", "location", "vehicle_type", "vehicle_capacity",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if get_language() == "rw":
            labels = {
                "username": "Izina rikoreshwa",
                "password1": "Ijambo ry'ibanga",
                "password2": "Emeza ijambo ry'ibanga",
            }
            for name, label in labels.items():
                self.fields[name].label = label

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("role") == Profile.Role.TRANSPORTER:
            if not cleaned.get("vehicle_type"):
                self.add_error("vehicle_type", _("Enter the vehicle type you can provide."))
            if not cleaned.get("vehicle_capacity"):
                self.add_error("vehicle_capacity", _("Enter your vehicle capacity in kilograms."))
        else:
            cleaned["vehicle_type"] = ""
            cleaned["vehicle_capacity"] = None
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        user.email = self.cleaned_data.get("email", "")
        if commit:
            user.save()
            Profile.objects.create(
                user=user,
                role=self.cleaned_data["role"],
                phone=self.cleaned_data.get("phone", ""),
                district=self.cleaned_data.get("district", ""),
                sector=self.cleaned_data.get("sector", ""),
                cell=self.cleaned_data.get("cell", ""),
                village=self.cleaned_data.get("village", ""),
                location=self.cleaned_data.get("location"),
                vehicle_type=self.cleaned_data.get("vehicle_type", ""),
                vehicle_capacity=self.cleaned_data.get("vehicle_capacity"),
            )
        return user


class LocalizedAuthenticationForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if get_language() == "rw":
            self.fields["username"].label = "Izina rikoreshwa"
            self.fields["password"].label = "Ijambo ry'ibanga"


class DateInputForm(forms.ModelForm):
    kinya_labels = {
        "Farm": "Ururima",
        "Crop": "Igihingwa",
        "Crop name": "Izina ry'igihingwa",
        "Crop variety": "Ubwoko bw'imbuto",
        "Planting date": "Itariki yo gutera",
        "Expected growing days": "Iminsi iteganyijwe yo gukura",
        "Expected quantity": "Ingano iteganyijwe",
        "Quantity unit": "Igipimo",
        "Stage": "Icyiciro cy'igihingwa",
        "Field observations": "Ibyagaragaye mu murima",
        "Name": "Izina",
        "District": "Akarere",
        "Sector": "Umurenge",
        "Cell": "Akagari",
        "Village": "Umudugudu",
        "Size hectares": "Ingano y'ubutaka (ha)",
        "Product name": "Izina ry'igicuruzwa",
        "Quantity": "Ingano",
        "Price per unit": "Igiciro kuri buri gipimo",
        "Price negotiable": "Igiciro kirumvikanwaho",
        "Expected available date": "Itariki iteganyijwe kubonekaho",
        "Quality description": "Ibisobanuro by'ubwiza",
        "Delivery preference": "Uburyo bwo kugeza umusaruro",
        "Required quantity": "Ingano ikenewe",
        "Target price per unit": "Igiciro ntarengwa kuri buri gipimo",
        "Needed by date": "Itariki bikeneweho",
        "Quality requirements": "Ibisabwa ku bwiza",
        "Proposed unit price": "Igiciro gitanzwe kuri buri gipimo",
        "Collection date": "Itariki yo gutwara",
        "Delivery location": "Aho bigomba kugezwa",
        "Pickup location": "Aho bizakurwa",
        "Destination": "Aho bijyanwa",
        "Pickup date": "Itariki yo kubitwara",
        "Vehicle capacity": "Ubushobozi bw'ikinyabiziga (kg)",
        "Estimated cost": "Ikiguzi kigereranyijwe",
        "Crop record": "Inyandiko y'igihingwa",
        "Crop name": "Izina ry'igihingwa",
        "Quantity remaining": "Ingano isigaye",
        "Harvest date": "Itariki yo gusarura",
        "Storage start date": "Itariki yo kubika",
        "Storage location": "Aho bibitswe",
        "Inspection interval days": "Iminsi hagati y'igenzura",
        "Max storage days": "Iminsi ntarengwa yo kubika",
        "Last inspection date": "Itariki iheruka kugenzurirwaho",
        "Inspection notes": "Ibyagaragaye mu igenzura",
        "Farm": "Ururima",
        "Category": "Icyiciro cy'ikiguzi",
        "Amount": "Amafaranga",
        "Expense date": "Itariki y'ikiguzi",
        "Description": "Ibisobanuro",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if get_language() == "rw":
            for field in self.fields.values():
                if field.label:
                    field.label = self.kinya_labels.get(str(field.label), str(field.label))
                if field.help_text:
                    field.help_text = ""
        for field in self.fields.values():
            if isinstance(field, forms.DateField):
                field.widget = forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")
                field.input_formats = ["%Y-%m-%d"]


class FarmForm(DateInputForm):
    class Meta:
        model = Farm
        fields = ("name", "district", "sector", "cell", "village", "location", "size_hectares")
        widgets = {
            "size_hectares": forms.NumberInput(attrs={"step": "0.01", "min": "0.01"}),
        }


class CropRecordForm(DateInputForm):
    class Meta:
        model = CropRecord
        fields = (
            "farm", "crop_name", "variety", "planting_date", "expected_growing_days",
            "expected_quantity", "quantity_unit", "stage", "field_observations",
        )
        widgets = {
            "expected_growing_days": forms.NumberInput(attrs={"min": "1"}),
            "expected_quantity": forms.NumberInput(attrs={"step": "0.01", "min": "0.01"}),
            "field_observations": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, farmer, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["farm"].queryset = Farm.objects.filter(farmer=farmer)


class ListingForm(DateInputForm):
    class Meta:
        model = ProductListing
        fields = (
            "crop_record", "product_name", "quantity", "quantity_unit", "price_per_unit",
            "negotiable", "expected_available_date", "district", "quality_description",
            "delivery_preference",
        )
        widgets = {
            "quantity": forms.NumberInput(attrs={"step": "0.01", "min": "0.01"}),
            "price_per_unit": forms.NumberInput(attrs={"step": "1", "min": "0"}),
            "quality_description": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, farmer, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["crop_record"].queryset = CropRecord.objects.filter(farm__farmer=farmer)
        self.fields["crop_record"].required = False


class BuyerDemandForm(DateInputForm):
    class Meta:
        model = BuyerDemand
        fields = (
            "product_name", "required_quantity", "quantity_unit", "target_price_per_unit",
            "needed_by_date", "district", "quality_requirements",
        )
        widgets = {
            "required_quantity": forms.NumberInput(attrs={"step": "0.01", "min": "0.01"}),
            "target_price_per_unit": forms.NumberInput(attrs={"step": "1", "min": "0"}),
            "quality_requirements": forms.Textarea(attrs={"rows": 3}),
        }


class PlaceOrderForm(DateInputForm):
    class Meta:
        model = Order
        fields = ("quantity", "proposed_unit_price", "collection_date", "delivery_location")
        widgets = {
            "quantity": forms.NumberInput(attrs={"step": "0.01", "min": "0.01"}),
            "proposed_unit_price": forms.NumberInput(attrs={"step": "1", "min": "0"}),
        }


class ConfirmAgreementForm(forms.Form):
    agreed_unit_price = forms.DecimalField(
        max_digits=12, decimal_places=2, min_value=0, label="Agreed price (FRW per unit)"
    )


class TransportRequestForm(DateInputForm):
    class Meta:
        model = TransportRequest
        fields = (
            "pickup_location", "destination", "pickup_date", "vehicle_capacity", "estimated_cost",
        )
        widgets = {
            "vehicle_capacity": forms.NumberInput(attrs={"step": "0.01", "min": "0.01"}),
            "estimated_cost": forms.NumberInput(attrs={"step": "1", "min": "0"}),
        }


class StorageRecordForm(DateInputForm):
    class Meta:
        model = StorageRecord
        fields = (
            "crop_record", "crop_name", "quantity_remaining", "quantity_unit", "harvest_date",
            "storage_start_date", "storage_location", "inspection_interval_days",
            "max_storage_days", "last_inspection_date", "inspection_notes",
        )
        widgets = {
            "quantity_remaining": forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
            "inspection_interval_days": forms.NumberInput(attrs={"min": "1"}),
            "max_storage_days": forms.NumberInput(attrs={"min": "1"}),
            "inspection_notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, farmer, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["crop_record"].queryset = CropRecord.objects.filter(farm__farmer=farmer)
        self.fields["crop_record"].required = False


class ExpenseForm(DateInputForm):
    class Meta:
        model = Expense
        fields = ("farm", "category", "amount", "expense_date", "description")
        widgets = {
            "amount": forms.NumberInput(attrs={"step": "1", "min": "0.01"}),
            "description": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, farmer, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["farm"].queryset = Farm.objects.filter(farmer=farmer)
        self.fields["farm"].required = False


class InspectionForm(forms.ModelForm):
    last_inspection_date = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        input_formats=["%Y-%m-%d"],
    )

    class Meta:
        model = StorageRecord
        fields = ("last_inspection_date", "inspection_notes")
        widgets = {"inspection_notes": forms.Textarea(attrs={"rows": 3})}
