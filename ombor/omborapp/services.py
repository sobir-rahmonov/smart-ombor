from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.db.models import DecimalField, F, Sum
from django.db.models.functions import TruncDate
from django.utils import timezone

from .models import Category, Product, StockMovement

WEEKDAY_LABELS = ["Du", "Se", "Ch", "Pa", "Ju", "Sh", "Ya"]


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


def get_weekly_movements(owner, days=7):
    """Oxirgi kunlar bo'yicha kirim va chiqim miqdori (grafik uchun)."""
    today = timezone.localdate()
    start = today - timedelta(days=days - 1)

    rows = (
        StockMovement.objects.filter(product__owner=owner, created_at__date__gte=start)
        .annotate(day=TruncDate("created_at"))
        .values("day", "movement_type")
        .annotate(total=Sum("quantity"))
    )
    totals = {(row["day"], row["movement_type"]): row["total"] for row in rows}

    movement_type = StockMovement.MovementType
    result = []
    for offset in range(days):
        day = start + timedelta(days=offset)
        result.append(
            {
                "label": WEEKDAY_LABELS[day.weekday()],
                "in_qty": totals.get((day, movement_type.IN), 0),
                "out_qty": totals.get((day, movement_type.OUT), 0),
            }
        )

    max_value = max((max(d["in_qty"], d["out_qty"]) for d in result), default=0) or 1
    for item in result:
        item["in_percent"] = _bar_percent(item["in_qty"], max_value)
        item["out_percent"] = _bar_percent(item["out_qty"], max_value)
    return result


def _bar_percent(value, max_value):
    """Ustun balandligi foizda. Noldan katta qiymat ko'rinib turishi uchun kamida 4%."""
    if value == 0:
        return 0
    return max(round(value / max_value * 100), 4)