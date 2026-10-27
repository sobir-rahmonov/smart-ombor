from .services import get_low_stock_products


def low_stock(request):
    """Sidebar'dagi 'kam qolgan' belgisi uchun hamma sahifaga son beradi."""
    if request.user.is_authenticated:
        return {"low_stock_count": get_low_stock_products(request.user).count()}
    return {}