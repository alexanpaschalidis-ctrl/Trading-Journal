"""Die 4 übergeordneten Trading-Locations.

Jede Location hat eine Farbe, die zugeordneten Einstiegsgründe (Checkliste)
und die Kaan-Aslan-Wissensdateien, die der Mentor heranzieht. Die Wissensdateien
liegen als Kopie im lokalen ``knowledge/``-Ordner, damit sie auch in der Cloud
gelesen werden können (kein Zugriff auf das Mac-Dateisystem).
"""

from __future__ import annotations

from pathlib import Path

KNOWLEDGE_ROOT = Path(__file__).parent / "knowledge"

# Farben (aus dem bestehenden Dashboard-Theme)
GOLD = "#C9A961"
MINT = "#6FFFB0"
RED = "#E27B6E"
TEXT_MUTED = "#8FA89E"

# Dateien, die bei JEDEM Trade als Kontext mitgegeben werden.
KERN_WISSEN = [
    "bias_charakteristik/bc06_bruch_und_retest_einer_location.md",
    "bias_charakteristik/bc30_fakeouts.md",
    "bias_charakteristik/bc15_kein_respekt_vor_einer_location.md",
    "gewichtung_faktoren.md",
]

LOCATIONS = [
    {
        "slug": "konsolidierung",
        "label": "Konsolidierung",
        "color": "#C9A961",
        "wissen": [
            "konsolidierung.md",
            "bias_charakteristik/bc28_intraday-konsolidierungen.md",
            "bias_charakteristik/bc04_80-20-regel_range-durchhandeln.md",
            "output/consolidation_01_extracted.yaml",
        ],
        "gruende": [
            "Bruch + Retest der Range",
            "Range-Extrem (80/20-Regel)",
            "Fake-Out abgewartet",
            "Reversal nach One-Way-Auktion",
            "Hohe Volatilität / ATR erhöht",
            "Beidseitige Fakes erkannt",
        ],
    },
    {
        "slug": "volumenkanten",
        "label": "Volumenbergkanten",
        "color": "#6FB8FF",
        "wissen": [
            "volumen.md",
            "output/volume_mountain_edge_01_definition.yaml",
        ],
        "gruende": [
            "Reaktion an oberer Volumenkante",
            "Reaktion an unterer Volumenkante",
            "POC als Magnet",
            "LVN-Durchlauf (schnelle Bewegung)",
            "Akzeptanz/Ablehnung an VAH",
            "Akzeptanz/Ablehnung an VAL",
            "Ausbruch mit steigendem Volumen",
        ],
    },
    {
        "slug": "tageshoch_tief",
        "label": "Tageshoch/Tagestief",
        "color": "#B98FFF",
        "wissen": [
            "hochs_tiefs.md",
            "boden_decken.md",
            "bias_charakteristik/bc09_abnutzung_eines_strukturpunkts_location.md",
        ],
        "gruende": [
            "Bruch Tageshoch",
            "Bruch Tagestief",
            "Retest Tageshoch",
            "Retest Tagestief",
            "Liquidity Grab / Manipulation",
            "Abnutzung des Strukturpunkts",
        ],
    },
    {
        "slug": "sonstige",
        "label": "Sonstige Location",
        "color": "#8FA89E",
        "wissen": [
            "marktphasen.md",
            "gewichtung_faktoren.md",
        ],
        "gruende": [
            "Trendfortsetzung",
            "Gegen-Trend / Reversal",
            "Marktphasenwechsel",
            "Session-Eröffnung",
            "Sonstiges (siehe Notiz)",
        ],
    },
]

LOCATIONS_BY_SLUG = {loc["slug"]: loc for loc in LOCATIONS}


def get_location(slug: str) -> dict | None:
    return LOCATIONS_BY_SLUG.get(slug)


def wissensdateien(slug: str) -> list[str]:
    """Relative Pfade aller Wissensdateien für eine Location (inkl. Kernwissen)."""
    loc = LOCATIONS_BY_SLUG.get(slug, {})
    seen: list[str] = []
    for rel in list(loc.get("wissen", [])) + KERN_WISSEN:
        if rel not in seen:
            seen.append(rel)
    return seen
