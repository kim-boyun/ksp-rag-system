# Sample Data

이 폴더에 PDF 파일을 넣으면 인제스트할 수 있습니다.

## 테스트용 샘플 생성

간단한 테스트를 위해 다음 방법으로 샘플 PDF를 생성할 수 있습니다:

### 방법 1: 온라인 도구 사용
1. Google Docs에서 문서 작성
2. 파일 → 다운로드 → PDF

### 방법 2: 샘플 문서 다운로드
```bash
# 예시: 공개 PDF 다운로드
curl -o data/raw/sample.pdf "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf"
```

### 방법 3: Python으로 샘플 생성
```python
from fpdf import FPDF

pdf = FPDF()
pdf.add_page()
pdf.set_font("Arial", size=12)
pdf.cell(200, 10, txt="RAG System Test Document", ln=True, align='C')
pdf.cell(200, 10, txt="This is a sample document for testing.", ln=True)
pdf.output("data/raw/sample.pdf")
```

## 인제스트 실행

```bash
make ingest
```
