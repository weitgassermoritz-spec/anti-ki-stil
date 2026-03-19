# KI-Detektor v3.1 — Installation

## Option 1: Web-App (für dich und deine Freunde)

### Lokal starten
```bash
cd anti-ki-stil
pip install -r requirements.txt
streamlit run app.py
```
Öffnet sich im Browser unter `http://localhost:8501`. Einfach .docx hochladen.

### Für Freunde im Netzwerk freigeben
```bash
streamlit run app.py --server.address 0.0.0.0 --server.port 8501
```
Deine Freunde öffnen dann `http://DEINE-IP:8501` im Browser.

### Gratis im Internet hosten (Streamlit Cloud)
1. Erstelle ein GitHub Repo mit dem `anti-ki-stil` Ordner
2. Geh zu [share.streamlit.io](https://share.streamlit.io)
3. Verbinde dein GitHub Repo
4. Wähle `app.py` als Main File
5. Deploy — fertig, deine Freunde bekommen einen Link

## Option 2: Terminal / CLI
```bash
# Einzelne Datei
python3 scripts/ki_analyze.py meine-datei.docx

# Ganzer Ordner mit HTML-Report
python3 scripts/ki_analyze.py BA_Quellen/ --html report.html

# Mit Satz-Details
python3 scripts/ki_analyze.py BA_Quellen/ --html report.html --verbose
```

## Option 3: Claude Code Skill
```bash
cp -r anti-ki-stil ~/.claude/skills/
```
Dann in Claude Code: "Mach einen KI-Check auf mein Kapitel"

## Voraussetzungen
- Python 3.8+
- `pip install -r requirements.txt`
