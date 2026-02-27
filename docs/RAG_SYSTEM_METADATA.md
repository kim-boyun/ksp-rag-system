# KSP RAG 시스템 메타정보 (전체 사양)

이 문서는 본 RAG 시스템의 모든 단계, 사용 모델, 설정, 데이터 구조를 정리한 메타정보입니다.

---

## 1. 개요

- **시스템명**: KSP RAG System (Knowledge Sharing Program 문서 검색 및 질의응답)
- **실행 모드**: `local` | `server` (환경변수 `MODE`)
- **검색 엔진**: `local` (BM25+FAISS) | `elastic` (Elasticsearch) (환경변수 `RETRIEVER_MODE`)
- **LLM**: `local_api` (OpenAI 호환 API) | `server_http` (vLLM 등 HTTP 엔드포인트)

---

## 2. 인제스트 (Ingest)

### 2.1 입력/출력

| 항목 | 값 |
|------|-----|
| 입력 디렉터리 | `data/raw/` (기본), `*.pdf` |
| 출력 파일 | `data/processed/chunks.jsonl` (JSONL, 한 줄당 청크 1개) |
| CLI | `python -m ragapp ingest` (옵션: `--input`, `--output`, `--tables`, `--figures`, `--figure-model`) |

### 2.2 PDF 로딩

| 항목 | 내용 |
|------|------|
| 텍스트 추출 | **pypdf** (PdfReader), 페이지 단위 `extract_text()` |
| 메타데이터 | PDF 내장 메타데이터 (Title, Author, Subject, Creator) |
| 페이지 범위 단위 | `PAGE_RANGE_SIZE = 50` (대용량 PDF 메모리 절약용, 50페이지씩 로드) |
| 테이블 추출 시 | **pdfplumber** 사용, `find_tables()` 우선, 없으면 `extract_tables()` |

### 2.3 청킹 (Chunking)

| 항목 | 값 |
|------|-----|
| 스플리터 | **LangChain** `RecursiveCharacterTextSplitter` |
| 청크 크기 | `chunk_size = 512` (문자 수, 설정 가능) |
| 청크 오버랩 | `chunk_overlap = 50` (설정 가능) |
| 구분자 순서 | `["\n\n", "\n", ". ", " ", ""]`, `keep_separator=True` |
| 단위 | **페이지 단위** (한 페이지 텍스트를 위 설정으로 분할) |
| 청크 ID 형식 | `{doc_id}_{MD5(base)[:8]}`, base = `{doc_id}_p{page_num}_c{chunk_idx}[suffix]` |

### 2.4 표(Table) 처리

| 항목 | 값 |
|------|-----|
| 추출기 | `TableExtractor` (pdfplumber 테이블 → 2D 그리드) |
| 출력 형식 | `markdown` | `html` (기본: markdown) |
| 헤더 행 수 | `table_header_rows = 1` (선형화/메타데이터용) |
| 청크 메타데이터 | `page_num`, `table_idx`, `merged_cells`, `header_rows`, `column_names`, `linearized` |
| content_type | `table_md` | `table_html` |

### 2.5 차트/이미지(Figure) 처리 (선택)

| 항목 | 값 |
|------|-----|
| 기본 | `EXTRACT_FIGURES=false` (설정 시 `true` 또는 CLI `--figures`) |
| 이미지 추출 | **PyMuPDF (fitz)**, 페이지별 `get_images()` / `extract_image()`, 최소 크기 80x80 픽셀 미만 제외 |
| 설명 생성 모델 | `blip` | `openai_vision` | `deplot` (기본: blip) |
| content_type | `figure` |
| 적용 조건 | 페이지 수 ≤ `PAGE_RANGE_SIZE`(50) 인 PDF만 (스트리밍 모드에서는 대용량 PDF는 figure 스킵) |

### 2.6 청크 스키마 (chunks.jsonl 한 줄)

