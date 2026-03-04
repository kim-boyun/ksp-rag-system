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
로컬 모드 (Mac 개발)          운영 서버 (이 레포)          GPU 서버 (별도)
├─ BM25 + FAISS             ├─ Elasticsearch            ├─ vLLM
├─ 로컬 임베딩 모델            ├─ RAG App                 └─ OpenAI-compatible API
└─ OpenAI API               ├─ Streamlit UI
                            └─ 인덱싱/임베딩
```

**역할 분리**:
- **운영 서버 (이 레포)**: Elasticsearch + RAG app + Streamlit + 인덱싱/임베딩
- **GPU 서버 (별도)**: vLLM inference API만 제공 (`ops/gpu/docker-compose.yml`)

**자세한 아키텍처**: [docs/architecture/overview.md](docs/architecture/overview.md)  
**프로젝트 전체 총정리**: [PROJECT_OVERVIEW.md](PROJECT_OVERVIEW.md) · **문서 인덱스**: [docs/README.md](docs/README.md)

---

## 📐 Deployment Topology

### 시스템 구성

KSP RAG System은 **역할 분리 아키텍처**를 채택합니다:

```
┌─────────────────────────────────┐         ┌─────────────────────────────────┐
│      운영 서버 (App Server)      │         │      GPU 서버 (별도 서버)        │
│      (이 레포지토리)              │         │      (ops/gpu/docker-compose.yml) │
├─────────────────────────────────┤         ├─────────────────────────────────┤
│                                  │         │                                  │
│  • Elasticsearch (9200)          │         │  • vLLM API (8000)              │
│  • RAG App (Python)              │  HTTP   │  • OpenAI-compatible            │
│  • Streamlit UI (8501)           │  ────>  │  • GPU 추론 전용                │
│  • 인덱싱/임베딩 (BGE)            │         │                                  │
│                                  │         │                                  │
└─────────────────────────────────┘         └─────────────────────────────────┘
```

### 왜 이렇게 분리하는가?

1. **비용 최적화**: GPU 서버는 추론 시에만 사용 → 유휴 시간 비용 절감, 운영 서버는 CPU 기반으로 충분
2. **운영 편의성**: 각 서버의 독립적인 스케일링 및 업데이트 가능, GPU 서버 장애 시 운영 서버는 계속 동작
3. **성능 최적화**: GPU 서버는 추론에만 집중 → 최대 처리량 확보, 운영 서버는 검색/인덱싱에 집중 → 응답 시간 단축

### 운영 서버 배포 절차

**위치**: 이 레포지토리

**필요 사항**:
- Docker & Docker Compose
- 최소 4GB RAM (Elasticsearch용)
- GPU 불필요

**배포 단계**:

```bash
# 1. 저장소 클론
git clone <repo-url>
cd ksp-rag-system

# 2. 환경 변수 설정
cp .env.server.example .env.server
vim .env.server  # SERVER_LLM_BASE_URL 설정

# 3. 서비스 시작
make up-server  # Elasticsearch + App 시작

# 4. 인덱싱
make index-elastic

# 5. UI 시작 (선택)
make ui-server  # http://localhost:8501
```

**포트**:
- `9200`: Elasticsearch (내부)
- `8501`: Streamlit UI (외부 접근 가능)

**방화벽 규칙**:
- 인바운드: 8501 (Streamlit UI)
- 아웃바운드: GPU 서버 8000 포트 접근 필요

### GPU 서버 배포 절차

**위치**: 별도 서버 (Ubuntu 권장)

**필요 사항**:
- Docker & Docker Compose
- NVIDIA GPU (CUDA 지원)
- NVIDIA Container Toolkit
- 최소 16GB GPU 메모리 (모델에 따라 다름)

**배포 단계**:

```bash
# 1. 저장소 클론
git clone <repo-url>
cd ksp-rag-system

# 2. GPU 설정 디렉토리로 이동
cd ops/gpu

# 3. 환경 설정 (선택 사항)
cp .env.gpu.example .env.gpu
vim .env.gpu  # 필요시 수정

# 4. GPU 서버에서 vLLM 시작
docker compose up -d

