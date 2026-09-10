"""Invia una formazione al sito, partendo da una spec `formazione.json`.

Flusso: legge la spec → valida e costruisce il payload → mostra l'anteprima →
chiede conferma → login + invio.

Uso:
    python3 invia_formazione.py formazione.json          # chiede conferma
    python3 invia_formazione.py formazione.json --yes     # invia senza chiedere (per Hermes)

Richiede FANTA_USER / FANTA_PWD nel file .env.
"""

import json
import sys

import build_payload as bp
import config
import fanta_api as fa
from roster_map import RosterMap

RUOLO_NOME = {"P": "Por", "D": "Dif", "C": "Cen", "A": "Att"}


def anteprima(spec, rm):
    testa = f"Modulo: {str(spec['modulo']).replace('-', '')}"
    if spec.get("cmday"):
        testa += f"   (Serie A giornata {spec['cmday']}, turno lega {spec.get('mday', '?')})"
    righe = [testa, "Titolari:"]
    # Ordina i titolari per ruolo per una lettura chiara.
    tit = [(n, rm.resolve(n)[1]) for n in spec["titolari"]]
    tit.sort(key=lambda t: bp.ORDINE_RUOLI[t[1]])
    for n, role in tit:
        righe.append(f"  {RUOLO_NOME.get(role, role)}  {n}")
    righe.append("Panchina (ordine di ingresso):")
    for i, n in enumerate(spec.get("panchina", []), 1):
        role = rm.resolve(n)[1]
        righe.append(f"  {i:>2}. {RUOLO_NOME.get(role, role)}  {n}")
    cap = spec.get("capitano") or []
    if cap:
        righe.append(f"Capitano: {', '.join(cap)}")
    return "\n".join(righe)


def invia(spec, conferma_automatica=False, base_dir="."):
    rm = RosterMap(base_dir=base_dir)

    env = fa.load_env(f"{base_dir}/.env" if base_dir != "." else ".env")
    user, pwd = env.get("FANTA_USER"), env.get("FANTA_PWD")
    if not user or not pwd:
        raise SystemExit("Mancano FANTA_USER / FANTA_PWD nel file .env")

    # Sessione con ri-login automatico se il token scade (robustezza).
    session = fa.FantaSession(user, pwd, config.LEGA["id_squadra"], config.LEGA["idcomp"])

    # Lettura della giornata corrente DAL SITO (autorevole): mai indovinare mday/cmday.
    dto = session.get_lineup()["teamLineupDto"]
    spec = dict(spec, mday=dto["mday"], cmday=dto["cmday"])   # sovrascrive quanto nel file

    payload = bp.build_payload(spec, rm=rm)          # valida tutto

    print(anteprima(spec, rm))
    print()

    if not conferma_automatica:
        risposta = input("Invio questa formazione sul sito? [s/N] ").strip().lower()
        if risposta not in ("s", "si", "sì", "y", "yes"):
            print("Annullato: niente inviato.")
            return None

    _status, resp = session.save_lineup(payload)
    print(f"✓ Inviata. Il sito conferma: modulo {resp.get('mdl')}, giornata lega {resp.get('mday')}, "
          f"{len(resp.get('starts') or [])} titolari, {len(resp.get('bench') or [])} in panchina.")
    return resp


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return
    path = argv[0]
    conferma_automatica = "--yes" in argv[1:]
    with open(path, "r", encoding="utf-8") as f:
        spec = json.load(f)
    invia(spec, conferma_automatica=conferma_automatica)


if __name__ == "__main__":
    main(sys.argv[1:])
