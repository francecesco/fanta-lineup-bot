"""Entrypoint: compone le dipendenze reali e avvia il loop always-on."""
import logging
import fanta_api
from roster_map import RosterSito
from bot import scheduler
from bot.settings import carica_settings
from bot.state import Store
from bot.brain import Brain
from bot.notifier import TelegramNotifier
from bot.engine import Engine
from bot.invio import invia


def _make_provider(settings):
    """Ritorna un provider callable: ogni chiamata fa login + get_lineup freschi."""
    def provider():
        sess = fanta_api.FantaSession(
            settings.fanta_user, settings.fanta_pwd,
            settings.lega["id_squadra"], settings.lega["idcomp"],
            settings.lega.get("divisione", "A"))
        res = sess.get_lineup()
        return res, sess, None
    return provider


def costruisci(settings, rm=None, brain=None, notifier=None):
    """Compone le dipendenze. rm/brain/notifier iniettabili per test ermetici; in
    produzione restano None e si costruiscono i reali. La rosa (`RosterSito`) parte
    vuota e viene popolata dai dati del sito a ogni get_lineup: nessun file Excel."""
    store = Store(settings.db_path)
    rm = rm if rm is not None else RosterSito()
    brain = brain if brain is not None else Brain(
        settings.gemini_api_key, settings.gemini_model,
        max_tentativi=settings.max_tentativi_gemini, rm=rm)
    notifier = notifier if notifier is not None else TelegramNotifier(
        settings.telegram_token, settings.telegram_chat_id)
    engine = Engine(store, brain, notifier, invia, rm, settings)
    provider = _make_provider(settings)
    return engine, store, provider


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    settings = carica_settings()
    engine, store, provider = costruisci(settings)
    engine._provider = provider
    try:
        engine.notifier.registra_comandi()   # menu "/" su Telegram
    except Exception:
        logging.exception("registrazione comandi Telegram fallita (procedo comunque)")
    logging.info("Bot avviato per lega %s", settings.lega.get("nome", settings.lega["idcomp"]))
    scheduler.run_loop(engine, store, settings, provider)


if __name__ == "__main__":
    main()
