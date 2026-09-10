"""Invio riusabile: spec → build_payload → save_lineup → riverifica leggendo dal sito."""
import build_payload as bp

class InvioError(Exception):
    pass

def invia(spec, cmday, session, rm):
    try:
        payload = bp.build_payload(dict(spec, cmday=cmday), rm=rm)
    except bp.ValidationError as e:
        raise InvioError(f"spec non valido: {e}") from e
    try:
        session.save_lineup(payload)
    except Exception as e:
        raise InvioError(f"il sito ha rifiutato l'invio: {e}") from e
    riletto = session.get_lineup()
    mdl_sito = riletto.get("teamLineupDto", {}).get("mdl")
    return {"mdl": payload["mdl"], "starts": payload["starts"],
            "verificato": mdl_sito == payload["mdl"]}
