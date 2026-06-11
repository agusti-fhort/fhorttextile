"""Backend d'autenticació: accepta email O username com a identificador.

Permet que l'usuari introdueixi el seu email al formulari de login (el camp del JWT
segueix sent `username`). Ordre: 1) username exacte (retrocompatibilitat), 2) email
case-insensitive d'un usuari ACTIU. Email duplicat o inexistent → None (no autentica).
"""
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model


class EmailOrUsernameBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        User = get_user_model()
        # 1) Intentar per username (retrocompatibilitat).
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            # 2) Intentar per email (case-insensitive, NOMÉS actius). 0 o >1 → no autentica.
            try:
                user = User.objects.get(email__iexact=username, is_active=True)
            except (User.DoesNotExist, User.MultipleObjectsReturned):
                return None
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
