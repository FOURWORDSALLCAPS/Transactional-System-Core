import uuid
import logging
from decimal import Decimal
from datetime import timedelta

from django.db import transaction as db_transaction
from django.db.models import F, Q, Sum
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Wallet, Transaction, TransactionLock
from .serializers import TransferSerializer
from .tasks import send_transaction_notification

User = get_user_model()
logger = logging.getLogger(__name__)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def register_transfer(request):
    serializer = TransferSerializer(data=request.data)

    if not serializer.is_valid():
        return Response(
            {"error": "Неверные данные", "details": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )

    transfer = serializer.validated_data
    from_wallet_id = transfer["from_wallet_id"]
    to_wallet_id = transfer["to_wallet_id"]
    amount = transfer["amount"]
    description = transfer.get("description", "")

    try:
        result = process_transfer_with_lock(
            from_wallet_id=from_wallet_id,
            to_wallet_id=to_wallet_id,
            amount=amount,
            description=description,
        )

        return Response(result, status=status.HTTP_201_CREATED)

    except ValueError as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    except ValidationError as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.error(f"Ошибка при переводе: {e}", exc_info=True)
        return Response(
            {"error": "Внутренняя ошибка сервера"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


def calculate_commission(amount: Decimal) -> tuple[Decimal, Decimal, Decimal]:
    commission_threshold = Decimal("1000")
    commission_rate = Decimal("0.10")

    if amount > commission_threshold:
        commission = amount * commission_rate
        total_amount = amount + commission
        return amount, commission, total_amount
    else:
        return amount, Decimal("0.00"), amount


def get_or_create_admin_wallet() -> Wallet:
    admin_wallet_id = 100
    try:
        return Wallet.objects.get(id=admin_wallet_id)  # noqa
    except Wallet.DoesNotExist:  # noqa
        pass

    system_user, _ = User.objects.get_or_create(
        username="system",
        defaults={
            "email": "system@example.com",
            "is_active": True,
            "is_staff": False,
            "is_superuser": False,
        },
    )

    admin_wallet, created = Wallet.objects.get_or_create(  # noqa
        user=system_user,
        currency="USD",
        defaults={
            "balance": Decimal("0.00"),
        },
    )

    return admin_wallet


def create_transaction_lock(
    wallet: Wallet, transaction: Transaction, lock_type: str, amount: Decimal
) -> TransactionLock:
    expires_at = timezone.now() + timedelta(minutes=5)

    return TransactionLock.objects.create(  # noqa
        wallet=wallet,
        transaction=transaction,
        lock_type=lock_type,
        amount=amount,
        expires_at=expires_at,
    )


def process_transfer_with_lock(
    from_wallet_id: int, to_wallet_id: int, amount: Decimal, description: str
) -> dict:
    transaction_id = str(uuid.uuid4())

    try:
        with db_transaction.atomic():
            wallets = Wallet.objects.select_for_update().filter(  # noqa
                Q(id=from_wallet_id) | Q(id=to_wallet_id)
            )

            wallet_dict = {wallet.id: wallet for wallet in wallets}
            from_wallet = wallet_dict[from_wallet_id]
            to_wallet = wallet_dict[to_wallet_id]

            if from_wallet.currency != to_wallet.currency:
                raise ValidationError("Валюты кошельков не совпадают")

            transfer_amount, commission, total_amount = calculate_commission(amount)

            active_locks = TransactionLock.objects.filter(  # noqa
                wallet=from_wallet, expires_at__gt=timezone.now()
            ).aggregate(total_locked=Sum("amount"))["total_locked"] or Decimal("0.00")

            available_balance = from_wallet.balance - active_locks

            if available_balance < total_amount:
                raise ValidationError(
                    f"Недостаточно средств. "
                    f"Доступно: {available_balance}, требуется: {total_amount}"
                )

            transaction = Transaction.objects.create(  # noqa
                transaction_id=transaction_id,
                from_wallet=from_wallet,
                to_wallet=to_wallet,
                amount=transfer_amount,
                commission=commission,
                total_amount=total_amount,
                transaction_type=Transaction.TransactionType.TRANSFER,
                status=Transaction.Status.PENDING,
                description=description,
            )

            create_transaction_lock(
                wallet=from_wallet,
                transaction=transaction,
                lock_type="debit",
                amount=total_amount,
            )

            create_transaction_lock(
                wallet=to_wallet,
                transaction=transaction,
                lock_type="credit",
                amount=transfer_amount,
            )

            admin_wallet = None
            commission_transaction = None

            if commission > 0:
                admin_wallet = get_or_create_admin_wallet()
                admin_wallet = Wallet.objects.select_for_update().get(  # noqa
                    id=admin_wallet.id  # noqa
                )

                commission_transaction = Transaction.objects.create(  # noqa
                    transaction_id=f"{transaction_id}_commission",
                    from_wallet=from_wallet,
                    to_wallet=admin_wallet,
                    amount=commission,
                    commission=Decimal("0.00"),
                    total_amount=commission,
                    transaction_type=Transaction.TransactionType.COMMISSION,
                    status=Transaction.Status.PENDING,
                    description=f"Комиссия за перевод {transaction_id}",
                    related_transaction=transaction,
                )

                create_transaction_lock(
                    wallet=admin_wallet,
                    transaction=commission_transaction,
                    lock_type="credit",
                    amount=commission,
                )

            from_wallet.balance = F("balance") - total_amount
            from_wallet.save(update_fields=["balance"])

            to_wallet.balance = F("balance") + transfer_amount
            to_wallet.save(update_fields=["balance"])

            if admin_wallet and commission_transaction:
                admin_wallet.balance = F("balance") + commission
                admin_wallet.save(update_fields=["balance"])

                commission_transaction.status = Transaction.Status.COMPLETED
                commission_transaction.completed_at = timezone.now()
                commission_transaction.save(update_fields=["status", "completed_at"])

            transaction.status = Transaction.Status.COMPLETED
            transaction.completed_at = timezone.now()
            transaction.save(update_fields=["status", "completed_at"])

            from_wallet.refresh_from_db()
            to_wallet.refresh_from_db()

            TransactionLock.objects.filter(  # noqa
                Q(transaction=transaction) | Q(transaction=commission_transaction)
                if commission_transaction
                else Q()
            ).delete()

            notification_info = {
                "transaction_id": transaction_id,
                "from_wallet_id": from_wallet_id,
                "to_wallet_id": to_wallet_id,
                "from_user_id": from_wallet.user.id,
                "to_user_id": to_wallet.user.id,
                "to_user_email": to_wallet.user.email,
                "amount": str(transfer_amount),
                "commission": str(commission),
                "total_amount": str(total_amount),
                "description": description,
                "timestamp": transaction.completed_at.isoformat(),
                "new_balance": str(to_wallet.balance),
                "force_error": True,
            }

            send_transaction_notification.apply_async(
                args=[notification_info], countdown=1
            )

            result = {
                "transaction_id": transaction_id,
                "status": "completed",
                "from_wallet": {
                    "id": from_wallet.id,
                    "new_balance": str(from_wallet.balance),
                },
                "to_wallet": {
                    "id": to_wallet.id,
                    "new_balance": str(to_wallet.balance),
                },
                "amount": str(transfer_amount),
                "commission": str(commission),
                "total_amount": str(total_amount),
                "description": description,
                "timestamp": transaction.completed_at.isoformat(),
            }

            if commission > 0 and admin_wallet:
                result["admin_wallet"] = {
                    "id": admin_wallet.id,
                    "commission_received": str(commission),
                    "new_balance": str(admin_wallet.balance),
                }

            return result
    except Exception:
        TransactionLock.objects.filter(  # noqa
            Q(transaction__transaction_id=transaction_id)
            | Q(transaction__transaction_id=f"{transaction_id}_commission")
        ).delete()
        Transaction.objects.filter(transaction_id=transaction_id).update(  # noqa
            status=Transaction.Status.FAILED
        )
        Transaction.objects.filter(  # noqa
            transaction_id=f"{transaction_id}_commission"
        ).update(status=Transaction.Status.FAILED)

        raise
