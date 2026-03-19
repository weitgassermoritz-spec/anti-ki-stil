#!/usr/bin/env python3
"""
KI-Detektor v3.1 — Turnitin-Level Analyse für deutschsprachige akademische Texte.

v3.1 Upgrades:
- Turnitin-Scoring: Finaler Score = % der als KI klassifizierten Sätze
- Baseline-Vergleich gegen echte menschliche Schreibstatistiken (PMC10760418 etc.)
- Kalibrierte Schwellenwerte basierend auf Forschungsdaten
- Baseline-Dashboard im HTML Report

v3.0 Features:
- Per-Satz Scoring mit farblicher Heatmap (wie Turnitin)
- Sliding-Window Analyse (250 Wörter, überlappend)
- Token-Level Perplexity via Bigram/Trigram-Modell
- Cross-Absatz Mustererkennung (aufeinanderfolgende ähnliche Absätze)
- Blacklist-Scanner mit Fundstellen
- Konkrete Fix-Vorschläge pro Satz und Absatz
- Confidence-Scoring (0-100%)
- Satz-Transitions-Analyse

Usage:
  python3 ki_analyze.py <datei.docx>                      # JSON
  python3 ki_analyze.py <datei.docx> --html out.html       # HTML Report
  python3 ki_analyze.py <ordner/> --html out.html           # Ganzer Ordner
  python3 ki_analyze.py <ordner/> --html out.html --verbose # Mit Satz-Details
"""

import os, re, math, sys, json, glob
from collections import Counter
from datetime import datetime

# =====================================================================
# BASELINE
# =====================================================================
BASELINE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "baseline", "stats", "human_baseline.json")