| 필드 | 타입 | 설명 |
|------|------|------|
| chunk_id | string | 고유 ID (해시 포함) |
| doc_id | string | 문서 ID (기본: PDF 파일명 stem) |
| source_path | string | PDF 절대 경로 |
| page_start | int | 시작 페이지 |
| page_end | int | 끝 페이지 |
| content | string | 청크 본문 |
| content_type | string | `text` \| `table_md` \| `table_html` \| `figure` |
| metadata | object | page_num, chunk_idx, char_count, (표/figure 시 추가 필드) |

---

## 3. 임베딩 (Embedding)

### 3.1 사용 모델

| 용도 | 기본 모델 | 비고 |
|------|-----------|------|
| **Config 기본** (로컬 retriever용) | `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` | config.local_embedding_model |
| **Elasticsearch 인덱싱/검색** | `BAAI/bge-small-en-v1.5` | index-elastic CLI 기본값, 파이프라인은 config.local_embedding_model 사용 (운영에서는 `BAAI/bge-m3` 권장) |
| **로컬 인덱스(FAISS)** | `BAAI/bge-m3` | build_local_index 기본, 다국어 1024차원 |
| **BGE 클래스 기본** | `BAAI/bge-m3` | BGEEmbedding 인자 생략 시 |

### 3.2 BGE 공통 동작

| 항목 | 값 |
|------|-----|
| 라이브러리 | **sentence-transformers** (SentenceTransformer) |
| 쿼리 시 prefix | `"Represent this sentence for searching relevant passages: " + query` |
| 정규화 | `normalize_embeddings=True` (cosine similarity용 L2 정규화) |
| 배치 크기 | 문서 임베딩 시 기본 `batch_size=32` |
| 캐시 | HuggingFace 기본 캐시 (`/root/.cache/huggingface` in Docker) |

### 3.3 차원

- `bge-small-en-v1.5`: 384
- `bge-m3`: 1024
- `paraphrase-multilingual-MiniLM-L12-v2`: 384

### 3.4 bge-small / bge-m3 병행 전략

- **bge-small** (`BAAI/bge-small-en-v1.5`)
  - 장점: 모델 크기 작고 빠름 → 로컬 개발·테스트용, Windows/저사양 환경에서 적합
  - 사용 예:
    - 로컬 인덱스: `ragapp index --embedding-model BAAI/bge-small-en-v1.5`
    - ES 인덱스: `ragapp index-elastic --model BAAI/bge-small-en-v1.5`
- **bge-m3** (`BAAI/bge-m3`)
  - 장점: 1024차원, 다국어·정확도 우선 시 적합 → 운영/지식 허브용 권장
  - 사용 예:
    - 로컬 인덱스: `ragapp index --embedding-model BAAI/bge-m3`
    - ES 인덱스: `ragapp index-elastic --model BAAI/bge-m3`
- **중요**: 하나의 인덱스(FAISS/Elasticsearch) 안에서는 **인덱싱 시점의 임베딩 모델과 검색 시점의 임베딩 모델이 동일해야** 함  
  - 384차원(bge-small)로 만든 인덱스에는 384차원 모델만, 1024차원(bge-m3) 인덱스에는 1024차원 모델만 사용 가능

---

## 4. 인덱싱 (Indexing)

### 4.1 Elasticsearch 인덱스

| 항목 | 값 |
|------|-----|
| 인덱스 이름 | `ksp_rag_index` (설정 가능) |
| 스트리밍 배치 | `INDEX_BATCH_SIZE = 10_000` (한 번에 읽고 임베딩 후 bulk 인덱싱) |
| 임베딩 배치 | 기본 32 |
| 재생성 | `index-elastic --recreate` 시 기존 인덱스 삭제 후 재생성 |
| 재개 | recreate 없이 실행 시 이미 인덱스된 chunk_id는 스킵 |

**매핑 요약**

| 필드 | 타입 | 설명 |
|------|------|------|
| content | text | standard analyzer |
| embedding | dense_vector | dims=임베딩 차원, similarity=cosine, index=true |
| metadata | object | enabled (doc_id, source_path, page_num 등 저장) |
| chunk_id | keyword |

**_id**: chunk_id가 512바이트 이하면 그대로, 초과 시 SHA256 해시 사용.

### 4.2 로컬 인덱스 (BM25 + FAISS)

