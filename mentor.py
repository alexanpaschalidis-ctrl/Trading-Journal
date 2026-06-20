"""KI-Trading-Mentor auf Basis der Kaan-Aslan/Traivend-Methodik.

Liest die zur Location gehörenden Wissensdateien, schickt sie zusammen mit den
Trade-Daten und dem TradingView-Screenshot (Vision) an Claude und gibt ein
ehrliches deutschsprachiges Feedback zurück.
"""

from __future__ import annotations

import base64

import streamlit as st

import db
from locations import get_location, wissensdateien
from trades import berechne_pnl, chance_risiko, format_eur

DEFAULT_MODEL = "claude-opus-4-8"
# Längenbudget pro Wissensdatei (Zeichen), damit der Prompt nicht ausufert.
MAX_ZEICHEN_PRO_DATEI = 6000

SYSTEM_PROMPT = """Du bist ein erfahrener Trading-Mentor, ausgebildet in der \
Methodik von Kaan Aslan / Traivend (Auktionsmarkttheorie, Volumenprofil, \
Location-Trading, Marktphasen). Du bewertest einen einzelnen Trade aus dem \
Journal eines Schülers ehrlich und konkret auf Deutsch.

Gehe so vor:
1. Urteil: War der Trade gut, solide oder schlecht? Begründe kurz.
2. Location & Setup: Passte der Einstieg zur gewählten Location und zu den \
   genannten Einstiegsgründen? Beziehe dich konkret auf die mitgelieferte \
   Wissensbasis (z.B. Volumenkanten wichtiger als POC, Bruch+Retest einer \
   Location, Fakeout-Filter, kein Respekt vor einer Location).
3. Screenshot: Was zeigt der Chart? Stimmen Entry, SL und TP mit der Struktur \
   überein? Benenne, was du im Bild siehst.
4. Risiko: Bewerte Chance-Risiko-Verhältnis und SL/TP-Platzierung.
5. Worauf achten: 2-4 konkrete, umsetzbare Hinweise für das nächste Mal.

Sei direkt und konstruktiv. Erfinde keine Kursdaten, die nicht erkennbar sind. \
Wenn Informationen fehlen, sag es. Antworte in klarem Markdown mit kurzen \
Überschriften."""


class MentorFehler(Exception):
    """Wird geworfen, wenn der Mentor nicht aufgerufen werden kann."""


def _lese_wissen(slug: str) -> str:
    namen = wissensdateien(slug)
    inhalte = db.lese_wissen(tuple(namen))
    teile: list[str] = []
    for rel in namen:
        text = inhalte.get(rel)
        if not text:
            continue
        if len(text) > MAX_ZEICHEN_PRO_DATEI:
            text = text[:MAX_ZEICHEN_PRO_DATEI] + "\n… (gekürzt)"
        teile.append(f"### Wissensquelle: {rel}\n{text}")
    return "\n\n".join(teile)


def _trade_steckbrief(trade: dict) -> str:
    loc = get_location(trade.get("location_slug")) or {}
    pnl = format_eur(berechne_pnl(trade))
    crv = chance_risiko(trade)
    gruende = ", ".join(trade.get("einstiegsgruende") or []) or "—"
    return (
        f"- Location: {loc.get('label', trade.get('location_slug'))}\n"
        f"- BIAS vorhanden: {trade.get('bias', '—')}\n"
        f"- Richtung: {trade.get('richtung', '—')}\n"
        f"- Instrument: {trade.get('instrument', '—')}, Kontrakte: {trade.get('kontrakte', '—')}\n"
        f"- Entry: {trade.get('entry', '—')} | SL: {trade.get('sl', '—')} | TP: {trade.get('tp', '—')}\n"
        f"- Status/Ausgang: {trade.get('status', '—')} (Exit: {trade.get('exit_preis', '—')})\n"
        f"- Realisierte PNL: {pnl}\n"
        f"- Geplantes CRV: {crv if crv is not None else '—'}\n"
        f"- Einstiegsgründe: {gruende}\n"
        f"- Notiz des Traders: {trade.get('notiz') or '—'}"
    )


def hole_feedback(trade: dict, screenshot_bytes: bytes | None) -> tuple[str, str]:
    """Ruft Claude auf und gibt (feedback_markdown, modell) zurück."""
    api_key = st.secrets.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise MentorFehler(
            "Kein ANTHROPIC_API_KEY in den Secrets hinterlegt. Bitte den Key "
            "eintragen, damit der Mentor Feedback geben kann."
        )

    try:
        from anthropic import Anthropic
    except ImportError as exc:  # pragma: no cover
        raise MentorFehler("Das Paket 'anthropic' ist nicht installiert.") from exc

    model = st.secrets.get("MENTOR_MODEL", DEFAULT_MODEL)
    client = Anthropic(api_key=api_key)

    wissen = _lese_wissen(trade.get("location_slug", ""))
    steckbrief = _trade_steckbrief(trade)

    content: list[dict] = []
    if screenshot_bytes:
        media_type = "image/png" if screenshot_bytes[:8].startswith(b"\x89PNG") else "image/jpeg"
        content.append(
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": media_type,
                    "data": base64.standard_b64encode(screenshot_bytes).decode("utf-8"),
                },
            }
        )

    content.append(
        {
            "type": "text",
            "text": (
                "Hier ist der Trade aus meinem Journal. Bitte gib mir dein "
                "Mentor-Feedback.\n\n"
                f"## Trade-Daten\n{steckbrief}\n\n"
                f"## Relevante Kaan-Aslan-Wissensbasis\n{wissen}"
            ),
        }
    )

    try:
        response = client.messages.create(
            model=model,
            max_tokens=2000,
            system=SYSTEM_PROMPT,
            thinking={"type": "adaptive"},
            messages=[{"role": "user", "content": content}],
        )
    except Exception as exc:  # anthropic-Fehler sauber an die UI durchreichen
        raise MentorFehler(f"Anthropic-API-Fehler: {exc}") from exc

    text = "".join(b.text for b in response.content if b.type == "text").strip()
    if not text:
        raise MentorFehler("Der Mentor hat keine Antwort geliefert. Bitte erneut versuchen.")
    return text, model
