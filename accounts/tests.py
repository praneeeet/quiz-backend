import uuid
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()

class AccountsTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='player1', email='p1@test.com', password='Pass123!', role='player'
        )
        self.register_url = '/api/v1/auth/register/'
        self.login_url = '/api/v1/auth/login/'
        self.profile_url = '/api/v1/auth/profile/'
        self.logout_url = '/api/v1/auth/logout/'

    def test_register_success(self):
        # Register a new user
        data = {'username': 'newuser', 'email': 'new@test.com', 'password': 'Pass123!', 'password_confirm': 'Pass123!'}
        response = self.client.post(self.register_url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_login_success(self):
        # Login with existing credentials
        data = {'username': 'player1', 'password': 'Pass123!'}
        response = self.client.post(self.login_url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_profile_access_unauthenticated(self):
        # Cannot access profile without login
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_profile_access_authenticated(self):
        # Can access profile after login
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_profile_update_works(self):
        # Can update email via profile
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(self.profile_url, {'email': 'newemail@test.com'})
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, 'newemail@test.com')

    def test_role_cannot_be_changed_via_profile(self):
        # Player cannot promote themselves to admin via profile
        self.client.force_authenticate(user=self.user)
        self.client.patch(self.profile_url, {'role': 'admin'})
        self.user.refresh_from_db()
        self.assertEqual(self.user.role, 'player')

    def test_logout_success(self):
        # Logout using refresh token
        self.client.force_authenticate(user=self.user)
        refresh = RefreshToken.for_user(self.user)
        response = self.client.post(self.logout_url, {'refresh': str(refresh)})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