| 항목 | 값 |
|------|-----|
| 출력 디렉터리 | `data/index/` (기본) |
| FAISS 인덱스 | `IndexFlatIP` (내적 = 코사인, 정규화된 벡터 가정) |
| BM25 | **rank_bm25** BM25Okapi, 토큰화: `text.lower().split()` |
| 저장 파일 | `faiss.index`, `bm25.pkl`, `chunks.jsonl`, `metadata.json` |

---

## 5. 검색 (Retrieval)

### 5.1 Elasticsearch (Hybrid)

| 항목 | 값 |
|------|-----|
| BM25 | `content` 필드에 `match` 쿼리, boost=1.0 |
| Dense | `cosineSimilarity(params.query_vector, 'embedding') + 1.0` (script_score) |
| 결합 | bool `should` (BM25 + Dense) → Elasticsearch가 스코어 결합 |
| 반환 개수 | `top_k` (설정 기본 5, .env 예시 12) |
| 쿼리 임베딩 | 위 BGE 쿼리 prefix 적용 |

### 5.2 로컬 (BM25 + FAISS + RRF)

| 항목 | 값 |
|------|-----|
| RRF 상수 k | 60 |
| BM25/FAISS 각각 상위 `top_k * 2` 취한 뒤 RRF로 병합 후 상위 `top_k` 반환 |

### 5.3 쿼리 확장 (선택)

| 항목 | 값 |
|------|-----|
| 설정 | `QUERY_EXPANSION_ENABLED`, `QUERY_EXPANSION_NUM_QUERIES` (기본 3) |
| 동작 | LLM으로 질문 변형 2개 추가 생성 → 3개 질의로 각각 검색 → RRF(k=60)로 병합 후 상위 `top_k` |

---

## 6. 리랭킹 (Reranking, 선택)

| 항목 | 값 |
|------|-----|
| 구현 | **LLMReranker** (OpenAI API) |
| 동작 | 문서별로 “질문–문서 관련도 0–100 점수” 요청 → 점수로 정렬 후 상위 `rerank_top_k` 반환 |
| 기본 상위 개수 | `rerank_top_k = 3` (config), .env 예시 5 |
| 스코어 정규화 | 0–100 → 0.0–1.0, 실패/파싱 실패 시 0.5 |

---

## 7. LLM (답변 생성)

### 7.1 로컬 API (local_api)

| 항목 | 값 |
|------|-----|
| 클라이언트 | **openai** (OpenAI Python) |
| 설정 | LLM_API_KEY, LLM_MODEL (예: gpt-3.5-turbo), LLM_TEMPERATURE (기본 0.7), LLM_MAX_TOKENS (기본 1000) |
| 호출 | chat completion (user 메시지 1개) |

### 7.2 서버 HTTP (server_http)

| 항목 | 값 |
|------|-----|
| 엔드포인트 | `SERVER_LLM_BASE_URL` + `/v1/completions` (또는 chat) |
| 모델 | `SERVER_LLM_MODEL` (예: openai/gpt-oss-120b) |
| 용도 | vLLM 등 OpenAI 호환 HTTP 서버 |

---

## 8. 프롬프트

### 8.1 QA 프롬프트 (qa.txt)

- 플레이스홀더: `{context}`, `{question}`
- 지침: 문서 근거만 사용, 출처 명시 `[출처: 문서 ID {doc_num}]`, 근거 부족 시 “제공된 문서에서 관련 정보를 찾을 수 없습니다” 등, 질문과 같은 언어로 답변.

### 8.2 시스템 프롬프트 (system.txt)

- 역할: 문서 기반 질의응답 전문가.
- 원칙: 문서 내용만 근거, 추측 금지, 출처(문서명, 페이지) 명시, 언어 일치.

### 8.3 컨텍스트 포맷 (format_qa_prompt)

- 각 문서: `[문서 i]\n출처: {doc_id}\n페이지: {page}\n청크 ID: {chunk_id}\n유형: {content_type}\n내용:\n{content}`

### 8.4 인용 추출 (extract_citations)

- 정규식: `\[출처:.*?문서\s*(\d+).*?\]` → 문서 번호 매칭 후 해당 retrieved_doc 메타데이터로 출처 정보 구성.

