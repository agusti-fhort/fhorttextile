from django.contrib.auth import get_user_model
from django.core.validators import RegexValidator
from django.db import transaction
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
    # id = User.id; profile_id = UserProfile.id. ModelTask.assignee és FK a UserProfile, així que
    # l'scope viewer del frontend (meva/d'altri) ha de comparar assignee_id amb profile_id,
    # MAI amb id/user_id (no depèn de cap coincidència profile_id==user_id).
    profile_id = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'id', 'profile_id', 'username', 'first_name', 'last_name', 'email',
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

    def get_profile_id(self, obj):
        profile = self._profile(obj)
        return profile.id if profile else None

    def get_capabilities(self, obj):
        return sorted(get_capabilities(obj))


class UserListSerializer(serializers.ModelSerializer):
    """For the responsible-person selector. Only active tenant users."""

    full_name = serializers.SerializerMethodField()
    # id = User.id; profile_id = UserProfile.id. ModelTask.assignee és FK a UserProfile, així que
    # els selectors d'assignació han d'enviar profile_id (no l'id de User) — no depèn de cap coincidència.
    profile_id = serializers.SerializerMethodField()
    color_avatar = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('id', 'profile_id', 'username', 'full_name', 'email', 'color_avatar')

    def get_profile_id(self, obj):
        p = getattr(obj, 'profile', None)
        return p.id if p else None

    def get_color_avatar(self, obj):
        p = getattr(obj, 'profile', None)
        return (p.color_avatar if p else None) or '#888888'

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
    profile_id = serializers.SerializerMethodField()   # UserProfile.id (≠ User.id en general)
    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_blank=True)
    rol_nom = serializers.CharField(source='profile.rol_nom')
    actiu = serializers.BooleanField(source='profile.actiu')
    permisos = serializers.JSONField(source='profile.permisos')
    color_avatar = serializers.CharField(
        source='profile.color_avatar', required=False,
        validators=[RegexValidator(
            regex=r'^#[0-9A-Fa-f]{6}$',
            message="color_avatar ha de ser un hex #RRGGBB.")],
    )
    capabilities = serializers.SerializerMethodField()
    allowed_tasks = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'id', 'profile_id', 'username', 'email', 'full_name',
            'first_name', 'last_name',
            'rol_nom', 'actiu', 'permisos', 'color_avatar',
            'capabilities', 'allowed_tasks',
        )
        read_only_fields = ('id', 'username', 'email')

    def get_profile_id(self, obj):
        p = getattr(obj, 'profile', None)
        return p.id if p else None

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
        """Escriptura niada: escriu només els camps presents (PATCH parcial).
        first_name/last_name → User; rol_nom/actiu/permisos/color_avatar → UserProfile."""
        profile_data = validated_data.pop('profile', {})
        user_fields = [a for a in ('first_name', 'last_name') if a in validated_data]
        for attr in user_fields:
            setattr(instance, attr, validated_data[attr])
        if user_fields:
            instance.save(update_fields=user_fields)
        profile = instance.profile
        for attr in ('rol_nom', 'actiu', 'permisos', 'color_avatar'):
            if attr in profile_data:
                setattr(profile, attr, profile_data[attr])
        profile.save()
        return instance


class UserCreateSerializer(serializers.Serializer):
    """Alta d'usuari (gated manage_users). Crea el User amb create_user(); el signal post_save
    crea el UserProfile DINS del tenant i create() l'actualitza amb nom_complet/rol_nom/permisos.
    NO crea el profile a mà (evita duplicar la feina del signal)."""

    username = serializers.CharField(max_length=150)
    email = serializers.EmailField(required=False, allow_blank=True, default='')
    nom_complet = serializers.CharField(required=False, allow_blank=True, default='')
    rol_nom = serializers.CharField()
    password = serializers.CharField(write_only=True, style={'input_type': 'password'})
    permisos = serializers.JSONField(required=False, default=dict)

    def validate_username(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("username requerit.")
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("Ja existeix un usuari amb aquest username.")
        return value

    def validate_password(self, value):
        if not value:
            raise serializers.ValidationError("password no pot ser buit.")
        return value

    def validate_rol_nom(self, value):
        if value not in ROLE_CAPABILITIES:
            raise serializers.ValidationError(
                f"Rol desconegut '{value}'. Valors vàlids: {sorted(ROLE_CAPABILITIES)}.")
        return value

    def validate_permisos(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError("permisos ha de ser un objecte JSON.")
        return value

    def create(self, validated_data):
        with transaction.atomic():
            user = User.objects.create_user(
                username=validated_data['username'],
                email=validated_data.get('email', ''),
                password=validated_data['password'],
            )
            # El signal post_save(User) ja ha creat el UserProfile dins del tenant; el recuperem
            # i l'actualitzem amb les dades del formulari (no el creem a mà).
            profile = UserProfile.objects.get(user=user)
            profile.nom_complet = validated_data.get('nom_complet') or user.username
            profile.rol_nom = validated_data['rol_nom']
            profile.permisos = validated_data.get('permisos') or {}
            profile.save(update_fields=['nom_complet', 'rol_nom', 'permisos'])
        return user
