"""Orchestrazione: guida le transizioni su eventi utente e su scadenza timer."""
from datetime import datetime, date, time
from zoneinfo import ZoneInfo
from bot import giornata as gio
from bot import orari
from bot import formato
from bot.brain import BrainError
from bot.invio import InvioError
from bot.notifier import Evento
from bot.state import PROPOSTA, IN_MODIFICA, INVIATA

class Engine:
    def __init__(self, store, brain, notifier, invia_fn, rm, settings):
        self.store = store
        self.brain = brain
        self.notifier = notifier
        self.invia_fn = invia_fn
        self.rm = rm
        self.settings = settings
        self._provider = None   # callable () -> (res_lineup, session, ora_limite)

    def _testo_proposta(self, spec, ruoli, cmday, ora_limite):
        return formato.messaggio_proposta(
            spec, ruoli, self.settings.lega.get("nome", ""), cmday, ora_limite)

    @staticmethod
    def _testo_esito(stato, dettaglio=""):
        return {"INVIATA": "✅ Formazione inviata.",
                "BLOCCATA": "❌ Invio bloccato: sistemala a mano sul sito.",
                "ERRORE": f"⚠️ Problema: {dettaglio}. Controlla a mano."}[stato]

    def _aggiorna_rosa(self, res):
        """Rinfresca la rosa dai dati live del sito, se la fonte lo supporta (RosterSito)."""
        agg = getattr(self.rm, "aggiorna", None)
        if callable(agg):
            agg(res)

    def prepara(self, idcomp, cmday, res_lineup, ora_limite):
        self._aggiorna_rosa(res_lineup)
        tabella = gio.tabella_rosa(res_lineup)
        try:
            spec = self.brain.proponi(tabella, cmday)
        except BrainError as e:
            self.store.segna_errore(idcomp, cmday, str(e))
            self._avvisa_errore(idcomp, cmday, str(e))
            return
        msg_id = self.notifier.manda_proposta(
            {"idcomp": idcomp, "cmday": cmday}, spec,
            self._testo_proposta(spec, gio.ruoli(res_lineup), cmday, ora_limite))
        self.store.set_proposta(idcomp, cmday, spec, msg_id, ora_limite)

    def _avvisa_errore(self, idcomp, cmday, dettaglio):
        g = self.store.get(idcomp, cmday)
        testo = self._testo_esito("ERRORE", dettaglio)
        if g and g.msg_id:
            self.notifier.aggiorna_messaggio(g.msg_id, testo)
        else:
            self.notifier.manda_messaggio(testo)

    def on_evento(self, ev, provider=None):
        if provider:
            self._provider = provider
        if ev.tipo == "comando":
            self._esegui_comando(ev.testo)
            return
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
        self._aggiorna_rosa(res)
        tabella = gio.tabella_rosa(res)
        try:
            spec = self.brain.modifica(g.spec, ev.testo, tabella, ev.cmday)
        except BrainError as e:
            self.notifier.aggiorna_messaggio(g.msg_id,
                f"Non sono riuscito ad applicare la modifica ({e}). Resta valida la proposta precedente.")
            self.store.set_proposta(ev.idcomp, ev.cmday, g.spec, g.msg_id, g.ora_limite)
            return
        msg_id = self.notifier.manda_proposta(
            {"idcomp": ev.idcomp, "cmday": ev.cmday}, spec,
            self._testo_proposta(spec, gio.ruoli(res), ev.cmday, ora_limite))
        self.store.set_proposta(ev.idcomp, ev.cmday, spec, msg_id, ora_limite)

    def invia_ora(self, idcomp, cmday):
        if self._provider is None:
            return
        if not self.store.prova_lock_invio(idcomp, cmday):
            return  # già in invio / non più inviabile
        g = self.store.get(idcomp, cmday)
        res, session, _ora = self._provider()
        self._aggiorna_rosa(res)
        try:
            esito = self.invia_fn(g.spec, cmday, session, self.rm)
        except InvioError as e:
            self.store.segna_errore(idcomp, cmday, str(e))
            self.notifier.aggiorna_messaggio(g.msg_id, self._testo_esito("ERRORE", str(e)))
            return
        if esito.get("verificato"):
            self.store.segna_inviata(idcomp, cmday)
            self.notifier.aggiorna_messaggio(g.msg_id, self._testo_esito("INVIATA"))
        else:
            msg = "inviata ma la verifica dal sito non torna (modulo diverso), controlla a mano"
            self.store.segna_errore(idcomp, cmday, msg)
            self.notifier.aggiorna_messaggio(g.msg_id, self._testo_esito("ERRORE", msg))

    def scaduto(self, idcomp, cmday):
        g = self.store.get(idcomp, cmday)
        if g and g.stato in (PROPOSTA, IN_MODIFICA):
            self.invia_ora(idcomp, cmday)

    def heartbeat(self, provider, oggi_iso=None):
        self._provider = provider
        tz = self.settings.tz
        oggi = date.fromisoformat(oggi_iso) if oggi_iso else datetime.now(ZoneInfo(tz)).date()
        adesso = datetime.combine(oggi, time(0, 0), ZoneInfo(tz))  # inizio giornata: i kickoff odierni sono "futuri"
        res, _session, _ = provider()
        idcomp = self.settings.lega["idcomp"]
        cmday = gio.cmday(res)
        if self.store.get(idcomp, cmday):
            return  # già gestita (idempotenza)
        # Deadline = PRIMO calcio d'inizio dell'INTERO turno (l'anticipo), non della prima
        # partita dei miei: dal fischio d'inizio della giornata la formazione è bloccata.
        cal = self.brain.calendario(cmday)
        if not orari.calendario_valido(cal, adesso, tz=tz):
            return  # nessun calendario affidabile: non si prepara oggi (limite noto)
        ora_limite = orari.ora_limite(cal, self.settings.buffer_invio_min, adesso,
                                      self.settings.cutoff_fallback, tz)
        if ora_limite.date() != oggi:
            return  # il turno non inizia oggi
        g, creata = self.store.crea_se_assente(idcomp, cmday, ora_limite)
        if creata:
            self.prepara(idcomp, cmday, res, ora_limite)

    # ---- comandi Telegram (guidati dall'utente) ----
    _AIUTO = (
        "<b>Comandi</b>\n"
        "/formazione — calcola e proponi la formazione adesso\n"
        "/stato — stato della giornata e ora limite\n"
        "/vedi — mostra la formazione salvata sul sito\n"
        "/invia — invia subito la proposta corrente\n"
        "/blocca — blocca l'auto-invio di questa giornata\n"
        "/modifica &lt;testo&gt; — modifica a parole (es. /modifica gioca il 352)\n"
        "/aiuto — questo messaggio")

    def _esegui_comando(self, testo):
        parti = (testo or "").strip().split(maxsplit=1)
        cmd = parti[0].lstrip("/").split("@")[0].lower() if parti else ""
        arg = parti[1].strip() if len(parti) > 1 else ""
        if cmd in ("aiuto", "help", "start", ""):
            self.notifier.manda_messaggio(self._AIUTO)
            return
        if self._provider is None:
            self.notifier.manda_messaggio("⚠️ Non riesco a leggere dal sito ora, riprova tra poco.")
            return
        if cmd == "formazione":
            self._cmd_formazione()
        elif cmd == "stato":
            self._cmd_stato()
        elif cmd == "vedi":
            self._cmd_vedi()
        elif cmd == "invia":
            self._cmd_invia()
        elif cmd == "blocca":
            self._cmd_blocca()
        elif cmd == "modifica":
            self._cmd_modifica(arg)
        else:
            self.notifier.manda_messaggio(f"Comando sconosciuto: /{cmd}\n\n{self._AIUTO}")

    def _contesto(self):
        """(res, idcomp, cmday) dalla lettura fresca del sito."""
        res, _session, _ora = self._provider()
        return res, self.settings.lega["idcomp"], gio.cmday(res)

    def _ora_limite_turno(self, cmday):
        adesso = datetime.now(ZoneInfo(self.settings.tz))
        try:
            cal = self.brain.calendario(cmday)
        except Exception:
            cal = []
        return orari.ora_limite(cal, self.settings.buffer_invio_min, adesso,
                                self.settings.cutoff_fallback, self.settings.tz)

    def _cmd_formazione(self):
        res, idcomp, cmday = self._contesto()
        g = self.store.get(idcomp, cmday)
        if g and g.stato == INVIATA:
            self.notifier.manda_messaggio(
                f"Giornata {cmday}: già inviata. Usa /vedi per rileggerla dal sito.")
            return
        ora_limite = self._ora_limite_turno(cmday)
        self.store.crea_se_assente(idcomp, cmday, ora_limite)
        self.prepara(idcomp, cmday, res, ora_limite)

    def _cmd_stato(self):
        _res, idcomp, cmday = self._contesto()
        g = self.store.get(idcomp, cmday)
        if not g:
            self.notifier.manda_messaggio(
                f"Giornata {cmday}: non ancora preparata. Usa /formazione per prepararla ora.")
            return
        ol = g.ora_limite.strftime("%a %d/%m %H:%M") if g.ora_limite else "—"
        testo = f"Giornata {cmday}: stato <b>{g.stato}</b> · ora limite {ol}"
        if g.errore:
            testo += f"\n⚠️ {g.errore}"
        self.notifier.manda_messaggio(testo)

    def _cmd_vedi(self):
        res, _idcomp, _cmday = self._contesto()
        dto = res.get("teamLineupDto", {})
        info = {p.get("pid"): p for p in res.get("lineUpInfo", [])}
        def nome(pid):
            p = info.get(pid)
            return p.get("plyr") if p else str(pid)
        titolari = [nome(p) for p in (dto.get("starts") or [])]
        panca = [nome(p) for p in (dto.get("bench") or [])]
        if not titolari:
            self.notifier.manda_messaggio("Sul sito non risulta ancora una formazione salvata.")
            return
        self.notifier.manda_messaggio(
            formato.messaggio_sito(titolari, panca, gio.ruoli(res), dto.get("mdl")))

    def _cmd_invia(self):
        _res, idcomp, cmday = self._contesto()
        g = self.store.get(idcomp, cmday)
        if not g or g.stato not in (PROPOSTA, IN_MODIFICA):
            self.notifier.manda_messaggio(
                "Nessuna proposta da inviare. Usa /formazione per prepararne una.")
            return
        self.invia_ora(idcomp, cmday)

    def _cmd_blocca(self):
        _res, idcomp, cmday = self._contesto()
        if self.store.blocca(idcomp, cmday):
            g = self.store.get(idcomp, cmday)
            if g and g.msg_id:
                self.notifier.aggiorna_messaggio(g.msg_id, self._testo_esito("BLOCCATA"))
            else:
                self.notifier.manda_messaggio(self._testo_esito("BLOCCATA"))
        else:
            self.notifier.manda_messaggio("Non c'è una proposta bloccabile per questa giornata.")

    def _cmd_modifica(self, arg):
        _res, idcomp, cmday = self._contesto()
        g = self.store.get(idcomp, cmday)
        if not g or not g.spec:
            self.notifier.manda_messaggio(
                "Non c'è una formazione da modificare. Usa /formazione prima.")
            return
        if not arg:
            self.store.set_in_modifica(idcomp, cmday)
            self.notifier.chiedi_testo_modifica({"idcomp": idcomp, "cmday": cmday})
            return
        self._applica_modifica(Evento("modifica_testo", idcomp, cmday, arg))

    def on_evento_riconcilia(self, tipo, g, provider):
        self._provider = provider
        if tipo == "invia":
            self.invia_ora(g.idcomp, g.cmday)
        elif tipo == "verifica_invio":
            res, _session, _ = provider()
            mdl_sito = res.get("teamLineupDto", {}).get("mdl")
            atteso = (g.spec or {}).get("modulo")
            def _norm(m): return str(m).replace("-", "").strip() if m else ""
            if mdl_sito and atteso and _norm(mdl_sito) == _norm(atteso):
                self.store.segna_inviata(g.idcomp, g.cmday)
            else:
                self.store.segna_errore(g.idcomp, g.cmday, "invio interrotto: verifica manuale")
        elif tipo == "prepara":
            res, _session, ol = provider()
            self.prepara(g.idcomp, g.cmday, res, g.ora_limite or ol)
