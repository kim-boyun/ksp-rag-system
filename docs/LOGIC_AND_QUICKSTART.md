# 로직 점검 및 처음부터 실행 가이드

## 1. 전체 로직 점검 (수정 반영)

### 1.1 설정 (config)

- **MODE**: `local` | `server` → LLM/연결 방식 구분
- **RETRIEVER_MODE**: `local`(BM25+FAISS) | `elastic`(Elasticsearch) → 실제 사용하는 검색 엔진
- **캐시**: `CACHE_ENABLED`, `CACHE_TTL_SECONDS`, `CACHE_MAX_SIZE` → 질의 결과 캐시
- **쿼리 확장**: `QUERY_EXPANSION_ENABLED`, `QUERY_EXPANSION_NUM_QUERIES` → 다중 표현 검색 후 RRF 병합

설정은 `.env.local` 또는 `.env.server`(실행 전 `.env`로 복사)에서 읽고, Docker 실행 시 `env_file: .env`로 컨테이너에 전달됨.

---

### 1.2 인제스트 (run_ingest)

1. **PDF 목록**: `input_dir`에서 `*.pdf` 정렬
2. **PDF별 처리**:
   - **표 사용 시** (`extract_tables=True`): `load_with_tables()` → pdfplumber `find_tables()` + `extract()` → 2D 그리드(None=병합 셀)
   - **표 미사용 시**: `load()` → pypdf로 텍스트만
3. **표 → 청크** (TableExtractor):  
   병합 셀 계산(`_compute_merged_cells`), 선형화(`_linearize_table`), 메타데이터(`header_rows`, `column_names`, `merged_cells`, `linearized`), content=마크다운(또는 HTML)+선형화
4. **figure 사용 시** (`extract_figures=True`):  
   `extract_figures_from_pdf()`(PyMuPDF로 이미지 추출) → `figures_to_chunks()`에서 `figure_model`(blip | openai_vision | deplot)로 설명 생성 → `content_type=figure` 청크
5. **텍스트 청킹**: TextChunker로 페이지 텍스트 → 청크
6. **출력**: 모든 청크를 한 JSONL 파일에 저장. `content_type`: `text` | `table_md` | `table_html` | `figure`

**검증**: `validate_chunks_file()`에서 필수 필드·`content_type` 허용 목록 확인.

---

### 1.3 인덱스 빌드

- **로컬**: `chunks.jsonl` → 임베딩(BGE) + BM25 코퍼스 → FAISS 인덱스 + BM25 + 메타 저장 (`data/index/`)
- **Elastic**: `chunks.jsonl` → 동일 임베딩 + Elasticsearch에 하이브리드 인덱스 생성

인제스트에서 만든 표/figure 청크도 `content` 기준으로 그대로 임베딩·검색에 사용됨.

---

### 1.4 질의 파이프라인 (RAGPipeline.ask)

1. **캐시 조회**: `cache_enabled`이면 `(query, mode, top_k)` 해시로 조회 → hit 시 즉시 반환
2. **쿼리 확장** (선택): `query_expansion_enabled`이고 `query_expansion_num_queries > 1`이면 LLM으로 대체 표현 생성 → `[원문, p1, p2, ...]`
3. **검색**:
   - 확장 시: 각 질의로 `retriever.retrieve(q, top_k*2)` 호출 → `merge_retrieval_results_rrf()`로 RRF 병합 후 상위 `top_k`개
   - 미확장 시: 단일 질의로 `retriever.retrieve(query, top_k)`
4. **리랭크** (옵션): `use_rerank`이면 리랭커로 상위 `rerank_top_k`개만 유지
5. **생성**: `format_qa_prompt(query, docs)`로 프롬프트 조립 → LLM 생성
6. **캐시 저장**: `cache_enabled`이면 응답을 캐시에 저장

캐시 키는 질의 원문·mode·top_k만 사용. 문서/인덱스 갱신 시 캐시는 자동 무효화되지 않으므로, 인제스트·인덱스 재구축 후에는 서비스 재시작 또는 TTL 경과로 자연 무효화됨.

---

### 1.5 일관성·주의점

- **표**: loaders는 `find_tables()`로 병합 셀을 None으로 반환. tables.py에서 rowspan/colspan 계산·메타·선형화까지 일관되게 처리.
- **figure**: blip/openai_vision/deplot 선택 시 모두 `figures_to_chunks` 한 경로로 청크 생성. 인덱스/검색은 content만 사용하므로 동일.
- **캐시**: 동일 질의(공백 정규·소문자)만 캐시 키로 쓰므로, 대소문자만 다른 질의는 별도 캐시 엔트리.
- **쿼리 확장 실패**: LLM 예외 시 원문 하나만으로 검색하도록 fallback.

---

