# app.py
import os, json, time, datetime as dt
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel, Field, field_validator
from telegram import Bot

# =========================
# Paths y helpers
# =========================
BASE_DIR = Path(__file__).resolve().parent
KB_PATH = BASE_DIR / "kb_noise.json"
SETTINGS_PATH = BASE_DIR / "settings.json"

def load_json(path: Path, default_obj: dict) -> dict:
    """Lee JSON; si no existe lo crea con default."""
    if not path.exists():
        path.write_text(json.dumps(default_obj, indent=2), encoding="utf-8")
        # devolvemos una copia en memoria, no la referencia original
        return json.loads(json.dumps(default_obj))
    return json.loads(path.read_text(encoding="utf-8"))

def save_json(path: Path, obj: dict) -> None:
    """Escribe JSON de forma segura (archivo temporal + replace)."""
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2), encoding="utf-8")
    tmp.replace(path)

# =========================
# Defaults
# =========================
DEFAULT_SETTINGS = {
  "auth_token": "tokenarduino",
  "telegram_token": "8452001489:AAHVFF63RAeLKa3sQ3u5ez-GwD5hqobunNU",
  "telegram_chat_id": 1206197921
}

DEFAULT_KB = {
    "alpha": 0.1,
    "k_bounds": {"min": 2.0, "max": 4.0},
    "pico_min": 150.0,
    "warmup_samples": 300,
    "cooldown_sec": 7,
    "last_alert_ts": 0,
    "bands": [
        {"name":"band1","start":"08:00","end":"12:00","mu_rms":90,"sigma_rms":15,"k":3.0,"samples":0},
        {"name":"band2","start":"14:00","end":"20:00","mu_rms":110,"sigma_rms":20,"k":3.0,"samples":0},
        {"name":"band3","start":"21:00","end":"05:00","mu_rms":60,"sigma_rms":10,"k":3.5,"samples":0}
    ],
    "perf": {"fp": 0, "fn": 0}
}

# =========================
# Carga settings + KB
# =========================
# 1) Settings: primero settings.json, luego permitir override por variables de entorno
_settings = load_json(SETTINGS_PATH, DEFAULT_SETTINGS)
SETTINGS = {
    "auth_token": os.getenv("AGENT_AUTH_TOKEN", _settings.get("auth_token", DEFAULT_SETTINGS["auth_token"])),
    "telegram_token": os.getenv("TELEGRAM_BOT_TOKEN", _settings.get("telegram_token", DEFAULT_SETTINGS["telegram_token"])),
    "telegram_chat_id": int(os.getenv("TELEGRAM_CHAT_ID", _settings.get("telegram_chat_id", DEFAULT_SETTINGS["telegram_chat_id"]))),
}

# 2) KB: si no existe se crea con DEFAULT_KB
kb = load_json(KB_PATH, DEFAULT_KB)

# =========================
# Telegram bot
# =========================
bot = Bot(SETTINGS["telegram_token"])

def send_telegram(text: str) -> None:
    try:
        bot.send_message(chat_id=SETTINGS["telegram_chat_id"], text=text, parse_mode="Markdown")
    except Exception as e:
        print("Telegram error:", e)

# =========================
# Utilidades lógicas
# =========================
def ensure_auth(header: Optional[str]) -> None:
    if not header:
        raise HTTPException(401, "Missing Authorization header")
    typ, _, tok = header.partition(" ")
    if typ.lower() != "bearer" or tok.strip() != SETTINGS["auth_token"]:
        raise HTTPException(401, "Invalid token")

def hhmm_to_min(hhmm: str) -> int:
    h, m = map(int, hhmm.split(":"))
    return h * 60 + m

def band_now(kb_obj: dict) -> dict:
    now = dt.datetime.now()
    t = now.hour * 60 + now.minute
    for b in kb_obj["bands"]:
        s, e = hhmm_to_min(b["start"]), hhmm_to_min(b["end"])
        # banda normal
        if e >= s and s <= t < e:
            return b
        # banda que cruza medianoche
        if e < s and (t >= s or t < e):
            return b
    return kb_obj["bands"][0]

def persist_kb() -> None:
    save_json(KB_PATH, kb)

# =========================
# Modelos Pydantic (v2)
# =========================
class Ingest(BaseModel):
    device_id: str
    ts: int = Field(default_factory=lambda: int(time.time()))
    rms: float
    peak: int
    v: int = 1

    @field_validator("rms")
    @classmethod
    def _rms_ok(cls, v: float):
        if v < 0:
            raise ValueError("rms must be >= 0")
        return v

    @field_validator("peak")
    @classmethod
    def _peak_ok(cls, v: int):
        if v < 0:
            raise ValueError("peak must be >= 0")
        return v

class SetBand(BaseModel):
    name: str
    start: str = Field(..., pattern=r"^\d{2}:\d{2}$")
    end: str   = Field(..., pattern=r"^\d{2}:\d{2}$")

