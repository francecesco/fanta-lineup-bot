#!/usr/bin/env python3
"""Legge rosa.xlsx e la stampa in forma leggibile, oppure genera il template.

Uso:
  leggi_rosa.py [percorso/rosa.xlsx]        stampa la rosa (default: cerca rosa.xlsx
                                            nella cartella corrente e nelle superiori)
  leggi_rosa.py --template [percorso]       crea un rosa.xlsx di esempio da sovrascrivere

Colonne attese in riga 1 (ordine libero, maiuscole ignorate):
  Ruolo | Giocatore | Squadra | Quotazione | Pagato | Note
Le ultime tre sono facoltative. Ruolo: P, D, C, A (accettati anche Por/Dif/Cen/Att).
"""
import sys
import os
from pathlib import Path

try:
    import openpyxl
except ImportError:
    sys.stderr.write(
        "openpyxl non installato. Esegui questo script tramite rosa.sh, che crea "
        "l'ambiente virtuale della skill e installa la libreria.\n"
    )
    sys.exit(2)

RUOLI = {"P": "P", "D": "D", "C": "C", "A": "A",
         "POR": "P", "DIF": "D", "CEN": "C", "ATT": "A",
         "PORTIERE": "P", "DIFENSORE": "D", "CENTROCAMPISTA": "C", "ATTACCANTE": "A"}
ORDINE = ["P", "D", "C", "A"]
NOME_RUOLO = {"P": "Portieri", "D": "Difensori", "C": "Centrocampisti", "A": "Attaccanti"}
SLOT_ATTESI = {"P": 3, "D": 8, "C": 8, "A": 6}

ALIAS = {
    "ruolo": "ruolo", "r": "ruolo",
    "giocatore": "giocatore", "nome": "giocatore", "calciatore": "giocatore",
    "squadra": "squadra", "club": "squadra", "team": "squadra",
    "quotazione": "quotazione", "qt": "quotazione", "qt.a": "quotazione", "quota": "quotazione",
    "pagato": "pagato", "prezzo": "pagato", "costo": "pagato",
    "note": "note", "nota": "note",
}


def trova_file(arg: str | None) -> Path:
    if arg:
        p = Path(arg).expanduser()
        if not p.exists():
            sys.exit(f"File non trovato: {p}")
        return p
    here = Path.cwd()
    for cartella in [here, *here.parents]:
        for nome in ("rosa.xlsx", "rosa.xlsm", "rosa.xls"):
            cand = cartella / nome
            if cand.exists():
                return cand
    sys.exit(
        "rosa.xlsx non trovato nella cartella corrente ne' nelle superiori. "
        "Crea il template con: rosa.sh --template"
    )


def leggi(percorso: Path) -> list[dict]:
    if percorso.suffix.lower() == ".xls":
        sys.exit(
            f"{percorso.name} e' nel vecchio formato binario .xls: aprilo con Excel/Numbers "
            "e salvalo come rosa.xlsx, poi rilancia."
        )
    wb = openpyxl.load_workbook(percorso, read_only=True, data_only=True)
    ws = wb["Rosa"] if "Rosa" in wb.sheetnames else wb.worksheets[0]
    righe = [r for r in ws.iter_rows(values_only=True) if any(c is not None and str(c).strip() for c in r)]
    if not righe:
        sys.exit("Il foglio e' vuoto.")
    intestazione = [ALIAS.get(str(c).strip().lower(), None) if c is not None else None for c in righe[0]]
    if "ruolo" not in intestazione or "giocatore" not in intestazione:
        sys.exit(
            "Riga 1 deve contenere almeno le colonne 'Ruolo' e 'Giocatore' "
            f"(trovate: {[c for c in righe[0] if c is not None]})."
        )
    idx = {nome: i for i, nome in enumerate(intestazione) if nome}
    rosa = []
    for n, r in enumerate(righe[1:], start=2):
        def cella(k):
            i = idx.get(k)
            if i is None or i >= len(r) or r[i] is None:
                return ""
            return str(r[i]).strip()
        ruolo_raw = cella("ruolo").upper()
        ruolo = RUOLI.get(ruolo_raw)
        if not ruolo:
            sys.stderr.write(f"Riga {n}: ruolo '{ruolo_raw}' non riconosciuto, saltata.\n")
            continue
        if not cella("giocatore"):
            continue
        rosa.append({
            "ruolo": ruolo, "giocatore": cella("giocatore"), "squadra": cella("squadra"),
            "quotazione": cella("quotazione"), "pagato": cella("pagato"), "note": cella("note"),
        })
    return rosa


