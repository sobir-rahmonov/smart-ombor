from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.views import LoginView
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import BooleanField, Count, ExpressionWrapper, F, Q
from django.db.models.deletion import ProtectedError
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import (
    CreateView,
    DeleteView,
    ListView,
    TemplateView,
    UpdateView,
)
from django.views.generic.edit import FormMixin

from .forms import (
    CategoryForm,
    ProductForm,
    StockMovementForm,
    StyledLoginForm,
    UserCreateForm,
)
from .models import Category, Product, StockMovement

from .models import Category, Product, StockMovement
from .services import (
    InsufficientStockError,
    create_stock_movement,
    delete_user_with_data,
    get_low_stock_products,
    get_total_stock_value,
    get_weekly_movements,
)

User = get_user_model()


from .forms import StyledLoginForm   # importlar qatorida bo'lishi shart




# ---------- Umumiy yordamchi klasslar ----------

class SuperuserRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Faqat bosh admin (superuser) kira oladi."""

    def test_func(self):
        return self.request.user.is_superuser


class OwnerQuerysetMixin:
    """Faqat joriy foydalanuvchining yozuvlarini qaytaradi."""

    def get_queryset(self):
        return super().get_queryset().filter(owner=self.request.user)


class OwnerFormKwargsMixin:
    """Formaga joriy foydalanuvchini egasi sifatida beradi."""

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["owner"] = self.request.user
        return kwargs


class SafeDeleteView(LoginRequiredMixin, OwnerQuerysetMixin, DeleteView):
    """Bog'langan yozuvi bor obyektni o'chirmaydi, xabar ko'rsatadi."""

    template_name = "omborapp/confirm_delete.html"
    success_message = "Muvaffaqiyatli o'chirildi."
    protected_message = "Bu yozuv boshqa ma'lumotlarga bog'langan, o'chirib bo'lmaydi."

    def form_valid(self, form):
        try:
            response = super().form_valid(form)
        except ProtectedError:
            messages.error(self.request, self.protected_message)
            return redirect(self.success_url)
        messages.success(self.request, self.success_message)
        return response


# ---------- Kirish ----------



   

class AdminLoginView(LoginView):
    template_name = "omborapp/login.html"
    authentication_form = StyledLoginForm
    redirect_authenticated_user = True


# ---------- Dashboard ----------

class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "omborapp/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        movement_type = StockMovement.MovementType

        movements = StockMovement.objects.filter(product__owner=user)
        today_movements = movements.filter(created_at__date=timezone.localdate())
        today_in = today_movements.filter(movement_type=movement_type.IN).count()
        today_out = today_movements.filter(movement_type=movement_type.OUT).count()
        low_stock = get_low_stock_products(user)

        context.update(
            {
                "products_count": Product.objects.filter(owner=user).count(),
                "categories_count": Category.objects.filter(owner=user).count(),
                "total_value": get_total_stock_value(user),
                "low_stock_count": low_stock.count(),
                "low_stock_products": low_stock[:5],
                "today_in": today_in,
                "today_out": today_out,
                "today_total": today_in + today_out,
                "recent_movements": movements.select_related("product")[:5],
            }
        )
        return context


# ---------- Kategoriyalar ----------

class CategoryListView(LoginRequiredMixin, OwnerQuerysetMixin, ListView):
    model = Category
    paginate_by = 10

    def get_queryset(self):
        return super().get_queryset().annotate(products_count=Count("products"))


class CategoryCreateView(
    LoginRequiredMixin, OwnerFormKwargsMixin, SuccessMessageMixin, CreateView
):
    model = Category
    form_class = CategoryForm
    success_url = reverse_lazy("category_list")
    success_message = "Kategoriya qo'shildi."


class CategoryUpdateView(
    LoginRequiredMixin, OwnerQuerysetMixin, OwnerFormKwargsMixin,
    SuccessMessageMixin, UpdateView,
):
    model = Category
    form_class = CategoryForm
    success_url = reverse_lazy("category_list")
    success_message = "Kategoriya yangilandi."


class CategoryDeleteView(SafeDeleteView):
    model = Category
    success_url = reverse_lazy("category_list")
    success_message = "Kategoriya o'chirildi."
    protected_message = "Bu kategoriyada mahsulotlar bor, avval ularni o'chiring yoki ko'chiring."


# ---------- Mahsulotlar ----------

class ProductListView(LoginRequiredMixin, OwnerQuerysetMixin, ListView):
    model = Product
    paginate_by = 10

    def get_queryset(self):
        queryset = super().get_queryset().select_related("category")
        params = self.request.GET

        search = params.get("q", "").strip()
        if search:
            queryset = queryset.filter(name__icontains=search)

        category_id = params.get("category", "")
        if category_id.isdigit():
            queryset = queryset.filter(category_id=category_id)

        status = params.get("status")
        if status == "low":
            queryset = queryset.filter(quantity__lte=F("min_quantity"))
        elif status == "ok":
            queryset = queryset.filter(quantity__gt=F("min_quantity"))

        return queryset.annotate(
            low=ExpressionWrapper(
                Q(quantity__lte=F("min_quantity")), output_field=BooleanField()
            )
        ).order_by("-low", "name")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        products = Product.objects.filter(owner=user)
        all_count = products.count()
        low_count = products.filter(quantity__lte=F("min_quantity")).count()

        params = self.request.GET.copy()
        params.pop("page", None)
        tab_params = params.copy()
        tab_params.pop("status", None)

        context.update(
            {
                "categories": Category.objects.filter(owner=user),
                "search": self.request.GET.get("q", ""),
                "selected_category": self.request.GET.get("category", ""),
                "selected_status": self.request.GET.get("status", ""),
                "querystring": params.urlencode(),
                "tab_query": tab_params.urlencode(),
                "all_count": all_count,
                "low_count": low_count,
                "ok_count": all_count - low_count,
            }
        )
        return context