## 2. 처음부터 실행 방법

아래는 **로컬 모드**(BM25+FAISS + OpenAI API) 기준이며, **서버 모드**(Elasticsearch + 외부 vLLM)는 2.7절 참고.

### 2.1 필요 조건

- Docker Desktop 설치 및 실행
- (로컬 모드) OpenAI API 키
- (서버 모드) Elasticsearch 접근 가능, vLLM 서버 URL

### 2.2 환경 설정 (최초 1회)

**Windows (PowerShell, 프로젝트 루트):**

```powershell
.\setup.ps1
```

또는 수동:

```powershell
Copy-Item .env.local.example .env.local
Copy-Item .env.server.example .env.server
```

`.env.local`을 열어 다음을 설정:

- `LLM_API_KEY=sk-proj-...` (실제 OpenAI 키)
- (선택) 캐시/쿼리 확장: `CACHE_ENABLED`, `QUERY_EXPANSION_ENABLED`, `QUERY_EXPANSION_NUM_QUERIES`

### 2.3 Docker 이미지 빌드

```powershell
docker compose build app
```

### 2.4 PDF 넣기

- 질의할 PDF를 `data\raw\`에 둠.
- (선택) 표만 쓰고 figure는 빼려면 인제스트에서 `--figures` 없이 실행.

### 2.5 인제스트 (PDF → 청크)

**기본 (텍스트 + 표, figure 없음):**

```powershell
Copy-Item .env.local .env
docker compose --profile local run --rm app python -m ragapp ingest
```

**표 + figure (BLIP):**

```powershell
Copy-Item .env.local .env
docker compose --profile local run --rm app python -m ragapp ingest --figures --figure-model blip
```

**표 + figure (차트는 DePlot):**

```powershell
Copy-Item .env.local .env
docker compose --profile local run --rm app python -m ragapp ingest --figures --figure-model deplot
```

출력: `data\processed\chunks.jsonl`

### 2.6 로컬 인덱스 빌드

```powershell
Copy-Item .env.local .env
docker compose --profile local run --rm app python -m ragapp index --embedding-model BAAI/bge-small-en-v1.5
```

출력: `data\index\` (FAISS + BM25 등)

### 2.7 RAG 질의

```powershell
Copy-Item .env.local .env
docker compose --profile local run --rm app python -m ragapp ask "문서의 주제가 뭔가요?"
```

리랭크 사용:

```powershell
docker compose --profile local run --rm app python -m ragapp ask "문서의 주제가 뭔가요?" --rerank
```

- 첫 질의: 캐시 미스 → (선택) 쿼리 확장 → 검색 → 리랭크 → 생성 → 캐시 저장.
- 동일 질의 재실행: 캐시 히트 → 즉시 반환.

### 2.8 (선택) 웹 UI

```powershell
Copy-Item .env.local .env
docker compose --profile ui up -d
```

브라우저: http://localhost:8501

---

## 3. 서버 모드 (Elasticsearch + 외부 vLLM) 요약

1. `.env.server`에 `SERVER_LLM_BASE_URL`, `SERVER_LLM_MODEL` 설정.
2. `Copy-Item .env.server .env`
3. `docker compose --profile server up -d` (Elasticsearch + 앱)
4. 인제스트: `docker compose --profile server run --rm app python -m ragapp ingest` (옵션 동일)
5. 인덱스: `docker compose --profile server run --rm app python -m ragapp index-elastic`
6. 질의: `docker compose --profile server run --rm app python -m ragapp ask "질문"` (RETRIEVER_MODE=elastic 사용 시)

자세한 서버 배포는 `docs/WINDOWS.md`, `docs/SERVER_DEPLOYMENT.md` 참고.

---

## 4. 한 번에 보는 순서 (로컬)

| 순서 | 작업 | 명령 예시 |
|------|------|-----------|
| 1 | 환경 설정 | `.\setup.ps1` 후 `.env.local`에 `LLM_API_KEY` 설정 |
| 2 | 빌드 | `docker compose build app` |
| 3 | PDF 배치 | `data\raw\`에 PDF 복사 |
| 4 | 인제스트 | `Copy-Item .env.local .env` 후 `docker compose --profile local run --rm app python -m ragapp ingest` (필요 시 `--figures` 등) |
| 5 | 인덱스 | `docker compose --profile local run --rm app python -m ragapp index --embedding-model BAAI/bge-small-en-v1.5` |
| 6 | 질의 | `docker compose --profile local run --rm app python -m ragapp ask "질문"` |
| 7 | (선택) UI | `docker compose --profile ui up -d` → http://localhost:8501 |

문서 추가 후 재인제스트·인덱스 재구축 시, 캐시는 TTL 경과 또는 앱 재시작 전까지 이전 답을 줄 수 있음.
