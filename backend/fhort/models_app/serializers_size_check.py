"""SC-1 — Size Check serializers.

Graella d'1 columna (talla base): valor_teoric (snapshot) vs valor_real (mesurat),
amb tolerància vigent del BaseMeasurement (fallback 0.6) i `fora_tolerancia` calculat
al backend (font de veritat per pintar vermell al front).
"""
from rest_framework import serializers

from .models import SizeCheck, SizeCheckLine

TOL_DEFAULT = 0.6


class SizeCheckLineSerializer(serializers.ModelSerializer):
    """Autosave d'una cel·la: valor_real, acceptat i nota editables; la resta congelada."""

    class Meta:
        model = SizeCheckLine
        fields = ['id', 'size_check', 'pom', 'valor_teoric', 'valor_real', 'decisio', 'nota']
        read_only_fields = ['id', 'size_check', 'pom', 'valor_teoric']


class SizeCheckSummarySerializer(serializers.ModelSerializer):
    """List: una fila per check (històric del model)."""
    model_codi = serializers.CharField(source='model.codi_intern', read_only=True)
    resolt_per_nom = serializers.CharField(source='resolt_per.nom_complet', read_only=True)
    n_linies = serializers.SerializerMethodField()

    class Meta:
        model = SizeCheck
        fields = [
            'id', 'model', 'model_codi', 'estat', 'talla_base_label',
            'missatge_fabricant', 'resolt_per_nom', 'resolt_at', 'created_at', 'n_linies',
        ]

    def get_n_linies(self, obj):
        return obj.linies.count()


class SizeCheckGridSerializer(serializers.ModelSerializer):
    """Retrieve: la graella de treball (1 columna talla base + tolerància + estat dins/fora)."""
    model = serializers.SerializerMethodField()
    resolt_per_nom = serializers.CharField(source='resolt_per.nom_complet', read_only=True)
    lines = serializers.SerializerMethodField()
    # SC-3: precheck per al front — si el model té deltes, en resoldre es propagarà el
    # grading i cal l'avís+confirma. Reusa el mateix helper que resolve_size_check.
    te_deltes = serializers.SerializerMethodField()

    class Meta:
        model = SizeCheck
        fields = [
            'id', 'estat', 'talla_base_label', 'missatge_fabricant',
            'resolt_per_nom', 'resolt_at', 'created_at', 'model', 'lines', 'te_deltes',
        ]

    def get_model(self, obj):
        m = obj.model
        return {
            'id': m.id, 'codi': m.codi_intern, 'nom': m.nom_prenda,
            'base_size_label': m.base_size_label,
        }

    def get_te_deltes(self, obj):
        from .services_size_check import model_te_deltes
        return model_te_deltes(obj.model)

    def get_lines(self, obj):
        from .models import BaseMeasurement
        # Una sola query: tolerància + ordre vigents per POM del model (sense N+1).
        bm_map = {
            bm.pom_id: bm
            for bm in BaseMeasurement.objects.filter(model_id=obj.model_id)
        }

        out = []
        for line in obj.linies.select_related('pom', 'pom__pom_global').all():
            bm = bm_map.get(line.pom_id)
            tol_minus = float(bm.tolerancia_minus) if bm and bm.tolerancia_minus is not None else TOL_DEFAULT
            tol_plus = float(bm.tolerancia_plus) if bm and bm.tolerancia_plus is not None else TOL_DEFAULT

            vt = line.valor_teoric
            vr = line.valor_real
            # valor_real null → dins (gris), no vermell.
            fora = bool(vr is not None and (vr < vt - tol_minus or vr > vt + tol_plus))

            pom = line.pom
            out.append({
                'id': line.id,
                'pom_id': line.pom_id,
                'codi': pom.pom_code if pom else '',
                'nom': pom.name_cat if pom else '',
                'is_key': pom.is_key_measure if pom else False,
                'valor_teoric': vt,
                'valor_real': vr,
                'decisio': line.decisio,
                'nota': line.nota,
                'tol_minus': tol_minus,
                'tol_plus': tol_plus,
                'fora_tolerancia': fora,
            })

        # Ordena per l'ordre de la fitxa (BaseMeasurement.ordre del model).
        ordre_map = {pid: bm.ordre for pid, bm in bm_map.items()}
        out.sort(key=lambda r: ordre_map.get(r['pom_id'], 10 ** 9))
        return out
