# 🚀 KSP RAG System

Docker 기반 하이브리드 RAG 시스템 (로컬/서버 모드 지원)

## 📌 주요 특징

- ✅ **완전한 Docker 환경**: 로컬에 Python 설치 불필요
- ✅ **듀얼 모드**: 로컬(개발) ↔ 서버(운영) 프로파일 전환
- ✅ **하이브리드 검색**: BM25 + FAISS (로컬) / Elasticsearch (서버)
- ✅ **유연한 LLM**: OpenAI API (로컬) / vLLM (서버)
- ✅ **인터페이스 기반**: Protocol을 사용한 확장 가능한 설계

## 🏗️ 아키텍처

```
로컬 모드 (Mac 개발)          서버 모드 (Ubuntu GPU)
├─ BM25 + FAISS             ├─ Elasticsearch (하이브리드)
├─ 로컬 임베딩 모델            ├─ GPU 임베딩 모델
└─ OpenAI API               └─ vLLM HTTP endpoint
```

## 🚀 빠른 시작 (로컬 개발)

### 0단계: 환경 설정

```bash
# 자동 설정 스크립트 실행
make setup

# 또는 수동으로
cp .env.local.example .env.local
cp .env.server.example .env.server
```

그런 다음 **`.env.local` 파일을 열어서 실제 API 키를 입력**하세요:

```bash
# .env.local 파일 편집
LLM_API_KEY=sk-proj-your-actual-openai-key-here  # ← 실제 키 입력
```

### 1단계: Docker 빌드

```bash
make build
```

**예상 시간**: 5-10분 (최초 빌드 시)

### 2단계: 데이터 인제스트

```bash
# PDF 파일을 data/raw/에 배치
# 그런 다음 인제스트 실행
make ingest
```

**출력**: `data/processed/chunks.jsonl` (1800+ chunks)

### 3단계: 로컬 인덱스 빌드

```bash
# 작은 모델로 빠르게 빌드
make index-small
```

**출력**: `data/index/` (BM25 + FAISS)

### 4단계: RAG 질의 테스트

```bash
# CLI로 질문
make ask-local Q="What is the main topic?"
```

**예상 출력**:
```
💬 Answer:
The document discusses... [출처: 문서 1, 문서 2]

📚 Citations:
• 문서 1: report.pdf (페이지: 45)
• 문서 2: summary.pdf (페이지: 12)
```

### 5단계: 웹 UI 실행

```bash
make ui-local
```

**브라우저**: http://localhost:8501

### 6단계: 스모크 테스트

```bash
make smoke-test
```

**테스트**: Ingest → Retrieve → Ask

## 📖 사용법

### CLI 명령어

#### 문서 인덱싱

```bash
# PDF 인제스트 (기본: data/raw → data/processed/chunks.jsonl)
make ingest

# 표 포함 인제스트
make ingest-tables

# 커스텀 경로
docker compose --profile local run --rm app python -m ragapp ingest \
  --input data/raw \
  --output data/processed/chunks.jsonl

# 도움말
docker compose --profile local run --rm app python -m ragapp ingest --help
```

#### RAG 질의

```bash
# 질문하기 (로컬 모드)
make ask Q="RAG란 무엇인가요?"

# 질문하기 (서버 모드)
make ask-server Q="RAG란 무엇인가요?"

# 설정 확인 (로컬)
make config-local

# 설정 확인 (서버)
make config-server

# 버전 확인
make version

# 도움말
docker compose --profile local run --rm app python -m ragapp --help
```

### 개발 & 테스트

```bash
# 테스트 실행
make test

# 커버리지 포함 테스트
make test-cov

# 컨테이너 접속
make shell
```

### Docker Compose 직접 사용

```bash
# 로컬 모드 (placeholder 동작)
docker compose --profile local run --rm app python -m ragapp ask "hello"

# 서버 모드 (Elasticsearch + vLLM)
docker compose --profile server up -d
docker compose --profile server run --rm -e MODE=server app python -m ragapp ask "hello"
```

## 📂 프로젝트 구조

