"""Decisioni di scheduling (pure) + loop always-on del bot."""
import logging
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from bot.state import PROPOSTA, DA_PREPARARE, INVIO_IN_CORSO, IN_MODIFICA

def azioni_riconciliazione(adesso, giornate):
    azioni = []
    for g in giornate:
        if g.stato in (PROPOSTA, IN_MODIFICA) and g.ora_limite and adesso >= g.ora_limite:
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

def run_loop(engine, store, settings, provider, stop_event=None):
    """Loop always-on. `provider` è una callable () -> (res, session, ora_limite) che fa
    login+get_lineup freschi: viene passata così com'è all'engine, che la invoca quando serve.
    NB: descritto per l'esecuzione reale; le decisioni sono testate nelle funzioni pure sopra."""
    tz = settings.tz
    def adesso():
        return datetime.now(ZoneInfo(tz))

    # 1) Riconciliazione all'avvio
    try:
        for tipo, g in azioni_riconciliazione(adesso(), store.non_terminali()):
            engine.on_evento_riconcilia(tipo, g, provider)
    except Exception:
        logging.exception("errore nella riconciliazione all'avvio")

    prossimo_hb = prossimo_heartbeat(adesso(), settings.ora_heartbeat, tz)
    while not (stop_event and stop_event.is_set()):
        try:
            # 2) poll eventi Telegram (non blocca a lungo: getUpdates ha timeout server-side)
            for ev in engine.notifier.poll_eventi():
                engine.on_evento(ev, provider)
            # 3) heartbeat giornaliero
            if adesso() >= prossimo_hb:
                engine.heartbeat(provider)
                prossimo_hb = prossimo_heartbeat(adesso(), settings.ora_heartbeat, tz)
            # 4) timer d'invio: se una PROPOSTA ha superato l'ora_limite, invia
            for tipo, g in azioni_riconciliazione(adesso(), store.non_terminali()):
                if tipo == "invia":
                    engine.scaduto(g.idcomp, g.cmday)
        except Exception:
            logging.exception("errore nel loop principale, continuo")
        time.sleep(5)
