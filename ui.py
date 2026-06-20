"""Mobile-first UI-Bausteine im minimalistischen Apple-Stil (hell)."""

from __future__ import annotations

import streamlit as st

from trades import format_eur

# Apple-System-Palette
BLUE = "#007AFF"
GREEN = "#34C759"
RED = "#FF3B30"
GRAY = "#8E8E93"
TEXT_MAIN = "#1C1C1E"
TEXT_MUTED = "#8E8E93"
HAIRLINE = "rgba(60,60,67,0.12)"

CSS = """
<style>
/* SF-Systemschrift überall */
html, body, .stApp, button, input, textarea, select,
[class*="css"] {
    font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text",
        "Helvetica Neue", Arial, sans-serif !important;
    -webkit-font-smoothing: antialiased;
}

/* Streamlit-Chrome verstecken, ruhiger Hintergrund */
#MainMenu, header, footer {visibility: hidden;}
.stApp {background: #F2F2F7;}
.block-container {padding-top: 1.4rem; padding-bottom: 3rem; max-width: 600px;}

/* Titel */
.app-title {
    font-size: 1.7rem; font-weight: 700; color: #1C1C1E;
    letter-spacing: -0.02em; margin-bottom: 0.15rem;
}
.app-sub {color: #8E8E93; font-size: 0.9rem; margin-bottom: 0.9rem;}

/* Buttons — clean, abgerundet, blauer Text */
.stButton > button, .stFormSubmitButton > button {
    width: 100%; border-radius: 12px; padding: 0.55rem 1rem;
    font-size: 1rem; font-weight: 500;
    background: #FFFFFF; color: #007AFF;
    border: 1px solid rgba(60,60,67,0.12);
    box-shadow: 0 1px 2px rgba(0,0,0,0.04);
    transition: background 0.15s ease;
}
.stButton > button:hover {background: #F2F2F7; color: #007AFF; border-color: rgba(60,60,67,0.2);}
.stButton > button:active {background: #E5E5EA;}
/* Formular-Absenden = gefülltes Blau (primäre Aktion) */
.stFormSubmitButton > button {background: #007AFF; color: #FFFFFF; border: none; font-weight: 600;}
.stFormSubmitButton > button:hover {background: #0067D9; color: #FFFFFF;}

/* Bubbles (Location-Karten) */
.bubble {
    background: #FFFFFF; border: 1px solid rgba(60,60,67,0.1);
    border-radius: 16px; padding: 16px; min-height: 118px;
    display: flex; flex-direction: column; gap: 6px;
    box-shadow: 0 1px 2px rgba(0,0,0,0.04);
}
.bubble-top {display: flex; align-items: center; gap: 7px;}
.bubble-dot {width: 9px; height: 9px; border-radius: 50%; display: inline-block; flex: none;}
.bubble-label {font-size: 0.92rem; font-weight: 600; color: #1C1C1E; letter-spacing: -0.01em;}
.bubble-pnl {font-size: 1.5rem; font-weight: 700; margin-top: auto; letter-spacing: -0.02em;}
.bubble-sub {font-size: 0.72rem; color: #8E8E93;}

/* Trade-Karten */
.trade-card {
    background: #FFFFFF; border: 1px solid rgba(60,60,67,0.1);
    border-radius: 14px; padding: 14px 16px; margin-bottom: 10px;
    box-shadow: 0 1px 2px rgba(0,0,0,0.04);
}
.trade-top {display: flex; justify-content: space-between; align-items: baseline; gap: 8px;}
.trade-dir {font-weight: 600; color: #1C1C1E;}
.trade-pnl {font-weight: 700; font-size: 1.1rem; letter-spacing: -0.01em;}
.trade-meta {font-size: 0.8rem; color: #8E8E93; margin-top: 4px;}
.trade-reasons {font-size: 0.8rem; color: #007AFF; margin-top: 4px;}

/* Kalender */
.cal-grid {display: grid; grid-template-columns: repeat(7, 1fr); gap: 4px; margin-top: 8px;}
.cal-head {text-align: center; font-size: 0.7rem; color: #8E8E93; padding: 2px 0; font-weight: 600;}
.cal-cell {
    min-height: 58px; border-radius: 10px; padding: 4px 5px;
    background: #FFFFFF; border: 1px solid rgba(60,60,67,0.08);
    display: flex; flex-direction: column; overflow: hidden;
}
.cal-empty {background: transparent; border: none;}
.cal-today {border: 1.5px solid #007AFF;}
.cal-day {color: #8E8E93; font-size: 0.68rem;}
.cal-pnl {font-weight: 700; font-size: 0.8rem; margin-top: auto; line-height: 1.1; letter-spacing: -0.01em;}
.cal-count {color: #8E8E93; font-size: 0.6rem;}
</style>
"""


def inject_css() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def pnl_color(betrag: float | None) -> str:
    if betrag is None or betrag == 0:
        return GRAY
    return GREEN if betrag > 0 else RED


def passwort_gate() -> bool:
    """Zeigt das Passwortfeld; gibt True zurück, wenn freigeschaltet."""
    if st.session_state.get("authentifiziert"):
        return True

    erwartet = st.secrets.get("APP_PASSWORD")
    if not erwartet:
        st.error(
            "Kein APP_PASSWORD in den Secrets gesetzt. Bitte in "
            "`.streamlit/secrets.toml` bzw. in den Streamlit-Cloud-Secrets eintragen."
        )
        return False

    st.markdown('<div class="app-title">Trading Journal</div>', unsafe_allow_html=True)
    st.markdown('<div class="app-sub">Bitte Passwort eingeben</div>', unsafe_allow_html=True)
    pw = st.text_input("Passwort", type="password", label_visibility="collapsed")
    if st.button("Einloggen"):
        if pw == erwartet:
            st.session_state["authentifiziert"] = True
            st.rerun()
        else:
            st.error("Falsches Passwort.")
    return False


def bubble_html(label: str, pnl: float | None, color: str) -> str:
    farbe = pnl_color(pnl)
    return (
        f'<div class="bubble">'
        f'<div class="bubble-top"><span class="bubble-dot" style="background:{color}"></span>'
        f'<span class="bubble-label">{label}</span></div>'
        f'<div class="bubble-pnl" style="color:{farbe}">{format_eur(pnl)}</div>'
        f'<div class="bubble-sub">realisiert</div></div>'
    )
