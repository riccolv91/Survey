#!/usr/bin/env python3
"""Build a single self-contained HTML file visualising the survey data."""
import json, re, html, os

import os
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(SCRIPT_DIR)
DATA = os.path.join(SCRIPT_DIR, '_build', 'survey_data.json')
OUT = os.path.join(REPO, 'survey_dashboard.html')

respondents = json.load(open(DATA, encoding='utf-8'))

# Normalize category from "응답 분야"
def category(resp_field):
    s = resp_field or ''
    if s.startswith('①') or '학계' in s or '대학' in s: return '학계'
    if s.startswith('②') or '시공사' in s: return '시공'
    if s.startswith('③') or 'BIM 전문' in s or '모델링·컨설팅' in s: return 'BIM전문'
    if s.startswith('④'):
        if '설계' in s: return '설계'
        if '감리' in s: return '감리'
        return '엔지니어링'
    return '기타'

# Enrich respondents
for r in respondents:
    r['category'] = category(r['personal'].get('응답 분야', ''))
    r['name'] = r['personal'].get('성명','?')
    r['org'] = r['personal'].get('소속','')
    r['career'] = r['personal'].get('경력·BIM 실적','')
    r['date'] = r['personal'].get('회신일','')

# Helper: get first choice for a question
def first_choice(q):
    chs = q.get('choices', [])
    return chs[0] if chs else ''

# Extract canonical option label from a choice value using mapping
def canon(choice, options):
    """Return matching option label or 'etc' if no match."""
    for opt in options:
        if opt in choice:
            return opt
    # try strip circled number
    m = re.match(r'^[①②③④⑤⑥⑦]', choice)
    if m:
        prefix = choice[0]
        for opt in options:
            if opt.startswith(prefix):
                return opt
    return None

# Build structured aggregates per question
# Define single-choice option sets
SCHEMA = {
    'Q1': {
        'title': "2027년 '300억↑ 기타공사' 확대가 현장에서 가능한가",
        'kind': 'single',
        'options': ["① 계획대로 '27년 가능", '② 선결조건이 충족되면 가능', '③ 1~2년 준비기간이 더 필요', '④ 적용 대상 기준을 바꿔야 가능', '⑤ 판단 곤란']
    },
    'Q1-2': {
        'title': "'27년 시행 시 가장 우려되는 문제 (복수선택)",
        'kind': 'multi',
        'splitter': '/',
    },
    'Q2': {
        'title': '확대에 앞서 반드시 갖춰져야 할 것 (복수선택)',
        'kind': 'multi',
        'splitter': '/',
    },
    'Q3-2': {
        'title': "총공사비 구간별 '27년 BIM 적용 가능성",
        'kind': 'matrix',
        'keys': ['300억~500억 미만', '500억~1,000억 미만', '1,000억 이상'],
        'values': ['○', '△', '×'],
    },
    'Q5': {
        'title': "'27년 적용 대상 기준으로 가장 적절한 안 (1순위)",
        'kind': 'ranked',
    },
    'Q6': {
        'title': '적용 확대 방식으로 어느 것이 현실적',
        'kind': 'single',
        'options': ['① 금액 기준 단계적 인하 (현행 서울시)', '② 금액 구간별 단계 적용', '③ 금액 고정, 요구수준 단계적 상향 (홍콩)', '④ 금액 구간×요구수준 교차 (독일)', '⑤ 기타']
    },
    'Q7': {
        'title': '총공사비 300억 원 기준선은 타당한가',
        'kind': 'single',
        'options': ['① 타당하다', '② 더 높은 금액이 적절', '③ 더 낮춰도 된다', '④ 금액 기준 자체가 부적절']
    },
    'Q8': {
        'title': "'29년 '100억↑ 건축공사' 단계",
        'kind': 'single',
        'options': ["① 계획대로 '29년 가능", '② 100억 기준 조정 필요', '③ 토목 일정에 맞춰 조정', '④ 판단 곤란']
    },
    'Q10': {
        'title': '국토부 후속 기준 미정비가 현장에 주는 영향',
        'kind': 'single',
        'options': ['매우 크다', '크다', '보통', '작다', '없다']
    },
    'E1': {
        'title': 'BIM 적용 시 설계 실제 투입(공수) 증가 수준',
        'kind': 'single',
        'options': ['① 5% 미만', '② 5~10%', '③ 10~20%', '④ 20% 이상', '⑤ 판단 곤란']
    },
    'E2': {
        'title': 'BIM으로 착공 전 발견되는 설계오류 규모',
        'kind': 'single',
        'options': ['① 명확히 이득', '② 대체로 이득', '③ 비슷', '④ 손해', '⑤ 판단 곤란']
    },
    'E3': {
        'title': '공공이 감수할 만한 추가비용의 한계',
        'kind': 'single',
        'options': ['① 설계비 5%', '② 설계비 10% 추가까지', '③ 설계비 20% 추가까지', '④ 비용과 무관하게 추진', '⑤ 판단 곤란']
    },
    'E4': {
        'title': '확대가 경제적으로 타당해지는 시점',
        'kind': 'single',
        'options': ['① 이미 감당 가능', '② 2~3년 후', '③ 4~5년 후', '④ 더 이후', '⑤ 자연히 해소되지 않음']
    },
    'E5': {
        'title': 'BIM 대가(별도 추가 대가) 지급이 맞는가',
        'kind': 'single',
        'options': ['① 필요', '② 부분적 필요', '③ 판단 곤란', '④ 필요 없음']
    },
    'E6': {
        'title': 'BIM 대가 처리 방식',
        'kind': 'single',
        'options': ['① 별도 대가기준 필수', '② 기본 대가에 포함하여 인상', '③ 현 단계에서는 필요, 장기적으로 불필요', '④ 설계비 포함', '⑤ 판단 곤란']
    },
}

