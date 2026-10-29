#!/usr/bin/env python3
"""Parse 2-column PDF survey → flat lines matching docx structure."""
import subprocess, re, sys

SPLIT = 50
HEADER_RE = re.compile(r'^(Q\d+(?:-\d+)?|E\d+|D\d+|C\d+|B\d+|R\d+|Z\d+)\.\s*(.+)$')
SECTION_RE = re.compile(r'^[ⅠⅡⅢⅣⅤ]')
PERSONAL = {'성명','소속','직위','응답 분야','경력·BIM 실적','주요 수행 시설군','회신일'}

def pdf_rows(pdf_path):
    raw = subprocess.check_output(['pdftotext', '-layout', pdf_path, '-'], text=True)
    pairs = []
    for s in raw.split('\n'):
        if not s.strip():
            pairs.append(('', ''))
            continue
        # Strip page headers/footers
        if re.match(r'^\s*\d+\.\s*\d+\.\s*\d+\.\s+오전', s): continue
        if s.strip() == '자문 의견서': continue
        if s.strip().startswith('file:///'): continue
        s_e = s.expandtabs(4)
        left = s_e[:SPLIT].rstrip() if len(s_e) >= 0 else ''
        right = s_e[SPLIT:].rstrip() if len(s_e) > SPLIT else ''
        pairs.append((left.strip(), right.strip()))
    return pairs

def parse_pdf(pdf_path):
    pairs = pdf_rows(pdf_path)
    out = []
    # Group right-column lines per "question row" (between question header rows)
    cur_q_header = None
    cur_q_title_parts = []
    cur_right_rows = []  # list of lists; each inner list is successive right lines for one logical row

    def flush():
        if cur_q_header is None:
            return
        out.append(f"{cur_q_header[0]}. {' '.join(cur_q_title_parts).strip()}")
        # Merge continuation right-column lines: a line starts a new logical row if it begins with
        # a known pattern (선택, Korean label with ":", a facility+stage pattern, "1순위", "2순위")
        # Otherwise it continues the previous logical row.
        logical = []
        for line in cur_right_rows:
            line = line.strip()
            if not line: continue
            is_new = False
            if re.match(r'^선택\s*[:：]', line): is_new = True
            elif re.match(r'^\d순위\s*[:：]', line): is_new = True
            elif re.match(r'^(그렇게|가장|선택하신|구간별로|시설군과|서울시의|현재 기준으로|수행 기관|BIM 업무|성과품|검수|과업|오류|1건당|그렇게 보시는)', line): is_new = True
            elif re.match(r'^[가-힣A-Za-z0-9][^:]{1,45}[:：]\s*', line): is_new = True
            if is_new or not logical:
                logical.append(line)
            else:
                logical[-1] = logical[-1] + ' ' + line
        for l in logical:
            out.append(l)

    for l, r in pairs:
        if l.startswith(('Ⅰ','Ⅱ','Ⅲ','Ⅳ','Ⅴ')):
            flush(); cur_q_header=None; cur_q_title_parts=[]; cur_right_rows=[]
            out.append(l)
            continue
        # Personal section rows: value may be on left (padded) or split across l+r
        if l:
            m2 = re.match(r'^(성명|소속|직위|응답 분야|경력·BIM 실적|주요 수행 시설군|회신일)\s{2,}(.*)$', l)
            if m2:
                flush(); cur_q_header=None; cur_q_title_parts=[]; cur_right_rows=[]
                val = (m2.group(2) + ' ' + r).strip()
                out.append(m2.group(1)); out.append(val)
                continue
        m = HEADER_RE.match(l) if l else None
        if m:
            flush()
            cur_q_header = (m.group(1), m.group(2))
            cur_q_title_parts = [m.group(2)]
            cur_right_rows = [r] if r else []
            continue
        # Continuation of current question
        if cur_q_header:
            if l and not l.startswith(('문항',)):
                cur_q_title_parts.append(l)
            if r:
                cur_right_rows.append(r)
    flush()
    return out

if __name__ == '__main__':
    for l in parse_pdf(sys.argv[1]):
        print(l)
