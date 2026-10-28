from django.contrib import admin

from .models import Category, Product, StockMovement


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "created_at")
    list_filter = ("owner",)
    search_fields = ("name",)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "category", "price", "quantity", "min_quantity")
    list_filter = ("owner", "category")
    search_fields = ("name",)
    # Qoldiq faqat kirim/chiqim orqali o'zgaradi
    readonly_fields = ("quantity",)


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    """Faqat ko'rish uchun: harakatni shu yerdan yozsak, qoldiq yangilanmay qoladi."""

    list_display = ("created_at", "product", "movement_type", "quantity", "price")
    list_filter = ("movement_type",)
    search_fields = ("product__name",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False