# Q3 facility matrix
Q3_FACILITIES = ['도로(선형)','교량','터널·지하구조물','철도(도시철도)','공공건축','상·하수도','하천·치수','공동구·지하시설물']
Q3_STAGES = ['설계단계 BIM 적용', '시공단계 연계']

# Build per-question aggregates
def aggregate():
    agg = {}
    for qid, cfg in SCHEMA.items():
        agg[qid] = {'title': cfg['title'], 'kind': cfg['kind']}
        if cfg['kind'] == 'single':
            counts = {opt: 0 for opt in cfg['options']}
            counts['기타/무응답'] = 0
            per_resp = {}  # name -> option
            for r in respondents:
                q = r['questions'].get(qid)
                ch = first_choice(q) if q else ''
                matched = None
                if ch:
                    # 1) exact circled-number prefix match
                    for opt in cfg['options']:
                        prefix = opt[0] if opt and opt[0] in '①②③④⑤⑥⑦' else ''
                        if prefix and ch.startswith(prefix):
                            matched = opt; break
                    # 2) exact equality
                    if not matched:
                        for opt in cfg['options']:
                            if ch.strip() == opt.strip():
                                matched = opt; break
                    # 3) longest-first substring (prefer "매우 크다" over "크다")
                    if not matched:
                        for opt in sorted(cfg['options'], key=lambda s: -len(s)):
                            o_body = re.sub(r'^[①②③④⑤⑥⑦]\s*', '', opt).strip()
                            if o_body and o_body in ch:
                                matched = opt; break
                if matched:
                    counts[matched] += 1
                    per_resp[r['name']] = matched
                else:
                    counts['기타/무응답'] += 1
                    per_resp[r['name']] = ch or '(무응답)'
            agg[qid]['counts'] = counts
            agg[qid]['per_resp'] = per_resp
        elif cfg['kind'] == 'multi':
            counts = {}
            per_resp = {}
            for r in respondents:
                q = r['questions'].get(qid)
                ch = first_choice(q) if q else ''
                if not ch:
                    per_resp[r['name']] = []
                    continue
                parts = [p.strip() for p in re.split(r'\s*/\s*', ch) if p.strip()]
                per_resp[r['name']] = parts
                for p in parts:
                    # Shorten key: take first clause before ':'
                    key = p.split(':')[0].strip()
                    key = re.sub(r'^[①②③④⑤⑥⑦⑧⑨⑩]\s*', '', key)
                    counts[key] = counts.get(key, 0) + 1
            agg[qid]['counts'] = counts
            agg[qid]['per_resp'] = per_resp
        elif cfg['kind'] == 'matrix':
            # Q3-2: value is from extras keys matching cfg['keys']
            mat = {}  # key -> {value: count}
            per_resp = {}
            for k in cfg['keys']:
                mat[k] = {v: 0 for v in cfg['values']}
            for r in respondents:
                q = r['questions'].get(qid, {})
                extras = q.get('extras', {})
                row = {}
                for k in cfg['keys']:
                    val = ''
                    for ek, ev in extras.items():
                        if ek.strip().startswith(k) or k in ek:
                            val = ev; break
                    row[k] = val
                    # Classify
                    for v in cfg['values']:
                        if val.startswith(v):
                            mat[k][v] += 1
                            break
                per_resp[r['name']] = row
            agg[qid]['matrix'] = mat
            agg[qid]['per_resp'] = per_resp
            agg[qid]['values'] = cfg['values']
            agg[qid]['keys'] = cfg['keys']
        elif cfg['kind'] == 'ranked':
            # Q5: 1순위 and 2순위 in extras
            opt_counts_1 = {}
            opt_counts_2 = {}
            per_resp = {}
            for r in respondents:
                q = r['questions'].get(qid, {})
                extras = q.get('extras', {})
                r1 = ''
                r2 = ''
                for k, v in extras.items():
                    if k.startswith('1순위'): r1 = v
                    if k.startswith('2순위'): r2 = v
                # Extract plan letter
                def plan_letter(s):
                    m = re.match(r'^\(?([가-하])\)?\s*(A|B|C|D|E|F|G)안', s)
                    if m: return m.group(2) + '안'
                    m2 = re.match(r'^\(?([가나다라마바사])\)?', s)
                    if m2:
                        mp = {'가':'A안','나':'B안','다':'C안','라':'D안','마':'E안','바':'F안','사':'G안'}
                        return mp.get(m2.group(1), s[:10])
                    return s[:15] or '-'
                a1 = plan_letter(r1) if r1 else ''
                a2 = plan_letter(r2) if r2 else ''
                if a1:
                    opt_counts_1[a1] = opt_counts_1.get(a1, 0) + 1
                if a2:
                    opt_counts_2[a2] = opt_counts_2.get(a2, 0) + 1
                per_resp[r['name']] = {'1순위': r1, '2순위': r2, '1순위_요약': a1, '2순위_요약': a2}
            agg[qid]['first'] = opt_counts_1
            agg[qid]['second'] = opt_counts_2
            agg[qid]['per_resp'] = per_resp
    # Q3 matrix separately
    q3 = {'title': '시설군별·단계별 지금 확대 가능 범위',
          'facilities': Q3_FACILITIES, 'stages': Q3_STAGES,
          'values': ['○','△','×'],
          'matrix': {}, 'per_resp': {}}
    for f in Q3_FACILITIES:
        for s in Q3_STAGES:
            q3['matrix'][f'{f}|{s}'] = {'○':0,'△':0,'×':0}
    for r in respondents:
        q = r['questions'].get('Q3', {})
        extras = q.get('extras', {})
        row = {}
        for f in Q3_FACILITIES:
            for s in Q3_STAGES:
                key = f'{f} ({s})'
                val = ''
                for ek, ev in extras.items():
                    if f in ek and s in ek:
                        val = ev.strip()
                        break
                row[key] = val
                for v in ['○','△','×']:
                    if val.startswith(v):
                        q3['matrix'][f'{f}|{s}'][v] += 1
                        break
        q3['per_resp'][r['name']] = row
    agg['Q3'] = q3

    # Q11 subfields
    q11 = {'title': '타 발주기관(LH·SH·도로공사 등) BIM 과업 수행 경험',
           'subfields': ['BIM 업무 대가 수준', '성과품 요구수준', '검수의 엄격성', '과업 수행 기간의 여유'],
           'values': ['서울시보다 낮음/적음','비슷','서울시보다 높음/많음'],
           'experience_counts': {'있음': 0, '없음': 0, '기타': 0},
           'counts': {}, 'per_resp': {}}
    for sf in q11['subfields']:
        q11['counts'][sf] = {v: 0 for v in q11['values']}
    for r in respondents:
        q = r['questions'].get('Q11', {})
        ch = first_choice(q)
        extras = q.get('extras', {})
        # experience
        exp = '기타'
        if '있음' in ch: exp = '있음'
        elif '없음' in ch: exp = '없음'
        q11['experience_counts'][exp] += 1
        row = {'경험': ch}
        for sf in q11['subfields']:
            val = ''
            for ek, ev in extras.items():
                if sf in ek:
                    val = ev.strip(); break
            row[sf] = val
            for v in q11['values']:
                if v in val or val in v:
                    q11['counts'][sf][v] += 1
                    break
        q11['per_resp'][r['name']] = row
    agg['Q11'] = q11
    return agg

