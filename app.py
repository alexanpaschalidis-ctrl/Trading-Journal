"""Trading Journal — Streamlit-App (mobile-first, Cloud-tauglich).

Startseite: 4 Location-Bubbles mit realisierter € PNL. Klick öffnet das Journal
der Location mit Trade-Erfassung, Trade-Liste und KI-Mentor-Feedback.
"""

from __future__ import annotations

import streamlit as st

import db
import ui
from locations import LOCATIONS, get_location
from mentor import MentorFehler, hole_feedback
from trades import (
    BIAS_OPTIONEN,
    INSTRUMENTE,
    RICHTUNGEN,
    STATUS_MANUELL,
    STATUS_OPTIONEN,
    berechne_pnl,
    chance_risiko,
    format_eur,
)

st.set_page_config(page_title="Trading Journal", page_icon="📈", layout="centered")
ui.inject_css()


# --- Navigation ---------------------------------------------------------------

def goto(view: str) -> None:
    st.session_state["view"] = view
    st.rerun()


def home() -> None:
    st.markdown('<div class="app-title">Trading Journal</div>', unsafe_allow_html=True)
    st.markdown('<div class="app-sub">Wähle eine Location</div>', unsafe_allow_html=True)

    try:
        summen = db.pnl_pro_location()
    except Exception as exc:
        st.error(f"Verbindung zur Datenbank fehlgeschlagen: {exc}")
        summen = {}

    gesamt = sum(summen.values()) if summen else 0.0

    for reihe in range(0, len(LOCATIONS), 2):
        cols = st.columns(2)
        for col, loc in zip(cols, LOCATIONS[reihe:reihe + 2]):
            with col:
                pnl = summen.get(loc["slug"])
                st.markdown(ui.bubble_html(loc["label"], pnl, loc["color"]), unsafe_allow_html=True)
                if st.button("Öffnen", key=f"open_{loc['slug']}"):
                    goto(loc["slug"])

    st.markdown(
        f'<div class="app-sub" style="margin-top:14px">Gesamt realisiert: '
        f'<b style="color:{ui.pnl_color(gesamt)}">{format_eur(gesamt)}</b></div>',
        unsafe_allow_html=True,
    )


# --- Trade-Formular -----------------------------------------------------------

def neuer_trade_formular(loc: dict) -> None:
    with st.expander("➕ Neuer Trade", expanded=False):
        with st.form(f"form_{loc['slug']}", clear_on_submit=True):
            c1, c2 = st.columns(2)
            richtung = c1.radio("Richtung", RICHTUNGEN, horizontal=True)
            bias = c2.radio("BIAS vorhanden?", BIAS_OPTIONEN, horizontal=True)

            c3, c4 = st.columns(2)
            instrument = c3.selectbox("Instrument", INSTRUMENTE)
            kontrakte = c4.number_input("Kontrakte", min_value=1, value=1, step=1)

            c5, c6, c7 = st.columns(3)
            entry = c5.number_input("Entry", value=0.0, step=0.25, format="%.2f")
            sl = c6.number_input("SL", value=0.0, step=0.25, format="%.2f")
            tp = c7.number_input("TP", value=0.0, step=0.25, format="%.2f")

            status = st.selectbox("Status / Ausgang", STATUS_OPTIONEN)
            exit_preis = None
            if status == STATUS_MANUELL:
                exit_preis = st.number_input("Manueller Exit-Preis", value=0.0, step=0.25, format="%.2f")

            gruende = st.multiselect("Einstiegsgründe", loc["gruende"])
            notiz = st.text_area("Notiz (warum eingestiegen?)", placeholder="Eigene Gedanken zum Trade …")
            bild = st.file_uploader("TradingView-Screenshot", type=["png", "jpg", "jpeg"])

            speichern = st.form_submit_button("Trade speichern")

        if speichern:
            screenshot_path = None
            if bild is not None:
                try:
                    daten, ctype = db.komprimiere_bild(bild.getvalue())
                    screenshot_path = db.upload_screenshot(daten, ctype)
                except Exception as exc:
                    st.error(f"Screenshot konnte nicht gespeichert werden: {exc}")

            trade = {
                "location_slug": loc["slug"],
                "richtung": richtung,
                "instrument": instrument,
                "kontrakte": float(kontrakte),
                "entry": float(entry),
                "sl": float(sl),
                "tp": float(tp),
                "bias": bias,
                "status": status,
                "exit_preis": float(exit_preis) if exit_preis is not None else None,
                "einstiegsgruende": gruende,
                "notiz": notiz,
                "screenshot_path": screenshot_path,
            }
            try:
                db.insert_trade(trade)
                st.success(f"Trade gespeichert · PNL {format_eur(berechne_pnl(trade))}")
                st.rerun()
            except Exception as exc:
                st.error(f"Speichern fehlgeschlagen: {exc}")


