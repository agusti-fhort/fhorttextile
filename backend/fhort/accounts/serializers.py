from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import UserProfile
from .capabilities import get_capabilities, get_allowed_task_types, ROLE_CAPABILITIES


User = get_user_model()


class MeSerializer(serializers.ModelSerializer):
    """Profile of the authenticated user (current tenant)."""

    full_name = serializers.SerializerMethodField()
    avatar_url = serializers.SerializerMethodField()
    nom_complet = serializers.SerializerMethodField()
    rol_nom = serializers.SerializerMethodField()
    color_avatar = serializers.SerializerMethodField()
    capabilities = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'id', 'username', 'first_name', 'last_name', 'email',
            'full_name', 'avatar_url',
            'nom_complet', 'rol_nom', 'color_avatar',
            'capabilities',
        )

    def _profile(self, obj):
        return getattr(obj, 'profile', None)

    def get_full_name(self, obj):
        full = f'{obj.first_name} {obj.last_name}'.strip()
        if full:
            return full
        profile = self._profile(obj)
        return getattr(profile, 'nom_complet', '') or obj.username

    def get_avatar_url(self, obj):
        # If an ImageField is added in the future, return its URL.
        # For now there is no uploaded avatar; we keep the field but always None.
        return None

    def get_nom_complet(self, obj):
        profile = self._profile(obj)
        return profile.nom_complet if profile else ''

    def get_rol_nom(self, obj):
        profile = self._profile(obj)
        return profile.rol_nom if profile else ''

    def get_color_avatar(self, obj):
        profile = self._profile(obj)
        return profile.color_avatar if profile else '#888888'

    def get_capabilities(self, obj):
        return sorted(get_capabilities(obj))


class UserListSerializer(serializers.ModelSerializer):
    """For the responsible-person selector. Only active tenant users."""

    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('id', 'username', 'full_name', 'email')

    def get_full_name(self, obj):
        full = f'{obj.first_name} {obj.last_name}'.strip()
        if full:
            return full
        profile = getattr(obj, 'profile', None)
        return getattr(profile, 'nom_complet', '') or obj.username


class UserProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)

    class Meta:
        model = UserProfile
        fields = (
            'id', 'username', 'email',
            'nom_complet', 'rol_nom', 'actiu',
            'cost_hora', 'color_avatar',
        )


class UserAdminSerializer(serializers.ModelSerializer):
    """Gestió d'usuaris (gated manage_users). Escriu rol_nom/actiu/permisos al UserProfile
    relacionat (queryset = User amb select_related('profile')). capabilities/allowed_tasks =
    derivats de només-lectura per a la matriu de permisos del front."""

    full_name = serializers.SerializerMethodField()
    rol_nom = serializers.CharField(source='profile.rol_nom')
    actiu = serializers.BooleanField(source='profile.actiu')
    permisos = serializers.JSONField(source='profile.permisos')
    capabilities = serializers.SerializerMethodField()
    allowed_tasks = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'id', 'username', 'email', 'full_name',
            'rol_nom', 'actiu', 'permisos',
            'capabilities', 'allowed_tasks',
        )
        read_only_fields = ('id', 'username', 'email')

    def get_full_name(self, obj):
        full = f'{obj.first_name} {obj.last_name}'.strip()
        if full:
            return full
        profile = getattr(obj, 'profile', None)
        return getattr(profile, 'nom_complet', '') or obj.username

    def get_capabilities(self, obj):
        return sorted(get_capabilities(obj))

    def get_allowed_tasks(self, obj):
        return sorted(get_allowed_task_types(obj))

    def validate_rol_nom(self, value):
        if value not in ROLE_CAPABILITIES:
            raise serializers.ValidationError(
                f"Rol desconegut '{value}'. Valors vàlids: {sorted(ROLE_CAPABILITIES)}.")
        return value

    def validate_permisos(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError("permisos ha de ser un objecte JSON.")
        return value

    def update(self, instance, validated_data):
        """Escriptura niada: escriu només els camps de profile presents (PATCH parcial)."""
        profile_data = validated_data.pop('profile', {})
        profile = instance.profile
        for attr in ('rol_nom', 'actiu', 'permisos'):
            if attr in profile_data:
                setattr(profile, attr, profile_data[attr])
        profile.save()
        return instance