aggregates = aggregate()

# Category distribution
cat_counts = {}
for r in respondents:
    cat_counts[r['category']] = cat_counts.get(r['category'], 0) + 1

# Prepare per-respondent text responses for display
def collect_text_responses():
    """For each question code, gather non-empty text answers per respondent."""
    all_qids = set()
    for r in respondents:
        all_qids.update(r['questions'].keys())
    # Order
    def qkey(q):
        order = {'Q':1,'E':2,'D':3,'C':4,'B':5,'R':6,'Z':7}
        prefix = q[0]
        import re as _re
        m = _re.match(r'^([A-Z])(\d+)(?:-(\d+))?$', q)
        if m:
            p, n, sub = m.group(1), int(m.group(2)), int(m.group(3) or 0)
            return (order.get(p,99), n, sub)
        return (99,0,0)
    ordered = sorted(all_qids, key=qkey)
    questions_display = []
    for qid in ordered:
        entry = {'qid': qid, 'title': '', 'responses': []}
        for r in respondents:
            q = r['questions'].get(qid)
            if not q: continue
            if not entry['title']:
                entry['title'] = q.get('title','')
            # Collect text (full body)
            body = q.get('text') or '\n'.join(q.get('body', []))
            entry['responses'].append({
                'name': r['name'], 'org': r['org'], 'category': r['category'],
                'choices': q.get('choices', []),
                'extras': q.get('extras', {}),
                'text': body,
            })
        if entry['title'] or entry['responses']:
            questions_display.append(entry)
    return questions_display

questions_display = collect_text_responses()

# ---- Build HTML ----
# JSON payload
payload = {
    'respondents': [{
        'name': r['name'], 'org': r['org'], 'position': r['personal'].get('직위',''),
        'category': r['category'], 'resp_field': r['personal'].get('응답 분야',''),
        'career': r['career'], 'facilities': r['personal'].get('주요 수행 시설군',''),
        'date': r['date']
    } for r in respondents],
    'cat_counts': cat_counts,
    'aggregates': aggregates,
    'questions_display': questions_display,
}

payload_json = json.dumps(payload, ensure_ascii=False)

