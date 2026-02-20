# .env.local 처음부터 사용하기 (Elasticsearch + 개인 LLM, 인제스트 포함)

**Elasticsearch 검색 + 개인 LLM** 조합으로, 인제스트부터 질의·UI까지 한 번에 하는 방법입니다.

---

## 1. 필요한 것

- Docker Desktop (실행 중)
- 프로젝트 폴더 `ksp-rag-system`
- 인제스트할 PDF 파일들
- 개인 LLM용 API 키 (OpenAI 등)

---

## 2. 환경 설정

### 2.1 env 파일 만들기

```bash
cd ksp-rag-system
make setup
cp .env.local.example .env.local
```

### 2.2 .env.local 수정

파일을 열어서 **아래만** 본인 값으로 바꿉니다.

| 항목 | 설명 | 예시 |
|------|------|------|
| `LLM_API_KEY` | 사용할 API 키 | `sk-...` (OpenAI) |
| `LLM_MODEL` | 모델 이름 | `gpt-3.5-turbo`, `gpt-4` |
| `LLM_API_TYPE` | API 타입 (필요 시) | `openai` |

표/이미지 추출 옵션만 바꾸고 싶으면:

- `EXTRACT_FIGURES=false` → 텍스트+표만 (빠름)
- `EXTRACT_FIGURES=true` → 차트/이미지 설명까지 추출 (느림)

---

## 3. Docker 이미지 빌드

```bash
make build
```

---

## 4. 인제스트 (PDF → 청크)

### 4.1 PDF 넣기

PDF를 다음 폴더에 넣습니다.

```
ksp-rag-system/data/raw/
```

### 4.2 인제스트 실행

`.env.local` 설정(CHUNK_SIZE, EXTRACT_FIGURES 등)을 쓰려면, 먼저 이 설정을 `.env`로 복사한 뒤 인제스트를 돌립니다.

```bash
cp .env.local .env
make ingest
```

표까지 추출하려면:

```bash
cp .env.local .env
make ingest-tables
```

결과 파일: `data/processed/chunks.jsonl`

---

## 5. Elasticsearch 띄우기

```bash
make elastic-up
```

30초 정도 뒤에 헬스체크:

```bash
make elastic-health
```

`"status" : "green"` 이면 정상입니다.

---

## 6. Elasticsearch 인덱스 빌드 (임베딩)

`chunks.jsonl`을 Elasticsearch에 넣는 단계입니다. 이 명령은 내부에서 `.env.server`를 사용합니다(Elastic 주소만 쓰고, LLM은 사용 안 함).

```bash
make index-elastic
```

청크가 많으면 시간이 꽤 걸릴 수 있습니다.

---

## 7. 질의·UI (Elasticsearch + 개인 LLM)

이제 **검색 = Elasticsearch**, **답 생성 = .env.local 에 설정한 개인 LLM** 으로 동작합니다.

### CLI로 질의

```bash
make ask-local Q="궁금한 질문 한 문장"
```

### Streamlit UI

```bash
make ui-local
```

브라우저에서 **http://localhost:8501** 접속 후 질의합니다.

UI 종료:

```bash
make ui-down
```

---

## 8. 전체 순서 요약

| 순서 | 할 일 | 명령 |
|------|--------|------|
| 1 | 설정 | `make setup` → `cp .env.local.example .env.local` → LLM 키/모델 수정 |
| 2 | 이미지 | `make build` |
| 3 | PDF 넣기 | `data/raw/` 에 PDF 배치 |
| 4 | 인제스트 | `cp .env.local .env` → `make ingest` (또는 `make ingest-tables`) |
| 5 | Elasticsearch | `make elastic-up` → `make elastic-health` |
| 6 | 인덱스 | `make index-elastic` |
| 7 | 질의 | `make ask-local Q="질문"` 또는 `make ui-local` |

---

## 9. 자주 쓰는 명령

| 목적 | 명령 |
|------|------|
| 설정 확인 | `.env.local` 에서 LLM_API_KEY, ELASTIC_* 등 확인 |
| 인제스트만 다시 | `cp .env.local .env` → `make ingest` |
| 인덱스만 다시 | `make index-elastic` |
| Elasticsearch 중지 | `make elastic-down` |

---

## 10. 문제 해결

- **`Create .env.local from ...`**  
  → `cp .env.local.example .env.local` 하고 `LLM_API_KEY` 등 수정

- **Elasticsearch 연결 실패**  
  → `make elastic-up` 후 30초 기다렸다가 `make elastic-health` 재시도

- **인덱스가 없다는 오류**  
  → `make index-elastic` 실행 여부 확인

- **LLM 오류 (401, timeout 등)**  
  → `.env.local` 의 `LLM_API_KEY`, `LLM_MODEL`, `LLM_API_TYPE` 확인
