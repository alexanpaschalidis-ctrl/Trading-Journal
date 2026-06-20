"""Trading Journal — Streamlit-App (mobile-first, Cloud-tauglich).

Startseite: 4 Location-Bubbles mit realisierter € PNL + Kalender-Ansicht.
Klick auf eine Bubble öffnet das Journal der Location mit Trade-Erfassung,
Bearbeiten/Löschen und KI-Mentor-Feedback.
"""

from __future__ import annotations

import calendar as calmod
from datetime import date

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

MONATSNAMEN = [
    "Januar", "Februar", "März", "April", "Mai", "Juni",
    "Juli", "August", "September", "Oktober", "November", "Dezember",
]


# --- Helfer -------------------------------------------------------------------

def goto(view: str) -> None:
    st.session_state["view"] = view
    st.rerun()


def _index(options: list, value, default: int = 0) -> int:
    try:
        return options.index(value)
    except (ValueError, TypeError):
        return default


def _parse_datum(s) -> date:
    try:
        return date.fromisoformat(s)
    except (ValueError, TypeError):
        return date.today()


# --- Home ---------------------------------------------------------------------

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
                if st.button("Öffnen", key=f"bubblebtn_{loc['slug']}", use_container_width=True):
                    goto(loc["slug"])

    st.markdown(
        f'<div class="app-sub" style="margin-top:14px">Gesamt realisiert: '
        f'<b style="color:{ui.pnl_color(gesamt)}">{format_eur(gesamt)}</b></div>',
        unsafe_allow_html=True,
    )

    if st.button("📅 Kalender-Ansicht"):
        goto("kalender")


# --- Kalender -----------------------------------------------------------------

def kalender_view() -> None:
    if st.button("← Zurück zur Übersicht"):
        goto("home")

    heute = date.today()
    jahr = st.session_state.setdefault("kal_jahr", heute.year)
    monat = st.session_state.setdefault("kal_monat", heute.month)

    c1, c2, c3 = st.columns([1, 3, 1])
    if c1.button("‹", key="kal_prev"):
        monat -= 1
        if monat < 1:
            monat, jahr = 12, jahr - 1
        st.session_state["kal_monat"], st.session_state["kal_jahr"] = monat, jahr
        st.rerun()
    c2.markdown(
        f'<div class="app-title" style="text-align:center;font-size:1.25rem;margin:0">'
        f'{MONATSNAMEN[monat - 1]} {jahr}</div>',
        unsafe_allow_html=True,
    )
    if c3.button("›", key="kal_next"):
        monat += 1
        if monat > 12:
            monat, jahr = 1, jahr + 1
        st.session_state["kal_monat"], st.session_state["kal_jahr"] = monat, jahr
        st.rerun()

    try:
        tage = db.pnl_pro_tag()
    except Exception as exc:
        st.error(f"Daten konnten nicht geladen werden: {exc}")
        tage = {}

    html = ['<div class="cal-grid">']
    for wd in ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]:
        html.append(f'<div class="cal-head">{wd}</div>')

    monats_pnl, monats_count = 0.0, 0
    for woche in calmod.Calendar(firstweekday=0).monthdayscalendar(jahr, monat):
        for tag in woche:
            if tag == 0:
                html.append('<div class="cal-cell cal-empty"></div>')
                continue
            ds = date(jahr, monat, tag).isoformat()
            heute_cls = " cal-today" if ds == heute.isoformat() else ""
            info = tage.get(ds)
            if info:
                pnl, cnt = info["pnl"], info["count"]
                monats_pnl += pnl
                monats_count += cnt
                farbe = ui.pnl_color(pnl)
                vz = "+" if pnl > 0 else ("−" if pnl < 0 else "")
                betrag = f'{vz}{abs(pnl):,.0f}'.replace(",", ".")
                html.append(
                    f'<div class="cal-cell{heute_cls}"><div class="cal-day">{tag}</div>'
                    f'<div class="cal-pnl" style="color:{farbe}">{betrag}€</div>'
                    f'<div class="cal-count">{cnt} Trade{"s" if cnt != 1 else ""}</div></div>'
                )
            else:
                html.append(
                    f'<div class="cal-cell{heute_cls}"><div class="cal-day">{tag}</div></div>'
                )
    html.append("</div>")
    st.markdown("".join(html), unsafe_allow_html=True)

    st.markdown(
        f'<div class="app-sub" style="margin-top:12px">Dieser Monat: '
        f'<b style="color:{ui.pnl_color(monats_pnl)}">{format_eur(monats_pnl)}</b> · '
        f'{monats_count} Trades</div>',
        unsafe_allow_html=True,
    )


