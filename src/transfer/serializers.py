from rest_framework import serializers
from decimal import Decimal
from .models import Wallet


class TransferSerializer(serializers.Serializer):
    from_wallet_id = serializers.IntegerField(required=True, min_value=1)
    to_wallet_id = serializers.IntegerField(required=True, min_value=1)
    amount = serializers.DecimalField(
        required=True, max_digits=20, decimal_places=2, min_value=Decimal("0.01")
    )
    description = serializers.CharField(
        required=False, allow_blank=True, max_length=500
    )

    def validate(self, data):
        if data["from_wallet_id"] == data["to_wallet_id"]:
            raise serializers.ValidationError(
                {"to_wallet_id": "Нельзя переводить на тот же кошелек"}
            )

        try:
            from_wallet = Wallet.objects.get(id=data["from_wallet_id"])
            data["from_wallet"] = from_wallet
        except Wallet.DoesNotExist:
            raise serializers.ValidationError(
                {"from_wallet_id": "Кошелек отправителя не найден"}
            )

        try:
            to_wallet = Wallet.objects.get(id=data["to_wallet_id"])
            data["to_wallet"] = to_wallet
        except Wallet.DoesNotExist:
            raise serializers.ValidationError(
                {"to_wallet_id": "Кошелек получателя не найден"}
            )

        return data
