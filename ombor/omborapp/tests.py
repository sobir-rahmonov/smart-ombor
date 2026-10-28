from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Category, Product, StockMovement
from .services import (
    InsufficientStockError,
    create_stock_movement,
    delete_user_with_data,
    get_low_stock_products,
    get_weekly_movements,
)

User = get_user_model()


def make_product(owner, name, quantity=0, min_quantity=5, price="1000"):
    category, _ = Category.objects.get_or_create(owner=owner, name="Umumiy")
    return Product.objects.create(
        owner=owner,
        name=name,
        category=category,
        price=Decimal(price),
        quantity=quantity,
        min_quantity=min_quantity,
    )


class BaseTestCase(TestCase):
    """Ikkita mijoz va bitta bosh admin tayyorlaydi."""

    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_superuser("boss", password="Boss-pass-123")
        cls.aziz = User.objects.create_user("aziz", password="Aziz-pass-123")
        cls.madina = User.objects.create_user("madina", password="Madina-pass-123")
        cls.aziz_product = make_product(cls.aziz, "Aziz tovari", quantity=20)
        cls.madina_product = make_product(cls.madina, "Madina tovari", quantity=20)


class StockServiceTests(BaseTestCase):
    def test_income_increases_quantity(self):
        create_stock_movement(
            product=self.aziz_product,
            movement_type=StockMovement.MovementType.IN,
            quantity=5,
            price=Decimal("1000"),
        )
        self.aziz_product.refresh_from_db()
        self.assertEqual(self.aziz_product.quantity, 25)

    def test_outcome_decreases_quantity(self):
        create_stock_movement(
            product=self.aziz_product,
            movement_type=StockMovement.MovementType.OUT,
            quantity=8,
            price=Decimal("1500"),
        )
        self.aziz_product.refresh_from_db()
        self.assertEqual(self.aziz_product.quantity, 12)

    def test_outcome_more_than_stock_is_rejected(self):
        with self.assertRaises(InsufficientStockError):
            create_stock_movement(
                product=self.aziz_product,
                movement_type=StockMovement.MovementType.OUT,
                quantity=21,
                price=Decimal("1500"),
            )
        self.aziz_product.refresh_from_db()
        self.assertEqual(self.aziz_product.quantity, 20)
        self.assertEqual(StockMovement.objects.count(), 0)

    def test_low_stock_only_for_owner(self):
        make_product(self.aziz, "Kam tovar", quantity=2, min_quantity=5)
        make_product(self.madina, "Madinaning kam tovari", quantity=1, min_quantity=5)

        names = [p.name for p in get_low_stock_products(self.aziz)]
        self.assertEqual(names, ["Kam tovar"])

    def test_weekly_movements_has_seven_days(self):
        create_stock_movement(
            product=self.aziz_product,
            movement_type=StockMovement.MovementType.IN,
            quantity=10,
            price=Decimal("1000"),
        )
        week = get_weekly_movements(self.aziz)
        self.assertEqual(len(week), 7)
        self.assertEqual(week[-1]["in_qty"], 10)
        self.assertEqual(week[-1]["in_percent"], 100)

    def test_delete_user_removes_all_their_data(self):
        create_stock_movement(
            product=self.aziz_product,
            movement_type=StockMovement.MovementType.IN,
            quantity=1,
            price=Decimal("1000"),
        )
        delete_user_with_data(self.aziz)

        self.assertFalse(User.objects.filter(username="aziz").exists())
        self.assertFalse(Product.objects.filter(name="Aziz tovari").exists())
        self.assertEqual(StockMovement.objects.count(), 0)
        # Boshqa mijozning ma'lumoti saqlanib qoladi
        self.assertTrue(Product.objects.filter(name="Madina tovari").exists())


class AuthenticationTests(BaseTestCase):
    def test_pages_require_login(self):
        for name in ["dashboard", "product_list", "category_list", "movement_list"]:
            response = self.client.get(reverse(name))
            self.assertEqual(response.status_code, 302, name)
            self.assertIn(reverse("login"), response.url, name)

    def test_login_with_correct_password(self):
        response = self.client.post(
            reverse("login"), {"username": "aziz", "password": "Aziz-pass-123"}
        )
        self.assertRedirects(response, reverse("dashboard"))

    def test_login_with_wrong_password_fails(self):
        response = self.client.post(
            reverse("login"), {"username": "aziz", "password": "xato"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].non_field_errors())