HTML = r"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>서울형 스마트건설 BIM 서면자문 응답 분석</title>
<script>__CHARTJS__</script>
<style>
  :root {
    --bg: #f6f7fb; --card: #ffffff; --ink: #1f2937; --muted: #6b7280;
    --accent: #2563eb; --accent-2: #0ea5e9; --line: #e5e7eb;
    --ok: #16a34a; --warn: #f59e0b; --bad: #dc2626; --neutral: #64748b;
    --chip-bg: #eef2ff; --chip-ink: #3730a3;
  }
  @media (prefers-color-scheme: dark) {
    :root:not([data-theme="light"]) {
      --bg:#0b1020; --card:#121a2d; --ink:#e5e7eb; --muted:#94a3b8;
      --accent:#60a5fa; --accent-2:#38bdf8; --line:#1f2a44;
      --chip-bg:#1e293b; --chip-ink:#c7d2fe;
    }
  }
  :root[data-theme="dark"] {
    --bg:#0b1020; --card:#121a2d; --ink:#e5e7eb; --muted:#94a3b8;
    --accent:#60a5fa; --accent-2:#38bdf8; --line:#1f2a44;
    --chip-bg:#1e293b; --chip-ink:#c7d2fe;
  }
  * { box-sizing: border-box; }
  body { margin:0; padding:0; background:var(--bg); color:var(--ink);
         font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans KR', Roboto, Pretendard, 'Apple SD Gothic Neo', sans-serif;
         line-height:1.55; }
  header { padding: 28px 16px 20px; max-width:1200px; margin: 0 auto; }
  header h1 { font-size: 26px; margin: 0 0 6px; letter-spacing:-.3px; }
  header .sub { color: var(--muted); font-size: 14px; }
  nav.tabs { max-width: 1200px; margin: 0 auto; padding: 0 16px;
             display:flex; gap:4px; overflow-x:auto; border-bottom:1px solid var(--line); }
  nav.tabs button { background:transparent; border:none; color:var(--muted);
                     padding:10px 14px; font-size:14px; cursor:pointer;
                     border-bottom:2px solid transparent; white-space:nowrap; }
  nav.tabs button.active { color: var(--accent); border-bottom-color: var(--accent); font-weight: 600; }
  main { max-width:1200px; margin: 0 auto; padding: 16px; }
  .section { display:none; }
  .section.active { display:block; }
  .grid { display:grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
          gap: 12px; }
  .card { background: var(--card); border:1px solid var(--line); border-radius: 10px;
          padding: 14px; }
  .card h3 { font-size: 15px; margin: 0 0 8px; }
  .kpi .val { font-size: 28px; font-weight: 700; margin-top:2px; }
  .kpi .label { color: var(--muted); font-size: 12px; }
  .chip { display:inline-block; background:var(--chip-bg); color:var(--chip-ink);
          padding:2px 8px; border-radius:999px; font-size:12px; margin-right:4px; }
  table { width:100%; border-collapse: collapse; font-size: 13px; }
  table th, table td { padding: 6px 8px; border-bottom:1px solid var(--line); text-align:left; vertical-align: top; }
  table th { background: rgba(0,0,0,.03); font-weight: 600; }
  .q-card { background: var(--card); border:1px solid var(--line); border-radius: 10px;
            padding: 16px; margin-bottom: 14px; }
  .q-head { display:flex; justify-content:space-between; align-items:center; gap:10px;
            margin-bottom: 8px; }
  .q-id { color: var(--accent); font-weight:700; font-size: 13px; }
  .q-title { font-weight:600; font-size: 15px; }
  .chart-wrap { position: relative; height: 240px; }
  details.resp { margin: 6px 0; border:1px solid var(--line); border-radius:8px;
                 padding: 6px 10px; }
  details.resp summary { cursor:pointer; font-size: 13px; font-weight:600;
                         display:flex; justify-content:space-between; align-items:center; gap: 8px; }
  details.resp[open] { background: rgba(99,102,241,.04); }
  .resp-body { padding: 8px 2px 2px; font-size: 13px; color: var(--ink);
                white-space: pre-wrap; }
  .resp-meta { font-size: 11px; color: var(--muted); font-weight: 400; }
  .filters { display:flex; gap:8px; flex-wrap: wrap; margin-bottom: 10px; }
  .filters label { display:flex; align-items:center; gap:6px; font-size:13px;
                   padding: 4px 10px; border:1px solid var(--line); border-radius: 999px;
                   cursor:pointer; }
  .filters input[type=checkbox] { accent-color: var(--accent); }
  .matrix-tbl td.v-ok { background: rgba(22,163,74,.12); color: var(--ok); font-weight:600; text-align:center; }
  .matrix-tbl td.v-partial { background: rgba(245,158,11,.14); color: var(--warn); font-weight:600; text-align:center; }
  .matrix-tbl td.v-bad { background: rgba(220,38,38,.14); color: var(--bad); font-weight:600; text-align:center; }
  .matrix-tbl td.v-empty { color: var(--muted); text-align:center; }
  .legend { font-size: 12px; color: var(--muted); margin-top: 6px; }
  .search-input { width: 100%; padding: 8px 10px; border:1px solid var(--line); border-radius: 8px;
                  background: var(--card); color: var(--ink); font-size: 14px; }
  button.theme { position: fixed; top: 10px; right: 10px; background: var(--card);
                 border:1px solid var(--line); color: var(--ink); padding: 6px 10px;
                 border-radius: 999px; cursor:pointer; font-size: 12px; z-index: 10; }
  .note { font-size: 12px; color: var(--muted); }
  .q-sub { font-size: 12px; color: var(--muted); margin-bottom: 10px; }
  .flex-row { display: flex; gap: 12px; flex-wrap: wrap; align-items: center; }
  .pill-count { background: var(--accent); color: #fff; padding: 1px 8px; border-radius: 999px;
                font-size: 11px; }
  @media (max-width: 700px) {
    header h1 { font-size: 20px; }
    .chart-wrap { height: 200px; }
  }
</style>
</head>
<body>
<button class="theme" onclick="toggleTheme()">🌓 테마</button>
<header>
  <h1>서울형 스마트건설 BIM 서면자문 — 응답 분석 대시보드</h1>
  <div class="sub">응답자 12명 · 자문의견서 11건(docx) + 서면자문 1건(pdf) · 2026.10</div>
</header>
<nav class="tabs" id="tabs">
  <button data-tab="overview" class="active">개요</button>
  <button data-tab="common">공통문항 Q1–Q11</button>
  <button data-tab="econ">경제성 E1–E6</button>
  <button data-tab="field">분야별 D·C·B·R</button>
  <button data-tab="wrap">마무리 Z1–Z5</button>
  <button data-tab="people">응답자별</button>
  <button data-tab="raw">원문 검색</button>
