from django.conf import settings
from django.db import models


class Category(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Egasi",
        on_delete=models.PROTECT,
        related_name="categories",
    )
    name = models.CharField("Nomi", max_length=100)
    created_at = models.DateTimeField("Yaratilgan vaqti", auto_now_add=True)

    class Meta:
        verbose_name = "Kategoriya"
        verbose_name_plural = "Kategoriyalar"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["owner", "name"], name="unique_category_name_per_owner"
            )
        ]

    def __str__(self):
        return self.name


class Product(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Egasi",
        on_delete=models.PROTECT,
        related_name="products",
    )
    name = models.CharField("Nomi", max_length=200)
    category = models.ForeignKey(
        Category,
        verbose_name="Kategoriya",
        on_delete=models.PROTECT,
        related_name="products",
    )
    price = models.DecimalField("Narxi", max_digits=12, decimal_places=2)
    quantity = models.PositiveIntegerField("Ombordagi qoldiq", default=0)
    min_quantity = models.PositiveIntegerField(
        "Minimal qoldiq", default=5,
        help_text="Qoldiq shu sondan kam bo'lsa, ogohlantirish chiqadi",
    )
    created_at = models.DateTimeField("Yaratilgan vaqti", auto_now_add=True)

    class Meta:
        verbose_name = "Mahsulot"
        verbose_name_plural = "Mahsulotlar"
        ordering = ["name"]

    def __str__(self):
        return self.name

    @property
    def is_low_stock(self):
        return self.quantity <= self.min_quantity

    @property
    def total_value(self):
        return self.price * self.quantity


class StockMovement(models.Model):
    class MovementType(models.TextChoices):
        IN = "in", "Kirim"
        OUT = "out", "Chiqim"

    product = models.ForeignKey(
        Product,
        verbose_name="Mahsulot",
        on_delete=models.PROTECT,
        related_name="movements",
    )
    movement_type = models.CharField(
        "Turi", max_length=3, choices=MovementType.choices
    )
    quantity = models.PositiveIntegerField("Miqdori")
    price = models.DecimalField("Narxi (1 dona)", max_digits=12, decimal_places=2)
    note = models.CharField("Izoh", max_length=255, blank=True)
    created_at = models.DateTimeField("Sana", auto_now_add=True)

    class Meta:
        verbose_name = "Ombor harakati"
        verbose_name_plural = "Ombor harakatlari"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_movement_type_display()}: {self.product} ({self.quantity})"

    @property
    def total_price(self):
        return self.price * self.quantity