from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .forms import ProfileForm, RegistrationForm
from .models import Role


User = get_user_model()


class RegistrationTests(TestCase):
    def registration_data(self, **overrides):
        data = {
            "first_name": "Alex",
            "last_name": "Driver",
            "username": "alexdriver",
            "email": "alex@example.com",
            "password1": "ParkMe-Secure-Password-481!",
            "password2": "ParkMe-Secure-Password-481!",
        }
        data.update(overrides)
        return data

    def test_registration_creates_driver_and_hashes_password(self):
        response = self.client.post(
            reverse("accounts:register"), self.registration_data()
        )

        self.assertRedirects(response, reverse("accounts:login"))
        user = User.objects.get(username="alexdriver")
        self.assertEqual(user.role, Role.DRIVER)
        self.assertTrue(user.check_password("ParkMe-Secure-Password-481!"))
        self.assertNotEqual(user.password, "ParkMe-Secure-Password-481!")

    def test_registration_requires_required_fields(self):
        response = self.client.post(reverse("accounts:register"), {})

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["form"].is_valid())
        self.assertEqual(User.objects.count(), 0)

    def test_registration_rejects_invalid_email(self):
        form = RegistrationForm(self.registration_data(email="not-an-email"))

        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)

    def test_registration_rejects_duplicate_username_and_email(self):
        User.objects.create_user(
            username="existing",
            email="existing@example.com",
            password="Existing-Secure-Password-481!",
        )

        duplicate_username = RegistrationForm(
            self.registration_data(username="EXISTING")
        )
        duplicate_email = RegistrationForm(
            self.registration_data(email="EXISTING@example.com")
        )

        self.assertFalse(duplicate_username.is_valid())
        self.assertIn("username", duplicate_username.errors)
        self.assertFalse(duplicate_email.is_valid())
        self.assertIn("email", duplicate_email.errors)

    def test_registration_rejects_password_mismatch(self):
        form = RegistrationForm(
            self.registration_data(password2="a-different-password")
        )

        self.assertFalse(form.is_valid())
        self.assertIn("password2", form.errors)


class AuthenticationAndRoleTests(TestCase):
    def setUp(self):
        self.driver = User.objects.create_user(
            username="driver",
            email="driver@example.com",
            password="Driver-Secure-Password-481!",
        )
        self.admin = User.objects.create_superuser(
            username="parkadmin",
            email="admin@example.com",
            password="Admin-Secure-Password-481!",
        )

    def test_valid_login_redirects_driver_to_driver_dashboard(self):
        response = self.client.post(
            reverse("accounts:login"),
            {"username": "driver", "password": "Driver-Secure-Password-481!"},
        )

        self.assertRedirects(response, reverse("accounts:driver_dashboard"))

    def test_invalid_login_shows_error(self):
        response = self.client.post(
            reverse("accounts:login"),
            {"username": "driver", "password": "wrong-password"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].non_field_errors())

    def test_authenticated_user_is_redirected_away_from_login(self):
        self.client.force_login(self.driver)

        response = self.client.get(reverse("accounts:login"))

        self.assertRedirects(response, reverse("accounts:driver_dashboard"))

    def test_logout_ends_session_and_requires_post(self):
        self.client.force_login(self.driver)

        get_response = self.client.get(reverse("accounts:logout"))
        self.assertEqual(get_response.status_code, 405)

        response = self.client.post(reverse("accounts:logout"))
        self.assertRedirects(response, reverse("home"))
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_unauthenticated_dashboard_redirects_to_login(self):
        response = self.client.get(reverse("accounts:driver_dashboard"))

        self.assertRedirects(
            response,
            f"{reverse('accounts:login')}?next={reverse('accounts:driver_dashboard')}",
        )

    def test_driver_cannot_open_administrator_dashboard(self):
        self.client.force_login(self.driver)

        response = self.client.get(reverse("accounts:admin_dashboard"))

        self.assertRedirects(response, reverse("accounts:driver_dashboard"))

    def test_administrator_cannot_open_driver_dashboard(self):
        self.client.force_login(self.admin)

        response = self.client.get(reverse("accounts:driver_dashboard"))

        self.assertRedirects(response, reverse("accounts:admin_dashboard"))

    def test_role_dashboards_show_role_specific_content(self):
        self.client.force_login(self.driver)
        driver_response = self.client.get(reverse("accounts:driver_dashboard"))
        self.client.force_login(self.admin)
        admin_response = self.client.get(reverse("accounts:admin_dashboard"))

        self.assertContains(driver_response, "Your parking details")
        self.assertContains(admin_response, "Administrator dashboard")
        self.assertEqual(admin_response.context["driver_count"], 1)

    def test_sidebar_shows_driver_links_and_marks_current_page(self):
        self.client.force_login(self.driver)

        response = self.client.get(reverse("parking:session_list"))

        self.assertContains(response, 'id="appSidebar"')
        self.assertContains(response, "My vehicles")
        self.assertContains(response, "Parking history")
        self.assertContains(response, "Reports")
        self.assertContains(response, 'aria-current="page"')
        self.assertNotContains(response, "Manage accounts")

    def test_sidebar_shows_administrator_directory_and_account_links(self):
        self.client.force_login(self.admin)

        response = self.client.get(reverse("accounts:admin_dashboard"))

        self.assertContains(response, "Facilities")
        self.assertContains(response, "Parking locations")
        self.assertContains(response, "Manage accounts")
        self.assertNotContains(response, "My vehicles")


class ProfileTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="driver",
            email="driver@example.com",
            first_name="Alex",
            last_name="Driver",
            password="Driver-Secure-Password-481!",
        )
        self.other_user = User.objects.create_user(
            username="other",
            email="other@example.com",
            password="Other-Secure-Password-481!",
        )

    def test_profile_requires_login(self):
        response = self.client.get(reverse("accounts:profile"))

        self.assertRedirects(
            response,
            f"{reverse('accounts:login')}?next={reverse('accounts:profile')}",
        )

    def test_user_can_view_only_their_own_profile(self):
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("accounts:profile"), {"user_id": self.other_user.pk}
        )

        self.assertEqual(response.context["profile_user"], self.user)
        self.assertContains(response, "driver@example.com")
        self.assertNotContains(response, "other@example.com")

    def test_user_can_update_profile_but_not_role_or_username(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("accounts:edit_profile"),
            {
                "first_name": "Updated",
                "last_name": "Name",
                "email": "updated@example.com",
                "role": Role.ADMINISTRATOR,
                "username": "administrator",
            },
        )

        self.assertRedirects(response, reverse("accounts:profile"))
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "Updated")
        self.assertEqual(self.user.email, "updated@example.com")
        self.assertEqual(self.user.username, "driver")
        self.assertEqual(self.user.role, Role.DRIVER)
        self.assertNotIn("role", ProfileForm(instance=self.user).fields)

    def test_profile_update_rejects_duplicate_email(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("accounts:edit_profile"),
            {
                "first_name": "Alex",
                "last_name": "Driver",
                "email": "OTHER@example.com",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("email", response.context["form"].errors)
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "driver@example.com")
