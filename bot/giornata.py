"""Da risposta get_lineup → tabella-rosa testuale per Gemini + metadati giornata. Puro."""
RUOLO = {1: "P", 2: "D", 3: "C", 4: "A"}
_ORD = {"P": 0, "D": 1, "C": 2, "A": 3}

def _role(p):
    r = p.get("role")
    r = r[0] if isinstance(r, list) and r else r
    return RUOLO.get(int(r), "?")

def cmday(res: dict) -> int:
    return res["teamLineupDto"]["cmday"]

def squadre_utente(res: dict) -> list:
    viste, out = set(), []
    for p in res.get("lineUpInfo", []):
        t = p.get("tname")
        if t and t not in viste:
            viste.add(t)
            out.append(t)
    return out

def tabella_rosa(res: dict) -> str:
    info = res.get("lineUpInfo", [])
    righe = []
    for p in sorted(info, key=lambda x: (_ORD.get(_role(x), 9), -(x.get("percent") or 0))):
        dove = "casa" if p.get("hoaw") == 0 else "trasferta"
        stato = "OK" if p.get("status") == 1 else "INDISPONIBILE"
        righe.append(
            f"{_role(p)} | {p['plyr']} | {p['tname']} | {p.get('teamH')}-{p.get('teamA')} "
            f"({dove}) | titolarità {p.get('percent')}% | {stato} "
            f"| media {p.get('agrd')} fantamedia {p.get('fagrd')}")
    return "\n".join(righe)
