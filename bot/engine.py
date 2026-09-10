"""Orchestrazione: guida le transizioni su eventi utente e su scadenza timer."""
from bot import giornata as gio
from bot.brain import BrainError
from bot.invio import InvioError

class Engine:
    def __init__(self, store, brain, notifier, invia_fn, rm, settings):
        self.store = store
        self.brain = brain
        self.notifier = notifier
        self.invia_fn = invia_fn
        self.rm = rm
        self.settings = settings
        self._provider = None   # callable () -> (res_lineup, session, ora_limite)

    @staticmethod
    def _testo_proposta(spec, ora_limite):
        tit = ", ".join(spec.get("titolari", []))
        quando = ora_limite.strftime("%H:%M") if ora_limite else "?"
        return (f"<b>Giornata: modulo {spec.get('modulo')}</b>\n{tit}\n\n"
                f"Invio automatico entro le {quando} se non intervieni.")

    @staticmethod
    def _testo_esito(stato, dettaglio=""):
        return {"INVIATA": "✅ Formazione inviata.",
                "BLOCCATA": "❌ Invio bloccato: sistemala a mano sul sito.",
                "ERRORE": f"⚠️ Problema: {dettaglio}. Controlla a mano."}[stato]

    def prepara(self, idcomp, cmday, res_lineup, ora_limite):
        tabella = gio.tabella_rosa(res_lineup)
        try:
            spec = self.brain.proponi(tabella, cmday)
        except BrainError as e:
            self.store.segna_errore(idcomp, cmday, str(e))
            self._avvisa_errore(idcomp, cmday, str(e))
            return
        msg_id = self.notifier.manda_proposta(
            {"idcomp": idcomp, "cmday": cmday}, spec, self._testo_proposta(spec, ora_limite))
        self.store.set_proposta(idcomp, cmday, spec, msg_id, ora_limite)

    def _avvisa_errore(self, idcomp, cmday, dettaglio):
        g = self.store.get(idcomp, cmday)
        if g and g.msg_id:
            self.notifier.aggiorna_messaggio(g.msg_id, self._testo_esito("ERRORE", dettaglio))

    def on_evento(self, ev, provider=None):
        if provider:
            self._provider = provider
        if ev.tipo == "blocca":
            if self.store.blocca(ev.idcomp, ev.cmday):
                g = self.store.get(ev.idcomp, ev.cmday)
                self.notifier.aggiorna_messaggio(g.msg_id, self._testo_esito("BLOCCATA"))
        elif ev.tipo == "conferma":
            self.invia_ora(ev.idcomp, ev.cmday)
        elif ev.tipo == "modifica":
            self.store.set_in_modifica(ev.idcomp, ev.cmday)
            self.notifier.chiedi_testo_modifica({"idcomp": ev.idcomp, "cmday": ev.cmday})
        elif ev.tipo == "modifica_testo":
            self._applica_modifica(ev)

    def _applica_modifica(self, ev):
        g = self.store.get(ev.idcomp, ev.cmday)
        if not g or not g.spec:
            return
        res, _session, ora_limite = self._provider()
        tabella = gio.tabella_rosa(res)
        try:
            spec = self.brain.modifica(g.spec, ev.testo, tabella, ev.cmday)
        except BrainError as e:
            self.notifier.aggiorna_messaggio(g.msg_id,
                f"Non sono riuscito ad applicare la modifica ({e}). Resta valida la proposta precedente.")
            self.store.set_proposta(ev.idcomp, ev.cmday, g.spec, g.msg_id, g.ora_limite)
            return
        msg_id = self.notifier.manda_proposta(
            {"idcomp": ev.idcomp, "cmday": ev.cmday}, spec, self._testo_proposta(spec, ora_limite))
        self.store.set_proposta(ev.idcomp, ev.cmday, spec, msg_id, ora_limite)

    def invia_ora(self, idcomp, cmday):
        if not self.store.prova_lock_invio(idcomp, cmday):
            return  # già in invio / non più in PROPOSTA
        g = self.store.get(idcomp, cmday)
        res, session, _ora = self._provider()
        try:
            self.invia_fn(g.spec, cmday, session, self.rm)
        except InvioError as e:
            self.store.segna_errore(idcomp, cmday, str(e))
            self.notifier.aggiorna_messaggio(g.msg_id, self._testo_esito("ERRORE", str(e)))
            return
        self.store.segna_inviata(idcomp, cmday)
        self.notifier.aggiorna_messaggio(g.msg_id, self._testo_esito("INVIATA"))

    def scaduto(self, idcomp, cmday):
        from bot.state import PROPOSTA
        g = self.store.get(idcomp, cmday)
        if g and g.stato == PROPOSTA:
            self.invia_ora(idcomp, cmday)
