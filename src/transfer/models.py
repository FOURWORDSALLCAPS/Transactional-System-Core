from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator


class Wallet(models.Model):
    user = models.ForeignKey(
        get_user_model(),
        on_delete=models.CASCADE,
        related_name="wallets",
        verbose_name="Пользователь",
    )
    currency = models.CharField(max_length=10, default="USD", verbose_name="Валюта")
    balance = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=0.00,
        validators=[MinValueValidator(0)],
        verbose_name="Баланс",
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

    class Meta:
        verbose_name = "Кошелек"
        verbose_name_plural = "Кошельки"
        unique_together = ["user", "currency"]
        indexes = [
            models.Index(fields=["user", "currency"]),
        ]

    def __str__(self):
        return f"Кошелек {self.user.username} ({self.currency}): {self.balance}"


class Transaction(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "В обработке"
        COMPLETED = "completed", "Завершена"
        FAILED = "failed", "Не удалась"
        CANCELLED = "cancelled", "Отменена"

    class TransactionType(models.TextChoices):
        TRANSFER = "transfer", "Перевод"
        COMMISSION = "commission", "Комиссия"
        DEPOSIT = "deposit", "Пополнение"
        WITHDRAWAL = "withdrawal", "Списание"

    transaction_id = models.CharField(
        max_length=50, unique=True, db_index=True, verbose_name="ID транзакции"
    )
    from_wallet = models.ForeignKey(
        Wallet,
        on_delete=models.PROTECT,
        related_name="outgoing_transactions",
        verbose_name="С кошелька",
        null=True,
        blank=True,
    )
    to_wallet = models.ForeignKey(
        Wallet,
        on_delete=models.PROTECT,
        related_name="incoming_transactions",
        verbose_name="На кошелек",
    )
    amount = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        validators=[MinValueValidator(0.01)],
        verbose_name="Сумма перевода",
    )
    commission = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=0.00,
        validators=[MinValueValidator(0)],
        verbose_name="Комиссия системы",
    )
    total_amount = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        validators=[MinValueValidator(0.01)],
        verbose_name="Общая сумма (amount + commission)",
    )
    transaction_type = models.CharField(
        max_length=20,
        choices=TransactionType.choices,
        default=TransactionType.TRANSFER,
        verbose_name="Тип транзакции",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name="Статус",
    )
    description = models.TextField(blank=True, verbose_name="Описание")
    related_transaction = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="related_transactions",
        verbose_name="Связанная транзакция",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    processed_at = models.DateTimeField(
        null=True, blank=True, verbose_name="Дата обработки"
    )
    completed_at = models.DateTimeField(
        null=True, blank=True, verbose_name="Дата завершения"
    )

    class Meta:
        verbose_name = "Транзакция"
        verbose_name_plural = "Транзакции"
        indexes = [
            models.Index(fields=["transaction_id"]),
            models.Index(fields=["from_wallet", "to_wallet"]),
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["transaction_type"]),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return f"Транзакция {self.transaction_id}: {self.amount} ({self.status})"

    def save(self, *args, **kwargs):
        if not self.total_amount:
            self.total_amount = self.amount + self.commission
        super().save(*args, **kwargs)


class TransactionLock(models.Model):
    wallet = models.ForeignKey(
        Wallet,
        on_delete=models.CASCADE,
        related_name="transaction_locks",
        verbose_name="Заблокированный кошелек",
    )
    transaction = models.ForeignKey(
        Transaction,
        on_delete=models.CASCADE,
        related_name="locks",
        verbose_name="Транзакция",
    )
    lock_type = models.CharField(
        max_length=20,
        choices=[
            ("debit", "Списание"),
            ("credit", "Зачисление"),
        ],
        verbose_name="Тип блокировки",
    )
    amount = models.DecimalField(
        max_digits=20, decimal_places=2, verbose_name="Заблокированная сумма"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    expires_at = models.DateTimeField(verbose_name="Дата истечения блокировки")

    class Meta:
        verbose_name = "Блокировка транзакции"
        verbose_name_plural = "Блокировки транзакций"
        indexes = [
            models.Index(fields=["wallet", "expires_at"]),
        ]
        unique_together = ["wallet", "transaction"]

    def __str__(self):
        return f"Блокировка {self.wallet.id}: {self.amount} ({self.lock_type})"
