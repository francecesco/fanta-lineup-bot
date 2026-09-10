"""Mappa nome giocatore ↔ ID fantacalcio.it, con ruolo e squadra.

Fonte ID/ruolo: il listone `Quotazioni_*.xlsx` (colonna `Id` = ID usato dall'API,
verificato). Fonte dei giocatori posseduti: `rosa.xlsx`.

Uso tipico:
    rm = RosterMap()
    rm.resolve("Calhanoglu")   -> (2194, "C")
"""

import os
import unicodedata

import config

# openpyxl è importato in modo "lazy" dentro i metodi di caricamento: così build_payload
# può essere usato con un RosterMap alternativo anche senza openpyxl installato.


def _norm(name):
    """Normalizza un nome per il confronto tollerante (accenti, maiuscole, spazi)."""
    s = unicodedata.normalize("NFKD", str(name))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return " ".join(s.lower().split())


class RosterMap:
    def __init__(self, quotazioni=None, rosa=None, base_dir="."):
        self.quotazioni_path = os.path.join(base_dir, quotazioni or config.FILE_QUOTAZIONI)
        self.rosa_path = os.path.join(base_dir, rosa or config.FILE_ROSA)
        self._by_name = {}       # nome esatto -> (id, ruolo, squadra)
        self._by_norm = {}       # nome normalizzato -> lista di (nome, id, ruolo)
        self.owned = {}          # nome esatto in rosa -> ruolo
        self._load_quotazioni()
        self._load_rosa()

    # ---- caricamento ----
    def _load_quotazioni(self):
        import openpyxl
        wb = openpyxl.load_workbook(self.quotazioni_path, read_only=True, data_only=True)
        ws = wb["Tutti"] if "Tutti" in wb.sheetnames else wb.active
        rows = list(ws.iter_rows(values_only=True))
        hdr_i = next(i for i, r in enumerate(rows[:5])
                     if r and any(str(c).strip().lower() == "id" for c in r if c is not None))
        hdr = [str(c).strip().lower() if c is not None else "" for c in rows[hdr_i]]
        ci, cn, cr = hdr.index("id"), hdr.index("nome"), hdr.index("r")
        cs = hdr.index("squadra") if "squadra" in hdr else None
        for r in rows[hdr_i + 1:]:
            if r[ci] is None or r[cn] is None:
                continue
            name = str(r[cn]).strip()
            pid = int(r[ci])
            role = str(r[cr]).strip().upper()
            team = str(r[cs]).strip() if cs is not None and r[cs] is not None else ""
            self._by_name[name] = (pid, role, team)
            self._by_norm.setdefault(_norm(name), []).append((name, pid, role))

    def _load_rosa(self):
        import openpyxl
        wb = openpyxl.load_workbook(self.rosa_path, read_only=True, data_only=True)
        ws = wb["Rosa"] if "Rosa" in wb.sheetnames else wb.active
        rows = [r for r in ws.iter_rows(values_only=True)
                if any(c is not None and str(c).strip() for c in r)]
        hdr = [str(c).strip().lower() if c is not None else "" for c in rows[0]]
        ir = hdr.index("ruolo") if "ruolo" in hdr else 0
        ig = hdr.index("giocatore") if "giocatore" in hdr else 1
        rolemap = {"P": "P", "D": "D", "C": "C", "A": "A",
                   "POR": "P", "DIF": "D", "CEN": "C", "ATT": "A"}
        for r in rows[1:]:
            if ig >= len(r) or r[ig] is None:
                continue
            name = str(r[ig]).strip()
            role = rolemap.get(str(r[ir]).strip().upper(), "") if ir < len(r) and r[ir] else ""
            if name:
                self.owned[name] = role

    # ---- risoluzione ----
    def resolve(self, name, require_owned=True):
        """Restituisce (id, ruolo) per un giocatore. Solleva ValueError se non risolvibile.

        Con require_owned=True, il giocatore deve essere in `rosa.xlsx`.
        """
        key = str(name).strip()
        if require_owned and key not in self.owned and _norm(key) not in {_norm(k) for k in self.owned}:
            raise ValueError(f"'{name}' non è nella tua rosa (rosa.xlsx)")
        if key in self._by_name:
            pid, role, _ = self._by_name[key]
            return pid, role
        cands = self._by_norm.get(_norm(key), [])
        if len(cands) == 1:
            _n, pid, role = cands[0]
            return pid, role
        if not cands:
            raise ValueError(f"'{name}' non trovato nel listone quotazioni "
                             f"({config.FILE_QUOTAZIONI})")
        names = ", ".join(n for n, _, _ in cands)
        raise ValueError(f"'{name}' è ambiguo nel listone: {names}. Usa il nome esatto.")

    def role_of(self, name):
        return self.resolve(name)[1]
