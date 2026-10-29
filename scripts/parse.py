#!/usr/bin/env python3
"""Parse all survey files (docx + pdf) in the repo root into a unified JSON.

Usage:
    python3 scripts/parse.py           # reads <repo>/*.docx and *.pdf
    SURVEY_DIR=... python3 scripts/parse.py
Output goes to <repo>/scripts/_build/survey_data.json by default.
"""
import os, re, json, subprocess, tempfile, zipfile, xml.etree.ElementTree as ET

W_NS = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(SCRIPT_DIR)
SURVEY = os.environ.get('SURVEY_DIR', REPO)
BUILD = os.path.join(SCRIPT_DIR, '_build')
EXTRACT = os.path.join(BUILD, 'extracted')
OUT = os.path.join(BUILD, 'survey_data.json')
os.makedirs(EXTRACT, exist_ok=True)

def unzip_docx(docx_path, dest):
    with zipfile.ZipFile(docx_path) as z:
        z.extractall(dest)

def docx_lines(docx_dir):
    path = os.path.join(EXTRACT, docx_dir, 'word/document.xml')
    tree = ET.parse(path)
    root = tree.getroot()
    lines = []
    for p in root.iter(f'{W_NS}p'):
        text = ''
        for t in p.iter(f'{W_NS}t'):
            text += t.text or ''
        text = text.strip()
        if text:
            lines.append(text)
    return lines

def pdf_lines(pdf_path):
    # Use pdftotext -raw to get sequential text
    out = subprocess.check_output(['pdftotext', '-raw', pdf_path, '-'], text=True)
    # The pdf is 2-column question/answer table. -raw mode might merge badly.
    # Try layout mode to parse differently.
    out2 = subprocess.check_output(['pdftotext', '-layout', pdf_path, '-'], text=True)
    # Parse layout mode: left column is question, right column is answer
    lines_out = []
    for line in out2.split('\n'):
        line = line.rstrip()
        if not line.strip():
            continue
        lines_out.append(line)
    return lines_out

def parse_pdf_file(pdf_path):
    """Delegate to parse_pdf.py (sibling module)."""
    import importlib.util
    spec = importlib.util.spec_from_file_location('pp', os.path.join(SCRIPT_DIR, 'parse_pdf.py'))
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod.parse_pdf(pdf_path)

def _parse_pdf_old(pdf_path):
    """DISABLED old path."""
    raw = subprocess.check_output(['pdftotext', '-layout', pdf_path, '-'], text=True)
    lines = raw.split('\n')
    # Determine split column: find where right column starts (approx col 50+)
    # Build q_text and a_text buffers by line, splitting at ~col 50
    SPLIT = 50
    pairs = []  # list of (left, right)
    for line in lines:
        if not line.strip():
            if pairs and (pairs[-1][0] or pairs[-1][1]):
                pairs.append(['', ''])
            continue
        # expand tabs
        line = line.expandtabs(4)
        if len(line) < SPLIT:
            left = line.rstrip()
            right = ''
        else:
            left = line[:SPLIT].rstrip()
            right = line[SPLIT:].rstrip()
        pairs.append([left, right])
    # Now reconstruct a flat lines list: alternate question lines and answer lines
    # First collect left column text (questions) and right column text (answers)
    # as blocks separated by blank lines
    left_blocks = []
    right_blocks = []
    cur_l = []
    cur_r = []
    for l, r in pairs:
        if not l and not r:
            if cur_l: left_blocks.append(' '.join(cur_l)); cur_l = []
            if cur_r: right_blocks.append(' '.join(cur_r)); cur_r = []
            continue
        if l: cur_l.append(l)
        if r: cur_r.append(r)
    if cur_l: left_blocks.append(' '.join(cur_l))
    if cur_r: right_blocks.append(' '.join(cur_r))
    # Return as alternating lines: question block then answer block
    out = []
    maxlen = max(len(left_blocks), len(right_blocks))
    for i in range(maxlen):
        if i < len(left_blocks) and left_blocks[i]:
            out.append(left_blocks[i])
        if i < len(right_blocks) and right_blocks[i]:
            out.append(right_blocks[i])
    return out

