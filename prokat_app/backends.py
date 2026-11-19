from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q
from .phone_utils import normalize_phone


class EmailPhoneBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        identifier = username or kwargs.get(get_user_model().USERNAME_FIELD)
        if not identifier or password is None:
            return None

        UserModel = get_user_model()
        lookup = Q(username__iexact=identifier) | Q(email__iexact=identifier)
        phone = normalize_phone(identifier)
        if phone:
            lookup |= Q(kontakty__telefon=phone)
        user = UserModel._default_manager.filter(lookup).distinct().first()
        if user and user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
