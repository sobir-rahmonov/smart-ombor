from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import Category, Product, StockMovement


class StyledFormMixin:
    """Barcha maydonlarga CSS klasslarini avtomatik qo'shadi."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, forms.RadioSelect):
                continue
            is_select = isinstance(widget, forms.Select)
            widget.attrs["class"] = "form-select" if is_select else "form-input"


class OwnerFormMixin:
    """Formaga egasini (owner) beradi, shunda forma faqat uning ma'lumotini ko'radi."""

    def __init__(self, *args, owner, **kwargs):
        self.owner = owner
        super().__init__(*args, **kwargs)


class CategoryForm(OwnerFormMixin, StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Category
        fields = ["name"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.owner = self.owner

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        exists = (
            Category.objects.filter(owner=self.owner, name__iexact=name)
            .exclude(pk=self.instance.pk)
            .exists()
        )
        if exists:
            raise forms.ValidationError("Bunday kategoriya allaqachon mavjud.")
        return name


class ProductForm(OwnerFormMixin, StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Product
        fields = ["name", "category", "price", "min_quantity"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.owner = self.owner
        category = self.fields["category"]
        category.queryset = Category.objects.filter(owner=self.owner)
        category.empty_label = "Kategoriyani tanlang"


class StockMovementForm(OwnerFormMixin, StyledFormMixin, forms.ModelForm):
    class Meta:
        model = StockMovement
        fields = ["movement_type", "product", "quantity", "price", "note"]
        widgets = {
            "movement_type": forms.RadioSelect,
            "quantity": forms.NumberInput(attrs={"min": 1}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        movement_type = self.fields["movement_type"]
        movement_type.choices = StockMovement.MovementType.choices
        movement_type.initial = StockMovement.MovementType.IN

        product = self.fields["product"]
        product.queryset = Product.objects.filter(owner=self.owner)
        product.empty_label = "Mahsulotni tanlang"

    def clean_quantity(self):
        quantity = self.cleaned_data["quantity"]
        if quantity < 1:
            raise forms.ValidationError("Miqdor kamida 1 bo'lishi kerak.")
        return quantity

    def clean_price(self):
        price = self.cleaned_data["price"]
        if price < 0:
            raise forms.ValidationError("Narx manfiy bo'lmasligi kerak.")
        return price

    def clean(self):
        cleaned_data = super().clean()
        product = cleaned_data.get("product")
        quantity = cleaned_data.get("quantity")
        is_out = cleaned_data.get("movement_type") == StockMovement.MovementType.OUT

        if is_out and product and quantity and quantity > product.quantity:
            self.add_error("quantity", f"Omborda faqat {product.quantity} dona qolgan.")
        return cleaned_data


class UserCreateForm(StyledFormMixin, UserCreationForm):
    """Bosh admin mijoz uchun login va parol yaratadi."""

    class Meta(UserCreationForm.Meta):
        fields = ["username"]
        labels = {"username": "Login"}
        help_texts = {"username": "Mijoz tizimga shu login bilan kiradi."}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["password1"].label = "Parol"
        self.fields["password1"].help_text = "Kamida 8 ta belgi, faqat raqamdan iborat bo'lmasin."
        self.fields["password2"].label = "Parolni takrorlang"
        self.fields["password2"].help_text = ""