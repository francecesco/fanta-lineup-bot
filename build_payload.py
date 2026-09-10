"""Costruisce e valida il payload di salvataggio formazione a partire dai NOMI.

La skill `consiglia-formazione` sceglie modulo, titolari e panchina per nome; qui
li traduciamo nel body JSON che l'API si aspetta, con tutti i controlli di validità.

Spec in ingresso (dict, es. da `formazione.json`):
    {
      "modulo": "433",
      "titolari": ["Vicario", "Wesley", ...],   # 11 nomi
      "panchina": ["Grabara", ...],             # fino a 12 nomi, ordinati
      "capitano": [],                            # opzionale (formato TBD)
      "mday": 1                                  # giornata da schierare
    }
"""

import config
from roster_map import RosterMap

ORDINE_RUOLI = {"P": 0, "D": 1, "C": 2, "A": 3}


class ValidationError(Exception):
    """Formazione non valida (conteggi, ruoli, giocatori non posseduti, ...)."""


def _resolve(rm, name):
    """Risolve un nome, convertendo gli errori in ValidationError uniformi."""
    try:
        return rm.resolve(name)
    except ValueError as e:
        raise ValidationError(str(e)) from e


def build_payload(spec, rm=None, base_dir="."):
    rm = rm or RosterMap(base_dir=base_dir)

    modulo = str(spec.get("modulo", "")).replace("-", "").strip()
    if modulo not in config.MODULI:
        raise ValidationError(
            f"Modulo '{spec.get('modulo')}' non ammesso. Ammessi: {', '.join(config.MODULI)}"
        )
    need_d, need_c, need_a = config.MODULI[modulo]

    titolari = list(spec.get("titolari", []))
    panchina = list(spec.get("panchina", []))
    capitano = list(spec.get("capitano", []) or [])

    if len(titolari) != 11:
        raise ValidationError(f"Servono 11 titolari, ricevuti {len(titolari)}")
    if getattr(config, "PANCHINA_FISSA", False):
        # Panchina fissa: il sito pretende ESATTAMENTE tbench giocatori (LUP012).
        if len(panchina) != config.MAX_PANCHINA:
            raise ValidationError(
                f"Panchina fissa: servono esattamente {config.MAX_PANCHINA} in panchina, "
                f"ricevuti {len(panchina)}"
            )
    elif len(panchina) > config.MAX_PANCHINA:
        raise ValidationError(
            f"Panchina troppo lunga: {len(panchina)} > {config.MAX_PANCHINA}"
        )

    dup = _duplicati(titolari + panchina)
    if dup:
        raise ValidationError(f"Giocatori ripetuti: {', '.join(dup)}")

    # Risolvi titolari con ruolo, per validare il modulo e ordinare.
    tit = []
    for n in titolari:
        pid, role = _resolve(rm, n)
        tit.append((n, pid, role))

    conteggio = {"P": 0, "D": 0, "C": 0, "A": 0}
    for _n, _pid, role in tit:
        conteggio[role] = conteggio.get(role, 0) + 1
    atteso = {"P": 1, "D": need_d, "C": need_c, "A": need_a}
    if conteggio != atteso:
        raise ValidationError(
            f"Reparti non coerenti col modulo {modulo}: "
            f"attesi P1 D{need_d} C{need_c} A{need_a}, "
            f"trovati P{conteggio['P']} D{conteggio['D']} C{conteggio['C']} A{conteggio['A']}"
        )

    # Ordine richiesto dall'API: P, D, C, A (poi ordine di inserimento).
    tit.sort(key=lambda t: ORDINE_RUOLI[t[2]])
    starts_ids = [pid for _n, pid, _r in tit]

    # Panchina: mantiene l'ordine fornito (è già l'ordine di ingresso).
    bench_ids = [_resolve(rm, n)[0] for n in panchina]

    # Capitano: risolto se presente. NB formato server ancora da confermare.
    capt_ids = [_resolve(rm, n)[0] for n in capitano]
    for n in capitano:
        if n not in titolari:
            raise ValidationError(f"Il capitano '{n}' non è tra i titolari")

    mday = int(spec.get("mday", 1))
    cmday = int(spec["cmday"]) if spec.get("cmday") is not None else mday

    return {
        "starts": starts_ids,
        "bench": bench_ids,
        "capt": capt_ids,
        "mdl": modulo,
        "idcomp": config.LEGA["idcomp"],
        "mday": mday,
        "cmday": cmday,
        "tid": config.LEGA["id_squadra"],
        "allComp": False,
        "visb": True,
        "swtcA": 0,
        "swtcB": 0,
        "swtc": 0,
        "swtcMdl": "",
    }


def _duplicati(nomi):
    visti, dup = set(), []
    for n in nomi:
        if n in visti and n not in dup:
            dup.append(n)
        visti.add(n)
    return dup