def extract_personal(lines):
    """Section I: 자문위원 인적사항."""
    fields = ['성명','소속','직위','응답 분야','경력·BIM 실적','주요 수행 시설군','회신일']
    out = {}
    for i, l in enumerate(lines):
        for f in fields:
            if l == f and i+1 < len(lines):
                # Next line is the value
                val = lines[i+1]
                # Make sure not another field label
                if val not in fields:
                    out[f] = val
                    break
    return out

# Question codes to extract
Q_CODES = [
    'Q1','Q1-2','Q2','Q3','Q3-2','Q4','Q5','Q6','Q7','Q8','Q9','Q10','Q11',
    'E1','E2','E3','E4','E5','E6',
    'D1','D2','D3','D4','D5','D6','D7','D8',
    'C1','C2','C3','C4','C5','C6','C7',
    'B1','B2','B3','B4','B5','B6','B7',
    'R1','R2','R3','R4','R5','R6','R7',
    'Z1','Z2','Z3','Z4','Z5',
]

def parse_questions(lines):
    """Collect lines under each question code."""
    # Find indices of question headers
    header_re = re.compile(r'^(Q\d+(?:-\d+)?|E\d+|D\d+|C\d+|B\d+|R\d+|Z\d+)\.\s*(.+)$')
    indices = []  # (idx, code, title)
    for i, l in enumerate(lines):
        m = header_re.match(l)
        if m and m.group(1) in Q_CODES:
            indices.append((i, m.group(1), m.group(2)))
    # For each, collect lines until next question or section header
    section_re = re.compile(r'^[ⅠⅡⅢⅣⅤ].*')
    out = {}
    for k, (idx, code, title) in enumerate(indices):
        end = indices[k+1][0] if k+1 < len(indices) else len(lines)
        body_lines = []
        for j in range(idx+1, end):
            s = lines[j].strip()
            if not s or s in ('문항','자문 의견'):
                continue
            if section_re.match(s):
                break
            body_lines.append(s)
        out[code] = {'title': title.strip(), 'body': body_lines}
    return out

def extract_choices(body_lines):
    """Extract '선택 : ...' values and other field: value pairs from body lines."""
    choices = []
    extras = {}
    for line in body_lines:
        m = re.match(r'^선택\s*:\s*(.+)$', line)
        if m:
            choices.append(m.group(1).strip())
            continue
        # Other field : value patterns
        m2 = re.match(r'^([^:]{1,40})\s*:\s*(.+)$', line)
        if m2:
            key = m2.group(1).strip()
            val = m2.group(2).strip()
            if key and val:
                extras[key] = val
    return choices, extras

def process_file(name, lines):
    personal = extract_personal(lines)
    questions = parse_questions(lines)
    # Add parsed choices to each question
    for code, q in questions.items():
        ch, ex = extract_choices(q['body'])
        q['choices'] = ch
        q['extras'] = ex
        q['text'] = '\n'.join(q['body'])
    return {'file': name, 'personal': personal, 'questions': questions}

def main():
    respondents = []
    # Discover docx files in SURVEY dir, extract to EXTRACT dir
    for name in sorted(os.listdir(SURVEY)):
        full = os.path.join(SURVEY, name)
        if not os.path.isfile(full): continue
        if name.lower().endswith('.docx'):
            base = os.path.splitext(name)[0]
            dest = os.path.join(EXTRACT, base)
            os.makedirs(dest, exist_ok=True)
            try:
                unzip_docx(full, dest)
            except Exception as e:
                print(f'! skip {name}: {e}'); continue
            lines = docx_lines(base)
            respondents.append(process_file(base, lines))
        elif name.lower().endswith('.pdf'):
            try:
                lines = parse_pdf_file(full)
            except Exception as e:
                print(f'! skip {name}: {e}'); continue
            respondents.append(process_file(os.path.splitext(name)[0], lines))
    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump(respondents, f, ensure_ascii=False, indent=2)
    print(f'Written {len(respondents)} respondents to {OUT}')
    for r in respondents:
        p = r['personal']
        print(f"- {p.get('성명','?')} | {p.get('응답 분야','?')[:30]} | Q codes: {len(r['questions'])}")

if __name__ == '__main__':
    main()
