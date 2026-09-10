"""Configurazione del bot: segreti da .env, ID lega da config.LEGA, tunables con default."""
from dataclasses import dataclass, field
import fanta_api
import config

# Cutoff di sicurezza per giorno della settimana (0=lunedì ... 6=domenica): ora limite "HH:MM"
# oltre cui NON si invia più, usato quando il calendario reale non è disponibile/attendibile.
# Default prudente: prima dell'anticipo delle 12:30 nei weekend, prima dei posticipi infrasettimanali.
ORARI_DEFAULT = {
    "ora_heartbeat": "08:00",
    "buffer_invio_min": 30,
    "max_tentativi_gemini": 3,
    "gemini_model": "gemini-3.6-flash",
    "tz": "Europe/Rome",
    "db_path": "bot.db",
    "cutoff_fallback": {0: "18:15", 1: "18:15", 2: "18:15", 3: "18:15",
                        4: "18:15", 5: "12:15", 6: "12:15"},
}

_SEGRETI = ["FANTA_USER", "FANTA_PWD", "GEMINI_API_KEY",
            "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"]

@dataclass
class Settings:
    fanta_user: str
    fanta_pwd: str
    gemini_api_key: str
    telegram_token: str
    telegram_chat_id: str
    lega: dict
    ora_heartbeat: str = ORARI_DEFAULT["ora_heartbeat"]
    buffer_invio_min: int = ORARI_DEFAULT["buffer_invio_min"]
    max_tentativi_gemini: int = ORARI_DEFAULT["max_tentativi_gemini"]
    cutoff_fallback: dict = field(default_factory=lambda: dict(ORARI_DEFAULT["cutoff_fallback"]))
    tz: str = ORARI_DEFAULT["tz"]
    db_path: str = ORARI_DEFAULT["db_path"]
    gemini_model: str = ORARI_DEFAULT["gemini_model"]

def carica_settings(env_path: str = ".env") -> Settings:
    env = fanta_api.load_env(env_path)
    mancanti = [k for k in _SEGRETI if not env.get(k)]
    if mancanti:
        raise ValueError(f"Segreti mancanti in {env_path}: {', '.join(mancanti)}")
    return Settings(
        fanta_user=env["FANTA_USER"],
        fanta_pwd=env["FANTA_PWD"],
        gemini_api_key=env["GEMINI_API_KEY"],
        telegram_token=env["TELEGRAM_BOT_TOKEN"],
        telegram_chat_id=env["TELEGRAM_CHAT_ID"],
        lega=dict(config.LEGA),
        ora_heartbeat=getattr(config, "ORA_HEARTBEAT", ORARI_DEFAULT["ora_heartbeat"]),
        buffer_invio_min=getattr(config, "BUFFER_INVIO_MIN", ORARI_DEFAULT["buffer_invio_min"]),
        max_tentativi_gemini=getattr(config, "MAX_TENTATIVI_GEMINI", ORARI_DEFAULT["max_tentativi_gemini"]),
        cutoff_fallback=getattr(config, "CUTOFF_FALLBACK", dict(ORARI_DEFAULT["cutoff_fallback"])),
        tz=getattr(config, "TZ_BOT", ORARI_DEFAULT["tz"]),
        db_path=getattr(config, "DB_PATH", ORARI_DEFAULT["db_path"]),
        gemini_model=getattr(config, "GEMINI_MODEL", ORARI_DEFAULT["gemini_model"]),
    )
