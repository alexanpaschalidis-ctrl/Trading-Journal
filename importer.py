"""Trade-Import: aus Screenshot (Claude-Vision) oder CSV/Excel.

Liefert je Quelle eine Liste von Roh-Trades (dicts) mit den Feldern
``instrument, richtung, kontrakte, entry, exit, pnl_eur, datum`` — die der
User anschließend in der Vorschau korrigiert und einer Location zuordnet.
"""

from __future__ import annotations

import base64
import json
from datetime import date

import streamlit as st

from trades import PUNKTWERT

DEFAULT_MODEL = "claude-opus-4-8"

FELDER = ["instrument", "richtung", "kontrakte", "entry", "exit", "pnl_eur", "datum"]

# Synonyme für die Spalten-Erkennung beim CSV/Excel-Import (alles klein geschrieben)
SPALTEN_SYNONYME = {
    "instrument": ["instrument", "symbol", "contract", "markt", "produkt", "ticker"],
    "richtung": ["richtung", "side", "b/s", "buy/sell", "direction", "position", "l/s", "typ"],
    "kontrakte": ["kontrakte", "qty", "quantity", "menge", "size", "lots", "contracts", "anzahl"],
    "entry": ["entry", "entryprice", "einstieg", "open", "openprice", "avgentry", "price", "preis"],
    "exit": ["exit", "exitprice", "ausstieg", "close", "closeprice", "avgexit"],
    "pnl_eur": ["pnl", "p/l", "p&l", "profit", "gewinn", "realized", "realizedpnl",
                "netpnl", "pnleur", "ergebnis", "result"],
    "datum": ["datum", "date", "datetime", "time", "day", "tradedate", "closetime", "entrytime"],
}

_LONG = {"buy", "b", "long", "kauf", "l", "+"}
_SHORT = {"sell", "s", "short", "verkauf", "v", "-"}


class ImportFehler(Exception):
    pass


# --- Screenshot (Claude Vision) ----------------------------------------------

_SCHEMA = {
    "type": "object",
    "properties": {
        "trades": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "instrument": {"type": ["string", "null"]},
                    "richtung": {"type": ["string", "null"]},
                    "kontrakte": {"type": ["number", "null"]},
                    "entry": {"type": ["number", "null"]},
                    "exit": {"type": ["number", "null"]},
                    "pnl_eur": {"type": ["number", "null"]},
                    "datum": {"type": ["string", "null"]},
                },
                "required": FELDER,
                "additionalProperties": False,
            },
        }
    },
    "required": ["trades"],
    "additionalProperties": False,
}

_SYSTEM = (
    "Du liest Trading-Daten aus einem Screenshot einer Trade-/Positionsliste "
    "(z.B. aus Airtrade Pro / Rithmic). Gib für jede klar erkennbare Trade-Zeile "
    "ein Objekt zurück. Felder: instrument (Symbol wie ES, NQ, MNQ, MES), richtung "
    "('Long' für Buy/Kauf, 'Short' für Sell/Verkauf), kontrakte (Stückzahl), entry "
    "(Einstiegspreis), exit (Ausstiegspreis, sonst null), pnl_eur (realisierter "
    "Gewinn/Verlust als Zahl, sonst null), datum (YYYY-MM-DD, sonst null). "
    "Rate KEINE Werte — was du nicht sicher erkennst, lass null. Gib nur Zeilen "
    "zurück, die echte Trades sind (keine Summen-/Kopfzeilen)."
)


