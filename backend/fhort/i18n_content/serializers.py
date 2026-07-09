"""Mixin de serializer reutilitzable per exposar/acceptar traduccions.

Qualsevol ModelSerializer d'un model `TranslatableMixin` pot heretar aquest mixin i afegir
`'translations'` als seus `Meta.fields`. En lectura exposa `translations = { camp: { idioma:
text } }` (només idiomes addicionals; l'EN viu a la columna canònica). En escriptura accepta
el mateix dict i el desa (nested): text buit/absent → esborra la traducció d'aquell idioma.
"""
from django.contrib.contenttypes.models import ContentType
from rest_framework import serializers

from .models import Translation


class TranslationsSerializerMixin(serializers.Serializer):
    """Barreja abans de `ModelSerializer`: `class XSerializer(TranslationsSerializerMixin,
    serializers.ModelSerializer)`. Els camps traduïbles els declara el model a
    `TRANSLATABLE_FIELDS`; l'EN mai surt/entra aquí (viu a la columna del propi camp)."""

    translations = serializers.DictField(
        required=False,
        child=serializers.DictField(child=serializers.CharField(allow_blank=True, trim_whitespace=False)),
        help_text="{ camp: { idioma_ISO_639-1: text } } — idiomes addicionals a l'EN canònic.",
    )

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['translations'] = self._get_translations(instance)
        return data

    def _get_translations(self, instance):
        """Traduccions de l'objecte com a { camp: { idioma: text } }. En llista (many=True)
        llegeix d'una precàrrega feta en 1 sola query per a tota la pàgina (fi del N+1); en
        objecte únic (retrieve/create/update) fa la consulta directa (1 query)."""
        fields = getattr(instance, 'TRANSLATABLE_FIELDS', ())
        if not fields:
            return {}
        parent = self.parent
        if isinstance(parent, serializers.ListSerializer) and parent.instance is not None:
            cache = self._page_cache(parent, instance.__class__, fields)
            out = {f: {} for f in fields}
            out.update(cache.get(instance.pk, {}))
            return out
        return self._read_translations(instance)

    @staticmethod
    def _page_cache(parent, model, fields):
        """Precàrrega batch memoïtzada al ListSerializer: totes les Translation dels objectes
        de la pàgina en 1 query (content_type + object_id__in). Es construeix un sol cop per
        serialització de llista, independentment del nombre d'objectes."""
        cache = getattr(parent, '_translations_page_cache', None)
        if cache is not None:
            return cache
        cache = {}
        pks = [obj.pk for obj in parent.instance]
        if pks:
            ct = ContentType.objects.get_for_model(model)
            rows = Translation.objects.filter(content_type=ct, object_id__in=pks, field__in=fields)
            for r in rows:
                cache.setdefault(r.object_id, {}).setdefault(r.field, {})[r.language] = r.text
        parent._translations_page_cache = cache
        return cache

    @staticmethod
    def _read_translations(instance):
        fields = getattr(instance, 'TRANSLATABLE_FIELDS', ())
        if not fields:
            return {}
        ct = ContentType.objects.get_for_model(instance.__class__)
        rows = Translation.objects.filter(content_type=ct, object_id=instance.pk, field__in=fields)
        out = {f: {} for f in fields}
        for r in rows:
            out.setdefault(r.field, {})[r.language] = r.text
        return out

    def create(self, validated_data):
        translations = validated_data.pop('translations', None)
        instance = super().create(validated_data)
        if translations:
            self._write_translations(instance, translations)
        return instance

    def update(self, instance, validated_data):
        translations = validated_data.pop('translations', None)
        instance = super().update(instance, validated_data)
        if translations is not None:
            self._write_translations(instance, translations)
        return instance

    @staticmethod
    def _write_translations(instance, translations):
        allowed = set(getattr(instance, 'TRANSLATABLE_FIELDS', ()))
        ct = ContentType.objects.get_for_model(instance.__class__)
        for field, per_lang in translations.items():
            if field not in allowed or not isinstance(per_lang, dict):
                continue
            for lang, text in per_lang.items():
                lang = (lang or '').strip().lower()
                if not lang or lang == 'en':
                    continue  # l'EN viu a la columna canònica, no a la taula de traduccions
                if text:
                    Translation.objects.update_or_create(
                        content_type=ct, object_id=instance.pk, field=field, language=lang,
                        defaults={'text': text})
                else:
                    Translation.objects.filter(
                        content_type=ct, object_id=instance.pk, field=field, language=lang).delete()
