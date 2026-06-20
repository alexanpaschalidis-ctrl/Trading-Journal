"""Supabase-Anbindung: Trades speichern/laden + Screenshots im Storage-Bucket.

Der Client nutzt den service_role-Key aus den Streamlit-Secrets (server-seitig).
Cloud-Streamlit hat keinen dauerhaften Dateispeicher — alles Persistente liegt
in Supabase.
"""

from __future__ import annotations

import uuid
from io import BytesIO

import streamlit as st

from trades import berechne_pnl

BUCKET = "screenshots"
TABLE = "trades"
KNOWLEDGE_TABLE = "knowledge"


@st.cache_resource(show_spinner=False)
def _client():
    from supabase import create_client

    url = st.secrets.get("SUPABASE_URL")
    key = st.secrets.get("SUPABASE_KEY")
    if not url or not key:
        raise RuntimeError(
            "Supabase ist nicht konfiguriert. Bitte SUPABASE_URL und "
            "SUPABASE_KEY in den Secrets hinterlegen."
        )
    return create_client(url, key)


# --- Trades -------------------------------------------------------------------

def list_trades(location_slug: str) -> list[dict]:
    res = (
        _client()
        .table(TABLE)
        .select("*")
        .eq("location_slug", location_slug)
        .order("created_at", desc=True)
        .execute()
    )
    return res.data or []


def insert_trade(trade: dict) -> dict:
    trade = dict(trade)
    trade["pnl_eur"] = berechne_pnl(trade)
    res = _client().table(TABLE).insert(trade).execute()
    return (res.data or [{}])[0]


def update_trade(trade_id: str, fields: dict) -> None:
    _client().table(TABLE).update(fields).eq("id", trade_id).execute()


def delete_trade(trade_id: str) -> None:
    _client().table(TABLE).delete().eq("id", trade_id).execute()


def pnl_pro_tag() -> dict[str, dict]:
    """Pro Tag: realisierte PNL-Summe + Anzahl Trades (für die Kalender-Ansicht)."""
    res = _client().table(TABLE).select("datum,pnl_eur").execute()
    tage: dict[str, dict] = {}
    for row in res.data or []:
        datum = row.get("datum")
        if not datum:
            continue
        eintrag = tage.setdefault(datum, {"pnl": 0.0, "count": 0})
        eintrag["count"] += 1
        if row.get("pnl_eur") is not None:
            eintrag["pnl"] += float(row["pnl_eur"])
    return tage


@st.cache_data(show_spinner=False, ttl=3600)
def lese_wissen(namen: tuple[str, ...]) -> dict[str, str]:
    """Lädt die Wissensdateien (Markdown/YAML) aus der privaten knowledge-Tabelle."""
    if not namen:
        return {}
    res = (
        _client()
        .table(KNOWLEDGE_TABLE)
        .select("name,content")
        .in_("name", list(namen))
        .execute()
    )
    return {row["name"]: row["content"] for row in (res.data or [])}


def pnl_pro_location() -> dict[str, float]:
    """Summe der realisierten PNL je Location (offene Trades zählen nicht)."""
    res = _client().table(TABLE).select("location_slug,pnl_eur,status").execute()
    summen: dict[str, float] = {}
    for row in res.data or []:
        if row.get("status") == "offen":
            continue
        pnl = row.get("pnl_eur")
        if pnl is None:
            continue
        slug = row["location_slug"]
        summen[slug] = summen.get(slug, 0.0) + float(pnl)
    return summen


# --- Screenshots --------------------------------------------------------------

def upload_screenshot(data: bytes, content_type: str = "image/png") -> str:
    """Lädt ein Bild in den Bucket und gibt den Pfad zurück."""
    ext = "png" if "png" in content_type else "jpg"
    path = f"{uuid.uuid4().hex}.{ext}"
    _client().storage.from_(BUCKET).upload(
        path, data, {"content-type": content_type, "upsert": "false"}
    )
    return path


def signed_url(path: str | None, expires_in: int = 3600) -> str | None:
    """Zeitlich begrenzte URL zum Anzeigen eines privaten Screenshots."""
    if not path:
        return None
    try:
        res = _client().storage.from_(BUCKET).create_signed_url(path, expires_in)
        return res.get("signedURL") or res.get("signed_url")
    except Exception:
        return None


def delete_screenshot(path: str | None) -> None:
    if not path:
        return
    try:
        _client().storage.from_(BUCKET).remove([path])
    except Exception:
        pass


def download_screenshot(path: str | None) -> bytes | None:
    """Lädt die Bytes eines Screenshots (für den Mentor / Vision)."""
    if not path:
        return None
    try:
        return _client().storage.from_(BUCKET).download(path)
    except Exception:
        return None


def komprimiere_bild(raw: bytes, max_breite: int = 1600) -> tuple[bytes, str]:
    """Verkleinert große Screenshots, gibt (bytes, content_type) zurück."""
    try:
        from PIL import Image
    except Exception:
        return raw, "image/png"
    try:
        img = Image.open(BytesIO(raw))
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        if img.width > max_breite:
            hoehe = int(img.height * max_breite / img.width)
            img = img.resize((max_breite, hoehe))
        out = BytesIO()
        img.save(out, format="JPEG", quality=85)
        return out.getvalue(), "image/jpeg"
    except Exception:
        return raw, "image/png"