def extrahiere_aus_screenshot(image_bytes: bytes) -> list[dict]:
    api_key = st.secrets.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ImportFehler(
            "Kein ANTHROPIC_API_KEY in den Secrets — Screenshot-Import braucht "
            "die Claude-Bilderkennung."
        )
    try:
        from anthropic import Anthropic
    except ImportError as exc:  # pragma: no cover
        raise ImportFehler("Paket 'anthropic' ist nicht installiert.") from exc

    model = st.secrets.get("MENTOR_MODEL", DEFAULT_MODEL)
    client = Anthropic(api_key=api_key)
    media_type = "image/png" if image_bytes[:8].startswith(b"\x89PNG") else "image/jpeg"

    try:
        response = client.messages.create(
            model=model,
            max_tokens=3000,
            system=_SYSTEM,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": base64.standard_b64encode(image_bytes).decode("utf-8"),
                        },
                    },
                    {"type": "text", "text": "Lies alle Trades aus diesem Screenshot aus."},
                ],
            }],
            output_config={"format": {"type": "json_schema", "schema": _SCHEMA}},
        )
    except Exception as exc:
        raise ImportFehler(f"Anthropic-API-Fehler: {exc}") from exc

    text = "".join(b.text for b in response.content if b.type == "text").strip()
    try:
        roh = json.loads(text).get("trades", [])
    except (json.JSONDecodeError, AttributeError) as exc:
        raise ImportFehler("Antwort konnte nicht gelesen werden.") from exc
    return [_normalisiere(z) for z in roh]


# --- CSV / Excel --------------------------------------------------------------

def parse_tabelle(file_bytes: bytes, name: str):
    """Liest CSV oder Excel in ein DataFrame (pandas wird lazy importiert)."""
    import io

    import pandas as pd

    try:
        if name.lower().endswith((".xlsx", ".xls")):
            return pd.read_excel(io.BytesIO(file_bytes))
        return pd.read_csv(io.BytesIO(file_bytes), sep=None, engine="python")
    except Exception as exc:
        raise ImportFehler(f"Datei konnte nicht gelesen werden: {exc}") from exc


def mappe_spalten(df) -> list[dict]:
    """Ordnet die DataFrame-Spalten unseren Feldern zu und gibt Roh-Trades zurück."""
    import pandas as pd

    norm = {str(c).strip().lower().replace(" ", "").replace("_", ""): c for c in df.columns}
    zuordnung: dict[str, str] = {}
    for feld, synonyme in SPALTEN_SYNONYME.items():
        for syn in synonyme:
            key = syn.replace(" ", "").replace("_", "")
            if key in norm:
                zuordnung[feld] = norm[key]
                break

    rows: list[dict] = []
    for _, zeile in df.iterrows():
        roh = {}
        for feld in FELDER:
            spalte = zuordnung.get(feld)
            wert = zeile[spalte] if spalte is not None and spalte in zeile else None
            roh[feld] = None if (wert is None or pd.isna(wert)) else wert
        rows.append(_normalisiere(roh))
    return rows


# --- Normalisierung -----------------------------------------------------------

def _normalisiere(roh: dict) -> dict:
    return {
        "instrument": _instrument(roh.get("instrument")),
        "richtung": _richtung(roh.get("richtung")),
        "kontrakte": _zahl(roh.get("kontrakte")),
        "entry": _zahl(roh.get("entry")),
        "exit": _zahl(roh.get("exit")),
        "pnl_eur": _zahl(roh.get("pnl_eur")),
        "datum": _datum(roh.get("datum")),
    }


def _instrument(wert) -> str | None:
    if not wert:
        return None
    sym = str(wert).strip().upper()
    for key in sorted(PUNKTWERT, key=len, reverse=True):
        if sym.startswith(key):
            return key
    return sym  # unbekannt → Originalwert, User korrigiert in der Vorschau


def _richtung(wert) -> str | None:
    if wert is None:
        return None
    s = str(wert).strip().lower()
    # Short zuerst prüfen (sonst matcht "ver-kauf" auf "kauf")
    if s in _SHORT or "short" in s or "sell" in s or "verkauf" in s:
        return "Short"
    if s in _LONG or "long" in s or "buy" in s or "kauf" in s:
        return "Long"
    return None


def _zahl(wert) -> float | None:
    if wert is None or wert == "":
        return None
    try:
        s = str(wert).replace("€", "").replace("$", "").replace(" ", "").replace(",", ".")
        return float(s)
    except (TypeError, ValueError):
        return None


def _datum(wert) -> str | None:
    if not wert:
        return None
    # ISO (YYYY-MM-DD) zuerst — vermeidet pandas-Warnungen
    try:
        return date.fromisoformat(str(wert)[:10]).isoformat()
    except ValueError:
        pass
    try:
        import pandas as pd

        d = pd.to_datetime(wert, errors="coerce", dayfirst=True)
        return None if pd.isna(d) else d.date().isoformat()
    except Exception:
        return None
