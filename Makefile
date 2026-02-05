.PHONY: help build test clean setup

# ================================
# 기본 명령어
# ================================

help: ## 사용 가능한 명령어 표시
	@echo "KSP RAG System - Makefile Commands"
	@echo "=================================="
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

setup: ## 환경 설정 (.env 파일 생성)
	@bash setup.sh

# ================================
# Docker 관리
# ================================

build: ## Docker 이미지 빌드
	docker compose build app

rebuild: ## Docker 이미지 재빌드 (캐시 무시)
	docker compose build --no-cache app

up-local: ## 로컬 모드로 컨테이너 시작
	docker compose --profile local up -d

up-server: ## 서버 모드로 컨테이너 시작 (Elasticsearch 포함)
	docker compose --profile server up -d

down: ## 모든 컨테이너 종료
	docker compose down

clean: ## 컨테이너, 볼륨, 이미지 모두 삭제
	docker compose down -v
	docker rmi ksp-rag-system-app 2>/dev/null || true

clean-data: ## 처리된 데이터와 인덱스만 삭제
	@bash scripts/clean_all.sh

# ================================
# CLI 명령어
# ================================

config-local: ## 로컬 설정 확인
	docker compose --profile local run --rm app python -m ragapp config

config-server: ## 서버 설정 확인
	docker compose --profile server run --rm -e MODE=server app python -m ragapp config

version: ## 버전 확인
	docker compose --profile local run --rm app python -m ragapp version

# ================================
# 문서 인제스트
# ================================

ingest: ## 문서 인제스트 (PDF → chunks)
	docker compose --profile local run --rm app python -m ragapp ingest

ingest-tables: ## 문서 인제스트 (표 포함)
	docker compose --profile local run --rm app python -m ragapp ingest --tables

# ================================
# 인덱스 빌드
# ================================

index-local: ## 로컬 인덱스 빌드 (BM25 + FAISS)
	docker compose --profile local run --rm app python -m ragapp index

index-small: ## 로컬 인덱스 빌드 (작은 임베딩 모델)
	docker compose --profile local run --rm app python -m ragapp index --embedding-model BAAI/bge-small-en-v1.5

index-elastic: ## Elasticsearch 인덱스 빌드
	docker compose --profile server run --rm app python -m ragapp index-elastic

index-elastic-recreate: ## Elasticsearch 인덱스 재생성
	docker compose --profile server run --rm app python -m ragapp index-elastic --recreate

# ================================
# RAG 파이프라인
# ================================

ask-local: ## RAG 질의응답 (로컬 모드) - 사용: make ask-local Q="질문"
	docker compose --profile local run --rm app python -m ragapp ask "$(Q)"

ask: ask-local ## RAG 질의응답 (기본=로컬)

ask-rerank: ## RAG 질의응답 (리랭크 포함)
	docker compose --profile local run --rm app python -m ragapp ask "$(Q)" --rerank

ask-elastic: ## RAG 질의응답 (Elasticsearch 모드)
	docker compose --profile server run --rm app python -m ragapp ask "$(Q)" --mode elastic

ask-server: ask-elastic ## RAG 질의응답 (서버 모드)

# ================================
# 인덱싱 & 검색
# ================================

index: ## 로컬 인덱스 빌드 (BM25 + FAISS)
	docker compose --profile local run --rm app python -m ragapp index

index-small: ## 작은 모델로 빠르게 인덱스 빌드
	docker compose --profile local run --rm app python -m ragapp index \
		--model BAAI/bge-small-en-v1.5 \
		--batch-size 16

index-sample: ## 샘플 데이터로 빠른 테스트
	@echo "Creating sample (first 20 chunks)..."
	@head -n 20 data/processed/chunks.jsonl > data/processed/chunks_sample.jsonl
	docker compose --profile local run --rm app python -m ragapp index \
		--chunks data/processed/chunks_sample.jsonl \
		--output data/index_sample \
		--model BAAI/bge-small-en-v1.5 \
		--batch-size 8

# ================================
# Elasticsearch 관리
# ================================

elastic-up: ## Elasticsearch 서비스 시작
	docker compose --profile server up -d elasticsearch

elastic-down: ## Elasticsearch 서비스 중지
	docker compose --profile server stop elasticsearch

elastic-health: ## Elasticsearch 헬스체크
	@echo "Checking Elasticsearch health..."
	@curl -s http://localhost:9200/_cluster/health?pretty || echo "❌ Elasticsearch not running"

elastic-logs: ## Elasticsearch 로그 확인
	docker compose logs -f elasticsearch

kibana-up: ## Kibana 시작 (Elasticsearch UI)
	docker compose --profile server up -d kibana
	@echo "Kibana: http://localhost:5601"

# ================================
# LLM 서비스 관리 (GPU 서버)
# ================================

llm-up: ## LLM 서비스 시작 (GPU 필요)
	docker compose --profile server up -d llm

llm-down: ## LLM 서비스 중지
	docker compose --profile server stop llm

llm-health: ## LLM 헬스체크
	@echo "Checking LLM health..."
	@curl -s http://localhost:8000/health || echo "❌ LLM not running"