</nav>
<main>
  <section id="overview" class="section active">
    <div class="grid">
      <div class="card kpi"><div class="label">총 응답자</div><div class="val" id="kpi-count"></div></div>
      <div class="card kpi"><div class="label">설계</div><div class="val" id="kpi-설계"></div></div>
      <div class="card kpi"><div class="label">시공</div><div class="val" id="kpi-시공"></div></div>
      <div class="card kpi"><div class="label">BIM 전문</div><div class="val" id="kpi-BIM전문"></div></div>
      <div class="card kpi"><div class="label">학계</div><div class="val" id="kpi-학계"></div></div>
    </div>
    <div class="grid" style="margin-top:14px">
      <div class="card">
        <h3>응답자 분야 분포</h3>
        <div class="chart-wrap"><canvas id="chart-cat"></canvas></div>
      </div>
      <div class="card" style="grid-column: span 2">
        <h3>Q1. 2027년 확대 — 현장 수행 가능성</h3>
        <div class="chart-wrap"><canvas id="chart-Q1-ov"></canvas></div>
      </div>
    </div>
    <div class="grid" style="margin-top:14px">
      <div class="card"><h3>응답자 명단</h3>
        <table id="respondents-tbl"><thead><tr><th>성명</th><th>소속</th><th>분야</th><th>경력/BIM</th></tr></thead><tbody></tbody></table>
      </div>
    </div>
  </section>

  <section id="common" class="section">
    <div class="q-card">
      <div class="q-head"><div><span class="q-id">Q1</span> <span class="q-title">2027년 '300억↑ 기타공사' 확대가 현장에서 가능한가?</span></div></div>
      <div class="chart-wrap"><canvas id="chart-Q1"></canvas></div>
    </div>
    <div class="q-card">
      <div class="q-head"><div><span class="q-id">Q1-2</span> <span class="q-title">'27년 시행 시 가장 우려되는 문제 (복수선택)</span></div></div>
      <div class="chart-wrap" style="height: 320px"><canvas id="chart-Q1-2"></canvas></div>
    </div>
    <div class="q-card">
      <div class="q-head"><div><span class="q-id">Q2</span> <span class="q-title">확대에 앞서 반드시 갖춰져야 할 것 (복수선택)</span></div></div>
      <div class="chart-wrap" style="height: 360px"><canvas id="chart-Q2"></canvas></div>
    </div>
    <div class="q-card">
      <div class="q-head"><div><span class="q-id">Q3</span> <span class="q-title">시설군별·단계별 지금 확대 가능 범위</span></div></div>
      <div class="q-sub">○ 가능 / △ 조건부 / × 어려움</div>
      <div id="matrix-q3"></div>
    </div>
    <div class="q-card">
      <div class="q-head"><div><span class="q-id">Q3-2</span> <span class="q-title">총공사비 구간별 '27년 BIM 적용 가능성</span></div></div>
      <div class="chart-wrap"><canvas id="chart-Q3-2"></canvas></div>
    </div>
    <div class="q-card">
      <div class="q-head"><div><span class="q-id">Q5</span> <span class="q-title">'27년 적용 대상 기준으로 가장 적절한 안 (1·2순위)</span></div></div>
      <div class="chart-wrap"><canvas id="chart-Q5"></canvas></div>
    </div>
    <div class="q-card">
      <div class="q-head"><div><span class="q-id">Q6</span> <span class="q-title">적용 확대 방식 — 어느 것이 현실적?</span></div></div>
      <div class="chart-wrap"><canvas id="chart-Q6"></canvas></div>
    </div>
    <div class="q-card">
      <div class="q-head"><div><span class="q-id">Q7</span> <span class="q-title">총공사비 300억 원 기준선은 타당한가</span></div></div>
      <div class="chart-wrap"><canvas id="chart-Q7"></canvas></div>
    </div>
    <div class="q-card">
      <div class="q-head"><div><span class="q-id">Q8</span> <span class="q-title">'29년 '100억↑ 건축공사' 단계</span></div></div>
      <div class="chart-wrap"><canvas id="chart-Q8"></canvas></div>
    </div>
    <div class="q-card">
      <div class="q-head"><div><span class="q-id">Q10</span> <span class="q-title">국토부 후속 기준 미정비가 현장에 주는 영향</span></div></div>
      <div class="chart-wrap"><canvas id="chart-Q10"></canvas></div>
    </div>
    <div class="q-card">
      <div class="q-head"><div><span class="q-id">Q11</span> <span class="q-title">타 발주기관 BIM 과업 수행 경험 — 서울시와의 비교</span></div></div>
      <div class="q-sub">(응답자 중 '있음'으로 답한 사람의 응답을 비교)</div>
      <div class="chart-wrap" style="height: 320px"><canvas id="chart-Q11"></canvas></div>
    </div>
  </section>

  <section id="econ" class="section">
    <div class="grid">
      <div class="q-card"><div class="q-head"><div><span class="q-id">E1</span> <span class="q-title">설계 공수 증가 수준</span></div></div><div class="chart-wrap"><canvas id="chart-E1"></canvas></div></div>
      <div class="q-card"><div class="q-head"><div><span class="q-id">E2</span> <span class="q-title">착공 전 설계오류 발견 효과</span></div></div><div class="chart-wrap"><canvas id="chart-E2"></canvas></div></div>
      <div class="q-card"><div class="q-head"><div><span class="q-id">E3</span> <span class="q-title">공공이 감수할 추가비용 한계</span></div></div><div class="chart-wrap"><canvas id="chart-E3"></canvas></div></div>
      <div class="q-card"><div class="q-head"><div><span class="q-id">E4</span> <span class="q-title">경제적 타당 시점</span></div></div><div class="chart-wrap"><canvas id="chart-E4"></canvas></div></div>
      <div class="q-card"><div class="q-head"><div><span class="q-id">E5</span> <span class="q-title">별도 BIM 대가 지급 필요성</span></div></div><div class="chart-wrap"><canvas id="chart-E5"></canvas></div></div>
      <div class="q-card"><div class="q-head"><div><span class="q-id">E6</span> <span class="q-title">BIM 대가 처리 방식</span></div></div><div class="chart-wrap"><canvas id="chart-E6"></canvas></div></div>
    </div>
  </section>

  <section id="field" class="section">
    <p class="note">응답 분야별 전용 문항은 응답자 수가 소수이므로 원문 중심으로 열람합니다. 응답자 분야 필터로 좁혀 보세요.</p>
    <div id="field-questions"></div>
  </section>

  <section id="wrap" class="section">
    <div id="wrap-questions"></div>
  </section>

  <section id="people" class="section">
    <div class="filters" id="people-filters"></div>
    <div id="people-list"></div>
  </section>

  <section id="raw" class="section">
    <div style="margin-bottom:10px">
      <input class="search-input" id="raw-search" placeholder="원문에서 키워드 검색… (예: 대가, 검수, 시공, 유지관리)" />
    </div>
    <div id="raw-list"></div>
  </section>
