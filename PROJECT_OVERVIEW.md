# KSP RAG System — 프로젝트 총정리

Docker 기반 하이브리드 RAG(Retrieval-Augmented Generation) 시스템.  
로컬(개발) / 서버(운영) 이원화, Elasticsearch + BGE 임베딩, OpenAI API / vLLM 지원.

---

## 1. 한눈에 보기

| 항목 | 내용 |
|------|------|
| **목적** | PDF 등 문서 검색 + 질의응답 (Knowledge Hub) |
| **실행** | Docker Compose, Makefile 주 사용 |
| **검색** | Elasticsearch (BM25 + Dense Vector) 또는 로컬(BM25 + FAISS) |
| **임베딩** | BGE (bge-small 384차원 / bge-m3 1024차원) |
| **LLM** | 로컬: OpenAI API / 서버: 외부 vLLM (예: openai/gpt-oss-120b) |
| **UI** | Streamlit (8501) |

---

## 2. 아키텍처

- **운영 서버 (이 레포)**: Elasticsearch(9200) + RAG App + Streamlit(8501) + 인덱싱/임베딩(BGE)
- **GPU 서버 (별도)**: vLLM(8000) — OpenAI 호환 API만 제공 (`ops/gpu/`)

로컬 모드에서는 Elasticsearch + 개인 LLM(OpenAI API) 조합으로 개발/테스트.

상세: [docs/architecture/overview.md](docs/architecture/overview.md)

---

## 3. 디렉터리 구조

```
ksp-rag-system/
├── src/ragapp/              # RAG 앱 소스
│   ├── config.py            # pydantic-settings (.env 로드)
│   ├── cli.py               # Typer CLI (ingest, index, ask, health 등)
│   ├── ingest/              # PDF → chunks.jsonl (로더, 청킹, 표/이미지)
│   ├── index/               # Elasticsearch/로컬 인덱스 빌드
│   ├── embeddings/          # BGE 임베딩 (bge.py)
│   ├── retrievers/          # Elasticsearch / 로컬 하이브리드
│   ├── rerankers/           # LLM 리랭커
│   ├── pipeline/            # RAG 파이프라인, 쿼리 확장, RRF
│   ├── prompts/             # QA/시스템 프롬프트
│   └── llms/                # local_api, server_http
├── src/ui/                  # Streamlit 앱 (app.py)
├── tests/
├── data/                    # raw(PDF), processed(chunks.jsonl); gitignore
├── docs/                    # 문서 (가이드, 메타데이터, 아키텍처)
├── ops/gpu/                 # GPU 서버용 docker-compose, .env.gpu
├── docker-compose.yml       # profiles: local, server, ui
├── Dockerfile
├── Makefile                 # make up-server, ingest, index-elastic, ask 등
├── .env.local.example      # 로컬용 템플릿
├── .env.server.example      # 서버용 템플릿
└── pyproject.toml / poetry
```

---

## 4. 환경 변수 파일

| 파일 | 용도 | Git |
|------|------|-----|
| `.env` | 런타임 (Make가 .env.local 또는 .env.server 복사) | ignore |
| `.env.local` | 로컬 개발 (Elastic + OpenAI API) | ignore |
| `.env.server` | 서버 운영 (Elastic + vLLM) | ignore |
| `.env.local.example` | 로컬 템플릿 | 커밋 |
| `.env.server.example` | 서버 템플릿 | 커밋 |

주요 설정: `MODE`, `RETRIEVER_MODE`, `ELASTIC_INDEX_NAME`, `LOCAL_EMBEDDING_MODEL`, `LLM_PROVIDER`, `SERVER_LLM_BASE_URL`, `SERVER_LLM_MODEL`.  
상세: [docs/ENV_FILES_GUIDE.md](docs/ENV_FILES_GUIDE.md)

---

## 5. 임베딩 / 인덱스

- **bge-small** (384차원): 가볍고 빠름 — 테스트·로컬용. `make index-elastic-small` 등.
- **bge-m3** (1024차원): 다국어·고품질 — 운영 권장. 인덱스명 예: `ksp_rag_index` 또는 `ksp_rag_index_m3`.
- **규칙**: 인덱스 빌드 시 사용한 모델과 검색 시 `LOCAL_EMBEDDING_MODEL`이 동일해야 함.

