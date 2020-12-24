from django.contrib.auth.backends import BaseBackend
from rest_framework.generics import get_object_or_404

from api.models import User


class AuthenticationWithoutPassword(BaseBackend):

    def authenticate(self, request, email=None):
        if email is None:
            email = request.data.get('email', '')
        try:
            return get_object_or_404(User, email=email)
        except User.DoesNotExist:
            return None

    def get_user(self, user_id):
        try:
            return get_object_or_404(User, pk=user_id)
        except User.DoesNotExist:
            return None
