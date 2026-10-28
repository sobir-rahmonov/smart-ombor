from django.contrib.auth.views import LogoutView
from django.urls import path

from . import views

urlpatterns = [
    # Kirish / chiqish
    path("login/", views.AdminLoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),

    # Dashboard
    path("", views.DashboardView.as_view(), name="dashboard"),

    # Kategoriyalar
    path("categories/", views.CategoryListView.as_view(), name="category_list"),
    path("categories/add/", views.CategoryCreateView.as_view(), name="category_create"),
    path("categories/<int:pk>/edit/", views.CategoryUpdateView.as_view(), name="category_update"),
    path("categories/<int:pk>/delete/", views.CategoryDeleteView.as_view(), name="category_delete"),

    # Mahsulotlar
    path("products/", views.ProductListView.as_view(), name="product_list"),
    path("products/add/", views.ProductCreateView.as_view(), name="product_create"),
    path("products/<int:pk>/edit/", views.ProductUpdateView.as_view(), name="product_update"),
    path("products/<int:pk>/delete/", views.ProductDeleteView.as_view(), name="product_delete"),

    # Kirim / Chiqim
    path("movements/", views.MovementListView.as_view(), name="movement_list"),

    # Foydalanuvchilar (faqat bosh admin)
    path("users/", views.UserListView.as_view(), name="user_list"),
    path("users/add/", views.UserCreateView.as_view(), name="user_create"),
    path("users/<int:pk>/delete/", views.UserDeleteView.as_view(), name="user_delete"),
]