# --- Trade-Formular (neu + bearbeiten) ---------------------------------------

def trade_formular(loc: dict, trade: dict | None = None) -> bool:
    """Rendert das Formular. Gibt True zurück, wenn erfolgreich gespeichert."""
    ist_edit = trade is not None
    form_key = f"form_edit_{trade['id']}" if ist_edit else f"form_new_{loc['slug']}"

    with st.form(form_key, clear_on_submit=not ist_edit):
        c1, c2 = st.columns(2)
        richtung = c1.radio("Richtung", RICHTUNGEN, horizontal=True,
                            index=_index(RICHTUNGEN, trade.get("richtung") if trade else None))
        bias = c2.radio("BIAS vorhanden?", BIAS_OPTIONEN, horizontal=True,
                        index=_index(BIAS_OPTIONEN, trade.get("bias") if trade else None))

        c3, c4, c5 = st.columns(3)
        instrument = c3.selectbox("Instrument", INSTRUMENTE,
                                  index=_index(INSTRUMENTE, trade.get("instrument") if trade else None))
        kontrakte = c4.number_input("Kontrakte", min_value=1, step=1,
                                    value=int(trade["kontrakte"]) if trade and trade.get("kontrakte") else 1)
        datum = c5.date_input("Datum", value=_parse_datum(trade.get("datum")) if trade else date.today())

        c6, c7, c8 = st.columns(3)
        entry = c6.number_input("Entry", step=0.25, format="%.2f",
                                value=float(trade["entry"]) if trade and trade.get("entry") is not None else 0.0)
        sl = c7.number_input("SL", step=0.25, format="%.2f",
                             value=float(trade["sl"]) if trade and trade.get("sl") is not None else 0.0)
        tp = c8.number_input("TP", step=0.25, format="%.2f",
                             value=float(trade["tp"]) if trade and trade.get("tp") is not None else 0.0)

        status = st.selectbox("Status / Ausgang", STATUS_OPTIONEN,
                              index=_index(STATUS_OPTIONEN, trade.get("status") if trade else None))
        exit_preis = st.number_input(
            "Exit-Preis (nur bei manuellem Exit)", step=0.25, format="%.2f",
            value=float(trade["exit_preis"]) if trade and trade.get("exit_preis") is not None else 0.0,
        )

        gruende_default = [g for g in (trade.get("einstiegsgruende") or []) if g in loc["gruende"]] if trade else []
        gruende = st.multiselect("Einstiegsgründe", loc["gruende"], default=gruende_default)
        notiz = st.text_area("Notiz (warum eingestiegen?)",
                             value=(trade.get("notiz") or "") if trade else "")
        bild = st.file_uploader(
            "TradingView-Screenshot" + (" (leer lassen = aktuellen behalten)" if ist_edit else ""),
            type=["png", "jpg", "jpeg"],
        )

        speichern = st.form_submit_button("Änderungen speichern" if ist_edit else "Trade speichern")

    if not speichern:
        return False

    screenshot_path = trade.get("screenshot_path") if trade else None
    if bild is not None:
        try:
            daten_bytes, ctype = db.komprimiere_bild(bild.getvalue())
            neu_path = db.upload_screenshot(daten_bytes, ctype)
            if ist_edit and screenshot_path:
                db.delete_screenshot(screenshot_path)
            screenshot_path = neu_path
        except Exception as exc:
            st.error(f"Screenshot konnte nicht gespeichert werden: {exc}")

    daten = {
        "location_slug": loc["slug"],
        "richtung": richtung,
        "instrument": instrument,
        "kontrakte": float(kontrakte),
        "entry": float(entry),
        "sl": float(sl),
        "tp": float(tp),
        "bias": bias,
        "status": status,
        "exit_preis": float(exit_preis) if status == STATUS_MANUELL else None,
        "einstiegsgruende": gruende,
        "notiz": notiz,
        "datum": datum.isoformat(),
        "screenshot_path": screenshot_path,
    }

    try:
        if ist_edit:
            daten["pnl_eur"] = berechne_pnl(daten)
            db.update_trade(trade["id"], daten)
            st.success("Änderungen gespeichert.")
        else:
            db.insert_trade(daten)
            st.success(f"Trade gespeichert · PNL {format_eur(berechne_pnl(daten))}")
    except Exception as exc:
        st.error(f"Speichern fehlgeschlagen: {exc}")
        return False
    return True


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
        f'<div class="trade-meta">{trade.get("datum", "")} · Entry {trade.get("entry")} · '
        f'SL {trade.get("sl")} · TP {trade.get("tp")} · {trade.get("status")} · '
        f'BIAS {trade.get("bias")}{f" · CRV {crv}" if crv is not None else ""}</div>'
        f'<div class="trade-reasons">{gruende}</div>'
        + (f'<div class="trade-meta">📝 {trade.get("notiz")}</div>' if trade.get("notiz") else "")
        + "</div>",
        unsafe_allow_html=True,
    )

    if trade.get("screenshot_path"):
        url = db.signed_url(trade["screenshot_path"])
        if url:
            st.image(url, use_container_width=True)

    a1, a2 = st.columns(2)
    if a1.button("✏️ Bearbeiten", key=f"edit_{trade['id']}"):
        st.session_state["edit_id"] = trade["id"]
        st.rerun()
    if a2.button("🗑️ Löschen", key=f"del_{trade['id']}"):
        st.session_state[f"confirm_{trade['id']}"] = True
        st.rerun()

    if st.session_state.get(f"confirm_{trade['id']}"):
        st.warning("Diesen Trade wirklich löschen?")
        b1, b2 = st.columns(2)
        if b1.button("Ja, löschen", key=f"yes_{trade['id']}"):
            db.delete_screenshot(trade.get("screenshot_path"))
            db.delete_trade(trade["id"])
            st.session_state.pop(f"confirm_{trade['id']}", None)
            st.rerun()
        if b2.button("Abbrechen", key=f"no_{trade['id']}"):
            st.session_state.pop(f"confirm_{trade['id']}", None)
            st.rerun()

    if trade.get("mentor_feedback"):
        with st.expander("🧠 Mentor-Feedback"):
            st.markdown(trade["mentor_feedback"])
            st.caption(f"Modell: {trade.get('mentor_model', '—')}")
    elif st.button("🧠 Mentor-Feedback holen", key=f"mentor_{trade['id']}"):
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

    edit_id = st.session_state.get("edit_id")
    ziel = next((t for t in trades if t["id"] == edit_id), None) if edit_id else None
    if ziel:
        st.markdown("#### ✏️ Trade bearbeiten")
        if trade_formular(loc, trade=ziel):
            st.session_state.pop("edit_id", None)
            st.rerun()
        if st.button("Bearbeiten abbrechen"):
            st.session_state.pop("edit_id", None)
            st.rerun()
        st.divider()
    else:
        if edit_id:
            st.session_state.pop("edit_id", None)
        with st.expander("➕ Neuer Trade", expanded=False):
            if trade_formular(loc):
                st.rerun()

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
    elif view == "kalender":
        kalender_view()
    else:
        location_view(view)


main()
