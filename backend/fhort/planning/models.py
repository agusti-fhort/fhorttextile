"""Sprint Backend A — calendari laboral (base del motor de planificació).
Models per-tenant: calendari d'empresa (singleton) + absències per tècnic.
La jornada pròpia del tècnic viu a accounts.UserProfile.jornada_override.
Els festius oficials els aporta workalendar (Catalunya); aquí només els EXTRA del tenant."""
from django.db import models

# Claus de dia de la setmana alineades amb datetime.date.weekday() (0=mon … 6=sun).
DOW_KEYS = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']


def default_horaris():
    """Plantilla per defecte: dilluns-dijous 8-13/14-17, divendres 8-15, cap de setmana lliure.
    Format: {dia: [[inici, fi], ...]} amb hores 'HH:MM'. Trams = jornada partida (pausa dinar)."""
    return {
        'mon': [['08:00', '13:00'], ['14:00', '17:00']],
        'tue': [['08:00', '13:00'], ['14:00', '17:00']],
        'wed': [['08:00', '13:00'], ['14:00', '17:00']],
        'thu': [['08:00', '13:00'], ['14:00', '17:00']],
        'fri': [['08:00', '15:00']],
        'sat': [],
        'sun': [],
    }


class CompanyCalendar(models.Model):
    """Calendari laboral de l'empresa (singleton per tenant).
    `horaris`: trams hàbils per dia de la setmana (mon..sun) — plantilla base de jornada.
    `festius_extra`: dates ISO addicionals als festius oficials (workalendar Catalunya)."""
    horaris = models.JSONField(default=default_horaris)
    festius_extra = models.JSONField(default=list, blank=True)   # ["2026-12-24", ...]
    creat_at = models.DateTimeField(auto_now_add=True)
    actualitzat_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Company calendar'
        verbose_name_plural = 'Company calendars'

    def __str__(self):
        return f'CompanyCalendar #{self.pk}'

    @classmethod
    def load(cls):
        """Singleton per tenant: retorna l'únic registre (el crea amb la plantilla si no existeix)."""
        obj = cls.objects.first()
        if obj is None:
            obj = cls.objects.create()
        return obj

    def trams_per_dia(self, day):
        """Trams hàbils [['HH:MM','HH:MM'], ...] per a una data donada (datetime.date).
        Llista buida si el dia de la setmana no és laborable a la plantilla."""
        return self.horaris.get(DOW_KEYS[day.weekday()], []) or []


class Absencia(models.Model):
    """Absència d'un tècnic (vacances/baixa): rang de dates inclusiu [data_inici, data_fi]."""
    user_profile = models.ForeignKey('accounts.UserProfile', on_delete=models.CASCADE,
                                     related_name='absencies')
    data_inici = models.DateField()
    data_fi = models.DateField()
    motiu = models.CharField(max_length=200, blank=True, default='')

    class Meta:
        ordering = ['-data_inici']
        verbose_name = 'Absència'
        verbose_name_plural = 'Absències'

    def __str__(self):
        return f'{self.user_profile_id}: {self.data_inici}→{self.data_fi}'
