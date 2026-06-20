"""Datenmodell und PNL-Berechnung für Trades.

Ein Trade ist ein einfaches Dict (passend zur Supabase-Zeile). Die PNL ergibt
sich aus Richtung, Entry, Exit, Instrument-Punktwert und Kontraktanzahl.
"""

from __future__ import annotations

# Punktwert pro Index-Punkt in € (bzw. der Kontraktwährung). Erweiterbar.
PUNKTWERT = {
    "ES": 50.0,    # E-mini S&P 500
    "NQ": 20.0,    # E-mini Nasdaq 100
    "MES": 5.0,    # Micro E-mini S&P 500
    "MNQ": 2.0,    # Micro E-mini Nasdaq 100
    "YM": 5.0,     # E-mini Dow
    "FDAX": 25.0,  # DAX Future
    "FESX": 10.0,  # Euro Stoxx 50
}

INSTRUMENTE = list(PUNKTWERT.keys())

RICHTUNGEN = ["Long", "Short"]
BIAS_OPTIONEN = ["Ja", "Nein"]

STATUS_OFFEN = "offen"
STATUS_TP = "TP getroffen"
STATUS_SL = "SL getroffen"
STATUS_MANUELL = "manueller Exit"
STATUS_OPTIONEN = [STATUS_OFFEN, STATUS_TP, STATUS_SL, STATUS_MANUELL]


def effektiver_exit(trade: dict) -> float | None:
    """Exit-Preis abhängig vom Status. Bei TP/SL automatisch aus den Feldern."""
    status = trade.get("status")
    if status == STATUS_TP:
        return _num(trade.get("tp"))
    if status == STATUS_SL:
        return _num(trade.get("sl"))
    if status == STATUS_MANUELL:
        return _num(trade.get("exit_preis"))
    return None  # offen


def berechne_pnl(trade: dict) -> float | None:
    """PNL in € — None solange der Trade offen ist oder Daten fehlen."""
    exit_p = effektiver_exit(trade)
    entry = _num(trade.get("entry"))
    if exit_p is None or entry is None:
        return None
    instrument = trade.get("instrument")
    punktwert = PUNKTWERT.get(instrument)
    kontrakte = _num(trade.get("kontrakte"))
    if punktwert is None or kontrakte is None:
        return None
    richtung = 1 if trade.get("richtung") == "Long" else -1
    punkte = (exit_p - entry) * richtung
    return round(punkte * punktwert * kontrakte, 2)


def chance_risiko(trade: dict) -> float | None:
    """Geplantes CRV aus Entry/SL/TP (für die Anzeige), richtungsabhängig."""
    entry, sl, tp = _num(trade.get("entry")), _num(trade.get("sl")), _num(trade.get("tp"))
    if None in (entry, sl, tp):
        return None
    risiko = abs(entry - sl)
    chance = abs(tp - entry)
    if risiko == 0:
        return None
    return round(chance / risiko, 2)


def format_eur(betrag: float | None) -> str:
    if betrag is None:
        return "offen"
    vorzeichen = "+" if betrag > 0 else ("" if betrag == 0 else "−")
    return f"{vorzeichen}{abs(betrag):,.0f} €".replace(",", ".")


def _num(wert) -> float | None:
    if wert is None or wert == "":
        return None
    try:
        return float(wert)
    except (TypeError, ValueError):
        return None
