"""Serializers de configuració del calendari (Sprint A, Peça 3).
Validació estricta del format d'horaris (trams per dia mon..sun, inici<fi, ordenats i sense
solapament) i dels rangs d'absència."""
import datetime as _dt

from rest_framework import serializers

from .models import CompanyCalendar, Absencia, DOW_KEYS


def _parse_hhmm(value):
    """Retorna minuts des de mitjanit per a 'HH:MM' vàlid; 400 si no ho és."""
    if not isinstance(value, str):
        raise serializers.ValidationError(f"Hora invàlida: {value!r} (esperat 'HH:MM').")
    parts = value.split(':')
    if len(parts) != 2:
        raise serializers.ValidationError(f"Hora invàlida: '{value}' (format 'HH:MM').")
    try:
        h, m = int(parts[0]), int(parts[1])
    except ValueError:
        raise serializers.ValidationError(f"Hora invàlida: '{value}' (format 'HH:MM').")
    if not (0 <= h <= 23 and 0 <= m <= 59):
        raise serializers.ValidationError(f"Hora fora de rang: '{value}'.")
    return h * 60 + m


def validate_horaris(horaris):
    """Valida {dia: [[inici, fi], ...]} amb dies mon..sun, trams inici<fi, ordenats i sense
    solapament. Llança ValidationError (400) amb missatge clar si no és vàlid."""
    if not isinstance(horaris, dict):
        raise serializers.ValidationError("horaris ha de ser un objecte {dia: [[inici, fi], ...]}.")
    for day, trams in horaris.items():
        if day not in DOW_KEYS:
            raise serializers.ValidationError(f"Dia invàlid: '{day}'. Vàlids: {DOW_KEYS}.")
        if not isinstance(trams, list):
            raise serializers.ValidationError(f"Els trams de '{day}' han de ser una llista.")
        prev_end = -1
        for tram in trams:
            if not (isinstance(tram, (list, tuple)) and len(tram) == 2):
                raise serializers.ValidationError(
                    f"Tram invàlid a '{day}': {tram!r} (esperat [inici, fi]).")
            ini, fi = _parse_hhmm(tram[0]), _parse_hhmm(tram[1])
            if ini >= fi:
                raise serializers.ValidationError(
                    f"A '{day}': l'inici {tram[0]} ha de ser anterior al fi {tram[1]}.")
            if ini < prev_end:
                raise serializers.ValidationError(
                    f"A '{day}': trams solapats o desordenats ({tram!r}).")
            prev_end = fi
    return horaris


def validate_festius_extra(value):
    if not isinstance(value, list):
        raise serializers.ValidationError("festius_extra ha de ser una llista de dates ISO.")
    for iso in value:
        try:
            _dt.date.fromisoformat(iso)
        except (ValueError, TypeError):
            raise serializers.ValidationError(f"Data festiva invàlida: {iso!r} (esperat 'YYYY-MM-DD').")
    return value


class CompanyCalendarSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompanyCalendar
        fields = ['id', 'horaris', 'festius_extra', 'actualitzat_at']
        read_only_fields = ['id', 'actualitzat_at']

    def validate_horaris(self, v):
        return validate_horaris(v)

    def validate_festius_extra(self, v):
        return validate_festius_extra(v)


class JornadaSerializer(serializers.Serializer):
    """Override de jornada del tècnic. null/buit → torna a heretar la de l'empresa."""
    jornada_override = serializers.JSONField(allow_null=True, required=True)

    def validate_jornada_override(self, v):
        if v in (None, {}, ''):
            return None
        return validate_horaris(v)


class AbsenciaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Absencia
        fields = ['id', 'user_profile', 'data_inici', 'data_fi', 'motiu']

    def validate(self, data):
        ini = data.get('data_inici', getattr(self.instance, 'data_inici', None))
        fi = data.get('data_fi', getattr(self.instance, 'data_fi', None))
        if ini and fi and ini > fi:
            raise serializers.ValidationError("data_inici ha de ser anterior o igual a data_fi.")
        return data
