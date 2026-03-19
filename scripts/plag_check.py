#!/usr/bin/env python3
"""
Plagiat-Scanner v1.0 — Einfacher Web-basierter Plagiat-Check.

Nimmt markante Phrasen aus dem Text und sucht sie bei Google.
Meldet Treffer mit Quell-URLs.

Usage:
  python3 plag_check.py <datei.docx>
  python3 plag_check.py <datei.docx> --html report.html
"""

import os, re, sys, json, random, time
from datetime import datetime

def extract_text(path):
    from docx import Document
    doc = Document(path)
    paragraphs = []
    for p in doc.paragraphs:
        text = p.text.strip()
        if text and len(text.split()) > 10:
            if p.style and p.style.name and 'heading' in p.style.name.lower():
                continue
            paragraphs.append(text)
    return paragraphs

def extract_phrases(paragraphs, phrase_len=8, max_phrases=30):
    """Extract distinctive phrases (N-grams) for searching."""
    all_phrases = []

    for para_idx, para in enumerate(paragraphs):
        words = para.split()
        if len(words) < phrase_len:
            continue

        # Take phrases from start, middle, end of each paragraph
        positions = [0, len(words)//2, max(0, len(words)-phrase_len)]
        for pos in positions:
            phrase = ' '.join(words[pos:pos+phrase_len])
            # Skip if too generic (starts with common words)
            first_word = phrase.split()[0].lower()
            if first_word in ['die', 'der', 'das', 'ein', 'eine', 'es', 'in', 'und', 'oder', 'mit']:
                # Try next position
                alt_pos = min(pos + 3, len(words) - phrase_len)
                if alt_pos >= 0 and alt_pos + phrase_len <= len(words):
                    phrase = ' '.join(words[alt_pos:alt_pos+phrase_len])

            # Clean citation markers
            phrase = re.sub(r'\([^)]*\d{4}[^)]*\)', '', phrase).strip()
            phrase = re.sub(r'\s+', ' ', phrase)

            if len(phrase.split()) >= 5:
                all_phrases.append({
                    "phrase": phrase,
                    "para_idx": para_idx,
                    "source_text": para[:100] + "..."
                })

    # Deduplicate and limit
    seen = set()
    unique = []
    for p in all_phrases:
        key = p["phrase"][:30]
        if key not in seen:
            seen.add(key)
            unique.append(p)

    # Sample if too many
    if len(unique) > max_phrases:
        # Ensure we cover all paragraphs
        by_para = {}
        for p in unique:
            by_para.setdefault(p["para_idx"], []).append(p)
        sampled = []
        for para_phrases in by_para.values():
            sampled.append(para_phrases[0])
            if len(para_phrases) > 1:
                sampled.append(para_phrases[1])
        if len(sampled) < max_phrases:
            remaining = [p for p in unique if p not in sampled]
            sampled.extend(remaining[:max_phrases - len(sampled)])
        return sampled[:max_phrases]

    return unique

def search_phrase_google(phrase):
    """Search a phrase on Google and return results."""
    import urllib.request
    import urllib.parse

    query = f'"{phrase}"'
    url = f"https://www.google.com/search?q={urllib.parse.quote(query)}&num=5&hl=de"

    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    })

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode('utf-8', errors='ignore')

        # Count results
        if 'did not match any documents' in html or 'keine Ergebnisse' in html:
            return {"found": False, "count": 0, "urls": []}

        # Extract URLs from results
        urls = re.findall(r'<a href="/url\?q=(https?://[^&"]+)', html)
        # Filter out google URLs
        urls = [u for u in urls if 'google.' not in u and 'youtube.' not in u][:3]

        # Check if any results exist
        has_results = len(urls) > 0 or 'Ungefähr' in html or 'Ergebnisse' in html

        return {"found": has_results, "count": len(urls), "urls": urls}

    except Exception as e:
        return {"found": None, "error": str(e), "count": 0, "urls": []}

