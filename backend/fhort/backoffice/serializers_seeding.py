# F3 P-FREE-SEED (B5): serializer del SeedProfile (perfils de sembra del backoffice).
# El backoffice és SHARED: `seleccio` guarda BLOCS (concepte de producte), mai models
# de tenant. La validació de claus va contra SeedProfile.Bloc, no contra el catàleg.
from rest_framework import serializers

from .models import SeedProfile


class SeedProfileSerializer(serializers.ModelSerializer):
    blocks = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = SeedProfile
        fields = [
            'id', 'nom', 'descripcio', 'seleccio', 'blocks',
            'is_default_free', 'actiu', 'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']

    def get_blocks(self, obj):
        return obj.blocks

    def validate_seleccio(self, value):
        """`seleccio` = {"blocks": [<clau de Bloc>, ...]}. Rebutja claus desconegudes."""
        if not isinstance(value, dict):
            raise serializers.ValidationError("Ha de ser un objecte {'blocks': [...]}.")
        blocks = value.get('blocks', [])
        if not isinstance(blocks, list):
            raise serializers.ValidationError("'blocks' ha de ser una llista.")
        valids = set(SeedProfile.Bloc.values)
        desconeguts = [b for b in blocks if b not in valids]
        if desconeguts:
            raise serializers.ValidationError(
                f"Blocs desconeguts: {desconeguts}. Vàlids: {sorted(valids)}")
        # Normalitza: sense duplicats, ordre estable.
        return {'blocks': [b for b in SeedProfile.Bloc.values if b in set(blocks)]}
