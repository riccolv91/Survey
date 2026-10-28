# 서울형 스마트건설 BIM 서면자문 — 분석 파이프라인

저장소 루트에 올린 자문의견서(`.docx`) / 서면자문(`.pdf`) 파일을 읽어 하나의 HTML 대시보드(`survey_dashboard.html`)를 생성한다.

## 자동 재빌드 (권장)

`main` 브랜치에 설문 결과 파일(`*.docx`, `*.pdf`) 또는 `scripts/` 하위 코드를 push 하면
GitHub Actions 워크플로우 `.github/workflows/build-dashboard.yml` 이 자동으로:

1. `scripts/parse.py` 로 모든 설문 파일을 파싱해 `scripts/_build/survey_data.json` 생성
2. `scripts/build_html.py` 로 `survey_dashboard.html` 재생성
3. 변경이 있으면 같은 브랜치에 자동 커밋

워크플로우가 커밋을 push 하려면 저장소 설정 → Actions → "Workflow permissions" 가
"Read and write permissions" 로 되어 있어야 한다.

## 로컬에서 수동 실행

```bash
# 1) 저장소 루트의 .docx / .pdf 를 파싱
python3 scripts/parse.py

# 2) HTML 재생성
python3 scripts/build_html.py
```

필요 조건: Python 3.9+, `pdftotext` (Ubuntu/WSL: `apt install poppler-utils`, macOS: `brew install poppler`).

## 새 응답자 추가 시

1. 자문의견서 docx 또는 pdf 파일을 저장소 루트에 추가하고 `main`에 push
2. GitHub Actions 가 자동으로 대시보드 갱신

파일명 규칙은 특정 양식이 아니라 **확장자(.docx / .pdf)** 로만 판정한다.
문항 구조(Section I 인적사항, Q1~Q11, E1~E6, D/C/B/R, Z1~Z5)가 기존 양식과 같아야
집계·차트가 올바로 그려진다. 양식이 많이 바뀐 파일은 '응답자별' 탭에서 원문 열람으로는 보이지만
문항별 집계·차트에서는 '기타/무응답'으로 분류될 수 있다.

## 파일 구성

- `scripts/parse.py` — docx/pdf → `survey_data.json`
- `scripts/parse_pdf.py` — pdf 2단 레이아웃 파서
- `scripts/build_html.py` — JSON → `survey_dashboard.html`
- `scripts/chartjs.min.js` — Chart.js 4.4.6 UMD 번들 (HTML 안에 인라인됨)
- `scripts/_build/` — 중간 산출물 (git ignore)
