from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status

from tickets.tests.helpers import PASSWORD, SupportDeskTestCase

User = get_user_model()


class RegisterTests(SupportDeskTestCase):
    url = reverse("register")

    def payload(self, **overrides):
        data = {"username": "newuser", "email": "new@example.com", "password": PASSWORD}
        return {**data, **overrides}

    def test_register_always_creates_a_customer(self):
        response = self.client.post(self.url, self.payload(role="admin"))

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(User.objects.get(username="newuser").role, User.Role.CUSTOMER)
        self.assertNotIn("password", response.data)

    def test_register_rejects_duplicate_email(self):
        response = self.client.post(self.url, self.payload(email="CUSTOMER@example.com"))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)

    def test_register_rejects_weak_password(self):
        response = self.client.post(self.url, self.payload(password="12345"))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(User.objects.filter(username="newuser").exists())


class LoginTests(SupportDeskTestCase):
    def test_login_returns_tokens_and_user(self):
        response = self.client.post(
            reverse("login"), {"username": "customer", "password": PASSWORD}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertEqual(response.data["user"]["role"], "customer")

    def test_login_with_wrong_password_fails(self):
        response = self.client.post(reverse("login"), {"username": "customer", "password": "x"})

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_me_requires_a_valid_token(self):
        self.assertEqual(self.client.get(reverse("me")).status_code, status.HTTP_401_UNAUTHORIZED)

        login = self.client.post(reverse("login"), {"username": "agent", "password": PASSWORD})
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")
        response = self.client.get(reverse("me"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["username"], "agent")

    def test_refresh_token_is_rotated_and_old_one_stops_working(self):
        login = self.client.post(reverse("login"), {"username": "customer", "password": PASSWORD})
        old_refresh = login.data["refresh"]

        first = self.client.post(reverse("token-refresh"), {"refresh": old_refresh})
        second = self.client.post(reverse("token-refresh"), {"refresh": old_refresh})

        self.assertEqual(first.status_code, status.HTTP_200_OK)
        self.assertIn("access", first.data)
        self.assertNotEqual(first.data["refresh"], old_refresh)
        self.assertEqual(second.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout_blacklists_the_refresh_token(self):
        login = self.client.post(reverse("login"), {"username": "customer", "password": PASSWORD})
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")

        logout = self.client.post(reverse("logout"), {"refresh": login.data["refresh"]})
        refresh = self.client.post(reverse("token-refresh"), {"refresh": login.data["refresh"]})

        self.assertEqual(logout.status_code, status.HTTP_205_RESET_CONTENT)
        self.assertEqual(refresh.status_code, status.HTTP_401_UNAUTHORIZED)


class UserManagementTests(SupportDeskTestCase):
    def test_only_admin_can_list_users(self):
        self.login_as(self.customer)
        self.assertEqual(self.client.get("/api/users/").status_code, status.HTTP_403_FORBIDDEN)

        self.login_as(self.admin)
        response = self.client.get("/api/users/", {"role": "agent"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual({u["username"] for u in response.data["results"]}, {"agent", "agent2"})

    def test_admin_can_change_another_users_role(self):
        self.login_as(self.admin)

        response = self.client.patch(f"/api/users/{self.customer.pk}/", {"role": "agent"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.role, User.Role.AGENT)

    def test_admin_cannot_change_own_role(self):
        self.login_as(self.admin)

        response = self.client.patch(f"/api/users/{self.admin.pk}/", {"role": "customer"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.admin.refresh_from_db()
        self.assertEqual(self.admin.role, User.Role.ADMIN)

    def test_createsuperuser_gets_admin_role(self):
        user = User.objects.create_superuser("root", "root@example.com", PASSWORD)

        self.assertEqual(user.role, User.Role.ADMIN)