class DataIsolationTests(BaseTestCase):
    """Eng muhim testlar: mijoz boshqa mijozning ma'lumotini ko'ra olmaydi."""

    def setUp(self):
        self.client.force_login(self.aziz)

    def test_product_list_shows_only_own_products(self):
        response = self.client.get(reverse("product_list"))
        self.assertContains(response, "Aziz tovari")
        self.assertNotContains(response, "Madina tovari")

    def test_dashboard_loads_for_client(self):
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 200)

    def test_cannot_open_other_clients_product(self):
        url = reverse("product_update", args=[self.madina_product.pk])
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_cannot_delete_other_clients_product(self):
        url = reverse("product_delete", args=[self.madina_product.pk])
        self.assertEqual(self.client.post(url).status_code, 404)
        self.assertTrue(Product.objects.filter(pk=self.madina_product.pk).exists())

    def test_cannot_move_stock_of_other_clients_product(self):
        response = self.client.post(
            reverse("movement_list"),
            {
                "movement_type": "in",
                "product": self.madina_product.pk,
                "quantity": 5,
                "price": "1000",
                "note": "",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("product", response.context["form"].errors)
        self.assertEqual(StockMovement.objects.count(), 0)
        self.madina_product.refresh_from_db()
        self.assertEqual(self.madina_product.quantity, 20)

    def test_movement_history_shows_only_own_movements(self):
        create_stock_movement(
            product=self.madina_product,
            movement_type=StockMovement.MovementType.IN,
            quantity=3,
            price=Decimal("1000"),
        )
        response = self.client.get(reverse("movement_list"))
        self.assertNotContains(response, "Madina tovari")


class MovementViewTests(BaseTestCase):
    def setUp(self):
        self.client.force_login(self.aziz)
        self.url = reverse("movement_list")

    def test_income_via_form_updates_quantity(self):
        response = self.client.post(
            self.url,
            {
                "movement_type": "in",
                "product": self.aziz_product.pk,
                "quantity": 10,
                "price": "1200",
                "note": "Yangi partiya",
            },
        )
        self.assertRedirects(response, self.url)
        self.aziz_product.refresh_from_db()
        self.assertEqual(self.aziz_product.quantity, 30)
        self.assertEqual(StockMovement.objects.get().price, Decimal("1200"))

    def test_outcome_more_than_stock_shows_error(self):
        response = self.client.post(
            self.url,
            {
                "movement_type": "out",
                "product": self.aziz_product.pk,
                "quantity": 100,
                "price": "1500",
                "note": "",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("quantity", response.context["form"].errors)
        self.aziz_product.refresh_from_db()
        self.assertEqual(self.aziz_product.quantity, 20)


class UserManagementTests(BaseTestCase):
    def test_client_cannot_open_user_pages(self):
        self.client.force_login(self.aziz)
        for name in ["user_list", "user_create"]:
            self.assertEqual(self.client.get(reverse(name)).status_code, 403, name)

    def test_admin_sees_user_list(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("user_list"))
        self.assertContains(response, "aziz")
        self.assertContains(response, "madina")

    def test_admin_creates_client_account(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("user_create"),
            {
                "username": "yangi_mijoz",
                "password1": "Yangi-parol-2026",
                "password2": "Yangi-parol-2026",
            },
        )
        self.assertRedirects(response, reverse("user_list"))
        created = User.objects.get(username="yangi_mijoz")
        self.assertFalse(created.is_superuser)
        self.assertFalse(created.is_staff)

    def test_admin_deletes_client_with_data(self):
        self.client.force_login(self.admin)
        url = reverse("user_delete", args=[self.aziz.pk])
        response = self.client.post(url)
        self.assertRedirects(response, reverse("user_list"))
        self.assertFalse(User.objects.filter(pk=self.aziz.pk).exists())
        self.assertFalse(Product.objects.filter(owner_id=self.aziz.pk).exists())

    def test_admin_cannot_delete_admin(self):
        self.client.force_login(self.admin)
        url = reverse("user_delete", args=[self.admin.pk])
        self.assertEqual(self.client.post(url).status_code, 404)
        self.assertTrue(User.objects.filter(pk=self.admin.pk).exists())