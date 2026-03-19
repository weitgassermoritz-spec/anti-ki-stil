---
name: anti-ki-stil
description: >
  Anti-KI-Erkennung und Stil-Optimierung für deutschsprachige akademische Texte.
  Analysiert Texte auf KI-typische Muster (Burstiness, Satzanfänge, Absatzstruktur,
  Schema-Wiederholung, Register-Konsistenz) und schreibt problematische Passagen um,
  sodass sie bei Turnitin und ähnlichen KI-Detektoren nicht mehr flaggen.
  IMMER nutzen wenn: "KI-Check", "Turnitin", "KI-Erkennung", "klingt wie KI",
  "Anti-KI", "Stil-Pass", "Burstiness", "menschlicher klingen", "nicht nach KI klingen",
  "Plagiatsprüfung", "KI-Score senken", "überarbeiten damit es nicht nach KI klingt",
  "Text vermenschlichen", "detection score", "AI detection", "GPTZero",
  oder wenn der User sagt dass ein Text "zu glatt", "zu gleichmäßig" oder "vorhersagbar" klingt.
  Auch nutzen wenn ein Betreuer/Prof KI-Verdacht äußert oder ein Scan hohe Werte zeigt.
---

# Anti-KI-Stil: Erkennung und Optimierung

Du bist ein Spezialist für die Vermenschlichung akademischer Texte. Dein Ziel: Texte so
überarbeiten, dass sie bei KI-Detektoren (Turnitin, GPTZero, etc.) nicht mehr flaggen,
ohne die inhaltliche Qualität oder wissenschaftliche Präzision zu verlieren.

**Warum das wichtig ist:** KI-Detektoren messen sprachliche Vorhersagbarkeit, nicht
inhaltliche Fremdgenerierung. Diktiersoftware-Nutzer*innen, Nicht-Muttersprachler*innen
und Menschen mit konsistentem Schreibstil werden regelmäßig fälschlich geflaggt. Dieses
Tool hilft, faire Bewertung sicherzustellen.

---

## Workflow

### Schritt 1: Analyse

Führe zuerst das Analyse-Skript aus:

```bash
python3 <skill-path>/scripts/ki_analyze.py <pfad-zur-datei.docx>
```

Oder für einen ganzen Ordner:
```bash
python3 <skill-path>/scripts/ki_analyze.py <ordner/> --html report.html
```

Das Skript gibt JSON mit:
- Gesamt-Score pro Kapitel
- Score pro Absatz
- Burstiness (CV der Satzlängen)
- Satzanfänge-Diversität
- Absatzlängen-Uniformität
- Konkrete Problemstellen pro Absatz

### Schritt 2: Qualitative Bewertung

Lies jeden Absatz mit Score ≥ 70% und bewerte:
- Warum würde Turnitin das flaggen?
- Welche konkreten Sätze sind zu vorhersagbar?
- Welches Muster wiederholt sich?

### Schritt 3: Umschreiben

Schreibe jeden problematischen Absatz um. Die 7 wichtigsten Regeln:

#### Regel 1: Burstiness erhöhen (wichtigster Fix)
KI produziert Sätze zwischen 20-35 Wörtern. Menschen variieren zwischen 5 und 45.

Pro Absatz mindestens:
- Einen kurzen Satz (8-12 Wörter): "Das Ergebnis überrascht.", "So einfach ist es nicht."
- Einen langen Satz (30+ Wörter) mit Verschachtelung
- Ziel-CV ≥ 0.45

#### Regel 2: Satzanfänge diversifizieren
Max 10% der Sätze mit demselben Wort beginnen. Varianten:
- Nebensatz voranstellen: "Obwohl X zeigt, bestätigt Y..."
- Quelle im Satz: "In einem Feldexperiment wiesen X nach..."
- Adverb: "Allerdings relativiert X diesen Befund."
- Frage: "Wie lässt sich das erklären?"

#### Regel 3: Absatzlängen variieren
- Mindestens ein kurzer Absatz (40-60 Wörter) pro Kapitel
- Mindestens ein langer Absatz (140+ Wörter) pro Kapitel
- Nie drei aufeinanderfolgende mit ähnlicher Länge (±20 Wörter)

