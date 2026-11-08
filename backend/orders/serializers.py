import re
from rest_framework import serializers


class CartItemInput(serializers.Serializer):
    variant_id = serializers.IntegerField(min_value=1)
    quantity = serializers.IntegerField(min_value=1, max_value=30)


class QuoteInput(serializers.Serializer):
    items = CartItemInput(many=True, allow_empty=False, max_length=50)
    promo = serializers.CharField(
        max_length=40, required=False, allow_blank=True, default=""
    )
    city_code = serializers.IntegerField(min_value=1, required=False)
    delivery_method = serializers.ChoiceField(
        choices=["pickup", "courier"], default="pickup"
    )


class OrderInput(QuoteInput):
    request_key = serializers.UUIDField()
    name = serializers.CharField(min_length=2, max_length=150)
    email = serializers.EmailField(max_length=254)
    phone = serializers.CharField(max_length=30)
    city = serializers.CharField(max_length=150)
    city_code = serializers.IntegerField(min_value=1)
    pickup_code = serializers.CharField(
        max_length=80, allow_blank=True, required=False, default=""
    )
    address = serializers.CharField(
        max_length=400, allow_blank=True, required=False, default=""
    )
    comment = serializers.CharField(
        max_length=2000, allow_blank=True, required=False, default=""
    )
    consent = serializers.BooleanField()

    def validate_consent(self, value):
        if not value:
            raise serializers.ValidationError("Подтвердите согласие с документами.")
        return value

    def validate_phone(self, value):
        digits = re.sub(r"\D", "", value)
        if digits.startswith("8") and len(digits) == 11:
            digits = "7" + digits[1:]
        if not re.fullmatch(r"7\d{10}", digits):
            raise serializers.ValidationError("Укажите российский номер: +7 и 10 цифр.")
        return "+" + digits
