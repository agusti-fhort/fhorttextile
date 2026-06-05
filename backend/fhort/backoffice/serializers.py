# Sprint 1 — Capa 9: serializers d'autenticació i perfil del backoffice.
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer


class BackofficeTokenObtainSerializer(TokenObtainPairSerializer):
    """Emissió de token JWT restringida a usuaris amb BackofficeUser actiu.

    Afegeix `rol` i `nom` als claims del token perquè el frontend pugui pintar la
    UI sense una segona crida. La porta d'accés és validate(): qualsevol usuari
    del public sense perfil de backoffice (o desactivat) queda fora.
    """

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        perfil = getattr(user, 'backoffice_profile', None)
        token['rol'] = perfil.rol if perfil is not None else None
        token['nom'] = f'{user.first_name} {user.last_name}'.strip() or user.email
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        perfil = getattr(self.user, 'backoffice_profile', None)
        if perfil is None or not perfil.actiu:
            raise AuthenticationFailed('Accés no autoritzat')
        return data


class BackofficeUserMeSerializer(serializers.Serializer):
    """Perfil de l'usuari de backoffice autenticat (només lectura).

    Pren una instància de BackofficeUser; els camps d'identitat es projecten des
    de l'auth.User associat.
    """

    id = serializers.IntegerField(source='usuari.id', read_only=True)
    email = serializers.EmailField(source='usuari.email', read_only=True)
    first_name = serializers.CharField(source='usuari.first_name', read_only=True)
    last_name = serializers.CharField(source='usuari.last_name', read_only=True)
    rol = serializers.CharField(read_only=True)
    actiu = serializers.BooleanField(read_only=True)
    data_alta = serializers.DateField(read_only=True)
    ultim_acces = serializers.DateTimeField(read_only=True)
