from django.contrib import admin

from .models import Wallet, Transaction, TransactionLock


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ["user", "currency", "balance", "created_at", "updated_at"]


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = [
        "transaction_id",
        "from_wallet",
        "to_wallet",
        "amount",
        "commission",
        "total_amount",
        "transaction_type",
        "status",
        "description",
        "related_transaction",
    ]


@admin.register(TransactionLock)
class TransactionLockAdmin(admin.ModelAdmin):
    list_display = [
        "wallet",
        "transaction",
        "lock_type",
        "amount",
        "created_at",
        "expires_at",
    ]