def run_plag_check(path, max_phrases=25):
    """Run plagiarism check on a document."""
    paragraphs = extract_text(path)
    phrases = extract_phrases(paragraphs, max_phrases=max_phrases)

    results = []
    total = len(phrases)

    for i, p in enumerate(phrases):
        print(f"  [{i+1}/{total}] Suche: \"{p['phrase'][:50]}...\"", file=sys.stderr)
        search_result = search_phrase_google(p["phrase"])
        results.append({
            "phrase": p["phrase"],
            "para_idx": p["para_idx"],
            "found": search_result["found"],
            "urls": search_result.get("urls", []),
            "error": search_result.get("error"),
        })
        # Be nice to Google
        time.sleep(random.uniform(2, 4))

    matches = [r for r in results if r["found"]]
    no_match = [r for r in results if r["found"] == False]
    errors = [r for r in results if r["found"] is None]

    score = round(len(matches) / max(len(results) - len(errors), 1) * 100)

    return {
        "file": os.path.basename(path),
        "total_phrases": total,
        "matches": len(matches),
        "clean": len(no_match),
        "errors": len(errors),
        "plag_score": score,
        "details": results,
    }

def generate_html(result, output_path):
    matches = [r for r in result["details"] if r["found"]]
    clean = [r for r in result["details"] if r["found"] == False]
    score = result["plag_score"]

    sc = "#dc2626" if score >= 30 else "#ea580c" if score >= 15 else "#16a34a"

    html = f"""<!DOCTYPE html>
<html lang="de"><head><meta charset="UTF-8">
<title>Plagiat-Check Report</title>
<style>
body{{font-family:'Segoe UI',system-ui,sans-serif;max-width:56em;margin:0 auto;padding:1.5em;line-height:1.6;color:#1a1a2e;background:#fafafa}}
h1{{border-bottom:3px solid #0f172a;padding-bottom:.3em}}
.badge{{display:inline-block;padding:4px 12px;border-radius:6px;color:#fff;font-weight:bold}}
.match{{background:#fef2f2;border-left:4px solid #ef4444;padding:10px 14px;margin:6px 0;border-radius:0 8px 8px 0}}
.clean{{background:#f0fdf4;border-left:4px solid #22c55e;padding:8px 14px;margin:4px 0;border-radius:0 8px 8px 0}}
.url{{font-size:.85em;color:#3b82f6;word-break:break-all}}
</style></head><body>
<h1>Plagiat-Check Report</h1>
<p><strong>{result['file']}</strong> | {datetime.now().strftime('%d.%m.%Y %H:%M')} | {result['total_phrases']} Phrasen gepruft</p>
<p><strong>Plagiat-Score: <span class="badge" style="background:{sc}">{score}%</span></strong>
({result['matches']} Treffer / {result['total_phrases']} Phrasen)</p>
<p style="color:#64748b;font-size:.9em">0% = keine Treffer online (gut) | Hoher Score = Phrasen wurden online gefunden (pruefen ob korrekt zitiert)</p>
<hr>"""

    if matches:
        html += '<h2 style="color:#dc2626">Treffer</h2>'
        for m in matches:
            html += f'<div class="match"><strong>"{m["phrase"]}"</strong>'
            if m["urls"]:
                html += '<div style="margin-top:4px">'
                for u in m["urls"]:
                    clean_url = urllib_unquote(u) if 'urllib' in dir() else u
                    html += f'<div class="url">{u}</div>'
                html += '</div>'
            html += '</div>'

    html += '<h2 style="color:#22c55e">Keine Treffer (sauber)</h2>'
    for c in clean[:10]:
        html += f'<div class="clean">"{c["phrase"]}"</div>'
    if len(clean) > 10:
        html += f'<p style="color:#64748b">... und {len(clean)-10} weitere saubere Phrasen</p>'

    html += '</body></html>'
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Plagiat-Scanner v1.0")
        print("Usage: python3 plag_check.py <datei.docx> [--html report.html]")
        sys.exit(1)

    path = sys.argv[1]
    html_out = sys.argv[sys.argv.index("--html")+1] if "--html" in sys.argv else None

    print(f"Plagiat-Check: {os.path.basename(path)}", file=sys.stderr)
    result = run_plag_check(path)

    print(f"\nErgebnis: {result['plag_score']}% ({result['matches']}/{result['total_phrases']} Treffer)", file=sys.stderr)
    print(json.dumps(result, indent=2, ensure_ascii=False))

    if html_out:
        generate_html(result, html_out)
        print(f"HTML: {html_out}", file=sys.stderr)
