"""Mobile-first UI-Bausteine: Theme-CSS, Passwort-Gate, Bubble-Karten."""

from __future__ import annotations

import streamlit as st

from trades import format_eur

GOLD = "#C9A961"
MINT = "#6FFFB0"
RED = "#E27B6E"
TEXT_MAIN = "#E8E0CC"
TEXT_MUTED = "#8FA89E"

CSS = """
<style>
/* Streamlit-Chrome verstecken für App-Gefühl */
#MainMenu, header, footer {visibility: hidden;}
.block-container {padding-top: 1.2rem; padding-bottom: 3rem; max-width: 640px;}

/* Große Touch-Buttons */
.stButton > button {
    width: 100%;
    border-radius: 14px;
    padding: 0.7rem 1rem;
    font-size: 1.02rem;
    font-weight: 600;
    border: 1px solid rgba(201,169,97,0.35);
    background: #0F2B23;
    color: #E8E0CC;
}
.stButton > button:hover {border-color: #C9A961; color: #C9A961;}

/* Bubble-Raster (2 Spalten, responsiv) */
.bubble-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 14px;
    margin: 8px 0 4px 0;
}
.bubble {
    border-radius: 22px;
    padding: 22px 16px;
    min-height: 132px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    background: radial-gradient(circle at 30% 20%, rgba(255,255,255,0.05), rgba(0,0,0,0.15));
    border: 2px solid var(--bubble-color, #C9A961);
    box-shadow: 0 6px 18px rgba(0,0,0,0.35);
}
.bubble-label {font-size: 0.98rem; font-weight: 700; color: #E8E0CC; line-height: 1.2;}
.bubble-pnl {font-size: 1.5rem; font-weight: 800;}
.bubble-sub {font-size: 0.72rem; color: #8FA89E; letter-spacing: 0.04em; text-transform: uppercase;}

/* Trade-Karten */
.trade-card {
    border-radius: 16px;
    padding: 14px 16px;
    margin-bottom: 10px;
    background: #0F2B23;
    border: 1px solid rgba(201,169,97,0.25);
    border-left: 5px solid var(--accent, #C9A961);
}
.trade-top {display:flex; justify-content:space-between; align-items:baseline; gap:8px;}
.trade-dir {font-weight:700; color:#E8E0CC;}
.trade-pnl {font-weight:800; font-size:1.1rem;}
.trade-meta {font-size:0.82rem; color:#8FA89E; margin-top:4px;}
.trade-reasons {font-size:0.82rem; color:#C9A961; margin-top:4px;}

.app-title {font-size:1.6rem; font-weight:800; color:#C9A961; margin-bottom:0.2rem;}
.app-sub {color:#8FA89E; font-size:0.86rem; margin-bottom:0.8rem;}
.mentor-box {
    border-radius:14px; padding:12px 16px; margin-top:8px;
    background: rgba(201,169,97,0.08); border:1px solid rgba(201,169,97,0.3);
}
</style>
"""


def inject_css() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def pnl_color(betrag: float | None) -> str:
    if betrag is None or betrag == 0:
        return GOLD
    return MINT if betrag > 0 else RED


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
        f'<div class="bubble" style="--bubble-color:{color}">'
        f'<div class="bubble-label">{label}</div>'
        f'<div><div class="bubble-pnl" style="color:{farbe}">{format_eur(pnl)}</div>'
        f'<div class="bubble-sub">realisiert</div></div></div>'
    )