```
ksp-rag-system/
├── src/ragapp/
│   ├── __init__.py
│   ├── __main__.py          # Entry point (python -m ragapp)
│   ├── config.py            # pydantic-settings 설정
│   ├── cli.py               # Typer CLI 인터페이스
│   ├── ingest/              # 📥 문서 인제스트 파이프라인
│   │   ├── __init__.py
│   │   ├── loaders.py       # PDF 로더 (pypdf, pdfplumber)
│   │   ├── chunkers.py      # 텍스트 청킹
│   │   ├── tables.py        # 표 추출 및 변환
│   │   └── run_ingest.py    # 메인 파이프라인
│   └── pipeline/
│       ├── types.py         # Protocol 인터페이스
│       └── rag_pipeline.py  # RAG 파이프라인 오케스트레이터
├── tests/
│   ├── test_basic.py        # 기본 환경 테스트
│   ├── test_config.py       # 설정 테스트
│   ├── test_pipeline.py     # 파이프라인 테스트
│   └── test_ingest.py       # 인제스트 테스트
├── data/
│   ├── raw/                 # 원본 PDF 문서
│   └── processed/           # 처리된 chunks.jsonl
├── models/                  # 임베딩 모델 캐시 (추후)
├── scripts/
│   └── create_sample_pdf.py # 샘플 PDF 생성기
├── docker-compose.yml       # Docker Compose (profiles: local, server)
├── Dockerfile               # Multi-stage 빌드
├── pyproject.toml           # Poetry 의존성
├── Makefile                 # 명령어 단축키
├── .env.local.example       # 로컬 모드 설정 템플릿
├── .env.server.example      # 서버 모드 설정 템플릿
├── .env.local               # 로컬 설정 (git ignore, 직접 생성)
├── .env.server              # 서버 설정 (git ignore, 직접 생성)
└── setup.sh                 # 환경 설정 스크립트
```

## 🔧 기술 스택

- **언어**: Python 3.11
- **패키지 관리**: Poetry
- **프레임워크**: Pydantic, Typer, Rich
- **검색**: BM25, FAISS, Elasticsearch (예정)
- **LLM**: OpenAI API, vLLM (예정)
- **인프라**: Docker, Docker Compose

## 🎯 완료 기준

### 1단계: Docker 기반 레포 골격 ✅

- [x] `make build` 성공
- [x] `docker compose run --rm app python -m ragapp --help` 동작
- [x] `docker compose run --rm app python -m ragapp ask "hello"` placeholder 답변 출력
- [x] `make test` pytest 통과 (3개 이상)
- [x] 로컬/서버 모드 설정 분리 (.env.local, .env.server)
- [x] Protocol 기반 인터페이스 정의 (Retriever, Reranker, LLMClient)
- [x] Makefile 명령어 제공

### 2단계: PDF Ingest 파이프라인 ✅

- [x] PDF 텍스트 추출 (pypdf, pdfplumber)
- [x] 텍스트 청킹 (LangChain TextSplitter)
- [x] 표 추출 및 Markdown/HTML 변환
- [x] Chunk 스키마 (chunk_id, doc_id, source_path, page_start, page_end, content, content_type, metadata)
- [x] CLI 명령어: `python -m ragapp ingest`
- [x] JSONL 출력: `data/processed/chunks.jsonl`
- [x] pytest 테스트 (스키마 검증)

## 📝 사용 예시

### 1. PDF 문서 인덱싱

```bash
# 0. 샘플 PDF 생성 (테스트용)
make create-sample

# 1. PDF 파일을 data/raw/ 폴더에 넣기
cp your-document.pdf data/raw/

# 2. 인제스트 실행
make ingest

# 3. 결과 확인
cat data/processed/chunks.jsonl | head -n 1 | jq
```

**출력 예시**:
```json
{
  "chunk_id": "mydoc_a3b5c1d2",
  "doc_id": "mydoc",
  "source_path": "/app/data/raw/mydoc.pdf",
  "page_start": 1,
  "page_end": 1,
  "content": "RAG (Retrieval-Augmented Generation)는...",
  "content_type": "text",
  "metadata": {
    "chunk_idx": 0,
    "page_num": 1,
    "char_count": 487
  }
}
```

### 2. 표 추출 예시