</main>
<script>
const DATA = __PAYLOAD__;

const PAL = ['#2563eb','#0ea5e9','#16a34a','#f59e0b','#dc2626','#8b5cf6','#ec4899','#64748b'];
const PAL_SEQ = ['#dbeafe','#bfdbfe','#93c5fd','#60a5fa','#3b82f6','#1d4ed8'];

function getCssVar(name){ return getComputedStyle(document.documentElement).getPropertyValue(name).trim(); }
function textColor(){ return getCssVar('--ink') || '#1f2937'; }

// --- Tabs with lazy chart init ---
const tabInit = {};  // tab name -> initialized?
function activateTab(name){
  document.querySelectorAll('nav.tabs button').forEach(x=>x.classList.remove('active'));
  document.querySelectorAll('.section').forEach(x=>x.classList.remove('active'));
  const btn = document.querySelector(`nav.tabs button[data-tab="${name}"]`);
  if (btn) btn.classList.add('active');
  const sec = document.getElementById(name);
  if (sec) sec.classList.add('active');
  // After section is visible, init its charts (requires size)
  requestAnimationFrame(() => {
    if (tabInit[name]) return;
    try {
      initTab(name);
      tabInit[name] = true;
    } catch(e) { console.error('tab init failed', name, e); }
  });
}
document.querySelectorAll('nav.tabs button').forEach(b=>{
  b.addEventListener('click', ()=> activateTab(b.dataset.tab));
});

// --- Theme ---
function toggleTheme(){
  const cur = document.documentElement.getAttribute('data-theme');
  const next = cur === 'dark' ? 'light' : (cur === 'light' ? 'dark' : (matchMedia('(prefers-color-scheme: dark)').matches ? 'light' : 'dark'));
  document.documentElement.setAttribute('data-theme', next);
  try { localStorage.setItem('theme', next); } catch(e){}
  // Re-render charts to pick up colors
  Object.values(chartInstances).forEach(c => c && c.destroy());
  Object.keys(chartInstances).forEach(k => delete chartInstances[k]);
  Object.keys(tabInit).forEach(k => delete tabInit[k]);
  const active = document.querySelector('nav.tabs button.active');
  if (active) { requestAnimationFrame(() => { initTab(active.dataset.tab); tabInit[active.dataset.tab] = true; }); }
}
try { const t = localStorage.getItem('theme'); if (t) document.documentElement.setAttribute('data-theme', t); } catch(e){}

const chartInstances = {};
function makeChart(id, type, labels, datasets, extraOpts){
  const ctx = document.getElementById(id);
  if (!ctx) return null;
  const ink = textColor();
  const opts = Object.assign({
    responsive: true, maintainAspectRatio: false,
    plugins: {
      legend: { labels: { color: ink, font: { size: 11 } } },
      tooltip: { bodyFont: { size: 12 } },
    },
    scales: {
      x: { ticks: { color: ink, font: { size: 11 } }, grid: { color: getCssVar('--line') } },
      y: { ticks: { color: ink, font: { size: 11 }, precision: 0, stepSize: 1 }, grid: { color: getCssVar('--line') }, beginAtZero: true }
    }
  }, extraOpts || {});
  if (type === 'pie' || type === 'doughnut') {
    delete opts.scales;
  }
  chartInstances[id] = new Chart(ctx, { type, data: { labels, datasets }, options: opts });
}

// --- KPI ---
function renderKPI(){
  document.getElementById('kpi-count').textContent = DATA.respondents.length;
  ['설계','시공','BIM전문','학계'].forEach(c => {
    const el = document.getElementById('kpi-' + c);
    if (el) el.textContent = DATA.cat_counts[c] || 0;
  });
  // Respondents table
  const tbody = document.querySelector('#respondents-tbl tbody');
  tbody.innerHTML = '';
  DATA.respondents.forEach(r => {
    const tr = document.createElement('tr');
    tr.innerHTML = `<td>${r.name}</td><td>${r.org}</td><td><span class="chip">${r.category}</span></td><td>${r.career}</td>`;
    tbody.appendChild(tr);
  });
}

function catChart(){
  const labels = Object.keys(DATA.cat_counts);
  const data = labels.map(k => DATA.cat_counts[k]);
  makeChart('chart-cat','doughnut', labels, [{data, backgroundColor: PAL}]);
}

function singleChart(qid, canvasId){
  const agg = DATA.aggregates[qid];
  if (!agg) return;
  const labels = Object.keys(agg.counts);
  const data = labels.map(k => agg.counts[k]);
  // Shorten labels
  const short = labels.map(l => l.length > 24 ? l.slice(0,22) + '…' : l);
  makeChart(canvasId || ('chart-'+qid), 'bar', short, [{
    label: '응답 수', data, backgroundColor: PAL[0], borderRadius: 4
  }], { indexAxis: 'y', plugins:{legend:{display:false}} });
}

function multiChart(qid){
  const agg = DATA.aggregates[qid];
  if (!agg) return;
  const items = Object.entries(agg.counts).sort((a,b)=>b[1]-a[1]);
  const labels = items.map(x => x[0].length > 30 ? x[0].slice(0,28)+'…' : x[0]);
  const data = items.map(x => x[1]);
  makeChart('chart-'+qid, 'bar', labels, [{
    label: '선택 수', data, backgroundColor: PAL[1], borderRadius: 4
  }], { indexAxis: 'y', plugins:{legend:{display:false}} });
}

