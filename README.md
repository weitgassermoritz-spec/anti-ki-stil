# KI-Detektor v3.1

Turnitin-Level Analyse für deutschsprachige akademische Texte.

## Features

- **Turnitin-Score** — % der als KI klassifizierten Sätze (wie echtes Turnitin)
- **Per-Satz Highlighting** — Jeder Satz einzeln bewertet und farblich markiert
- **Baseline-Vergleich** — Gegen publizierte Forschungsdaten
- **Cross-Absatz Erkennung** — Gleiche Längen, Nummerierungen, Schema-Wiederholung
- **Blacklist-Scanner** — KI-typische Phrasen finden
- **Konkrete Fix-Vorschläge** — Pro Satz und Absatz

## Schnellstart

### Web-App (empfohlen)
```bash
pip install -r requirements.txt
streamlit run app.py
```

### Terminal
```bash
python3 scripts/ki_analyze.py meine-arbeit.docx --html report.html
```

## Basierend auf

- [PMC10760418](https://pmc.ncbi.nlm.nih.gov/articles/PMC10760418/) — Burstiness in academic abstracts
- [GPTZero](https://gptzero.me/news/perplexity-and-burstiness-what-is-it/) — Perplexity & Burstiness
- [Turnitin AI Detection Model](https://guides.turnitin.com/hc/en-us/articles/28294949544717-AI-writing-detection-model)