```bash
# 표 포함 인제스트
make ingest-tables
```

**표 청크 예시** (Markdown):
```json
{
  "chunk_id": "report_table_p5_t0",
  "doc_id": "report",
  "source_path": "/app/data/raw/report.pdf",
  "page_start": 5,
  "page_end": 5,
  "content": "| Name | Score | Rank |\n| --- | --- | --- |\n| Alice | 95 | 1 |\n| Bob | 87 | 2 |",
  "content_type": "table_md",
  "metadata": {
    "table_idx": 0,
    "page_num": 5,
    "num_rows": 3,
    "num_cols": 3
  }
}
```

## 📋 구현 현황

### ✅ Stage 1-8: 완전한 로컬/서버 RAG 시스템 완성
- [x] Docker 기반 개발 환경
- [x] PDF 인제스트 (텍스트 + 테이블 추출)
- [x] 하이브리드 검색 (BM25 + FAISS + RRF)
- [x] BGE 임베딩 (BAAI/bge-m3, BAAI/bge-small-en-v1.5)
- [x] LLM 리랭킹 (OpenAI API)
- [x] LLM 생성 (OpenAI API, vLLM 지원)
- [x] 인용 추출 및 표시
- [x] E2E 테스트
- [x] 완전한 CLI 인터페이스
- [x] **Elasticsearch 서버 모드** (Stage 7 완료)
  - [x] docker-compose에 Elasticsearch 추가
  - [x] Kibana UI (선택)
  - [x] 하이브리드 인덱스 구현 (BM25 + Dense Vector)
  - [x] RETRIEVER_MODE 전환 (local/elastic)
- [x] **Elasticsearch 통합** (Stage 8 완료)
  - [x] RAG Pipeline 통합
  - [x] 자동 모드 전환 (`retriever_mode`)
  - [x] CLI 명령어 확장 (`--mode elastic`)
  - [x] E2E 검증 완료
- [x] **GPU 서버 LLM 컨테이너** (Stage 9 완료)
  - [x] vLLM OpenAI 호환 서버
  - [x] GPU 설정 (nvidia runtime)
  - [x] 로컬/서버 모드 분리
  - [x] 헬스체크 & 테스트
- [x] **Streamlit 웹 UI** (Stage 10 완료)
  - [x] 웹 인터페이스 (포트 8501)
  - [x] 질문 → 답변 + 인용 표시
  - [x] 접기/펼치기 UI
  - [x] 로컬/서버 모드 지원
  - [x] 리랭킹 옵션
  - [x] 히스토리 추적

### ✅ 시스템 완성!

**완전한 RAG 시스템 운영 준비 완료**

---

## 🔄 서버 모드 (Elasticsearch)

### Elasticsearch 시작

```bash
# Elasticsearch 컨테이너 시작
make elastic-up

# 헬스체크 (30초 후)
make elastic-health
```

**예상 출력**:
```json
{
  "cluster_name" : "docker-cluster",
  "status" : "green",
  "number_of_nodes" : 1
}
```

### 인덱스 빌드

```bash
# 1) 문서 인제스트 (로컬과 동일)
make ingest

# 2) Elasticsearch 인덱스 생성
make index-elastic

# 또는 재생성
make index-elastic-recreate
```

### 검색 테스트

```bash
# Elasticsearch 기반 검색
make retrieve-elastic Q="온두라스 연금"

# 리랭크 포함
make retrieve-elastic-rerank Q="온두라스 연금 개혁"

# RAG (질문 + 답변)
make ask-elastic Q="온두라스 연금 시스템의 주요 특징은?"
```

### Kibana UI (선택)

```bash
# Kibana 시작
make kibana-up

# 브라우저 접속: http://localhost:5601
```

### Elasticsearch 관리

```bash
# 상태 확인
docker compose ps

# 로그 확인
make elastic-logs

# 중지
make elastic-down

# 인덱스 재생성
make index-elastic-recreate
```

**자세한 가이드**: [docs/ELASTICSEARCH_GUIDE.md](docs/ELASTICSEARCH_GUIDE.md)

---

## 🤖 GPU 서버 LLM 모드