class ProductCreateView(
    LoginRequiredMixin, OwnerFormKwargsMixin, SuccessMessageMixin, CreateView
):
    model = Product
    form_class = ProductForm
    success_url = reverse_lazy("product_list")
    success_message = "Mahsulot qo'shildi."


class ProductUpdateView(
    LoginRequiredMixin, OwnerQuerysetMixin, OwnerFormKwargsMixin,
    SuccessMessageMixin, UpdateView,
):
    model = Product
    form_class = ProductForm
    success_url = reverse_lazy("product_list")
    success_message = "Mahsulot yangilandi."


class ProductDeleteView(SafeDeleteView):
    model = Product
    success_url = reverse_lazy("product_list")
    success_message = "Mahsulot o'chirildi."
    protected_message = "Bu mahsulotning kirim/chiqim tarixi bor, o'chirib bo'lmaydi."


# ---------- Kirim / Chiqim ----------

class MovementListView(LoginRequiredMixin, OwnerFormKwargsMixin, FormMixin, ListView):
    """Tarix ro'yxati va yangi harakat formasi bitta sahifada."""

    model = StockMovement
    template_name = "omborapp/movement_list.html"
    form_class = StockMovementForm
    paginate_by = 10
    success_url = reverse_lazy("movement_list")


    def get_initial(self):
        """?new=in|out va ?product=<id> bo'yicha formani oldindan to'ldiradi."""
        initial = super().get_initial()
        action = self.request.GET.get("new")
        if action in StockMovement.MovementType.values:
            initial["movement_type"] = action

        product_id = self.request.GET.get("product", "")
        if product_id.isdigit():
            product = Product.objects.filter(
                owner=self.request.user, pk=product_id
            ).first()
            if product:
                initial["product"] = product.pk
                initial["price"] = product.price
        return initial

    def get_queryset(self):
        queryset = StockMovement.objects.filter(
            product__owner=self.request.user
        ).select_related("product")
        movement_type = self.request.GET.get("type")
        if movement_type in StockMovement.MovementType.values:
            queryset = queryset.filter(movement_type=movement_type)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        params = self.request.GET.copy()
        params.pop("page", None)
        context["selected_type"] = self.request.GET.get("type", "")
        context["querystring"] = params.urlencode()
        context["products_data"] = {
            product.pk: {"price": str(product.price), "quantity": product.quantity}
            for product in Product.objects.filter(owner=self.request.user)
        }
        return context

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        if form.is_valid():
            return self.form_valid(form)
        return self._render_invalid(form)

    def form_valid(self, form):
        try:
            create_stock_movement(**form.cleaned_data)
        except InsufficientStockError as error:
            form.add_error("quantity", str(error))
            return self._render_invalid(form)
        messages.success(self.request, "Harakat saqlandi.")
        return super().form_valid(form)

    def _render_invalid(self, form):
        self.object_list = self.get_queryset()
        return self.form_invalid(form)


# ---------- Foydalanuvchilar (faqat bosh admin) ----------

class UserListView(SuperuserRequiredMixin, ListView):
    model = User
    template_name = "omborapp/user_list.html"
    paginate_by = 10

    def get_queryset(self):
        return User.objects.annotate(products_count=Count("products")).order_by(
            "-is_superuser", "-date_joined"
        )


class UserCreateView(SuperuserRequiredMixin, SuccessMessageMixin, CreateView):
    model = User
    form_class = UserCreateForm
    template_name = "omborapp/user_form.html"
    success_url = reverse_lazy("user_list")
    success_message = "Foydalanuvchi qo'shildi."


class UserDeleteView(SuperuserRequiredMixin, DeleteView):
    """Mijozni va uning barcha ma'lumotlarini o'chiradi. Adminlarni o'chirib bo'lmaydi."""

    template_name = "omborapp/confirm_delete.html"
    success_url = reverse_lazy("user_list")

    def get_queryset(self):
        return User.objects.filter(is_superuser=False)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        target = self.object
        context["warning"] = (
            "Bu hisob bilan birga uning barcha ma'lumotlari ham butunlay o'chadi. "
            "Qaytarib bo'lmaydi."
        )
        context["delete_stats"] = [
            (Product.objects.filter(owner=target).count(), "mahsulot"),
            (Category.objects.filter(owner=target).count(), "kategoriya"),
            (
                StockMovement.objects.filter(product__owner=target).count(),
                "kirim/chiqim yozuvi",
            ),
        ]
        return context
    def form_valid(self, form):
        delete_user_with_data(self.object)
        messages.success(self.request, "Foydalanuvchi va uning ma'lumotlari o'chirildi.")
        return redirect(self.success_url)