# --- Trade-Liste --------------------------------------------------------------

def trade_karte(trade: dict) -> None:
    pnl = trade.get("pnl_eur")
    accent = ui.pnl_color(pnl)
    crv = chance_risiko(trade)
    gruende = ", ".join(trade.get("einstiegsgruende") or []) or "—"

    st.markdown(
        f'<div class="trade-card" style="--accent:{accent}">'
        f'<div class="trade-top"><span class="trade-dir">{trade.get("richtung")} '
        f'{trade.get("instrument")} ×{int(trade.get("kontrakte", 0))}</span>'
        f'<span class="trade-pnl" style="color:{accent}">{format_eur(pnl)}</span></div>'
        f'<div class="trade-meta">Entry {trade.get("entry")} · SL {trade.get("sl")} · '
        f'TP {trade.get("tp")} · {trade.get("status")} · BIAS {trade.get("bias")}'
        f'{f" · CRV {crv}" if crv is not None else ""}</div>'
        f'<div class="trade-reasons">{gruende}</div>'
        + (f'<div class="trade-meta">📝 {trade.get("notiz")}</div>' if trade.get("notiz") else "")
        + "</div>",
        unsafe_allow_html=True,
    )

    if trade.get("screenshot_path"):
        url = db.signed_url(trade["screenshot_path"])
        if url:
            st.image(url, use_container_width=True)

    if trade.get("mentor_feedback"):
        with st.expander("🧠 Mentor-Feedback"):
            st.markdown(trade["mentor_feedback"])
            st.caption(f"Modell: {trade.get('mentor_model', '—')}")
    else:
        if st.button("🧠 Mentor-Feedback holen", key=f"mentor_{trade['id']}"):
            mentor_aufruf(trade)


def mentor_aufruf(trade: dict) -> None:
    with st.spinner("Mentor analysiert den Trade …"):
        screenshot = db.download_screenshot(trade.get("screenshot_path"))
        try:
            feedback, modell = hole_feedback(trade, screenshot)
        except MentorFehler as exc:
            st.warning(str(exc))
            return
        try:
            db.update_trade(trade["id"], {"mentor_feedback": feedback, "mentor_model": modell})
        except Exception as exc:
            st.error(f"Feedback konnte nicht gespeichert werden: {exc}")
            return
    st.rerun()


def location_view(slug: str) -> None:
    loc = get_location(slug)
    if not loc:
        goto("home")
        return

    if st.button("← Zurück zur Übersicht"):
        goto("home")

    try:
        trades = db.list_trades(slug)
    except Exception as exc:
        st.error(f"Trades konnten nicht geladen werden: {exc}")
        trades = []

    realisiert = sum(t.get("pnl_eur") or 0 for t in trades if t.get("status") != "offen")
    st.markdown(
        f'<div class="app-title">{loc["label"]}</div>'
        f'<div class="app-sub">Realisiert: '
        f'<b style="color:{ui.pnl_color(realisiert)}">{format_eur(realisiert)}</b> · '
        f'{len(trades)} Trades</div>',
        unsafe_allow_html=True,
    )

    neuer_trade_formular(loc)

    if not trades:
        st.info("Noch keine Trades in dieser Location.")
    for trade in trades:
        trade_karte(trade)


# --- Einstieg -----------------------------------------------------------------

def main() -> None:
    if not ui.passwort_gate():
        return

    view = st.session_state.get("view", "home")
    if view == "home":
        home()
    else:
        location_view(view)


main()