m3 인덱스 실행·확인: [docs/RUN_WITH_M3_INDEX.md](docs/RUN_WITH_M3_INDEX.md)

---

## 6. LLM

- **로컬**: `LLM_PROVIDER=local_api`, `LLM_API_KEY`, `LLM_MODEL` (예: gpt-3.5-turbo).
- **서버**: `LLM_PROVIDER=server_http`, `SERVER_LLM_BASE_URL`, `SERVER_LLM_MODEL` (예: openai/gpt-oss-120b).

전환: [docs/LLM_SWITCHING_GUIDE.md](docs/LLM_SWITCHING_GUIDE.md)

---

## 7. 검색 / RRF

- **Elasticsearch**: BM25 + script_score(dense, cosineSimilarity). `ELASTIC_BM25_BOOST`, `ELASTIC_DENSE_BOOST`, `RETRIEVAL_MIN_SCORE`.
- **쿼리 확장**: 여러 질의로 검색 후 **RRF(k=60)** 로 병합.  
  RRF 점수: `score = Σ 1/(k + rank)`, k=60, rank는 각 run 내 순위(1부터).
- 참고문서 점수: 쿼리 확장 시 RRF 점수, 미사용 시 ES 원점수; 리랭크 사용 시 0–1 정규화된 LLM 관련도.

---

## 8. 주요 Makefile 명령

| 명령 | 설명 |
|------|------|
| `make setup` | .env 예시 복사 등 초기 설정 |
| `make build` | Docker 이미지 빌드 |
| `make elastic-up` | Elasticsearch 기동 |
| `make elastic-health` | ES 헬스체크 |
| `make elastic-export` | ES 데이터 tar 백업 |
| `make elastic-import` | tar로 ES 데이터 복원 |
| `make ingest` | PDF → chunks.jsonl |
| `make index-elastic` | Elasticsearch 인덱스 빌드 (기본 bge-m3) |
| `make index-elastic-small` | bge-small로 ES 인덱스 빌드 |
| `make ask Q="..."` | RAG 질의 (현재 .env 기준) |
| `make ask-server Q="..."` | 서버 모드 질의 |
| `make ui-server` | Streamlit 서버 모드 (8501) |
| `make llm-health` | 외부 vLLM 헬스체크 |
| `make smoke-test` | Ingest → Retrieve → Ask 스모크 테스트 |

---

## 9. 문서 인덱스 (docs/)

모든 가이드·메타데이터는 ** [docs/README.md](docs/README.md) ** 에 정리되어 있습니다.

- 배포·운영: SERVER_DEPLOYMENT, ELASTICSEARCH_GUIDE, RUN_WITH_M3_INDEX, GUIDE_ELASTIC_LOCAL_FULL, SETUP_MAC_FROM_SCRATCH  
- 사용: LOGIC_AND_QUICKSTART, WINDOWS, ENV_FILES_GUIDE, LLM_SWITCHING_GUIDE, NETWORK_ACCESS_GUIDE  
- 사양·아키텍처: RAG_SYSTEM_METADATA, architecture/overview  
- 기타: RAG_고도화_방안_총정리, archive/

---

## 10. 기술 스택

- Python 3.11, Poetry, Pydantic, Typer, Rich  
- Elasticsearch 8.x, sentence-transformers(BGE), FAISS, BM25  
- OpenAI API, vLLM(별도 서버)  
- Docker, Docker Compose, Streamlit  

---

## 11. 빠른 시작 (서버 모드)

```bash
cp .env.server.example .env.server
# .env.server: ELASTIC_INDEX_NAME, LOCAL_EMBEDDING_MODEL, SERVER_LLM_BASE_URL 등 수정
make build
make elastic-up && make elastic-health
make ingest && make index-elastic   # 또는 백업 복원 후 make elastic-import
make ui-server
# http://localhost:8501
```

이 문서는 레포 전체를 한곳에 요약한 것입니다. 상세 절차는 [README.md](README.md)와 [docs/README.md](docs/README.md)를 참고하세요.