# 5. 헬스체크
curl http://localhost:8000/health
```

**포트**:
- `8000`: vLLM API (운영 서버에서 접근)

**방화벽 규칙**:
- 인바운드: 8000 (운영 서버에서만 접근 가능하도록 제한)
- 아웃바운드: 인터넷 (모델 다운로드)

**환경 변수** (선택 사항):
```bash
# ops/gpu/.env.gpu (선택)
SERVER_LLM_MODEL=meta-llama/Llama-2-7b-chat-hf
GPU_MEMORY_UTILIZATION=0.9
```

자세한 설정은 [ops/gpu/README.md](ops/gpu/README.md)를 참고하세요.

### 네트워크 연결

**운영 서버 → GPU 서버**:
- 운영 서버의 `.env.server`에 `SERVER_LLM_BASE_URL=http://<GPU_SERVER_IP>:8000` 설정
- 네트워크 연결 확인: `make llm-health`

**동일 네트워크 배치 권장**:
- 가능하면 운영 서버와 GPU 서버를 동일 네트워크에 배치하여 지연 시간 최소화
- 또는 VPN/전용 네트워크 사용

### 상세 배포 가이드

**운영 서버**: [docs/SERVER_DEPLOYMENT.md](docs/SERVER_DEPLOYMENT.md)  
**아키텍처 상세**: [docs/architecture/overview.md](docs/architecture/overview.md)

## 🚀 빠른 시작 (로컬 개발)

> **Windows 사용자**: Makefile/셸 스크립트는 Windows 기본 셸에서 동작하지 않습니다. **[docs/WINDOWS.md](docs/WINDOWS.md)** 에서 PowerShell용 설정 및 실행 방법을 참고하세요.

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

### 3단계: Elasticsearch 인덱스 빌드

```bash
# Elasticsearch 실행 후 인덱스 빌드
make up-local   # Elasticsearch + 앱 컨테이너 시작
make index-local
```

**출력**: Elasticsearch 인덱스 `ksp_rag_index`

### 4단계: RAG 질의 테스트

```bash
# CLI로 질문 (Elasticsearch + 개인 LLM)
make ask Q="What is the main topic?"
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

# 그래프/차트(이미지) 설명 포함 (인제스트 시 한 번만 비전 처리, 질의는 텍스트만)
docker compose --profile server run --rm app python -m ragapp ingest --figures --figure-model blip
# 또는 OpenAI Vision 사용 시
docker compose --profile server run --rm app python -m ragapp ingest --figures --figure-model openai_vision

# 커스텀 경로
docker compose --profile server run --rm app python -m ragapp ingest \
  --input data/raw \
  --output data/processed/chunks.jsonl

# 도움말
docker compose --profile server run --rm app python -m ragapp ingest --help
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
docker compose --profile server run --rm app python -m ragapp --help
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
docker compose --profile server run --rm app python -m ragapp ask "hello"

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
├── .env.local.example  # 로컬(Elastic+LLM) 설정 템플릿
├── .env.server.example        # 서버 모드 설정 템플릿
├── .env.local         # 로컬 설정 (git ignore, 직접 생성)
├── .env.server                # 서버 설정 (git ignore, 직접 생성)
└── setup.sh                 # 환경 설정 스크립트
```

## ⚡ 캐싱 / 쿼리 확장 / 차트(DePlot)

- **캐싱**: 동일 질의 결과를 메모리 캐시에 저장해 반복 질의 시 검색·LLM 호출 없이 즉시 반환. `.env`에서 `CACHE_ENABLED`, `CACHE_TTL_SECONDS`, `CACHE_MAX_SIZE`로 제어.
- **쿼리 확장**: 질문을 LLM으로 2~3가지 표현으로 늘린 뒤 각각 검색하고, RRF로 병합해 recall 향상. `QUERY_EXPANSION_ENABLED`, `QUERY_EXPANSION_NUM_QUERIES`로 제어.
- **차트(DePlot)**: 인제스트 시 `--figure-model deplot`으로 차트 이미지를 표/텍스트로 변환(google/deplot). 질의 시에는 텍스트 검색만 사용.

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

## 🤖 외부 GPU 서버 vLLM 연동

### 아키텍처

- **GPU 서버**: vLLM (OpenAI-compatible) inference API만 제공
- **이 레포 (운영 서버)**: Elasticsearch + RAG app + Streamlit + 인덱싱/임베딩

### 외부 vLLM 설정

```bash
# .env.server 설정
LLM_PROVIDER=server_http
SERVER_LLM_BASE_URL=http://172.16.0.52:8000  # GPU 서버 base URL (vLLM)

# 외부 vLLM 헬스체크
make llm-health

# 외부 vLLM 테스트
make llm-test
```

### RAG with 외부 vLLM