llm-logs: ## LLM 로그 확인
	docker compose logs -f llm

llm-test: ## LLM 테스트 요청
	@echo "Testing LLM endpoint..."
	@curl -X POST http://localhost:8000/v1/completions \
		-H "Content-Type: application/json" \
		-d '{"model": "meta-llama/Llama-2-7b-chat-hf", "prompt": "Hello, ", "max_tokens": 20}' | jq

# ================================
# Streamlit UI
# ================================

ui: ## Streamlit UI 시작 (로컬 모드)
	cp .env.local .env
	docker compose --profile ui up

ui-local: ## Streamlit UI (로컬 모드, 백그라운드)
	cp .env.local .env
	docker compose --profile ui up -d
	@echo "Streamlit UI: http://localhost:8501"

ui-server: ## Streamlit UI (서버 모드, 백그라운드)
	cp .env.server .env
	docker compose --profile ui up -d
	@echo "Streamlit UI: http://localhost:8501"

ui-down: ## Streamlit UI 중지
	docker compose --profile ui down

ui-logs: ## Streamlit UI 로그
	docker compose logs -f ui

# ================================
# Elasticsearch 인덱스
# ================================

index-elastic: ## Elasticsearch 인덱스 빌드
	docker compose --profile server run --rm app python -m ragapp index-elastic

index-elastic-recreate: ## Elasticsearch 인덱스 재생성
	docker compose --profile server run --rm app python -m ragapp index-elastic --recreate

# ================================
# 검색 / RAG
# ================================

retrieve: ## 하이브리드 검색만 테스트 - 사용: make retrieve Q="질문"
	docker compose --profile local run --rm app python -m ragapp retrieve "$(Q)"

retrieve-rerank: ## 리랭크 포함 검색만 - 사용: make retrieve-rerank Q="질문"
	docker compose --profile local run --rm app python -m ragapp retrieve "$(Q)" \
		--rerank

retrieve-json: ## 검색 결과 JSON 저장 - 사용: make retrieve-json Q="질문"
	docker compose --profile local run --rm app python -m ragapp retrieve "$(Q)" \
		--output results_retrieve.json

retrieve-sample: ## 샘플 인덱스로 검색 테스트
	docker compose --profile local run --rm app python -m ragapp retrieve "$(Q)" \
		--index-dir data/index_sample

retrieve-elastic: ## Elasticsearch 검색 - 사용: make retrieve-elastic Q="질문"
	docker compose --profile server run --rm app python -m ragapp retrieve "$(Q)" --mode elastic

retrieve-elastic-rerank: ## Elasticsearch + 리랭크
	docker compose --profile server run --rm app python -m ragapp retrieve "$(Q)" --mode elastic --rerank

ask-elastic: ## Elasticsearch 기반 RAG
	docker compose --profile server run --rm app python -m ragapp ask "$(Q)"

# ================================
# 개발 & 테스트
# ================================

test-connection: ## Docker 환경 연결 테스트
	docker compose --profile local run --rm app python --version
	docker compose --profile local run --rm app python -c "import torch; import sentence_transformers; print('✅ Dependencies OK')"

test: ## pytest 실행
	docker compose --profile local run --rm app pytest tests/ -v

test-cov: ## 테스트 커버리지
	docker compose --profile local run --rm app pytest tests/ -v --cov=src --cov-report=html

test-e2e: ## E2E 테스트 (전체 파이프라인)
	@bash scripts/test_e2e.sh

shell: ## 앱 컨테이너 bash 접속
	docker compose --profile local run --rm app bash

# ================================
# RAG 파이프라인 (추후 구현)
# ================================

ingest-local: ## 로컬 모드로 문서 인덱싱
	@echo "⏳ 문서 인덱싱 중... (로컬 BM25+FAISS)"
	docker-compose run --rm -e MODE=local app python -m src.cli ingest

query-local: ## 로컬 모드 질의
	@echo "💬 질의: $(Q)"
	docker-compose run --rm -e MODE=local app python -m src.cli query "$(Q)"

ingest-server: ## 서버 모드로 문서 인덱싱
	@echo "⏳ 문서 인덱싱 중... (Elasticsearch)"
	docker-compose run --rm -e MODE=server app python -m src.cli ingest

query-server: ## 서버 모드 질의
	@echo "💬 질의: $(Q)"
	docker-compose run --rm -e MODE=server app python -m src.cli query "$(Q)"

# ================================
# 테스트
# ================================

smoke-test: ## 스모크 테스트 (ingest, retrieve, ask)
	@bash scripts/smoke_test.sh

quick-test: ## 빠른 테스트
	@bash scripts/quick_test.sh

# ================================
# 유틸리티
# ================================

logs: ## 로그 확인
	docker compose logs -f

ps: ## 실행 중인 컨테이너 확인
	docker compose ps

status: ## 시스템 상태 확인
	@echo "=== Docker Containers ==="
	@docker compose ps
	@echo ""
	@echo "=== Disk Usage ==="
	@du -sh data/processed data/index 2>/dev/null || echo "No data yet"