class SetK(BaseModel):
    name: str
    k: float


########### FastAPI app

app = FastAPI(title="Noise Agent (FastAPI)", version="1.1")

@app.get("/status")
def get_status(authorization: Optional[str] = Header(None)):
    ensure_auth(authorization)
    return {
        "ok": True,
        "now": dt.datetime.now().isoformat(),
        "kb": kb,
        "settings": {
            "has_auth_token": bool(SETTINGS["auth_token"]),
            "has_telegram_token": bool(SETTINGS["telegram_token"]),
            "telegram_chat_id": SETTINGS["telegram_chat_id"],
        },
    }

@app.post("/ingest")
def ingest(payload: Ingest, authorization: Optional[str] = Header(None)):
    ensure_auth(authorization)

    # Cotas "sanity" opcionales para descartar valores imposibles
    RMS_MAX, PEAK_MAX = 4095.0, 4095
    if not (0.0 <= payload.rms <= RMS_MAX):
        return {"ok": False, "ignored": "rms_out_of_range"}
    if not (0 <= payload.peak <= PEAK_MAX):
        return {"ok": False, "ignored": "peak_out_of_range"}

    b = band_now(kb)
    alpha      = kb["alpha"]
    pico_min   = kb["pico_min"]
    warmup     = kb["warmup_samples"]
    cooldown   = kb.get("cooldown_sec", 7)
    last_alert = kb.get("last_alert_ts", 0)
    now_ts     = int(time.time())

    in_warmup   = b["samples"] < warmup
    in_cooldown = (now_ts - last_alert) < cooldown
    threshold   = b["mu_rms"] + b["k"] * b["sigma_rms"]

    is_event = (not in_warmup) and (payload.rms > threshold) and (payload.peak > pico_min) and (not in_cooldown)

    if is_event:
        msg = (
            "🚨 *¡Alerta de sonido alto detectado!* 🚨\n\n"
            f"Se ha registrado un nivel de ruido que supera el umbral permitido.\n\n"
            f"📍 *Banda horaria:* {b['name']} ({b['start']} - {b['end']})\n"
            f"📟 *Dispositivo:* `{payload.device_id}`\n"
            f"📊 *Intensidad del sonido:* {payload.rms:.1f}\n"
            f"🔉 *Pico máximo:* {payload.peak}\n\n"
            "_Por favor, revise el entorno para identificar la fuente del sonido._"
            )
        send_telegram(msg)
        kb["last_alert_ts"] = now_ts
        persist_kb()
        return {"ok": True, "event": True, "threshold": threshold}

    # Aprendizaje incremental (EMA) solo en NO evento
    new_mu = (1 - alpha) * b["mu_rms"] + alpha * payload.rms
    new_sigma = (1 - alpha) * b["sigma_rms"] + alpha * abs(payload.rms - new_mu)
    b["mu_rms"] = new_mu
    b["sigma_rms"] = max(5.0, new_sigma)  
    b["samples"] = b.get("samples", 0) + 1

    persist_kb()
    return {"ok": True, "event": False, "threshold": threshold}

@app.post("/setband")
def set_band(body: SetBand, authorization: Optional[str] = Header(None)):
    ensure_auth(authorization)
    for b in kb["bands"]:
        if b["name"] == body.name:
            b["start"], b["end"] = body.start, body.end
            persist_kb()
            return {"ok": True, "band": b}
    # crear si no existe
    kb["bands"].append({
        "name": body.name, "start": body.start, "end": body.end,
        "mu_rms": 80.0, "sigma_rms": 15.0, "k": 3.0, "samples": 0
    })
    persist_kb()
    return {"ok": True, "bands": kb["bands"]}

@app.post("/setk")
def set_k(body: SetK, authorization: Optional[str] = Header(None)):
    ensure_auth(authorization)
    kmin, kmax = kb["k_bounds"]["min"], kb["k_bounds"]["max"]
    for b in kb["bands"]:
        if b["name"] == body.name:
            b["k"] = max(kmin, min(kmax, body.k))
            persist_kb()
            return {"ok": True, "band": b}
    raise HTTPException(404, "Band not found")

@app.post("/fp")
def mark_fp(authorization: Optional[str] = Header(None)):
    ensure_auth(authorization)
    b = band_now(kb)
    kb["perf"]["fp"] += 1
    kmax = kb["k_bounds"]["max"]
    b["k"] = min(kmax, b["k"] + 0.1)
    persist_kb()
    return {"ok": True, "band": b}

@app.post("/fn")
def mark_fn(authorization: Optional[str] = Header(None)):
    ensure_auth(authorization)
    b = band_now(kb)
    kb["perf"]["fn"] += 1
    kmin = kb["k_bounds"]["min"]
    b["k"] = max(kmin, b["k"] - 0.1)
    persist_kb()
    return {"ok": True, "band": b}