```bash
# 전체 서버 스택 시작 (Elasticsearch + app)
make up-server

# RAG 실행
make ask-elastic Q="질문"
```

**자세한 가이드**: [docs/ELASTICSEARCH_GUIDE.md](docs/ELASTICSEARCH_GUIDE.md)

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

**자세한 가이드**: [docs/SERVER_DEPLOYMENT.md](docs/SERVER_DEPLOYMENT.md)

---

## 🚀 배포 가이드

> **참고**: 배포 전에 위의 [Deployment Topology](#-deployment-topology) 섹션을 먼저 읽어보세요.

### 운영 서버 배포 (이 레포)

**역할**: Elasticsearch + RAG app + Streamlit + 인덱싱/임베딩

```bash
# 1. 저장소 클론
git clone <repository-url>
cd ksp-rag-system

# 2. 기존 서비스 확인 (Elastic이 이미 있는지)
make check-server

# 3. 환경 설정
cp .env.server.example .env.server
# .env.server 편집 - 외부 vLLM endpoint 설정

# 4. Docker 빌드
make build

# 5. 서비스 시작
make up-server  # Elasticsearch + app 시작

# 6. 데이터 인제스트
make ingest

# 7. Elasticsearch 인덱스 빌드
make index-elastic

# 8. 스모크 테스트
make smoke-test

# 9. UI 시작
make ui-server

# 10. 브라우저 접속
# http://<server-ip>:8501
```

### GPU 서버 배포 (별도 서버)

> **중요**: GPU 서버는 운영 서버와 별도로 배포됩니다. 위의 [Deployment Topology](#-deployment-topology) 섹션을 참고하세요.

**역할**: vLLM inference API만 제공

```bash
# 1. 저장소 클론
git clone <repository-url>
cd ksp-rag-system

# 2. GPU 설정 디렉토리로 이동
cd ops/gpu

# 3. 환경 설정 (선택 사항)
cp .env.gpu.example .env.gpu
vim .env.gpu  # 필요시 수정

# 4. GPU 서버에서 vLLM 시작
docker compose up -d

# 5. 헬스체크
curl http://localhost:8000/health

# 6. 운영 서버에서 외부 vLLM 연결 확인
# (운영 서버에서 실행)
make llm-health
```

**자세한 가이드**: [ops/gpu/README.md](ops/gpu/README.md)

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

#### 운영 서버 (이 레포)

| 명령어 | 설명 |
|--------|------|
| `make build` | Docker 이미지 빌드 |
| `make up-server` | 서버 모드 시작 (Elasticsearch + app) |
| `make ingest` | PDF 인제스트 |
| `make index-elastic` | Elasticsearch 인덱스 빌드 |
| `make ask-elastic Q="질문"` | Elasticsearch RAG 질의 |
| `make ui-server` | 서버 UI 시작 |
| `make smoke-test` | 스모크 테스트 |
| `make llm-health` | 외부 vLLM 헬스체크 |

#### GPU 서버 (별도)

| 명령어 | 설명 |
|--------|------|
| `make gpu-up` | vLLM 서비스 시작 (ops/gpu/docker-compose.yml) |
| `make gpu-down` | vLLM 서비스 중지 |
| `make gpu-health` | vLLM 헬스체크 |
| `make gpu-logs` | vLLM 로그 확인 |

**참고**: GPU 서버 명령어는 `ops/gpu/` 디렉토리에서 직접 실행하는 것을 권장합니다. 자세한 내용은 [ops/gpu/README.md](ops/gpu/README.md)를 참고하세요.

### 상세 배포 가이드

**운영 서버 배포**: [docs/SERVER_DEPLOYMENT.md](docs/SERVER_DEPLOYMENT.md)  
**아키텍처 상세**: [docs/architecture/overview.md](docs/architecture/overview.md)

**포함 내용**:
- 환경 설정 상세
- 서비스 시작 및 헬스체크
- 인덱스 빌드 및 검증
- 외부 vLLM 연결
- 성능 모니터링
- 트러블슈팅

**GPU 서버 배포**: `ops/gpu/docker-compose.yml` 사용
- GPU 서버에서 별도로 vLLM만 실행
- 운영 서버는 외부 endpoint로 연결
- 자세한 가이드: [ops/gpu/README.md](ops/gpu/README.md)
- 위의 [Deployment Topology](#-deployment-topology) 섹션 참고

---

## 📄 라이선스

MIT License