function q3Matrix(){
  const q3 = DATA.aggregates.Q3;
  if (!q3) return;
  const el = document.getElementById('matrix-q3');
  let html = '<table class="matrix-tbl"><thead><tr><th rowspan="2">시설군</th>';
  q3.stages.forEach(s => { html += `<th colspan="3">${s}</th>`; });
  html += '</tr><tr>';
  q3.stages.forEach(() => { html += `<th>○</th><th>△</th><th>×</th>`; });
  html += '</tr></thead><tbody>';
  q3.facilities.forEach(f => {
    html += `<tr><td>${f}</td>`;
    q3.stages.forEach(s => {
      const row = q3.matrix[`${f}|${s}`];
      html += `<td class="v-ok">${row['○']||'·'}</td><td class="v-partial">${row['△']||'·'}</td><td class="v-bad">${row['×']||'·'}</td>`;
    });
    html += '</tr>';
  });
  html += '</tbody></table>';
  el.innerHTML = html;
}

function q3_2Chart(){
  const m = DATA.aggregates['Q3-2'];
  if (!m) return;
  const labels = Object.keys(m.matrix);
  const vals = m.values;
  const colors = {'○':'#16a34a','△':'#f59e0b','×':'#dc2626'};
  const datasets = vals.map(v => ({
    label: v, data: labels.map(l => m.matrix[l][v] || 0),
    backgroundColor: colors[v], borderRadius: 4
  }));
  makeChart('chart-Q3-2', 'bar', labels, datasets, {
    scales: {
      x: { stacked: true, ticks: { color: textColor() }, grid: { color: getCssVar('--line') } },
      y: { stacked: true, ticks: { color: textColor() }, grid: { color: getCssVar('--line') }, beginAtZero: true }
    }
  });
}

function q5Chart(){
  const q = DATA.aggregates.Q5;
  if (!q) return;
  const all = new Set([...Object.keys(q.first), ...Object.keys(q.second)]);
  const labels = Array.from(all).sort();
  const d1 = labels.map(l => q.first[l]||0);
  const d2 = labels.map(l => q.second[l]||0);
  makeChart('chart-Q5', 'bar', labels, [
    { label:'1순위', data: d1, backgroundColor: PAL[0], borderRadius: 4 },
    { label:'2순위', data: d2, backgroundColor: PAL[3], borderRadius: 4 },
  ]);
}

function q11Chart(){
  const q = DATA.aggregates.Q11;
  if (!q) return;
  const labels = q.subfields;
  const vals = q.values;
  const colors = {'서울시보다 낮음/적음':'#64748b','비슷':'#2563eb','서울시보다 높음/많음':'#16a34a'};
  const datasets = vals.map(v => ({
    label: v, data: labels.map(l => q.counts[l][v]||0),
    backgroundColor: colors[v], borderRadius: 4
  }));
  makeChart('chart-Q11','bar', labels, datasets, {
    scales: {
      x: { stacked: true, ticks: { color: textColor() }, grid: { color: getCssVar('--line') } },
      y: { stacked: true, ticks: { color: textColor() }, grid: { color: getCssVar('--line') }, beginAtZero: true }
    }
  });
}

// Field-specific & wrap-up: list text responses with filter
function renderQuestionList(containerId, prefix){
  const list = DATA.questions_display.filter(q => q.qid.startsWith(prefix));
  const el = document.getElementById(containerId);
  el.innerHTML = '';
  list.forEach(q => {
    const card = document.createElement('div');
    card.className = 'q-card';
    const nResp = q.responses.filter(r=>r.text && r.text.trim()).length;
    card.innerHTML = `<div class="q-head"><div><span class="q-id">${q.qid}</span> <span class="q-title">${escapeHtml(q.title)}</span></div><span class="pill-count">${nResp}명</span></div>`;
    q.responses.forEach(r => {
      if (!r.text || !r.text.trim()) return;
      const d = document.createElement('details'); d.className='resp';
      d.innerHTML = `<summary><span>${r.name} <span class="chip">${r.category}</span></span><span class="resp-meta">${escapeHtml(r.org||'')}</span></summary><div class="resp-body">${escapeHtml(r.text)}</div>`;
      card.appendChild(d);
    });
    el.appendChild(card);
  });
}

function escapeHtml(s){
  return (s||'').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}

// People view: show each respondent as a card with all their answers
function renderPeople(){
  const filterEl = document.getElementById('people-filters');
  const cats = Array.from(new Set(DATA.respondents.map(r=>r.category)));
  filterEl.innerHTML = cats.map(c =>
    `<label><input type="checkbox" value="${c}" checked> ${c}</label>`
  ).join('') + `<label><input type="checkbox" id="pf-all" checked> 전체</label>`;
  function listPeople(){
    const checked = Array.from(filterEl.querySelectorAll('input[type=checkbox]:checked')).map(x=>x.value).filter(v=>v && v!=='on');
    const list = document.getElementById('people-list');
    list.innerHTML = '';
    DATA.respondents.forEach(r => {
      if (checked.length && !checked.includes(r.category)) return;
      const card = document.createElement('div'); card.className='q-card';
      card.innerHTML = `<div class="q-head"><div><strong>${r.name}</strong> · ${escapeHtml(r.org)}<br><span class="resp-meta">${escapeHtml(r.position||'')} · ${escapeHtml(r.career||'')} · 회신 ${r.date}</span></div><span class="chip">${r.category}</span></div>`;
      // Add brief choices summary
      const qsOrder = ['Q1','Q1-2','Q2','Q3-2','Q5','Q6','Q7','Q8','Q10','E1','E2','E3','E4','E5','E6'];
      let summary = '<div class="flex-row" style="margin-top:8px">';
      qsOrder.forEach(qid => {
        const q = DATA.questions_display.find(x=>x.qid===qid);
        if (!q) return;
        const r2 = q.responses.find(x=>x.name===r.name);
        if (!r2 || !r2.choices || !r2.choices.length) return;
        summary += `<span class="chip" title="${escapeHtml(q.title)}">${qid}: ${escapeHtml(r2.choices[0].slice(0,30))}</span>`;
      });
      summary += '</div>';
      card.innerHTML += summary;
      // All text responses
      DATA.questions_display.forEach(q => {
        const r2 = q.responses.find(x=>x.name===r.name);
        if (!r2 || !r2.text || !r2.text.trim()) return;
        const d = document.createElement('details'); d.className='resp';
        d.innerHTML = `<summary><span>${q.qid}. ${escapeHtml(q.title)}</span></summary><div class="resp-body">${escapeHtml(r2.text)}</div>`;
        card.appendChild(d);
      });
      list.appendChild(card);
    });
  }
  filterEl.addEventListener('change', e => {
    if (e.target.id === 'pf-all') {
      filterEl.querySelectorAll('input').forEach(i => { if (i.id!=='pf-all') i.checked = e.target.checked; });
    }
    listPeople();
  });
  listPeople();
}

