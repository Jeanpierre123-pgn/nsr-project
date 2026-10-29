from django.contrib import admin

from .models import (
    BuyerDemand, CropRecord, Expense, Farm, Notification, Order, ProductListing,
    Profile, StorageRecord, TransportRequest,
)

admin.site.register(
    (Profile, Farm, CropRecord, ProductListing, BuyerDemand, Order,
     TransportRequest, StorageRecord, Expense, Notification)
)
