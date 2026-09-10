"""Calcolo dell'ora limite d'invio a partire dal calendario, con clamp di sicurezza."""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

def _parse(k, tz):
    dt = datetime.fromisoformat(k)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo(tz))
    return dt

def calendario_valido(calendario, adesso, giorni_max=10, tz="Europe/Rome"):
    if not calendario:
        return False
    for m in calendario:
        try:
            k = _parse(m["kickoff"], tz)
        except (KeyError, ValueError, TypeError):
            return False
        if k < adesso or k > adesso + timedelta(days=giorni_max):
            return False
    return True

def _cutoff(adesso, cutoff_fallback, tz):
    hhmm = cutoff_fallback[adesso.weekday()]
    h, m = map(int, hhmm.split(":"))
    return adesso.replace(hour=h, minute=m, second=0, microsecond=0)

def ora_limite(calendario, buffer_min, adesso, cutoff_fallback, tz="Europe/Rome"):
    if calendario_valido(calendario, adesso, tz=tz):
        primo = min(_parse(m["kickoff"], tz) for m in calendario)
        return primo - timedelta(minutes=buffer_min)
    return _cutoff(adesso, cutoff_fallback, tz)
