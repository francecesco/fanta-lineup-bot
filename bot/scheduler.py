"""Decisioni di scheduling (pure) + loop always-on del bot."""
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from bot.state import PROPOSTA, DA_PREPARARE, INVIO_IN_CORSO

def azioni_riconciliazione(adesso, giornate):
    azioni = []
    for g in giornate:
        if g.stato == PROPOSTA and g.ora_limite and adesso >= g.ora_limite:
            azioni.append(("invia", g))
        elif g.stato == INVIO_IN_CORSO:
            azioni.append(("verifica_invio", g))
        elif g.stato == DA_PREPARARE:
            azioni.append(("prepara", g))
    return azioni

def prossimo_heartbeat(adesso, ora_heartbeat, tz):
    h, m = map(int, ora_heartbeat.split(":"))
    cand = adesso.astimezone(ZoneInfo(tz)).replace(hour=h, minute=m, second=0, microsecond=0)
    if cand < adesso:
        cand += timedelta(days=1)
    return cand

def secondi_a(adesso, target):
    return max(0.0, (target - adesso).total_seconds())

def run_loop(engine, store, settings, provider_factory, stop_event=None):
    """Loop always-on. provider_factory() -> callable che fa login+get_lineup freschi.
    NB: descritto per l'esecuzione reale; le decisioni sono testate nelle funzioni pure sopra."""
    tz = settings.tz
    def adesso():
        return datetime.now(ZoneInfo(tz))

    # 1) Riconciliazione all'avvio
    for tipo, g in azioni_riconciliazione(adesso(), store.non_terminali()):
        provider = provider_factory()
        engine.on_evento_riconcilia(tipo, g, provider)

    prossimo_hb = prossimo_heartbeat(adesso(), settings.ora_heartbeat, tz)
    while not (stop_event and stop_event.is_set()):
        # 2) poll eventi Telegram (non blocca a lungo: getUpdates ha timeout server-side)
        for ev in engine.notifier.poll_eventi():
            engine.on_evento(ev, provider_factory())
        # 3) heartbeat giornaliero
        if adesso() >= prossimo_hb:
            engine.heartbeat(provider_factory())
            prossimo_hb = prossimo_heartbeat(adesso(), settings.ora_heartbeat, tz)
        # 4) timer d'invio: se una PROPOSTA ha superato l'ora_limite, invia
        for tipo, g in azioni_riconciliazione(adesso(), store.non_terminali()):
            if tipo == "invia":
                engine.scaduto(g.idcomp, g.cmday)
        time.sleep(5)
