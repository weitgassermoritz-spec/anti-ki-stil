"""
KI-Detektor v3.1 — Web-App (Streamlit)
Turnitin-Level Analyse für akademische Texte.

Starten: streamlit run app.py
"""

import streamlit as st
import tempfile, os, json, time
from scripts.ki_analyze import analyze_document, score_color, score_bg, BASELINE

st.set_page_config(
    page_title="KI-Detektor",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ===== CLEAN, MODERN CSS =====
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

.stApp { font-family: 'Inter', sans-serif; }
[data-testid="stSidebar"] { display: none; }

h1 { color: #0f172a !important; font-weight: 700 !important; letter-spacing: -0.02em !important; }
h2 { color: #1e293b !important; font-weight: 600 !important; }
h3 { color: #334155 !important; font-weight: 600 !important; }

.hero {
    background: linear-gradient(135deg, #0f172a 0%, #1e3a5f 50%, #312e81 100%);
    padding: 28px 32px;
    border-radius: 16px;
    margin: 8px 0 20px 0;
}
.hero-score { color: white; font-size: 3.2em; font-weight: 700; line-height: 1; }
.hero-label { color: #94a3b8; font-size: 0.85em; font-weight: 500; letter-spacing: 0.05em; text-transform: uppercase; }
.hero-sub { color: #64748b; font-size: 0.9em; margin-top: 4px; }

.risk-badge {
    display: inline-block; padding: 6px 16px; border-radius: 20px;
    font-weight: 600; font-size: 0.95em; letter-spacing: 0.02em;
}

.score-badge {
    display: inline-block; padding: 3px 10px; border-radius: 5px;
    color: white; font-weight: 600; font-size: 0.85em;
}

.fix-card {
    background: #fefce8; border: 1px solid #fde68a; border-radius: 10px;
    padding: 12px 16px; margin: 6px 0;
}
.fix-card-high {
    background: #fef2f2; border: 1px solid #fecaca; border-radius: 10px;
    padding: 12px 16px; margin: 6px 0;
}

.para-block {
    padding: 10px 14px; margin: 4px 0; border-radius: 8px;
    border-left: 4px solid transparent; transition: all 0.2s;
}
.para-block:hover { box-shadow: 0 2px 8px rgba(0,0,0,0.08); }

.sent-hl { padding: 2px 4px; border-radius: 3px; transition: all 0.15s; }
.sent-hl:hover { opacity: 0.8; }

.baseline-chip {
    display: inline-block; padding: 3px 10px; border-radius: 12px;
    font-size: 0.78em; font-weight: 500; margin: 2px 4px 2px 0;
    border: 1px solid;
}

.metric-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 8px; margin: 8px 0; }
.metric-box {
    background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 10px;
    padding: 10px; text-align: center;
}
.metric-num { font-size: 1.5em; font-weight: 700; color: #0f172a; }
.metric-lbl { font-size: 0.75em; color: #64748b; font-weight: 500; }

.info-box {
    background: #f0f9ff; border: 1px solid #bae6fd; border-radius: 10px;
    padding: 16px; margin: 10px 0;
}
.info-box h4 { color: #0369a1; margin: 0 0 8px 0; }

.pattern-alert {
    background: #fff7ed; border-left: 4px solid #f97316; border-radius: 0 8px 8px 0;
    padding: 10px 14px; margin: 6px 0;
}

.blacklist-hit {
    background: #fef2f2; border-left: 4px solid #ef4444;
    padding: 6px 12px; border-radius: 0 6px 6px 0; margin: 3px 0;
    font-size: 0.88em;
}

footer { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# ===== HEADER =====
st.markdown("# 🔬 KI-Detektor")
st.markdown("Turnitin-Level Analyse fur akademische Texte — Per-Satz Scoring, Baseline-Vergleich, konkrete Fix-Vorschlage")
st.markdown("---")

# ===== FILE UPLOAD =====
uploaded_files = st.file_uploader(
    "**.docx Dateien hochladen**",
    type=["docx"],
    accept_multiple_files=True,
    help="Lade deine Kapitel als .docx hoch. Jeder Satz wird einzeln bewertet."
)

if not uploaded_files:
    # ===== LANDING PAGE =====
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        <div class="info-box">
        <h4>🎯 So funktioniert's</h4>
        <ol style="margin:0;padding-left:20px;font-size:0.9em">
        <li><strong>Hochladen</strong> — .docx Dateien per Drag & Drop</li>
        <li><strong>Analyse</strong> — Jeder Satz wird einzeln bewertet</li>
        <li><strong>Turnitin-Score</strong> — % der geflaggten Satze</li>
        <li><strong>Fixes</strong> — Konkrete Anweisungen was zu andern ist</li>
        </ol>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("""
        <div class="info-box">
        <h4>📊 Schwellenwerte</h4>
        <table style="width:100%;font-size:0.88em">
        <tr><td>🟢 Unter 20%</td><td><strong>Sicher</strong></td></tr>
        <tr><td>🟡 20 — 35%</td><td>Niedriges Risiko</td></tr>
        <tr><td>🟠 35 — 55%</td><td>Mittleres Risiko</td></tr>
        <tr><td>🔴 Uber 55%</td><td>Hohes Risiko</td></tr>
        </table>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("")
    with st.expander("📖 Welche Metriken werden gemessen?"):
        st.markdown("""
| Metrik | Was sie misst | Menschlich | KI-typisch |
|--------|--------------|------------|------------|
| **Burstiness (CV)** | Variation der Satzlangen | ≥ 0.45 | ≤ 0.30 |
| **Band-Ratio** | % Satze im 20-35W Fenster | 30-50% | 60-90% |
| **Starter-Diversitat** | Wie verschieden Satze beginnen | ≥ 0.55 | ≤ 0.42 |
| **Absatz-CV** | Variation der Absatzlangen | ≥ 0.25 | ≤ 0.15 |
| **Bigram-Entropie** | Vorhersagbarkeit der Wortwahl | ≥ 8.5 | ≤ 7.0 |

*Basierend auf publizierten Forschungsdaten (PMC10760418, GPTZero, Turnitin Whitepaper)*
        """)

    with st.expander("🔒 Datenschutz"):
        st.markdown("""
- Deine Dateien werden **nur lokal verarbeitet**
- **Nichts** wird gespeichert oder an Server gesendet
- Die Analyse lauft komplett auf diesem Rechner
        """)

else:
    # ===== ANALYSIS =====
    results = []
    status = st.empty()
    progress = st.progress(0)

    for i, uploaded_file in enumerate(uploaded_files):
        status.markdown(f"⏳ Analysiere **{uploaded_file.name}**...")
        progress.progress((i + 1) / len(uploaded_files))

        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp:
            tmp.write(uploaded_file.read())
            tmp_path = tmp.name

        name = uploaded_file.name
        ctype = "theorie" if any(x in name.lower() for x in ["kap_2", "kap2", "theorie", "literatur"]) else \
                "methodik" if any(x in name.lower() for x in ["kap_3", "kap3", "method", "design"]) else "sonstiges"

        result = analyze_document(tmp_path, ctype)
        result["file"] = uploaded_file.name
        results.append(result)
        os.unlink(tmp_path)

    status.empty()
    progress.empty()

    # ===== TURNITIN SCORE =====
    total_flagged = sum(r.get("flagged_sentences", 0) for r in results)
    total_sents = sum(r.get("total_sentences_scored", 0) for r in results)
    overall_turnitin = round(total_flagged / total_sents * 100) if total_sents else 0

    if overall_turnitin < 20:
        risk_text, risk_color, risk_bg = "Sicher", "#16a34a", "#dcfce7"
    elif overall_turnitin < 35:
        risk_text, risk_color, risk_bg = "Niedriges Risiko", "#ca8a04", "#fef9c3"
    elif overall_turnitin < 55:
        risk_text, risk_color, risk_bg = "Mittleres Risiko", "#ea580c", "#fff7ed"
    else:
        risk_text, risk_color, risk_bg = "Hohes Risiko", "#dc2626", "#fef2f2"

    st.markdown(f"""
    <div class="hero">
        <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:16px">
            <div>
                <div class="hero-label">Turnitin-Score</div>
                <div class="hero-score">{overall_turnitin}%</div>
                <div class="hero-sub">{total_flagged} von {total_sents} Satzen als KI-verdachtig eingestuft</div>
            </div>
            <div style="text-align:right">
                <div class="risk-badge" style="background:{risk_bg};color:{risk_color}">{risk_text}</div>
                <div class="hero-sub" style="margin-top:8px">Unter 20% = sicher bei Turnitin</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ===== CHAPTER OVERVIEW TABLE =====
    st.markdown("### 📋 Kapitel-Ubersicht")

    table_html = '<table style="width:100%;border-collapse:collapse;font-size:0.9em"><thead><tr style="background:#f1f5f9">'
    table_html += '<th style="padding:8px;text-align:left">Kapitel</th>'
    table_html += '<th style="padding:8px;text-align:center">Worter</th>'
    table_html += '<th style="padding:8px;text-align:center">Turnitin</th>'
    table_html += '<th style="padding:8px;text-align:center">Baseline</th>'
    table_html += '<th style="padding:8px;text-align:center">Probleme</th>'
    table_html += '</tr></thead><tbody>'

    for r in results:
        ts = r.get("turnitin_score", r["chapter_score"])
        bl = r.get("baseline_summary", {})
        bh = bl.get("human", 0)
        bt = bl.get("total", 5)
        bl_color = "#16a34a" if bh >= 4 else "#ca8a04" if bh >= 3 else "#ea580c" if bh >= 2 else "#dc2626"
        table_html += f'<tr style="border-bottom:1px solid #e2e8f0">'
        table_html += f'<td style="padding:8px"><strong>{r["file"].replace(".docx","")}</strong></td>'
        table_html += f'<td style="padding:8px;text-align:center">{r["words"]:,}</td>'
        table_html += f'<td style="padding:8px;text-align:center"><span class="score-badge" style="background:{score_color(ts)}">{ts}%</span></td>'
        table_html += f'<td style="padding:8px;text-align:center;color:{bl_color};font-weight:600">{bh}/{bt}</td>'
        table_html += f'<td style="padding:8px;text-align:center">{r["high_score_count"]} Absatze</td>'
        table_html += '</tr>'

    table_html += '</tbody></table>'
    st.markdown(table_html, unsafe_allow_html=True)

    # ===== PRIORITY FIXES =====
    st.markdown("### 🎯 Prioritats-Fixes")
    st.caption("Die wichtigsten Anderungen, sortiert nach Impact")

    all_fixes = []
    for r in results:
        for i, p in enumerate(r.get("paragraphs_detail", [])):
            if p["score"] >= 55 and p.get("fixes"):
                all_fixes.append({
                    "file": r["file"].replace(".docx", ""),
                    "para": i + 1, "score": p["score"],
                    "fix": p["fixes"][0],
                    "issue": p["issues"][0] if p["issues"] else "",
                    "type": "paragraph",
                })
        # Cross-patterns: max 2 per chapter, with real severity scores
        cp_count = 0
        for cp in r.get("cross_patterns", []):
            if cp_count >= 2:
                break
            cp_score = 75 if cp["severity"] == "high" else 60
            all_fixes.append({
                "file": r["file"].replace(".docx", ""),
                "para": cp["paragraphs"][0], "score": cp_score,
                "fix": cp["fix"], "issue": cp["detail"],
                "type": "pattern",
            })
            cp_count += 1

    all_fixes.sort(key=lambda x: -x["score"])

    if all_fixes:
        for fix in all_fixes[:12]:
            sc = fix["score"]
            card_class = "fix-card-high" if sc >= 70 else "fix-card"
            st.markdown(f"""
            <div class="{card_class}">
                <div style="display:flex;justify-content:space-between;align-items:center">
                    <div>
                        <strong>{fix['file']}</strong> &middot; Absatz {fix['para']}
                        <span class="score-badge" style="background:{score_color(sc)};margin-left:8px">{sc}%</span>
                    </div>
                </div>
                <div style="font-size:0.88em;color:#64748b;margin-top:4px">{fix['issue']}</div>
                <div style="font-size:0.88em;color:#4338ca;margin-top:2px">→ {fix['fix']}</div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.success("Keine kritischen Fixes notig! Dein Text sieht gut aus. 🎉")

    st.markdown("---")

    # ===== PER-CHAPTER DETAILS =====
    st.markdown("### 📊 Detail-Analyse pro Kapitel")

    for r in results:
        ts = r.get("turnitin_score", r["chapter_score"])
        flagged = r.get("flagged_sentences", 0)
        total_s = r.get("total_sentences_scored", 0)

        with st.expander(
            f"**{r['file'].replace('.docx','')}** — {ts}% Turnitin ({flagged}/{total_s} Satze)",
            expanded=(ts >= 15)
        ):
            # Metrics
            st.markdown(f"""
            <div class="metric-grid">
                <div class="metric-box"><div class="metric-num" style="color:{score_color(ts)}">{ts}%</div><div class="metric-lbl">Turnitin</div></div>
                <div class="metric-box"><div class="metric-num">{r['burstiness_cv']}</div><div class="metric-lbl">Burstiness</div></div>
                <div class="metric-box"><div class="metric-num">{r['mean_sentence_length']}</div><div class="metric-lbl">Ø Satzlange</div></div>
                <div class="metric-box"><div class="metric-num">{r['starter_diversity']}</div><div class="metric-lbl">Starter-Div</div></div>
                <div class="metric-box"><div class="metric-num">{r['paragraph_cv']}</div><div class="metric-lbl">Absatz-CV</div></div>
                <div class="metric-box"><div class="metric-num">{r['bigram_entropy']}</div><div class="metric-lbl">Entropie</div></div>
            </div>
            """, unsafe_allow_html=True)

            # Baseline
            if r.get("baseline"):
                bl_html = '<div style="margin:8px 0">'
                for metric, (zone, detail) in r["baseline"].items():
                    if zone == "human":
                        bl_html += f'<span class="baseline-chip" style="border-color:#16a34a;color:#16a34a;background:#f0fdf4">✓ {detail}</span>'
                    elif zone == "ai":
                        bl_html += f'<span class="baseline-chip" style="border-color:#dc2626;color:#dc2626;background:#fef2f2">✗ {detail}</span>'
                    else:
                        bl_html += f'<span class="baseline-chip" style="border-color:#ca8a04;color:#ca8a04;background:#fefce8">? {detail}</span>'
                bl_html += '</div>'
                st.markdown(bl_html, unsafe_allow_html=True)

            # Cross patterns
            if r.get("cross_patterns"):
                for cp in r["cross_patterns"]:
                    st.markdown(f"""
                    <div class="pattern-alert">
                        <strong>{cp['type'].replace('_',' ').title()}</strong>: {cp['detail']}
                        <div style="color:#9a3412;font-size:0.88em;margin-top:2px">→ {cp['fix']}</div>
                    </div>
                    """, unsafe_allow_html=True)

            # Blacklist
            if r.get("blacklist_hits"):
                for bl in sorted(r["blacklist_hits"], key=lambda x: -x["count"]):
                    st.markdown(f'<div class="blacklist-hit"><strong>"{bl["phrase"]}"</strong> — {bl["count"]}x gefunden</div>', unsafe_allow_html=True)

            # Sentence length chart
            all_sl = []
            for p in r["paragraphs_detail"]:
                all_sl.extend(p.get("sent_lengths", []))
            if all_sl:
                st.caption("Satzlangen-Profil (rot = im KI-typischen 20-35W Band)")
                mx = max(all_sl) if all_sl else 1
                chart_html = '<div style="display:flex;align-items:flex-end;gap:1px;height:50px;background:#f8fafc;padding:4px;border-radius:6px">'
                for sl in all_sl:
                    h = max(3, int(sl / mx * 45))
                    bc = "#ef4444" if 20 <= sl <= 35 else "#3b82f6"
                    chart_html += f'<div style="height:{h}px;width:4px;background:{bc};border-radius:2px 2px 0 0" title="{sl}W"></div>'
                chart_html += '</div>'
                st.markdown(chart_html, unsafe_allow_html=True)

            # Per-paragraph
            st.markdown("**Absatz-Analyse:**")
            for i, p in enumerate(r.get("paragraphs_detail", [])):
                ps = p["score"]

                # Build sentence HTML
                sent_html = ""
                if p.get("sent_details"):
                    for sd in p["sent_details"]:
                        ss = sd["score"]
                        sbg = score_bg(ss)
                        issues_str = '; '.join(sd['issues']) if sd['issues'] else 'OK'
                        fixes_str = '; '.join(sd.get('fixes', [])) if sd.get('fixes') else ''
                        title = f"{ss}%: {issues_str}"
                        if fixes_str:
                            title += f" | Fix: {fixes_str}"
                        sent_html += f'<span class="sent-hl" style="background:{sbg}" title="{title}">{sd["text"]}</span> '

                issues_html = f'<div style="font-size:0.8em;color:#64748b;margin-top:4px">{" | ".join(p["issues"])}</div>' if p["issues"] else ''
                fixes_html = f'<div style="font-size:0.8em;color:#4338ca;margin-top:2px;font-style:italic">{" | ".join(p["fixes"])}</div>' if p.get("fixes") else ''

                st.markdown(f"""
                <div class="para-block" style="background:{score_bg(ps)};border-left-color:{score_color(ps)}">
                    <div style="display:flex;justify-content:space-between;align-items:center">
                        <div><strong>P{i+1}</strong> <span class="score-badge" style="background:{score_color(ps)}">{ps}%</span></div>
                        <span style="color:#94a3b8;font-size:0.82em">{p["words"]}W &middot; {p.get("sentences","?")}S &middot; CV:{p["burstiness_cv"]}</span>
                    </div>
                    <div style="margin-top:6px;font-size:0.88em;line-height:1.9">{sent_html}</div>
                    {issues_html}
                    {fixes_html}
                </div>
                """, unsafe_allow_html=True)

    # ===== FOOTER =====
    st.markdown("---")
    st.caption("KI-Detektor v3.1 — Basierend auf publizierten Forschungsdaten (PMC10760418, GPTZero, Turnitin Whitepaper) — Alle Daten werden lokal verarbeitet.")
