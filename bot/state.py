"""Persistenza SQLite della macchina a stati per giornata. Chiave idempotente (idcomp, cmday)."""
import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

DA_PREPARARE = "DA_PREPARARE"
PROPOSTA = "PROPOSTA"
IN_MODIFICA = "IN_MODIFICA"
INVIO_IN_CORSO = "INVIO_IN_CORSO"   # transitorio: lock d'invio
BLOCCATA = "BLOCCATA"
INVIATA = "INVIATA"
ERRORE = "ERRORE"

TERMINALI = {BLOCCATA, INVIATA}

def now_rome(tz: str = "Europe/Rome") -> datetime:
    return datetime.now(ZoneInfo(tz))

def _iso(dt):
    return dt.isoformat() if dt else None

def _dt(s):
    return datetime.fromisoformat(s) if s else None

@dataclass
class Giornata:
    idcomp: int
    cmday: int
    stato: str
    spec: dict | None
    ora_limite: datetime | None
    msg_id: str | None
    inviata_at: str | None
    errore: str | None
    updated_at: str

class Store:
    def __init__(self, db_path: str):
        self.db = sqlite3.connect(db_path)
        self.db.row_factory = sqlite3.Row
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS giornate (
                idcomp INTEGER, cmday INTEGER, stato TEXT NOT NULL,
                spec_json TEXT, ora_limite TEXT, msg_id TEXT,
                inviata_at TEXT, errore TEXT, updated_at TEXT NOT NULL,
                PRIMARY KEY (idcomp, cmday)
            )""")
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS eventi (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                idcomp INTEGER, cmday INTEGER, tipo TEXT, dettaglio TEXT, ts TEXT
            )""")
        self.db.commit()

    # --- helpers ---
    def _row2g(self, r):
        if r is None:
            return None
        return Giornata(
            idcomp=r["idcomp"], cmday=r["cmday"], stato=r["stato"],
            spec=json.loads(r["spec_json"]) if r["spec_json"] else None,
            ora_limite=_dt(r["ora_limite"]), msg_id=r["msg_id"],
            inviata_at=r["inviata_at"], errore=r["errore"], updated_at=r["updated_at"],
        )

    def get(self, idcomp, cmday):
        r = self.db.execute(
            "SELECT * FROM giornate WHERE idcomp=? AND cmday=?", (idcomp, cmday)).fetchone()
        return self._row2g(r)

    def log(self, idcomp, cmday, tipo, dettaglio=""):
        self.db.execute(
            "INSERT INTO eventi (idcomp, cmday, tipo, dettaglio, ts) VALUES (?,?,?,?,?)",
            (idcomp, cmday, tipo, dettaglio, now_rome().isoformat()))
        self.db.commit()

    # --- transizioni ---
    def crea_se_assente(self, idcomp, cmday, ora_limite):
        esistente = self.get(idcomp, cmday)
        if esistente:
            return esistente, False
        self.db.execute(
            "INSERT INTO giornate (idcomp, cmday, stato, ora_limite, updated_at) VALUES (?,?,?,?,?)",
            (idcomp, cmday, DA_PREPARARE, _iso(ora_limite), now_rome().isoformat()))
        self.db.commit()
        self.log(idcomp, cmday, "creata")
        return self.get(idcomp, cmday), True

    def set_proposta(self, idcomp, cmday, spec, msg_id, ora_limite):
        self.db.execute(
            "UPDATE giornate SET stato=?, spec_json=?, msg_id=?, ora_limite=?, updated_at=? "
            "WHERE idcomp=? AND cmday=?",
            (PROPOSTA, json.dumps(spec), msg_id, _iso(ora_limite),
             now_rome().isoformat(), idcomp, cmday))
        self.db.commit()
        self.log(idcomp, cmday, "proposta", spec.get("modulo", ""))

    def set_in_modifica(self, idcomp, cmday):
        self.db.execute(
            "UPDATE giornate SET stato=?, updated_at=? WHERE idcomp=? AND cmday=? AND stato=?",
            (IN_MODIFICA, now_rome().isoformat(), idcomp, cmday, PROPOSTA))
        self.db.commit()

    def blocca(self, idcomp, cmday):
        cur = self.db.execute(
            "UPDATE giornate SET stato=?, updated_at=? "
            "WHERE idcomp=? AND cmday=? AND stato IN (?,?)",
            (BLOCCATA, now_rome().isoformat(), idcomp, cmday, PROPOSTA, IN_MODIFICA))
        self.db.commit()
        ok = cur.rowcount == 1
        if ok:
            self.log(idcomp, cmday, "bloccata")
        return ok

    def prova_lock_invio(self, idcomp, cmday):
        """Lock atomico: solo un chiamante passa da PROPOSTA a INVIO_IN_CORSO."""
        cur = self.db.execute(
            "UPDATE giornate SET stato=?, updated_at=? WHERE idcomp=? AND cmday=? AND stato=?",
            (INVIO_IN_CORSO, now_rome().isoformat(), idcomp, cmday, PROPOSTA))
        self.db.commit()
        return cur.rowcount == 1

    def segna_inviata(self, idcomp, cmday):
        ts = now_rome().isoformat()
        self.db.execute(
            "UPDATE giornate SET stato=?, inviata_at=?, updated_at=? WHERE idcomp=? AND cmday=?",
            (INVIATA, ts, ts, idcomp, cmday))
        self.db.commit()
        self.log(idcomp, cmday, "inviata")

    def segna_errore(self, idcomp, cmday, msg):
        self.db.execute(
            "UPDATE giornate SET stato=?, errore=?, updated_at=? WHERE idcomp=? AND cmday=?",
            (ERRORE, msg, now_rome().isoformat(), idcomp, cmday))
        self.db.commit()
        self.log(idcomp, cmday, "errore", msg)

    def non_terminali(self):
        rows = self.db.execute(
            "SELECT * FROM giornate WHERE stato NOT IN (?,?)", (BLOCCATA, INVIATA)).fetchall()
        return [self._row2g(r) for r in rows]

    def chiudi(self):
        self.db.close()