// Raw search
function renderRaw(){
  const input = document.getElementById('raw-search');
  const list = document.getElementById('raw-list');
  function run(){
    const q = (input.value||'').trim().toLowerCase();
    list.innerHTML = '';
    let matches = 0;
    DATA.questions_display.forEach(qd => {
      qd.responses.forEach(r => {
        if (!r.text) return;
        if (q && !r.text.toLowerCase().includes(q) && !qd.title.toLowerCase().includes(q)) return;
        matches++;
        const card = document.createElement('div'); card.className='q-card';
        card.innerHTML = `<div class="q-head"><div><span class="q-id">${qd.qid}</span> <span class="q-title">${escapeHtml(qd.title)}</span></div><span class="chip">${r.name} · ${r.category}</span></div><div class="resp-body">${highlight(escapeHtml(r.text), q)}</div>`;
        list.appendChild(card);
      });
    });
    if (q && matches === 0) list.innerHTML = '<div class="note">일치하는 응답 없음.</div>';
  }
  function highlight(text, q){
    if (!q) return text;
    const re = new RegExp('(' + q.replace(/[.*+?^${}()|[\]\\]/g,'\\$&') + ')', 'ig');
    return text.replace(re, '<mark>$1</mark>');
  }
  input.addEventListener('input', run);
  run();
}

// Guarded chart invocation
function safe(fn, label){ try{ fn(); } catch(e){ console.error('chart failed:', label, e); } }

function initTab(name){
  if (name === 'overview') {
    safe(catChart, 'cat');
    safe(() => singleChart('Q1', 'chart-Q1-ov'), 'Q1-ov');
  } else if (name === 'common') {
    safe(() => singleChart('Q1'), 'Q1');
    safe(() => multiChart('Q1-2'), 'Q1-2');
    safe(() => multiChart('Q2'), 'Q2');
    safe(q3Matrix, 'Q3');
    safe(q3_2Chart, 'Q3-2');
    safe(q5Chart, 'Q5');
    safe(() => singleChart('Q6'), 'Q6');
    safe(() => singleChart('Q7'), 'Q7');
    safe(() => singleChart('Q8'), 'Q8');
    safe(() => singleChart('Q10'), 'Q10');
    safe(q11Chart, 'Q11');
  } else if (name === 'econ') {
    ['E1','E2','E3','E4','E5','E6'].forEach(qid => safe(() => singleChart(qid), qid));
  }
}

function renderStaticContent(){
  renderKPI();
  // Field tab (D/C/B/R)
  const fieldEl = document.getElementById('field-questions');
  fieldEl.innerHTML = '';
  ['D','C','B','R'].forEach(prefix => {
    const list = DATA.questions_display.filter(q => q.qid.startsWith(prefix) && q.qid[1] && !isNaN(q.qid[1]));
    if (!list.length) return;
    const title = {D:'설계 분야 (D1~D8)',C:'시공 분야 (C1~C7)',B:'BIM 전문 분야 (B1~B7)',R:'학계 분야 (R1~R7)'}[prefix];
    const section = document.createElement('div');
    section.innerHTML = `<h2 style="margin-top:18px;font-size:18px">${title}</h2>`;
    list.forEach(q => {
      const card = document.createElement('div');
      card.className = 'q-card';
      const nResp = q.responses.filter(r=>r.text && r.text.trim()).length;
      card.innerHTML = `<div class="q-head"><div><span class="q-id">${q.qid}</span> <span class="q-title">${escapeHtml(q.title)}</span></div><span class="pill-count">${nResp}명 응답</span></div>`;
      q.responses.forEach(r => {
        if (!r.text || !r.text.trim()) return;
        const d = document.createElement('details'); d.className='resp';
        d.innerHTML = `<summary><span>${r.name} <span class="chip">${r.category}</span></span><span class="resp-meta">${escapeHtml(r.org||'')}</span></summary><div class="resp-body">${escapeHtml(r.text)}</div>`;
        card.appendChild(d);
      });
      section.appendChild(card);
    });
    fieldEl.appendChild(section);
  });
  renderQuestionList('wrap-questions', 'Z');
  renderPeople();
  renderRaw();
}

renderStaticContent();
// Initialize overview immediately (it's the active tab)
requestAnimationFrame(() => { initTab('overview'); tabInit['overview'] = true; });
</script>
</body>
</html>
"""

chartjs_src = open(os.path.join(SCRIPT_DIR, 'chartjs.min.js'), encoding='utf-8').read()
# Guard against closing </script> inside chartjs code
chartjs_src = chartjs_src.replace('</script>', '<\\/script>')
HTML = HTML.replace('__CHARTJS__', chartjs_src)
HTML = HTML.replace('__PAYLOAD__', payload_json)

with open(OUT, 'w', encoding='utf-8') as f:
    f.write(HTML)
print(f'Wrote {OUT} ({len(HTML)} bytes)')
