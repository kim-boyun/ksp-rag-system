# 🚀 RAG System 완전 가이드

## 📋 전체 워크플로우

### 1단계: 초기 설정
```bash
# 환경 설정
make setup

# API 키 입력
code .env.local  # LLM_API_KEY 수정
```

### 2단계: Docker 빌드
```bash
make build  # 또는 make rebuild
```

### 3단계: 문서 준비
```bash
# PDF 파일을 data/raw/에 넣기
cp your-documents.pdf data/raw/

# 또는 샘플 생성
make create-sample
```

### 4단계: 인제스트 (PDF → Chunks)
```bash
make ingest
```

**출력**: `data/processed/chunks.jsonl`

### 5단계: 인덱싱 (Chunks → 검색 인덱스)
```bash
# 빠른 테스트 (작은 모델)
make index-small

# 또는 고품질 (큰 모델, 느림)
make index
```

**출력**: `data/index/` (FAISS + BM25)

### 6단계: RAG 질의응답

#### A. 기본 RAG (리랭크 없음)
```bash
make ask Q="온두라스 연금 시스템의 주요 특징은?"
```

**프로세스**:
1. 하이브리드 검색 → TOP_K개 (예: 12개)
2. LLM 생성 → 12개 문서 기반 답변

#### B. 고품질 RAG (리랭크 포함)
```bash
make ask-rerank Q="온두라스 연금 개혁 방안은?"
```

**프로세스**:
1. 하이브리드 검색 → TOP_K개 (예: 12개)
2. LLM 리랭킹 → RERANK_TOP_K개 (예: 5개)
3. LLM 생성 → 5개 고품질 문서 기반 답변

---

## 🎯 단계별 명령어 요약

```bash
# 준비
make setup              # 환경 설정
make build             # Docker 빌드

# 데이터 파이프라인
make ingest            # PDF → chunks.jsonl
make index-small       # chunks → 검색 인덱스

# RAG 파이프라인
make ask Q="질문"      # 기본 RAG
make ask-rerank Q="질문"  # 리랭크 포함 RAG

# 검색만 (생성 없이)
make retrieve Q="질문"
make retrieve-rerank Q="질문"

# 유틸리티
make config-local      # 설정 확인
make test              # 단위 테스트
make test-e2e          # E2E 테스트
make clean-data        # 데이터 정리
```

---

## ⚙️ 설정 파일 (.env.local)

```bash
# 검색 설정
TOP_K=12               # 하이브리드 검색 결과 개수
RERANK_TOP_K=5         # 리랭크 후 최종 개수

# LLM 설정
LLM_PROVIDER=local_api
LLM_API_KEY=sk-proj-your-key
LLM_MODEL=gpt-3.5-turbo
```

**동작**:
- `make ask`: TOP_K(12개) 모두 사용 → LLM 생성
- `make ask-rerank`: TOP_K(12개) → LLM 리랭킹 → RERANK_TOP_K(5개) → LLM 생성

---

## 🔍 검색 vs RAG 차이

| 명령어 | 검색 | 리랭크 | LLM 생성 | 출력 |
|--------|------|--------|----------|------|
| `retrieve` | ✅ | ❌ | ❌ | 문서 목록 |
| `retrieve-rerank` | ✅ | ✅ | ❌ | 문서 목록 (정제됨) |
| `ask` | ✅ | ❌ | ✅ | **답변 + 인용** |
| `ask-rerank` | ✅ | ✅ | ✅ | **고품질 답변 + 인용** |

---

## 📊 성능 vs 품질

| 모드 | 검색 개수 | 리랭크 | LLM 비용 | 속도 | 품질 |
|------|-----------|--------|----------|------|------|
| **빠름** | 5개 | ❌ | 낮음 | ⚡⚡⚡ | ⭐⭐⭐ |
| **균형** | 12개 | ❌ | 중간 | ⚡⚡ | ⭐⭐⭐⭐ |
| **고품질** | 30개 | ✅ → 5개 | 높음 | ⚡ | ⭐⭐⭐⭐⭐ |

**추천**:
- 개발/테스트: `make ask` (빠름)
- 운영/중요 질문: `make ask-rerank` (고품질)

---

## 🐛 문제 해결

### 캐시 문제
```bash
# Python 캐시 삭제
find src -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

# 데이터 정리
make clean-data
```

### 빌드 문제
```bash
# 완전 재빌드
make rebuild
```

### API 키 오류
```bash
# API 키 확인
cat .env.local | grep LLM_API_KEY

# 올바른 키로 수정
code .env.local
```

---

## 📚 파일 구조

```
data/
├── raw/               # 원본 PDF
├── processed/         # chunks.jsonl
└── index/            # FAISS + BM25 인덱스

src/ragapp/
├── ingest/           # PDF → chunks
├── index/            # chunks → 인덱스
├── embeddings/       # BGE 임베딩
├── retrievers/       # 하이브리드 검색
├── rerankers/        # LLM 리랭킹
├── llms/             # LLM 클라이언트
├── prompts/          # 프롬프트 템플릿
└── pipeline/         # RAG 오케스트레이터
```
