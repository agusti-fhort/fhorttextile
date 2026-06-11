"""Sprint Backend A — servei de calendari laboral.

Construeix el calendari EFECTIU d'un tècnic (jornada pròpia o d'empresa + festius oficials
de Catalunya via workalendar + festius_extra del tenant + absències del tècnic) i ofereix
les primitives que el motor de scheduling (sprint B) encadenarà:

  - next_working_slot(profile, after)  → següent instant hàbil (salta pauses, finals de
    jornada, caps de setmana, festius i absències).
  - add_working_minutes(profile, start, minutes) → datetime final després de col·locar N
    minuts de feina respectant el calendari.

Treballa amb datetimes NAÏUS (rellotge local de l'empresa); la localització tz, si cal,
és responsabilitat del consumidor. Recolza els dies hàbils/festius en workalendar; la
lògica de trams (pauses, finals de jornada) és pròpia.
"""
import datetime as _dt
from functools import lru_cache

from workalendar.europe import Catalonia

from .models import CompanyCalendar, DOW_KEYS

_CAL = Catalonia()
_SAFETY_DAYS = 366 * 5   # límit dur per evitar bucles infinits si el calendari fos tot no-laborable


@lru_cache(maxsize=None)
def _catalonia_holidays(year):
    """Conjunt de dates festives oficials de Catalunya per a un any (cau a workalendar)."""
    return {d for d, _ in _CAL.holidays(year)}


def _festius_extra_set(cal):
    out = set()
    for iso in (cal.festius_extra or []):
        try:
            out.add(_dt.date.fromisoformat(iso))
        except (ValueError, TypeError):
            continue
    return out


def _is_holiday(d, cal):
    return d in _catalonia_holidays(d.year) or d in _festius_extra_set(cal)


def _absence_dates(profile):
    """Conjunt-funció: retorna un predicat tancat sobre les absències del tècnic."""
    ranges = [(a.data_inici, a.data_fi) for a in profile.absencies.all()]
    def _is_absent(d):
        return any(ini <= d <= fi for ini, fi in ranges)
    return _is_absent


def _effective_horaris(profile, cal):
    """Jornada vigent del tècnic: override propi si n'hi ha, si no la de l'empresa."""
    return profile.jornada_override if profile.jornada_override else cal.horaris


def _day_trams(profile, cal, d, is_absent):
    """Trams hàbils (datetime) del dia `d` per a aquest tècnic. [] si festiu, absència o
    dia no laborable a la jornada."""
    if _is_holiday(d, cal) or is_absent(d):
        return []
    horaris = _effective_horaris(profile, cal)
    out = []
    for a, b in (horaris.get(DOW_KEYS[d.weekday()], []) or []):
        sh, sm = map(int, a.split(':'))
        eh, em = map(int, b.split(':'))
        out.append((_dt.datetime.combine(d, _dt.time(sh, sm)),
                    _dt.datetime.combine(d, _dt.time(eh, em))))
    return out


def next_working_slot(profile, after):
    """Primer instant hàbil >= `after` (datetime naïf). Salta pauses, finals de jornada,
    caps de setmana, festius i absències."""
    cal = CompanyCalendar.load()
    is_absent = _absence_dates(profile)
    cur = after
    for _ in range(_SAFETY_DAYS):
        for s, e in _day_trams(profile, cal, cur.date(), is_absent):
            if cur < e:
                return s if cur < s else cur
        # cap tram avui després de `cur` → salta a l'inici del dia següent
        cur = _dt.datetime.combine(cur.date() + _dt.timedelta(days=1), _dt.time(0, 0))
    raise RuntimeError('next_working_slot: cap franja hàbil dins del límit de seguretat')


def add_working_minutes(profile, start, minutes):
    """Datetime final després de col·locar `minutes` minuts de feina a partir de `start`,
    respectant el calendari (pauses/jornada/caps de setmana/festius/absències). Primitiva
    que el motor de l'sprint B usarà per encadenar tasques."""
    if minutes <= 0:
        return next_working_slot(profile, start)
    cal = CompanyCalendar.load()
    is_absent = _absence_dates(profile)
    cur = next_working_slot(profile, start)
    remaining = _dt.timedelta(minutes=minutes)
    for _ in range(_SAFETY_DAYS):
        for s, e in _day_trams(profile, cal, cur.date(), is_absent):
            if cur < e:
                seg_start = s if cur < s else cur
                avail = e - seg_start
                if remaining <= avail:
                    return seg_start + remaining
                remaining -= avail
                cur = e   # tram esgotat → continua al següent tram/dia
        cur = _dt.datetime.combine(cur.date() + _dt.timedelta(days=1), _dt.time(0, 0))
    raise RuntimeError('add_working_minutes: límit de seguretat superat')


def prev_working_slot(profile, before):
    """Mirall ENRERE de next_working_slot: darrer instant hàbil <= `before` (datetime naïf),
    entès com el FINAL de feina disponible. Si `before` cau dins un tram (s < before <= e)
    el retorna tal qual; si cau després d'un tram (e < before) retrocedeix fins a `e`; si no
    hi ha cap tram abans avui, salta al final del dia anterior. Salta pauses, finals/inicis
    de jornada, caps de setmana, festius i absències."""
    cal = CompanyCalendar.load()
    is_absent = _absence_dates(profile)
    cur = before
    for _ in range(_SAFETY_DAYS):
        for s, e in reversed(_day_trams(profile, cal, cur.date(), is_absent)):
            if cur > s:
                return e if cur > e else cur
        # cap tram avui abans de `cur` → salta al final del dia anterior
        cur = _dt.datetime.combine(cur.date() - _dt.timedelta(days=1), _dt.time.max)
    raise RuntimeError('prev_working_slot: cap franja hàbil dins del límit de seguretat')


def subtract_working_minutes(profile, end, minutes):
    """Mirall ENRERE d'add_working_minutes: datetime d'INICI tal que treballant des d'aquest
    inici fins a `end` hi ha exactament `minutes` minuts laborables. Consumeix el temps cap
    enrere respectant el calendari (pauses/jornada/caps de setmana/festius/absències),
    reutilitzant els mateixos helpers que la primitiva endavant. Mateixa convenció naïf."""
    if minutes <= 0:
        return prev_working_slot(profile, end)
    cal = CompanyCalendar.load()
    is_absent = _absence_dates(profile)
    cur = prev_working_slot(profile, end)
    remaining = _dt.timedelta(minutes=minutes)
    for _ in range(_SAFETY_DAYS):
        for s, e in reversed(_day_trams(profile, cal, cur.date(), is_absent)):
            if cur > s:
                seg_end = e if cur > e else cur
                avail = seg_end - s
                if remaining <= avail:
                    return seg_end - remaining
                remaining -= avail
                cur = s   # tram esgotat → continua al tram/dia anterior
        cur = _dt.datetime.combine(cur.date() - _dt.timedelta(days=1), _dt.time.max)
    raise RuntimeError('subtract_working_minutes: límit de seguretat superat')