---

## 9. 캐시

| 항목 | 값 |
|------|-----|
| 사용 여부 | `CACHE_ENABLED` (기본 true) |
| TTL | `CACHE_TTL_SECONDS` (기본 3600) |
| 크기 | `CACHE_MAX_SIZE` (기본 1000, LRU) |
| 캐시 키 | `hash(query.strip().lower() \| mode \| top_k)` |

---

## 10. 파이프라인 흐름 (ask 한 번 호출 시)

1. **캐시 조회** (활성화 시) → hit 시 즉시 반환.
2. **쿼리 확장** (활성화 시) → LLM으로 변형 질의 생성 → 다중 검색 후 RRF 병합.
3. **검색** → Retriever (Elastic 또는 Local) → `top_k` (또는 확장 시 `top_k*2` 후 RRF로 `top_k`) 문서 반환.
4. **리랭킹** (옵션) → Reranker로 상위 `rerank_top_k`만 유지.
5. **프롬프트 생성** → `format_qa_prompt(question, documents)`.
6. **생성** → LLM.generate(prompt).
7. **캐시 저장** (활성화 시).
8. **인용 파싱** → 답변 텍스트에서 `[출처: 문서 N]` 추출 후 retrieved_docs와 매핑.

---

## 11. 설정 요약 (환경 변수)

| 변수 | 기본값(또는 예시) | 설명 |
|------|-------------------|------|
| MODE | local | local / server |
| RETRIEVER_MODE | local | local / elastic |
| CHUNK_SIZE | 512 | 청크 문자 수 |
| CHUNK_OVERLAP | 50 | 오버랩 문자 수 |
| TOP_K | 5 (예시 12) | 검색 상위 개수 |
| RERANK_TOP_K | 3 (예시 5) | 리랭크 후 상위 개수 |
| LLM_PROVIDER | local_api | local_api / server_http |
| LLM_MODEL | gpt-3.5-turbo | 로컬 LLM 모델 |
| LLM_TEMPERATURE | 0.7 | 생성 온도 |
| LLM_MAX_TOKENS | 1000 | 최대 토큰 |
| ELASTIC_HOST | elasticsearch | ES 호스트 |
| ELASTIC_PORT | 9200 | ES 포트 |
| ELASTIC_INDEX_NAME | ksp_rag_index | 인덱스 이름 |
| SERVER_LLM_BASE_URL | http://172.16.0.52:8000 | 서버 LLM URL |
| SERVER_LLM_MODEL | openai/gpt-oss-120b | 서버 LLM 모델 |
| local_embedding_model | paraphrase-multilingual-MiniLM-L12-v2 | config 기본 (Elastic 파이프라인에서도 사용) |
| EXTRACT_FIGURES | false | figure 추출 여부 |
| QUERY_EXPANSION_ENABLED | true | 쿼리 확장 사용 여부 |
| QUERY_EXPANSION_NUM_QUERIES | 3 | 원본 포함 질의 개수 |

---

## 12. 인프라/버전

| 항목 | 값 |
|------|-----|
| Python | 3.11 |
| Elasticsearch | 8.12.0 (Docker 이미지) |
| Kibana | 8.12.0 (선택) |
| Docker | compose v2, profile: local / server / ui / app-only |
| 임베딩 캐시 볼륨 | model-cache (/root/.cache/huggingface) |
| Elastic 데이터 볼륨 | elastic-data |

---

## 13. 주의사항 (모델 일치)

- **Elasticsearch**: 인덱스는 `index-elastic` 시 지정한 **임베딩 모델**로 만들어짐 (CLI 기본 `BAAI/bge-small-en-v1.5`). 검색 시 파이프라인은 **config의 local_embedding_model**을 사용하므로, 인덱스 빌드 시와 동일한 모델을 config에 두는 것이 안전함.
- **로컬 인덱스**: `data/index`의 metadata에 저장된 `embedding_model`로 검색 시 로드함 (기본 BAAI/bge-m3).

이 문서는 코드베이스 기준으로 작성되었으며, 실제 동작은 `.env` 및 CLI 인자에 따라 달라질 수 있습니다.
