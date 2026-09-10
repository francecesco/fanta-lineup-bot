#!/usr/bin/env python3
"""Legge dal sito lo stato della giornata per la tua rosa e lo stampa leggibile.

Per ogni giocatore: partita di giornata, casa/trasferta, % di titolarità (probabile
del sito), disponibilità (infortunato/squalificato), media e fantamedia. È la base
"autorevole" per il consiglio formazione: la ricerca web serve solo a rifinire
(rigoristi, forma recente, ballottaggi last-minute, conflitti).

Uso:  python3 stato_giornata.py
Richiede FANTA_USER / FANTA_PWD nel file .env della cartella del progetto.
"""

import os
import sys

_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _DIR)

import config
import fanta_api as fa

RUOLO = {1: "P", 2: "D", 3: "C", 4: "A"}
NOME_RUOLO = {"P": "Portieri", "D": "Difensori", "C": "Centrocampisti", "A": "Attaccanti"}
ORDINE = ["P", "D", "C", "A"]


def _role(p):
    r = p.get("role")
    if isinstance(r, list) and r:
        r = r[0]
    try:
        return RUOLO.get(int(r), "?")
    except (TypeError, ValueError):
        return "?"


def main():
    env = fa.load_env(os.path.join(_DIR, ".env"))
    user, pwd = env.get("FANTA_USER"), env.get("FANTA_PWD")
    if not user or not pwd:
        sys.exit("Mancano FANTA_USER / FANTA_PWD nel file .env")

    data = fa.login(user, pwd)
    lega = fa.find_league(data, config.LEGA["id_squadra"])
    res = fa.get_lineup(lega["jwt"], config.LEGA["idcomp"], lega.get("divisione", "A"))
    dto = res["teamLineupDto"]
    info = res["lineUpInfo"]

    print(f"# Stato giornata — {config.LEGA['nome']}")
    print(f"Serie A giornata {dto.get('cmday')} · turno lega {dto.get('mday')} · "
          f"modulo attualmente salvato: {dto.get('mdl')}\n")
    print("Legenda: %tit = probabile titolarità (sito) · Stato: OK / INDISPONIBILE (infortunato/squalificato)")
    print("         Media = media voto · FMedia = fantamedia (con bonus/malus). 0.0 = ancora senza voti.\n")

    for ruolo in ORDINE:
        gruppo = [p for p in info if _role(p) == ruolo]
        gruppo.sort(key=lambda p: (p.get("status", 1) == 2, -(p.get("percent") or 0)))
        print(f"## {NOME_RUOLO[ruolo]}\n")
        print(f"| {'Giocatore':<16} | {'Squadra':<11} | {'Partita':<9} | Dove | %tit | Stato | Media | FMedia |")
        print(f"|{'-'*18}|{'-'*13}|{'-'*11}|------|------|-------|-------|--------|")
        for p in gruppo:
            dove = "casa" if p.get("hoaw") == 0 else "tras"
            stato = "OK" if p.get("status") == 1 else "INDISPONIBILE"
            partita = f"{p.get('teamH','')}-{p.get('teamA','')}"
            print(f"| {str(p.get('plyr','')):<16} | {str(p.get('tname','')):<11} | {partita:<9} "
                  f"| {dove:<4} | {str(p.get('percent','')):>3}% | {stato:<5} "
                  f"| {str(p.get('agrd','')):>5} | {str(p.get('fagrd','')):>5} |")
        print()


if __name__ == "__main__":
    main()
