"""Formattazione dei messaggi Telegram: template 'campo a reparti' in HTML.

Telegram supporta solo un sottoinsieme di HTML (<b>, <i>, <pre>, ...): niente
tabelle né CSS. Qui componiamo un layout leggibile con emoji di ruolo, separatori
e grassetto, robusto sui telefoni (i nomi lunghi vanno a capo).
"""
import html

RUOLO_EMOJI = {"P": "🧤", "D": "🛡", "C": "🎯", "A": "🔥"}
_ORD = ["P", "D", "C", "A"]
_CERCHI = "①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮"
SEP = "━━━━━━━━━━━━━━━━━━"


def _esc(s):
    return html.escape(str(s), quote=False)


def fmt_modulo(modulo):
    cifre = [c for c in str(modulo or "") if c.isdigit()]
    return "-".join(cifre) if cifre else str(modulo or "?")


def _num(i):
    return _CERCHI[i] if i < len(_CERCHI) else f"{i + 1}."


def _raggruppa(nomi, ruoli):
    per = {r: [] for r in _ORD}
    ignoti = []
    for n in nomi:
        r = ruoli.get(n, "?")
        (per[r] if r in per else ignoti).append(n)
    return per, ignoti


def campo(titolari, ruoli):
    """Righe del campo: una per reparto (P/D/C/A) con emoji e nomi separati da ·."""
    per, ignoti = _raggruppa(titolari, ruoli)
    righe = []
    for r in _ORD:
        if per[r]:
            righe.append(f"{RUOLO_EMOJI[r]}  " + " · ".join(_esc(n) for n in per[r]))
    if ignoti:  # nomi senza ruolo noto: non perderli, in coda
        righe.append("▪️  " + " · ".join(_esc(n) for n in ignoti))
    return "\n".join(righe)


def panchina(nomi):
    return "  ".join(f"{_num(i)} {_esc(n)}" for i, n in enumerate(nomi))


def messaggio_proposta(spec, ruoli, lega, cmday, ora_limite):
    quando = ora_limite.strftime("%H:%M") if ora_limite else "?"
    testa = f"⚽ <b>{_esc(lega)}</b> — Giornata {cmday}" if lega else f"⚽ <b>Giornata {cmday}</b>"
    return (
        f"{testa}\n"
        f"🧩 Modulo <b>{fmt_modulo(spec.get('modulo'))}</b>\n{SEP}\n"
        f"{campo(spec.get('titolari', []), ruoli)}\n{SEP}\n"
        f"🪑 <b>Panchina</b> (ordine d'ingresso)\n{panchina(spec.get('panchina', []))}\n{SEP}\n"
        f"⏳ Auto-invio entro le <b>{quando}</b> se non intervieni")


def messaggio_sito(titolari, panca, ruoli, modulo):
    """Formazione attualmente salvata sul sito (comando /vedi)."""
    return (
        f"📋 <b>Sul sito ora</b> — modulo <b>{fmt_modulo(modulo)}</b>\n{SEP}\n"
        f"{campo(titolari, ruoli)}\n{SEP}\n"
        f"🪑 <b>Panchina</b>\n{panchina(panca)}")
