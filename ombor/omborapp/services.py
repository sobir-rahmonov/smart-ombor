from decimal import Decimal

from django.db import transaction
from django.db.models import DecimalField, F, Sum

from .models import Category, Product, StockMovement


class InsufficientStockError(Exception):
    """Chiqim uchun ombordagi qoldiq yetmaganda ko'tariladi."""


@transaction.atomic
def create_stock_movement(*, product, movement_type, quantity, price, note=""):
    """Kirim yoki chiqimni saqlaydi va mahsulot qoldig'ini yangilaydi."""
    product = Product.objects.select_for_update().get(pk=product.pk)

    if movement_type == StockMovement.MovementType.IN:
        product.quantity += quantity
    else:
        if quantity > product.quantity:
            raise InsufficientStockError(
                f"Omborda faqat {product.quantity} dona qolgan."
            )
        product.quantity -= quantity

    product.save(update_fields=["quantity"])

    return StockMovement.objects.create(
        product=product,
        movement_type=movement_type,
        quantity=quantity,
        price=price,
        note=note,
    )


def get_low_stock_products(owner):
    """Egasining qoldig'i minimal miqdordan oshmagan mahsulotlari."""
    return (
        Product.objects.filter(owner=owner, quantity__lte=F("min_quantity"))
        .select_related("category")
        .order_by("quantity")
    )


def get_total_stock_value(owner):
    """Egasining ombordagi barcha mahsulotlari qiymati (narx × qoldiq)."""
    result = Product.objects.filter(owner=owner).aggregate(
        total=Sum(F("price") * F("quantity"), output_field=DecimalField())
    )
    return result["total"] or Decimal("0")


@transaction.atomic
def delete_user_with_data(user):
    """Foydalanuvchini va uning barcha ma'lumotlarini tartib bilan o'chiradi."""
    StockMovement.objects.filter(product__owner=user).delete()
    Product.objects.filter(owner=user).delete()
    Category.objects.filter(owner=user).delete()
    user.delete()