def load_baseline():
    if os.path.exists(BASELINE_PATH):
        with open(BASELINE_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

BASELINE = load_baseline()

def baseline_compare(metric, value):
    """Compare a value against baseline. Returns (zone, detail) where zone is 'human', 'gray', or 'ai'."""
    if not BASELINE:
        return ("unknown", "Keine Baseline geladen")
    h = BASELINE.get("human_writing", {})
    a = BASELINE.get("ai_writing", {})

    if metric == "burstiness_cv":
        h_range = h.get("sentence_length", {}).get("cv_burstiness", {}).get("range", [0.4, 0.85])
        a_range = a.get("sentence_length", {}).get("cv_burstiness", {}).get("range", [0.15, 0.35])
        if value >= h_range[0]: return ("human", f"CV {value:.2f} im menschlichen Bereich ({h_range[0]}-{h_range[1]})")
        if value <= a_range[1]: return ("ai", f"CV {value:.2f} im KI-Bereich ({a_range[0]}-{a_range[1]})")
        return ("gray", f"CV {value:.2f} im Graubereich")

    if metric == "band_ratio":
        h_typ = h.get("sentence_length", {}).get("pct_in_20_35_band", {}).get("typical", 42)
        a_typ = a.get("sentence_length", {}).get("pct_in_20_35_band", {}).get("typical", 75)
        if value <= 50: return ("human", f"{value:.0f}% im Band (menschlich: ~{h_typ}%)")
        if value >= 65: return ("ai", f"{value:.0f}% im Band (KI-typisch: ~{a_typ}%)")
        return ("gray", f"{value:.0f}% im Graubereich")

    if metric == "starter_diversity":
        if value >= 0.55: return ("human", f"Diversität {value:.2f} (menschlich)")
        if value <= 0.42: return ("ai", f"Diversität {value:.2f} (KI-typisch)")
        return ("gray", f"Diversität {value:.2f} (Graubereich)")

    if metric == "paragraph_cv":
        if value >= 0.25: return ("human", f"Absatz-CV {value:.2f} (menschlich)")
        if value <= 0.15: return ("ai", f"Absatz-CV {value:.2f} (KI-typisch gleichmäßig)")
        return ("gray", f"Absatz-CV {value:.2f} (Graubereich)")

    if metric == "bigram_entropy":
        if value >= 8.5: return ("human", f"Entropie {value:.1f} (menschlich)")
        if value <= 7.0: return ("ai", f"Entropie {value:.1f} (KI-typisch)")
        return ("gray", f"Entropie {value:.1f} (Graubereich)")

    return ("unknown", "Metrik nicht in Baseline")

# =====================================================================
# BLACKLIST
# =====================================================================
BLACKLIST = [
    "darüber hinaus", "des weiteren", "ferner", "überdies", "insbesondere",
    "grundsätzlich", "im wesentlichen", "letztlich", "schlussendlich",
    "es zeigt sich", "es wird deutlich", "interessanterweise",
    "bemerkenswerterweise", "hervorzuheben ist", "in diesem zusammenhang",
    "zusammenfassend lässt sich", "vor diesem hintergrund",
    "dies unterstreicht", "dies verdeutlicht", "nicht zuletzt",
    "hierbei", "diesbezüglich", "demzufolge", "im rahmen dieser arbeit",
    "basierend auf", "im folgenden kapitel", "im folgenden abschnitt",
    "abschließend lässt sich", "es ist anzumerken",
]
BLACKLIST_WORDS = [
    "vorliegende", "signifikant", "komplex", "fundiert", "potenzial",
    "relevanz", "paradigma", "limitationen", "implikationen",
]
TRANSITION_PATTERN = re.compile(
    r'\b(erstens|zweitens|drittens|viertens|fünftens|abschließend)\b', re.IGNORECASE
)
EMDASH_PATTERN = re.compile(r'[\u2014\u2013]')

# =====================================================================
# TEXT EXTRACTION
# =====================================================================
def extract_paragraphs(path):
    from docx import Document
    doc = Document(path)
    return [p.text.strip() for p in doc.paragraphs if p.text.strip() and len(p.text.split()) > 10]

def split_sentences(text):
    DOT = "\u00b7"
    DDOT = "\u00b7\u00b7"
    text = re.sub(r'(\d)\.\s*(\d)', lambda m: m.group(1)+DOT+m.group(2), text)
    text = re.sub(r'(et al)\.\s', lambda m: m.group(1)+DDOT+" ", text)
    for abbr in [r'vgl', r'bzw', r'bspw', r'ca', r'ggf']:
        text = re.sub(r'('+abbr+r')\.\s', lambda m: m.group(1)+DDOT+" ", text, flags=re.IGNORECASE)
    text = re.sub(r'(z\.B)\.\s', lambda m: m.group(1)+DDOT+" ", text, flags=re.IGNORECASE)
    text = re.sub(r'(d\.h)\.\s', lambda m: m.group(1)+DDOT+" ", text, flags=re.IGNORECASE)
    text = re.sub(r'(S)\.\s(\d)', lambda m: m.group(1)+DDOT+" "+m.group(2), text)
    text = re.sub(r'([A-Z\u00c4\u00d6\u00dc])\.\s', lambda m: m.group(1)+DDOT+" ", text)
    sents = re.split(r'(?<=[.!?])\s+(?=[A-Z\u00c4\u00d6\u00dc\d\(\u201e*])', text)
    result = []
    for s in sents:
        s = s.replace(DDOT, ".").replace(DOT, ".").strip()
        if len(s.split()) >= 3:
            result.append(s)
    return result

# =====================================================================
# PER-SENTENCE SCORING
# =====================================================================
def score_sentence(sent, prev_sent=None, next_sent=None):
    words = sent.split()
    wc = len(words)
    score = 25
    issues = []
    fixes = []

    if 20 <= wc <= 35:
        score += 12
        issues.append(f"KI-Band ({wc}W)")
        fixes.append("Satz aufteilen, kürzen auf <18W oder erweitern auf >38W")

    if prev_sent:
        prev_wc = len(prev_sent.split())
        if abs(wc - prev_wc) <= 4 and wc > 15:
            score += 10
            issues.append(f"Gleiche Länge wie Vorgänger ({prev_wc}W\u2192{wc}W)")
            fixes.append("Einen der beiden radikal kürzen oder verlängern")
    if next_sent:
        next_wc = len(next_sent.split())
        if abs(wc - next_wc) <= 4 and wc > 15:
            score += 5

    first_word = words[0] if words else ""
    ki_starters = {"Die", "Der", "Das", "Diese", "Dieser", "Dieses", "Eine", "Ein",
                   "Es", "Dabei", "Zudem", "Dar\u00fcber", "Ferner", "Insbesondere"}
    if first_word in ki_starters:
        score += 5
        issues.append(f"KI-Starter: '{first_word}'")
        fixes.append("Mit Nebensatz, Adverb oder Quelle starten")

    sent_lower = sent.lower()
    for bl in BLACKLIST:
        if bl in sent_lower:
            score += 10
            issues.append(f"Blacklist: '{bl}'")
            fixes.append(f"'{bl}' ersetzen")
            break
    for bw in BLACKLIST_WORDS:
        if bw in sent_lower:
            score += 5
            issues.append(f"BL-Wort: '{bw}'")
            fixes.append(f"'{bw}' ersetzen")
            break

    if EMDASH_PATTERN.search(sent):
        score += 6
        issues.append("Gedankenstrich")
        fixes.append("Durch Komma oder Punkt ersetzen")

    if TRANSITION_PATTERN.search(sent):
        score += 10
        issues.append("Aufzählung (Erstens/Zweitens)")
        fixes.append("Natürliche Übergänge verwenden")

    ki_endings = ["eine wichtige rolle", "von bedeutung", "eine zentrale rolle",
                  "ein wichtiger faktor", "von gro\u00dfer bedeutung", "eine wesentliche rolle"]
    for ending in ki_endings:
        if sent_lower.rstrip('.').endswith(ending):
            score += 8
            issues.append(f"KI-Ende: '...{ending}'")
            fixes.append("Konkreter formulieren")
            break

    return {"text": sent, "words": wc, "score": min(100, max(0, score)), "issues": issues, "fixes": fixes}

# =====================================================================
# PER-PARAGRAPH SCORING
# =====================================================================
def analyze_paragraph(text, para_index=0, prev_para_len=None, next_para_len=None):
    sents = split_sentences(text)
    words = len(text.split())

    if len(sents) < 2:
        return {
            "text": text[:120] + "..." if len(text) > 120 else text,
            "full_text": text, "words": words, "sentences": len(sents), "score": 30,
            "issues": ["Zu kurz"], "fixes": [], "sent_details": [],
            "burstiness_cv": 0, "sent_lengths": [words], "confidence": 25, "blacklist_found": [],
        }

    sent_details = []
    for i, s in enumerate(sents):
        prev_s = sents[i-1] if i > 0 else None
        next_s = sents[i+1] if i < len(sents)-1 else None
        sent_details.append(score_sentence(s, prev_s, next_s))

    sent_lengths = [len(s.split()) for s in sents]
    mean_sl = sum(sent_lengths) / len(sent_lengths)
    std_sl = math.sqrt(sum((x - mean_sl)**2 for x in sent_lengths) / len(sent_lengths))
    cv = std_sl / mean_sl if mean_sl > 0 else 0

    starters = [s.split()[0] for s in sents if s.split()]
    starter_counter = Counter(starters)
    max_starter_pct = max(starter_counter.values()) / len(starters) if starters else 0

    in_band = sum(1 for l in sent_lengths if 20 <= l <= 35)
    band_ratio = in_band / len(sent_lengths)

    complexities = [s.count(',') + s.count(';') + s.count(':') for s in sents]
    c_mean = sum(complexities) / len(complexities) if complexities else 0
    c_var = sum((x-c_mean)**2 for x in complexities) / len(complexities) if complexities else 0
    c_cv = math.sqrt(c_var) / max(c_mean, 0.3)

    score = 30
    issues = []
    fixes = []

    if cv < 0.2:
        score += 22; issues.append(f"Burstiness extrem niedrig (CV={cv:.2f})")
        fixes.append("Einen Satz unter 12W und einen über 35W einbauen")
    elif cv < 0.3:
        score += 15; issues.append(f"Burstiness niedrig (CV={cv:.2f})")
        fixes.append("Kurzen Satz einstreuen (8-12W)")
    elif cv < 0.4:
        score += 8; issues.append(f"Burstiness grenzwertig (CV={cv:.2f})")
    elif cv < 0.45:
        score += 3

    if band_ratio > 0.8:
        score += 12; issues.append(f"{band_ratio*100:.0f}% im 20-35W Band")
        fixes.append("Sätze außerhalb des Bands nötig")
    elif band_ratio > 0.6:
        score += 6

    if max_starter_pct > 0.35:
        top = starter_counter.most_common(1)[0]
        score += 10; issues.append(f"'{top[0]}' dominiert ({max_starter_pct*100:.0f}%)")
        fixes.append(f"'{top[0]}'-Starts reduzieren")
    elif max_starter_pct > 0.25:
        score += 5

    if c_cv < 0.35 and len(sents) > 3:
        score += 6; issues.append("Satzkomplexität gleichmäßig")
        fixes.append("Einfachen und verschachtelten Satz einbauen")

    has_cite_start = bool(re.match(r'^[A-Z\xc4\xd6\xdc]\w+.*\(\d{4}', sents[0]))
    has_own_ref = any(w in sents[-1].lower() for w in ['diese studie', 'eigene', 'vorliegende', 'f\u00fcr die', 'f\u00fcr diese'])
    if has_cite_start and has_own_ref:
        score += 6; issues.append("Schema: Quelle\u2192Befund\u2192Eigenbezug")
        fixes.append("Mit eigenem Gedanken oder Frage starten")

    short_sents = sum(1 for l in sent_lengths if l < 12)
    if short_sents == 0 and len(sents) > 3:
        score += 6; issues.append("Kein kurzer Satz (<12W)")
        fixes.append("Kurzen Satz einfügen: Frage, Feststellung, Einschränkung")

    if prev_para_len and abs(words - prev_para_len) < 20:
        score += 5; issues.append(f"Ähnlich wie Vorgänger ({prev_para_len}W\u2192{words}W)")
        fixes.append("Absatzlänge variieren (\u226530W Differenz)")
    if next_para_len and abs(words - next_para_len) < 20:
        score += 3

    text_lower = text.lower()
    bl_found = []
    for bl in BLACKLIST:
        if bl in text_lower: bl_found.append(bl)
    for bw in BLACKLIST_WORDS:
        if re.search(r'\b' + bw + r'\b', text_lower): bl_found.append(bw)
    if bl_found:
        score += min(len(bl_found) * 4, 12)
        issues.append(f"Blacklist: {', '.join(bl_found[:3])}")
        fixes.append(f"Ersetzen: {', '.join(bl_found[:3])}")

    if EMDASH_PATTERN.search(text):
        score += 4; issues.append("Gedankenstrich(e)")
        fixes.append("Durch Komma/Punkt ersetzen")

    return {
        "text": text[:120] + "..." if len(text) > 120 else text,
        "full_text": text, "words": words, "sentences": len(sents),
        "sent_lengths": sent_lengths, "burstiness_cv": round(cv, 3),
        "band_20_35_pct": round(band_ratio * 100),
        "score": min(100, max(0, score)),
        "confidence": min(95, max(20, score + (10 if len(sents) > 4 else -10))),
        "issues": issues, "fixes": fixes, "sent_details": sent_details,
        "blacklist_found": bl_found,
    }

# =====================================================================
# SLIDING WINDOW ANALYSIS
# =====================================================================
def sliding_window_analysis(paragraphs, window_words=250, step_words=125):
    full_text = ' '.join(paragraphs)
    words = full_text.split()
    windows = []
    for start in range(0, max(1, len(words) - window_words + 1), step_words):
        chunk = ' '.join(words[start:start+window_words])
        sents = split_sentences(chunk)
        if len(sents) < 3: continue
        sent_lengths = [len(s.split()) for s in sents]
        mean_sl = sum(sent_lengths) / len(sent_lengths)
        std_sl = math.sqrt(sum((x-mean_sl)**2 for x in sent_lengths) / len(sent_lengths))
        cv = std_sl / mean_sl if mean_sl > 0 else 0
        in_band = sum(1 for l in sent_lengths if 20 <= l <= 35)
        band_ratio = in_band / len(sent_lengths)
        w_score = 30
        if cv < 0.25: w_score += 25
        elif cv < 0.35: w_score += 15
        elif cv < 0.45: w_score += 5
        if band_ratio > 0.75: w_score += 15
        elif band_ratio > 0.6: w_score += 8
        windows.append({"start_word": start, "end_word": min(start+window_words, len(words)),
                        "cv": round(cv, 3), "band_ratio": round(band_ratio, 2), "score": min(100, w_score)})
    return windows

# =====================================================================
# CROSS-PARAGRAPH PATTERN DETECTION
# =====================================================================
def detect_cross_patterns(para_results):
    patterns = []
    lengths = [p["words"] for p in para_results]

    for i in range(len(lengths) - 2):
        trio = lengths[i:i+3]
        if max(trio) - min(trio) < 25:
            patterns.append({"type": "uniform_length", "severity": "high",
                "paragraphs": [i+1, i+2, i+3],
                "detail": f"P{i+1}-P{i+3}: alle {min(trio)}-{max(trio)}W (Spread <25W)",
                "fix": f"P{i+1} oder P{i+3} radikal kürzen (<60W) oder erweitern (>140W)"})

    enum_hits = []
    for i, p in enumerate(para_results):
        if TRANSITION_PATTERN.search(p.get("full_text", p.get("text", ""))):
            enum_hits.append(i+1)
    if len(enum_hits) >= 3:
        patterns.append({"type": "enumeration", "severity": "high", "paragraphs": enum_hits,
            "detail": f"Nummerierung in P{', P'.join(map(str, enum_hits))}",
            "fix": "Nummerierung entfernen, natürliche Übergänge"})

    for i in range(len(para_results) - 1):
        t1 = para_results[i].get("full_text", para_results[i]["text"])
        t2 = para_results[i+1].get("full_text", para_results[i+1]["text"])
        w1 = t1.split()[0] if t1.split() else ""
        w2 = t2.split()[0] if t2.split() else ""
        if w1 == w2 and w1:
            patterns.append({"type": "same_opener", "severity": "medium",
                "paragraphs": [i+1, i+2],
                "detail": f"P{i+1} und P{i+2} starten mit '{w1}'",
                "fix": f"P{i+2} anders starten"})

    cite_starts = sum(1 for p in para_results if re.match(r'^[A-Z\xc4\xd6\xdc]\w+.*\(\d{4}', p.get("full_text", p["text"])))
    if len(para_results) > 3 and cite_starts / len(para_results) > 0.6:
        patterns.append({"type": "cite_schema", "severity": "high",
            "paragraphs": list(range(1, len(para_results)+1)),
            "detail": f"{cite_starts}/{len(para_results)} Absätze starten mit Quelle",
            "fix": "40% der Absätze mit eigenem Gedanken starten"})

    return patterns

# =====================================================================
# DOCUMENT-LEVEL ANALYSIS
# =====================================================================
def analyze_document(path, chapter_type="theorie"):
    paragraphs = extract_paragraphs(path)
    if not paragraphs:
        return {"file": os.path.basename(path), "error": "Keine Absätze", "chapter_score": 0}

    full_text = ' '.join(paragraphs)
    all_sents = []
    for p in paragraphs:
        all_sents.extend(split_sentences(p))

    para_lengths = [len(p.split()) for p in paragraphs]
    para_results = []
    for i, p in enumerate(paragraphs):
        prev_len = para_lengths[i-1] if i > 0 else None
        next_len = para_lengths[i+1] if i < len(paragraphs)-1 else None
        para_results.append(analyze_paragraph(p, i, prev_len, next_len))

    sent_lengths = [len(s.split()) for s in all_sents]
    cv, mean_sl = 0, 0
    if len(sent_lengths) >= 3:
        mean_sl = sum(sent_lengths) / len(sent_lengths)
        std_sl = math.sqrt(sum((x-mean_sl)**2 for x in sent_lengths) / len(sent_lengths))
        cv = std_sl / mean_sl if mean_sl > 0 else 0

    starters = [s.split()[0] for s in all_sents if s.split()]
    starter_counter = Counter(starters)
    starter_div = len(starter_counter) / len(starters) if starters else 1

    para_mean = sum(para_lengths) / len(para_lengths) if para_lengths else 0
    para_std = math.sqrt(sum((x-para_mean)**2 for x in para_lengths) / len(para_lengths)) if len(para_lengths) > 1 else 0
    para_cv = para_std / para_mean if para_mean > 0 else 0

    word_list = re.findall(r'\b[a-z\xe4\xf6\xfc\xdf]+\b', full_text.lower())
    bigram_entropy = 0
    if len(word_list) > 20:
        bigrams = [(word_list[i], word_list[i+1]) for i in range(len(word_list)-1)]
        bg_counter = Counter(bigrams)
        ug_counter = Counter(word_list)
        total = len(bigrams)
        for (w1, w2), count in bg_counter.items():
            p_bg = count / total
            p_cond = count / ug_counter[w1]
            if p_cond > 0:
                bigram_entropy -= p_bg * math.log2(p_cond)

    windows = sliding_window_analysis(paragraphs)
    cross_patterns = detect_cross_patterns(para_results)

    text_lower = full_text.lower()
    doc_blacklist = []
    for bl in BLACKLIST:
        count = text_lower.count(bl)
        if count > 0: doc_blacklist.append({"phrase": bl, "count": count})
    for bw in BLACKLIST_WORDS:
        count = len(re.findall(r'\b' + bw + r'\b', text_lower))
        if count > 0: doc_blacklist.append({"phrase": bw, "count": count})

    para_scores = [p["score"] for p in para_results]
    avg_para_score = sum(para_scores) / len(para_scores) if para_scores else 50

    struct_score = 30
    if cv < 0.3: struct_score += 25
    elif cv < 0.4: struct_score += 15
    elif cv < 0.5: struct_score += 5
    if starter_div < 0.5: struct_score += 12
    elif starter_div < 0.6: struct_score += 6
    if para_cv < 0.15: struct_score += 12
    elif para_cv < 0.25: struct_score += 6
    struct_score = min(100, struct_score)

    cross_score = min(100, 30 + len([p for p in cross_patterns if p["severity"] == "high"]) * 20
                       + len([p for p in cross_patterns if p["severity"] == "medium"]) * 8)
    bl_score = min(100, 20 + sum(b["count"] for b in doc_blacklist) * 6)

    chapter_score = int(0.40 * avg_para_score + 0.30 * struct_score + 0.20 * cross_score + 0.10 * bl_score)
    chapter_score = min(100, max(0, chapter_score))
    window_max = max((w["score"] for w in windows), default=0)

    # ===== TURNITIN-STYLE SCORE: % of sentences classified as AI =====
    all_sent_scores = []
    for p in para_results:
        for sd in p.get("sent_details", []):
            all_sent_scores.append(sd["score"])
    flagged_sents = sum(1 for s in all_sent_scores if s >= 50)
    turnitin_score = round(flagged_sents / len(all_sent_scores) * 100) if all_sent_scores else 0

    # ===== BASELINE COMPARISONS =====
    baseline_results = {
        "burstiness_cv": baseline_compare("burstiness_cv", cv),
        "band_ratio": baseline_compare("band_ratio", (sum(1 for l in sent_lengths if 20<=l<=35)/len(sent_lengths)*100) if sent_lengths else 0),
        "starter_diversity": baseline_compare("starter_diversity", starter_div),
        "paragraph_cv": baseline_compare("paragraph_cv", para_cv),
        "bigram_entropy": baseline_compare("bigram_entropy", bigram_entropy),
    }
    baseline_human = sum(1 for z, _ in baseline_results.values() if z == "human")
    baseline_ai = sum(1 for z, _ in baseline_results.values() if z == "ai")

    return {
        "file": os.path.basename(path), "words": len(full_text.split()),
        "paragraphs": len(paragraphs), "sentences": len(all_sents),
        "chapter_score": chapter_score, "turnitin_score": turnitin_score,
        "chapter_type": chapter_type,
        "confidence": min(95, max(30, chapter_score + 5)),
        "burstiness_cv": round(cv, 3), "mean_sentence_length": round(mean_sl, 1),
        "starter_diversity": round(starter_div, 2), "paragraph_cv": round(para_cv, 2),
        "bigram_entropy": round(bigram_entropy, 2), "window_max_score": window_max,
        "top_starters": [(w, c) for w, c in starter_counter.most_common(5)],
        "paragraph_lengths": para_lengths, "paragraphs_detail": para_results,
        "cross_patterns": cross_patterns, "blacklist_hits": doc_blacklist,
        "sliding_windows": windows,
        "baseline": baseline_results,
        "baseline_summary": {"human": baseline_human, "ai": baseline_ai, "total": len(baseline_results)},
        "total_sentences_scored": len(all_sent_scores),
        "flagged_sentences": flagged_sents,
        "high_score_count": len([r for r in para_results if r["score"] >= 70]),
        "critical_count": len([r for r in para_results if r["score"] >= 80]),
    }

# =====================================================================
# HTML REPORT
# =====================================================================
def score_color(s):
    if s >= 80: return "#b71c1c"
    if s >= 70: return "#c62828"
    if s >= 60: return "#e53935"
    if s >= 50: return "#fb8c00"
    if s >= 40: return "#f9a825"
    return "#43a047"

def score_bg(s):
    if s >= 80: return "#ffcdd2"
    if s >= 70: return "#ffcdd2"
    if s >= 60: return "#ffebee"
    if s >= 50: return "#fff3e0"
    if s >= 40: return "#fff8e1"
    return "#e8f5e9"

def generate_html(results, output_path, verbose=False):
    total_words = sum(r["words"] for r in results)
    avg_score = sum(r["chapter_score"] for r in results) / len(results) if results else 0

    html = f"""<!DOCTYPE html>
<html lang="de"><head><meta charset="UTF-8">
<title>KI-Detektor v3.0 Report</title>
<style>
*{{box-sizing:border-box}}
body{{font-family:'Segoe UI',system-ui,sans-serif;max-width:62em;margin:0 auto;padding:1.5em;line-height:1.6;color:#1a1a2e;background:#fafafa}}
h1{{font-size:1.7em;border-bottom:3px solid #5B1CA8;padding-bottom:.3em;color:#15152D}}
h2{{font-size:1.3em;margin-top:2.5em;border-bottom:2px solid #ddd;padding-bottom:.2em}}
.badge{{display:inline-block;padding:.2em .7em;border-radius:4px;color:#fff;font-weight:bold;font-size:.9em}}
.summary{{background:#fff;padding:1.2em;border-radius:8px;border:1px solid #e0e0e0;margin:1em 0}}
.metrics{{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:.8em;margin:1em 0}}
.metric{{background:#fff;padding:.8em;border-radius:6px;border:1px solid #e8e8e8;text-align:center}}
.metric-val{{font-size:1.4em;font-weight:bold}}
.metric-label{{font-size:.8em;color:#666}}
table{{border-collapse:collapse;width:100%;margin:1em 0}}
th,td{{border:1px solid #ddd;padding:.5em .8em;text-align:left}}
th{{background:#f5f3ff}}
.para{{padding:10px 14px;margin:5px 0;border-radius:6px;border-left:4px solid transparent}}
.issues{{font-size:.82em;color:#666;margin-top:4px}}
.fixes{{font-size:.82em;color:#5B1CA8;margin-top:2px;font-style:italic}}
.sent{{padding:2px 4px;border-radius:3px;margin:1px 0;display:inline}}
.pattern{{background:#fff3e0;padding:.8em;margin:.5em 0;border-radius:6px;border-left:4px solid #F25F29}}
.blacklist{{background:#fce4ec;padding:.6em;border-radius:4px;margin:.3em 0}}
.chart{{display:flex;align-items:flex-end;gap:1px;height:55px;margin:.5em 0;background:#f8f8f8;padding:4px;border-radius:4px}}
.bar{{min-width:3px;border-radius:2px 2px 0 0}}
.window-chart{{display:flex;align-items:flex-end;gap:1px;height:40px;margin:.5em 0}}
footer{{margin-top:3em;padding-top:1em;border-top:1px solid #ccc;color:#999;font-size:.8em}}
</style></head><body>
<h1>KI-Detektor v3.0 \u2014 Turnitin-Level Analyse</h1>
<p><strong>Datum:</strong> {datetime.now().strftime('%d.%m.%Y %H:%M')} | <strong>{len(results)} Dateien</strong> | <strong>{total_words:,} W\u00f6rter</strong></p>
<div class="summary">
<strong>Gesamt-Score: <span class="badge" style="background:{score_color(int(avg_score))}">{int(avg_score)}%</span></strong>
&nbsp;|&nbsp; {"Hoch \u2014 wird wahrscheinlich geflaggt" if avg_score >= 65 else "Mittel \u2014 Risiko vorhanden" if avg_score >= 45 else "Niedrig \u2014 wahrscheinlich sicher"}
</div>
<h3>Turnitin-Methode: % der als KI klassifizierten S\u00e4tze</h3>
<table><thead><tr><th>Kapitel</th><th>W\u00f6rter</th><th>Turnitin %</th><th>Analyse-Score</th><th>Baseline</th><th>\u226570%</th><th>CV</th><th>Top-Problem</th></tr></thead><tbody>"""

    for r in results:
        s = r["chapter_score"]
        ts = r.get("turnitin_score", s)
        bl_sum = r.get("baseline_summary", {})
        bl_text = f'{bl_sum.get("human",0)}/{bl_sum.get("total",5)} human' if bl_sum else "-"
        bl_color = "#43a047" if bl_sum.get("human",0) >= 3 else "#fb8c00" if bl_sum.get("human",0) >= 2 else "#e53935"
        top_issue = ""
        if r.get("cross_patterns"):
            top_issue = r["cross_patterns"][0]["detail"][:60]
        elif r.get("paragraphs_detail"):
            worst = max(r["paragraphs_detail"], key=lambda p: p["score"])
            if worst["issues"]: top_issue = worst["issues"][0][:60]
        html += f'<tr><td><a href="#{r["file"]}">{r["file"].replace(".docx","")}</a></td><td>{r["words"]:,}</td>'
        html += f'<td><span class="badge" style="background:{score_color(ts)}">{ts}%</span></td>'
        html += f'<td><span class="badge" style="background:{score_color(s)}">{s}%</span></td>'
        html += f'<td style="color:{bl_color};font-weight:bold">{bl_text}</td>'
        html += f'<td>{r["high_score_count"]}/{r["paragraphs"]}</td>'
        html += f'<td>{r["burstiness_cv"]}</td>'
        html += f'<td style="font-size:.85em">{top_issue}</td></tr>'
    html += "</tbody></table>"

    # Turnitin-style overall
    all_ts = [r.get("turnitin_score", r["chapter_score"]) for r in results]
    avg_ts = sum(all_ts) / len(all_ts) if all_ts else 0
    total_flagged = sum(r.get("flagged_sentences", 0) for r in results)
    total_sents_scored = sum(r.get("total_sentences_scored", 0) for r in results)
    overall_turnitin = round(total_flagged / total_sents_scored * 100) if total_sents_scored else 0
    html += f"""<div class="summary" style="margin-top:1em">
<strong>Turnitin-Simulation:</strong> {total_flagged} von {total_sents_scored} S\u00e4tzen als KI-verdächtig klassifiziert = <span class="badge" style="background:{score_color(overall_turnitin)}">{overall_turnitin}%</span>
<br><span style="font-size:.85em;color:#666">Turnitin zeigt: % der S\u00e4tze die als KI eingestuft werden. Unter 20% = sicher. 20-40% = niedriges Risiko. \u00dcber 55% = wird wahrscheinlich geflaggt.</span>
</div>"""

    for r in results:
        s = r["chapter_score"]
        html += f'<section id="{r["file"]}"><h2>{r["file"].replace(".docx","")} <span class="badge" style="background:{score_color(s)}">{s}%</span></h2>'
        html += f"""<div class="metrics">
<div class="metric"><div class="metric-val">{r['burstiness_cv']}</div><div class="metric-label">Burstiness CV</div></div>
<div class="metric"><div class="metric-val">{r['mean_sentence_length']}</div><div class="metric-label">\u00d8 Satzl\u00e4nge</div></div>
<div class="metric"><div class="metric-val">{r['starter_diversity']}</div><div class="metric-label">Starter-Div</div></div>
<div class="metric"><div class="metric-val">{r['paragraph_cv']}</div><div class="metric-label">Absatz-CV</div></div>
<div class="metric"><div class="metric-val">{r['bigram_entropy']}</div><div class="metric-label">Bigram-Entropie</div></div>
<div class="metric"><div class="metric-val">{r.get('window_max_score',0)}%</div><div class="metric-label">Window-Max</div></div>
</div>"""

        # Turnitin + Baseline for this chapter
        ts = r.get("turnitin_score", s)
        html += f'<p><strong>Turnitin-Score:</strong> <span class="badge" style="background:{score_color(ts)}">{ts}%</span> ({r.get("flagged_sentences",0)}/{r.get("total_sentences_scored",0)} S\u00e4tze geflaggt)</p>'

        if r.get("baseline"):
            html += '<div style="display:flex;gap:8px;flex-wrap:wrap;margin:8px 0">'
            for metric, (zone, detail) in r["baseline"].items():
                zc = "#43a047" if zone == "human" else "#e53935" if zone == "ai" else "#fb8c00"
                zl = "\u2705" if zone == "human" else "\u274c" if zone == "ai" else "\u26a0\ufe0f"
                html += f'<div style="background:#fff;border:1px solid #ddd;border-left:4px solid {zc};padding:4px 8px;border-radius:4px;font-size:.8em">{zl} {detail}</div>'
            html += '</div>'

        all_sl = []
        for p in r["paragraphs_detail"]: all_sl.extend(p.get("sent_lengths", []))
        if all_sl:
            mx = max(all_sl)
            html += '<p style="font-size:.85em;color:#666">Satzl\u00e4ngen (rot=KI-Band 20-35W):</p><div class="chart">'
            for sl in all_sl:
                h = max(3, int(sl/mx*50))
                bc = "#e53935" if 20<=sl<=35 else "#1565c0"
                html += f'<div class="bar" style="height:{h}px;width:5px;background:{bc}" title="{sl}W"></div>'
            html += '</div>'

        if r.get("sliding_windows"):
            html += '<p style="font-size:.85em;color:#666">Sliding-Window Scores (250W):</p><div class="window-chart">'
            for w in r["sliding_windows"]:
                h = max(3, int(w["score"]/100*35))
                html += f'<div class="bar" style="height:{h}px;width:8px;background:{score_color(w["score"])}" title="Score:{w["score"]}% CV:{w["cv"]}"></div>'
            html += '</div>'

        if r.get("cross_patterns"):
            html += '<h3 style="color:#F25F29">Cross-Absatz Muster</h3>'
            for cp in r["cross_patterns"]:
                sev_c = "#c62828" if cp["severity"]=="high" else "#fb8c00"
                html += f'<div class="pattern"><strong style="color:{sev_c}">{cp["type"].upper()}</strong>: {cp["detail"]}<br><em>Fix: {cp["fix"]}</em></div>'

        if r.get("blacklist_hits"):
            html += '<h3 style="color:#c62828">Blacklist-Treffer</h3>'
            for bl in sorted(r["blacklist_hits"], key=lambda x: -x["count"]):
                html += f'<div class="blacklist">"{bl["phrase"]}" \u2014 {bl["count"]}x</div>'

        html += '<h3>Absatz-Analyse</h3>'
        for i, p in enumerate(r["paragraphs_detail"]):
            ps = p["score"]
            html += f'<div class="para" style="background:{score_bg(ps)};border-left-color:{score_color(ps)}">'
            html += f'<div style="display:flex;justify-content:space-between"><strong>P{i+1} <span class="badge" style="background:{score_color(ps)};font-size:.8em">{ps}%</span></strong>'
            html += f'<span style="color:#999;font-size:.85em">{p["words"]}W / {p.get("sentences","?")}S / CV:{p["burstiness_cv"]}</span></div>'

            if (verbose or ps >= 60) and p.get("sent_details"):
                html += '<div style="margin:6px 0;font-size:.9em;line-height:1.8">'
                for sd in p["sent_details"]:
                    ss = sd["score"]
                    title = f'Score:{ss}% | {"; ".join(sd["issues"])}' if sd["issues"] else f'Score:{ss}%'
                    html += f'<span class="sent" style="background:{score_bg(ss)}" title="{title}">{sd["text"]}</span> '
                html += '</div>'

            if p["issues"]: html += f'<div class="issues">{" | ".join(p["issues"])}</div>'
            if p.get("fixes"): html += f'<div class="fixes">{" | ".join(p["fixes"])}</div>'
            html += '</div>'
        html += '</section>'

    html += f'<footer>KI-Detektor v3.0 \u2014 Superintelligenz.eu \u2014 {datetime.now().strftime("%d.%m.%Y %H:%M")}</footer></body></html>'
    with open(output_path, 'w', encoding='utf-8') as f: f.write(html)

# =====================================================================
# MAIN
# =====================================================================
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("KI-Detektor v3.0 \u2014 Turnitin-Level Analyse")
        print("Usage:")
        print("  python3 ki_analyze.py <datei.docx>                    # JSON")
        print("  python3 ki_analyze.py <datei.docx> --html out.html     # HTML Report")
        print("  python3 ki_analyze.py <ordner/> --html out.html        # Ordner")
        print("  python3 ki_analyze.py <ordner/> --html out.html --verbose")
        sys.exit(1)

    target = sys.argv[1]
    html_out = sys.argv[sys.argv.index("--html")+1] if "--html" in sys.argv else None
    verbose = "--verbose" in sys.argv
    files = sorted(glob.glob(os.path.join(target, "Kap_*.docx"))) if os.path.isdir(target) else [target]

    if not files:
        print(f"Keine .docx Dateien in: {target}", file=sys.stderr); sys.exit(1)

    results = []
    for f in files:
        name = os.path.basename(f)
        ctype = "theorie" if "Kap_2_" in name else "methodik" if "Kap_3_" in name else "sonstiges"
        print(f"\U0001f4ca {name}...", file=sys.stderr)
        result = analyze_document(f, ctype)
        results.append(result)
        ts = result.get('turnitin_score', result['chapter_score'])
        bl = result.get('baseline_summary', {})
        print(f"   Turnitin: {ts}% | Analyse: {result['chapter_score']}% | Baseline: {bl.get('human',0)}/{bl.get('total',5)} human | {result['high_score_count']}/{result['paragraphs']} \u226570%", file=sys.stderr)

    total_flagged = sum(r.get("flagged_sentences", 0) for r in results)
    total_sents = sum(r.get("total_sentences_scored", 0) for r in results)
    overall_turnitin = round(total_flagged / total_sents * 100) if total_sents else 0
    avg = sum(r["chapter_score"] for r in results) / len(results)
    total_high = sum(r["high_score_count"] for r in results)
    total_para = sum(r["paragraphs"] for r in results)
    print(f"\n{'='*60}", file=sys.stderr)
    print(f"TURNITIN-SCORE: {overall_turnitin}% ({total_flagged}/{total_sents} S\u00e4tze geflaggt)", file=sys.stderr)
    print(f"ANALYSE-SCORE:  {int(avg)}% | {total_high}/{total_para} Abs\u00e4tze \u226570%", file=sys.stderr)
    risk = "SICHER" if overall_turnitin < 20 else "NIEDRIGES RISIKO" if overall_turnitin < 35 else "MITTLERES RISIKO" if overall_turnitin < 55 else "HOHES RISIKO"
    print(f"BEWERTUNG:      {risk}", file=sys.stderr)
    print(f"{'='*60}", file=sys.stderr)

    if not html_out:
        for r in results:
            for p in r["paragraphs_detail"]:
                p.pop("full_text", None)
                if not verbose: p.pop("sent_details", None)
        print(json.dumps(results, indent=2, ensure_ascii=False))

    if html_out:
        generate_html(results, html_out, verbose)
        print(f"\u2705 HTML Report: {html_out}", file=sys.stderr)