def stampa(rosa: list[dict], percorso: Path) -> None:
    print(f"# Rosa letta da {percorso}  ({len(rosa)} giocatori)\n")
    nomi = {g["giocatore"] for g in rosa}
    esempio = {n for _, n, _, _ in ESEMPIO}
    if nomi == esempio:
        print(
            "> ATTENZIONE: questa e' ancora la rosa di ESEMPIO del template, non una rosa reale.\n"
            "> Avvisa l'utente e chiedi di compilare il file con la sua rosa prima di dare consigli.\n"
        )
    for ruolo in ORDINE:
        gruppo = [g for g in rosa if g["ruolo"] == ruolo]
        attesi = SLOT_ATTESI[ruolo]
        avviso = "" if len(gruppo) == attesi else f"  (ATTENZIONE: attesi {attesi})"
        print(f"## {NOME_RUOLO[ruolo]} ({len(gruppo)}){avviso}\n")
        print("| Giocatore | Squadra | Qt | Pagato | Note |")
        print("|---|---|---|---|---|")
        for g in gruppo:
            print(f"| {g['giocatore']} | {g['squadra']} | {g['quotazione']} | {g['pagato']} | {g['note']} |")
        print()
    squadre = sorted({g["squadra"] for g in rosa if g["squadra"]})
    print("## Squadre di Serie A coinvolte\n")
    print(", ".join(squadre) if squadre else "(colonna Squadra vuota: compilala, serve per cercare avversari e formazioni)")


ESEMPIO = [
    ("P", "Svilar", "Roma", ""), ("P", "Gollini", "Roma", "riserva blocco"), ("P", "Okoye", "Udinese", "titolare"),
    ("D", "Dimarco", "Inter", ""), ("D", "Bastoni", "Inter", ""), ("D", "Akanji", "Inter", ""),
    ("D", "Solet", "Udinese", ""), ("D", "Spinazzola", "Napoli", ""), ("D", "Theate", "Bologna", ""),
    ("C", "Calhanoglu", "Inter", "rigorista"), ("C", "De Bruyne", "Napoli", ""), ("C", "Zaccagni", "Lazio", ""),
    ("C", "Da Cunha", "Como", ""), ("C", "Politano", "Napoli", ""), ("C", "Orsolini", "Bologna", "rigorista"),
    ("C", "McTominay", "Napoli", ""), ("C", "Barella", "Inter", ""),
    ("A", "Thuram", "Inter", ""), ("A", "Hojlund", "Napoli", ""), ("A", "Douvikas", "Como", ""),
    ("A", "Kean", "Fiorentina", ""), ("A", "Scamacca", "Atalanta", ""), ("A", "Ramos G.", "Milan", ""),
]


def quotazioni_da_listone(cartella: Path) -> dict[str, str]:
    """Se nella cartella c'e' il listone Quotazioni_*.xlsx, recupera Qt.A per nome."""
    quote: dict[str, str] = {}
    for f in cartella.glob("Quotazioni_*.xlsx"):
        try:
            wb = openpyxl.load_workbook(f, read_only=True, data_only=True)
            ws = wb["Tutti"] if "Tutti" in wb.sheetnames else wb.worksheets[0]
            righe = list(ws.iter_rows(values_only=True))
            for i, r in enumerate(righe):
                if r and "Nome" in r and "Qt.A" in r:
                    i_nome, i_qt = r.index("Nome"), r.index("Qt.A")
                    for rr in righe[i + 1:]:
                        if rr and rr[i_nome]:
                            quote[str(rr[i_nome]).strip()] = str(rr[i_qt] or "")
                    break
        except Exception:
            pass
    return quote


def crea_template(percorso: Path) -> None:
    if percorso.exists():
        sys.exit(f"{percorso} esiste gia': non lo sovrascrivo. Cancellalo o rinominalo prima.")
    quote = quotazioni_da_listone(percorso.parent)
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Rosa"
    ws.append(["Ruolo", "Giocatore", "Squadra", "Quotazione", "Pagato", "Note"])
    for ruolo, nome, squadra, nota in ESEMPIO:
        ws.append([ruolo, nome, squadra, quote.get(nome, ""), "", nota])
    for col, larghezza in zip("ABCDEF", (8, 22, 14, 12, 10, 40)):
        ws.column_dimensions[col].width = larghezza
    wb.save(percorso)
    print(f"Template creato: {percorso}\nE' una rosa di ESEMPIO (dal tuo piano d'asta): sostituisci le righe con la tua rosa reale.")


def main(argv: list[str]) -> None:
    if argv and argv[0] in ("-h", "--help"):
        print(__doc__)
        return
    if argv and argv[0] == "--template":
        dest = Path(argv[1]).expanduser() if len(argv) > 1 else Path.cwd() / "rosa.xlsx"
        crea_template(dest)
        return
    percorso = trova_file(argv[0] if argv else None)
    rosa = leggi(percorso)
    if not rosa:
        sys.exit("Nessun giocatore valido trovato nel file.")
    stampa(rosa, percorso)


if __name__ == "__main__":
    main(sys.argv[1:])