### LLM 컨테이너 시작 (GPU 필요)

```bash
# 전제: Ubuntu GPU 서버 + nvidia-docker2

# LLM 서비스 시작
make llm-up

# 헬스체크 (모델 로딩 5-10분 대기)
make llm-health

# 테스트 요청
make llm-test
```

### RAG with Server LLM

```bash
# .env.server 설정
LLM_PROVIDER=server_http
SERVER_LLM_ENDPOINT=http://llm:8000/v1/completions

# 전체 서버 스택 시작
docker compose --profile server up -d

# RAG 실행
docker compose --profile server run --rm app python -m ragapp ask "질문"
```

**자세한 가이드**: [docs/STAGE9_COMPLETION.md](docs/STAGE9_COMPLETION.md)

---

## 🎨 Streamlit 웹 UI

### UI 시작

```bash
# 로컬 모드 (인덱스 준비 필요)
make ingest
make index-small
make ui-local

# 브라우저 접속
# http://localhost:8501
```

### 서버 모드

```bash
# Elasticsearch 인덱스 준비
make elastic-up
make ingest
make index-elastic

# UI 시작
make ui-server

# 브라우저 접속
# http://localhost:8501
```

### UI 기능
- ✅ 질문 입력 + 예시 질문 버튼
- ✅ 답변 + 인용 표시
- ✅ 검색 문서 접기/펼치기
- ✅ 리랭킹 옵션 (사이드바)
- ✅ 히스토리 추적
- ✅ 메타데이터 표시

**자세한 가이드**: [docs/STAGE10_COMPLETION.md](docs/STAGE10_COMPLETION.md)

---

## 🚀 GPU 서버 배포

### 빠른 배포 절차

**목표**: Mac 로컬에서 Ubuntu GPU 서버로 완전 이식

```bash
# 1. 저장소 클론
git clone <repository-url>
cd ksp-rag-system

# 2. 기존 서비스 확인 (Elastic/LLM이 이미 있는지)
make check-server

# 3. 환경 설정 (check-server 결과 참고)
cp .env.server.example .env.server
# .env.server 편집 - 기존 서비스 있으면 host.docker.internal 사용

# 4. Docker 빌드
make build

# 5. 서버 서비스 시작
# 기존 Elastic/LLM 없음 → make up-server
# 기존 Elastic/LLM 있음 → make up-server-app-only

# 6. 데이터 인제스트
make ingest

# 7. Elasticsearch 인덱스 빌드
make index-elastic

# 8. 스모크 테스트
make smoke-test

# 9. UI 시작
make ui-server  # 또는 make up-server-app-only 이미 했다면 생략

# 10. 브라우저 접속
# http://<server-ip>:8501
```

### 스모크 테스트

최소 3가지 핵심 기능 자동 검증:

```bash
make smoke-test
```

**테스트 항목**:
1. ✅ **Ingest**: PDF → chunks.jsonl
2. ✅ **Retrieve**: Elasticsearch 검색
3. ✅ **Ask**: RAG 질의응답

### 주요 명령어 요약

| 명령어 | 설명 |
|--------|------|
| `make build` | Docker 이미지 빌드 |
| `make up-server` | 서버 모드 시작 (Elastic+LLM) |
| `make ingest` | PDF 인제스트 |
| `make index-local` | 로컬 인덱스 빌드 |
| `make index-elastic` | Elasticsearch 인덱스 빌드 |
| `make ask-local Q="질문"` | 로컬 RAG 질의 |
| `make ask-elastic Q="질문"` | Elasticsearch RAG 질의 |
| `make ui-local` | 로컬 UI 시작 |
| `make ui-server` | 서버 UI 시작 |
| `make smoke-test` | 스모크 테스트 |

### 상세 배포 가이드

**완전한 배포 절차**: [docs/SERVER_DEPLOYMENT.md](docs/SERVER_DEPLOYMENT.md)

**포함 내용**:
- NVIDIA Container Toolkit 설치
- 환경 설정 상세
- 서비스 시작 및 헬스체크
- 인덱스 빌드 및 검증
- 성능 모니터링
- 트러블슈팅

---

## 📄 라이선스

MIT License
