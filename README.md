# Trading Journal mit KI-Mentor (Kaan Aslan / Traivend)

Mobil-optimiertes Trading Journal (Streamlit). Startseite zeigt 4 Location-Bubbles
mit realisierter € PNL. Klick öffnet das Journal: Trades erfassen (BIAS, SL/TP/Entry
→ € PNL, Einstiegsgründe + Notiz, TradingView-Screenshot). Pro Trade gibt ein
KI-Mentor (Claude, mit Bildanalyse) Feedback auf Basis der Kaan-Aslan-Wissensbasis.

Läuft am Mac **und** am iPhone, von überall — gehostet auf Streamlit Community Cloud,
Trades + Screenshots dauerhaft in Supabase, geschützt durch ein App-Passwort.

---

## Locations
- **Konsolidierung**
- **Volumenbergkanten**
- **Tageshoch/Tagestief**
- **Sonstige Location**

Die Wissensdateien für den Mentor liegen **privat in einer Supabase-Tabelle**
(`knowledge`). Sie werden einmalig per `seed_knowledge.sql` eingespielt (die Datei
bleibt lokal und ist `.gitignore`d, kommt also nicht ins öffentliche Repo).

---

## Einrichtung (einmalig)

### 1. Supabase (Datenbank + Screenshots)
1. Auf [supabase.com](https://supabase.com) ein kostenloses Projekt anlegen.
2. Im **SQL-Editor** den Inhalt von `supabase_schema.sql` ausführen
   (legt Tabelle `trades` + Storage-Bucket `screenshots` an).
   Danach den Inhalt von `seed_knowledge.sql` ausführen (legt die private
   Tabelle `knowledge` an und füllt sie mit den Kaan-Aslan-Wissensdateien).
3. Unter **Project Settings → API** notieren:
   - **Project URL** → `SUPABASE_URL`
   - **service_role** Key (geheim!) → `SUPABASE_KEY`

### 2. Anthropic API-Key (für den Mentor)
- Key aus der Anthropic Console holen → `ANTHROPIC_API_KEY`.
- Optional anderes Modell: `MENTOR_MODEL` (Default `claude-opus-4-8`).

### 3. App-Passwort
- Ein beliebiges sicheres Passwort wählen → `APP_PASSWORD`.

### 4. GitHub + Streamlit Cloud (Hosting)
1. Diesen Ordner als GitHub-Repo pushen (`.streamlit/secrets.toml` wird durch
   `.gitignore` NICHT mitgepusht — gut so).
2. Auf [share.streamlit.io](https://share.streamlit.io) das Repo verbinden,
   Hauptdatei `app.py`.
3. Unter **App → Settings → Secrets** eintragen:
   ```toml
   APP_PASSWORD = "…"
   ANTHROPIC_API_KEY = "sk-ant-…"
   SUPABASE_URL = "https://….supabase.co"
   SUPABASE_KEY = "service_role-key"
   # MENTOR_MODEL = "claude-sonnet-4-6"   # optional
   ```
4. Deployen. Die App-URL am iPhone öffnen → über das Teilen-Menü
   „Zum Home-Bildschirm“ für App-Gefühl.

---

## Lokal entwickeln
```bash
pip install -r requirements.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml   # und ausfüllen
streamlit run app.py --server.port 8503
```
Öffnet `http://localhost:8503`. (Ports 8501/8502 nutzt das bestehende Dashboard.)

---

## PNL-Berechnung
`PNL = (Exit − Entry) × Richtung × Punktwert × Kontrakte`

- Exit ergibt sich aus dem Status: „TP getroffen“ → TP, „SL getroffen“ → SL,
  „manueller Exit“ → eingegebener Exit-Preis, „offen“ → keine PNL.
- Punktwerte je Instrument (€/Punkt) in `trades.py` (`ES=50`, `NQ=20`, `MES=5`,
  `MNQ=2`, `YM=5`, `FDAX=25`, `FESX=10`) — dort leicht erweiterbar.

---

## Dateien
| Datei | Zweck |
|---|---|
| `app.py` | Streamlit-Entry, Passwort-Gate, Routing, Formular, Trade-Liste |
| `ui.py` | Mobile-CSS, Bubbles, Karten, Passwort-Gate |
| `locations.py` | 4 Locations, Farben, Einstiegsgründe, Wissens-Mapping |
| `trades.py` | Datenmodell, PNL-Berechnung, Instrument-Punktwerte |
| `db.py` | Supabase: Trades CRUD, Screenshot-Upload/Signed-URL |
| `mentor.py` | Claude-API-Aufruf (Vision + Wissensbasis) |
| `supabase_schema.sql` | Tabelle `trades` + Bucket zum Einmal-Ausführen |
| `seed_knowledge.sql` | **privat/lokal:** legt Tabelle `knowledge` an + befüllt sie |