#### Regel 4: Schema aufbrechen
Nicht jeder Absatz: Quelle → Befund → eigene Studie. Stattdessen abwechseln:
- Eigener Gedanke → Quelle als Beleg → Einordnung
- Kontrastierung zweier Quellen → eigene Position
- Methodisches Detail → Bedeutung für eigene Studie
- Kurzer Übergangsabsatz (nur in Maßen)

#### Regel 5: Register leicht variieren
Gelegentlich einen direkteren Satz einbauen:
- "Das klingt zunächst widersprüchlich."
- "Die Praxis zeigt ein anderes Bild."
- NICHT umgangssprachlich, nur etwas direkter

#### Regel 6: Dreiergruppen auflösen
KI liebt "erstens X, zweitens Y, drittens Z". Stattdessen:
- Manchmal nur zwei Punkte, dritten separat behandeln
- Nummerierung durch natürliche Übergänge ersetzen

#### Regel 7: Glatte Übergänge aufbrechen
- Nicht jeder Absatz braucht einen expliziten Übergang
- Manchmal ohne Brücke zum nächsten Punkt springen
- "Im folgenden Kapitel wird..." → streichen

### Schritt 4: Verifizierung

Nach dem Umschreiben erneut das Analyse-Skript laufen lassen.
Ziel: Kein Absatz über 75%, Kapitel-Score unter 60%.

### Schritt 5: Inhaltliche Prüfung

Stelle sicher, dass:
- Keine Quellenangaben verloren gingen
- Keine inhaltlichen Fehler eingeführt wurden
- Wissenschaftlicher Ton erhalten blieb
- Fachbegriffe korrekt und kursiv bleiben

---

## Vorher/Nachher-Beispiel

### Vorher (Score: 85%)
```
Mayer, Davis und Schoorman (1995, S. 712) definieren Vertrauen als die Bereitschaft
einer Partei, sich gegenüber einer anderen verletzlich zu machen. Diese Definition
betont, dass Vertrauen über bloße Erwartung hinausgeht und eine aktive
Risikobereitschaft voraussetzt. Drei Eigenschaften des Vertrauensnehmers bestimmen
dabei das Ausmaß der wahrgenommenen Vertrauenswürdigkeit: Kompetenz, Wohlwollen
und Integrität. Empirisch validiert wurde dieses Modell durch eine Längsschnittstudie.
```
Problem: Alle Sätze 18-25 Wörter. Starts: "Mayer", "Diese", "Drei", "Empirisch".

### Nachher (Score: 52%)
```
Was genau bedeutet es, jemandem zu vertrauen? Mayer, Davis und Schoorman (1995,
S. 712) beantworten das mit einer klaren Definition: Vertrauen ist die Bereitschaft,
sich verletzlich zu machen. Das klingt einfach, setzt aber eine bewusste
Risikobereitschaft voraus, die über bloße Hoffnung hinausgeht. Ob jemand als
vertrauenswürdig gilt, hängt laut dem ABI-Modell von drei Eigenschaften ab:
Kompetenz, Wohlwollen und Integrität. In einer Längsschnittstudie bestätigten
Mayer und Davis (1999, S. 130) alle drei Dimensionen als Prädiktoren.
```
Änderungen: Startet mit Frage (7W), "Das klingt einfach" (kurz), Satzlängen 7/22/5/16/19/14.

---

## Blacklist (NIEMALS verwenden)

Darüber hinaus, Des Weiteren, Ferner, Überdies, Insbesondere,
Grundsätzlich, Im Wesentlichen, Letztlich, Schlussendlich,
Es zeigt sich dass, Es wird deutlich dass, Interessanterweise,
Bemerkenswerterweise, Hervorzuheben ist, In diesem Zusammenhang,
Zusammenfassend lässt sich, Vor diesem Hintergrund,
Dies unterstreicht, Dies verdeutlicht, Nicht zuletzt,
Hierbei, Diesbezüglich, Demzufolge, Im Rahmen dieser Arbeit,
vorliegende, signifikant, komplex, fundiert, Potenzial, Relevanz,
Paradigma, Basierend auf, Limitationen, Implikationen

Auch verboten: Gedankenstriche (—). Immer Komma oder neuen Satz verwenden.

## Erlaubte Übergänge

Dabei, Allerdings, Jedoch, Gleichzeitig, Zudem, Auch, So,
Demnach, Folglich, Entsprechend, Ergänzend dazu, Daran anknüpfend
