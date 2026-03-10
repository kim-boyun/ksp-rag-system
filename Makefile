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

up-local: ## 로컬 모드로 컨테이너 시작 (Elasticsearch + 개인 LLM, .env.local)
	@test -f .env.local || (echo "Create .env.local from .env.local.example and set LLM_API_KEY"; exit 1)
	cp .env.local .env
	docker compose --profile server up -d

up-server: ## 서버 모드로 컨테이너 시작 (Elasticsearch + App, 외부 vLLM 사용, .env.server 사용)
	cp .env.server .env
	docker compose --profile server up -d

up-server-app-only: ## app+ui만 시작 (기존 Elastic/외부 vLLM 사용 시)
	@echo "기존 Elasticsearch/외부 vLLM 사용 - app, ui만 시작"
	cp .env.server .env 2>/dev/null || true
	docker compose --profile app-only up -d
	@echo "UI: http://localhost:8501"

check-server: ## 서버 기존 Elastic/LLM 서비스 확인 (배포 전 실행)
	@bash scripts/check_server_services.sh

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

config-local: ## 로컬 설정 확인 (.env.local 사용)
	cp .env.local .env
	docker compose --profile server run --rm app python -m ragapp config

config-server: ## 서버 설정 확인 (.env.server 사용)
	cp .env.server .env
	docker compose --profile server run --rm app python -m ragapp config

health-local: ## 헬스체크 (로컬 모드, .env.local 사용)
	cp .env.local .env
	docker compose --profile server run --rm app python -m ragapp health

health-server: ## 헬스체크 (서버 모드, .env.server 사용) - Elasticsearch + vLLM 체크
	cp .env.server .env
	docker compose --profile server run --rm app python -m ragapp health

health: health-server ## 헬스체크 (기본=서버 모드)

version: ## 버전 확인 (.env.local 사용)
	cp .env.local .env
	docker compose --profile server run --rm app python -m ragapp version

# ================================
# 문서 인제스트
# ================================

ingest: ## 문서 인제스트 (PDF → chunks, .env.local 사용)
	cp .env.local .env
	docker compose --profile server run --rm app python -m ragapp ingest

ingest-tables: ## 문서 인제스트 (표 포함)
	cp .env.local .env
	docker compose --profile server run --rm app python -m ragapp ingest --tables

# ================================
# 인덱스 빌드
# ================================

index-local: ## Elasticsearch 인덱스 빌드 (.env 사용, BGE-M3)
	cp .env.local .env
	docker compose --profile server run --rm app python -m ragapp index-elastic

# ================================
# RAG 파이프라인
# ================================

ask-local: ## RAG 질의응답 (Elasticsearch + 개인 LLM) - 사용: make ask-local Q="질문"
	@test -f .env.local || (echo "Create .env.local from .env.local.example and set LLM_API_KEY"; exit 1)
	cp .env.local .env
	docker compose --profile server run --rm app python -m ragapp ask "$(Q)"

ask: ask-local ## RAG 질의응답 (기본=로컬, Elastic+개인 LLM)

ask-rerank: ## RAG 질의응답 (리랭크 포함, .env.local 사용)
	cp .env.local .env
	docker compose --profile server run --rm app python -m ragapp ask "$(Q)" --rerank

ask-elastic: ## RAG 질의응답 (Elasticsearch 모드, .env.server 사용)
	cp .env.server .env
	docker compose --profile server run --rm app python -m ragapp ask "$(Q)" --mode elastic

ask-elastic-local-llm: ask-local ## (별칭) Elasticsearch 검색 + 개인 LLM

ask-server: ask-elastic ## RAG 질의응답 (서버 모드)

# ================================
# 인덱싱 & 검색
# ================================

index: index-local ## Elasticsearch 인덱스 빌드 (기본=index-local)

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

elastic-index-status: ## 인덱스 목록 + 문서 수 확인
	@echo "=== 인덱스 목록 & 문서 수 ==="
	@curl -s http://localhost:9200/_cat/indices?v 2>/dev/null || (echo "❌ Elasticsearch not running"; exit 1)
	@echo ""
	@echo "=== ksp_rag_index_m3 문서 수 ==="
	@curl -s http://localhost:9200/ksp_rag_index_m3/_count?pretty 2>/dev/null || true

elastic-index-model: ## 현재 인덱스 임베딩 차원 확인 (BGE-M3 = 1024)
	@echo "=== ksp_rag_index_m3 (BGE-M3) ==="
	@curl -s http://localhost:9200/ksp_rag_index_m3/_mapping?pretty 2>/dev/null | grep -A2 '"embedding"' || echo "  (인덱스 없음)"
	@echo "  dims=1024 → BGE-M3"

elastic-logs: ## Elasticsearch 로그 확인
	docker compose logs -f elasticsearch

# 현재 기기에서 인덱스 빌드 후, 볼륨을 tar로 내보내서 다른 PC로 복사할 때 사용
elastic-export: ## Elasticsearch 데이터(인덱스 포함)를 tar로 내보내기 → 다른 PC에서 elastic-import
	@echo "Stopping Elasticsearch..."
	docker compose --profile server stop elasticsearch
	@echo "Exporting elastic-data volume to data/elastic-data-backup.tar.gz ..."
	@mkdir -p data
	# elasticsearch 서비스 컨테이너 안에서, 이미 마운트된 /usr/share/elasticsearch/data 를 그대로 tar
	docker compose --profile server run --rm -v $$(pwd)/data:/backup elasticsearch sh -c "tar czf /backup/elastic-data-backup.tar.gz -C /usr/share/elasticsearch/data ."
	@echo "Done. Copy data/elastic-data-backup.tar.gz to the other PC, then run: make elastic-import"
	docker compose --profile server up -d elasticsearch

# 다른 PC에서 복사해 온 tar로 Elasticsearch 데이터 복원 (인덱스 재구축 불필요)
elastic-import: ## data/elastic-data-backup.tar.gz 로 Elasticsearch 데이터 복원
	@test -f data/elastic-data-backup.tar.gz || (echo "Put data/elastic-data-backup.tar.gz first."; exit 1)
	@echo "Stopping Elasticsearch..."
	docker compose --profile server stop elasticsearch
	@echo "Importing into elastic-data volume..."
	# elasticsearch 서비스 컨테이너 안에서, ES 데이터 디렉터리에 직접 복원
	docker compose --profile server run --rm -v $$(pwd)/data:/backup elasticsearch sh -c "rm -rf /usr/share/elasticsearch/data/* /usr/share/elasticsearch/data/..?* 2>/dev/null; tar xzf /backup/elastic-data-backup.tar.gz -C /usr/share/elasticsearch/data"
	@echo "Starting Elasticsearch..."
	docker compose --profile server up -d elasticsearch
	@echo "Done. Wait for ES to be healthy: make elastic-health"

kibana-up: ## Kibana 시작 (Elasticsearch 디버깅 UI, 선택 사항)
	docker compose --profile server --profile kibana up -d kibana
	@echo "Kibana: http://localhost:5601"

# ================================
# GPU 서버 (별도 compose 파일)
# ================================

gpu-up: ## GPU 서버에서 vLLM 시작 (ops/gpu/docker-compose.yml 사용)
	@echo "⚠️  이 명령어는 GPU 서버에서만 실행하세요."
	@echo "📁 GPU 설정: ops/gpu/"
	docker compose -f ops/gpu/docker-compose.yml up -d
	@echo "vLLM 서비스 시작됨: http://localhost:8000"

gpu-down: ## GPU 서버에서 vLLM 중지
	@echo "⚠️  이 명령어는 GPU 서버에서만 실행하세요."
	docker compose -f ops/gpu/docker-compose.yml down

gpu-logs: ## GPU 서버 vLLM 로그 확인
	@echo "⚠️  이 명령어는 GPU 서버에서만 실행하세요."
	docker compose -f ops/gpu/docker-compose.yml logs -f llm

gpu-health: ## GPU 서버 vLLM 헬스체크
	@echo "⚠️  이 명령어는 GPU 서버에서만 실행하세요."
	@echo "Checking vLLM health..."
	@curl -s http://localhost:8000/health || echo "❌ vLLM not running"

# ================================
# 외부 LLM 서비스 확인 (운영 서버에서)
# ================================

llm-health: ## 외부 LLM 헬스체크 (.env.server의 SERVER_LLM_BASE_URL 사용)
	@echo "Checking external LLM health..."
	@CODE=0; \
	if [ -f .env.server ]; then \
		if grep -q "^SERVER_LLM_BASE_URL=" .env.server; then \
			BASE_URL=$$(grep "^SERVER_LLM_BASE_URL=" .env.server | cut -d'=' -f2); \
			CODE=$$(curl -s -o /dev/null -w "%{http_code}" $$BASE_URL/health 2>/dev/null || echo "000"); \
		elif grep -q "^SERVER_LLM_ENDPOINT=" .env.server; then \
			ENDPOINT=$$(grep "^SERVER_LLM_ENDPOINT=" .env.server | cut -d'=' -f2 | sed 's|/v1/completions||'); \
			CODE=$$(curl -s -o /dev/null -w "%{http_code}" $$ENDPOINT/health 2>/dev/null || echo "000"); \
		else \
			CODE=$$(curl -s -o /dev/null -w "%{http_code}" http://172.16.0.52:8000/health 2>/dev/null || echo "000"); \
		fi \
	else \
		CODE=$$(curl -s -o /dev/null -w "%{http_code}" http://172.16.0.52:8000/health 2>/dev/null || echo "000"); \
	fi; \
	if [ "$$CODE" = "200" ]; then echo "✅ External LLM OK (HTTP $$CODE)"; else echo "❌ External LLM not accessible (HTTP $$CODE)"; fi

llm-test: ## 외부 LLM 테스트 요청 (.env.server의 SERVER_LLM_MODEL 사용)
	@echo "Testing external LLM endpoint..."
	@MODEL=$$(grep "^SERVER_LLM_MODEL=" .env.server 2>/dev/null | cut -d'=' -f2- | tr -d '"' | tr -d "'"); \
	if [ -z "$$MODEL" ]; then MODEL="meta-llama/Llama-2-7b-chat-hf"; fi; \
	if [ -f .env.server ]; then \
		if grep -q "^SERVER_LLM_BASE_URL=" .env.server; then \
			BASE_URL=$$(grep "^SERVER_LLM_BASE_URL=" .env.server | cut -d'=' -f2); \
			curl -s -X POST $$BASE_URL/v1/completions \
				-H "Content-Type: application/json" \
				-d "{\"model\": \"$$MODEL\", \"prompt\": \"Hello, \", \"max_tokens\": 20}" | jq || echo "❌ Request failed"; \
		elif grep -q "^SERVER_LLM_ENDPOINT=" .env.server; then \
			ENDPOINT=$$(grep "^SERVER_LLM_ENDPOINT=" .env.server | cut -d'=' -f2); \
			curl -s -X POST $$ENDPOINT \
				-H "Content-Type: application/json" \
				-d "{\"model\": \"$$MODEL\", \"prompt\": \"Hello, \", \"max_tokens\": 20}" | jq || echo "❌ Request failed"; \
		else \
			echo "⚠️  SERVER_LLM_BASE_URL not found. Using default..."; \
			curl -s -X POST http://172.16.0.52:8000/v1/completions \
				-H "Content-Type: application/json" \
				-d "{\"model\": \"$$MODEL\", \"prompt\": \"Hello, \", \"max_tokens\": 20}" | jq || echo "❌ Request failed"; \
		fi \
	else \
		echo "⚠️  .env.server not found. Using default endpoint..."; \
		curl -s -X POST http://172.16.0.52:8000/v1/completions \
			-H "Content-Type: application/json" \
			-d "{\"model\": \"$$MODEL\", \"prompt\": \"Hello, \", \"max_tokens\": 20}" | jq || echo "❌ Request failed"; \
	fi

# ================================
# Streamlit UI
# ================================

ui-local: ## Streamlit UI (Elasticsearch + 개인 LLM, 백그라운드)
	@test -f .env.local || (echo "Create .env.local from .env.local.example and set LLM_API_KEY"; exit 1)
	cp .env.local .env
	docker compose --profile server --profile ui up -d
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

index-elastic: ## Elasticsearch 인덱스 빌드 (BGE-M3, .env.server)
	cp .env.server .env
	docker compose --profile server run --rm app python -m ragapp index-elastic

index-elastic-recreate: ## Elasticsearch 인덱스 재생성 (BGE-M3, 기존 인덱스 삭제 후 재구축)
	cp .env.server .env
	docker compose --profile server run --rm app python -m ragapp index-elastic --recreate

index-elastic-native: ## [선택] 네이티브에서 M3 인덱스 빌드 (Docker 없이, MPS/CUDA 사용 시)
	@echo "Elasticsearch는 별도 실행 중이어야 합니다. make elastic-up"
	ELASTIC_HOST=localhost ELASTIC_INDEX_NAME=ksp_rag_index_m3 \
		poetry run python -m ragapp index-elastic --recreate --model BAAI/bge-m3 --host localhost

# ================================
# 검색 / RAG
# ================================

retrieve: ## Elasticsearch 검색만 테스트 - 사용: make retrieve Q="질문"
	cp .env.local .env
	docker compose --profile server run --rm app python -m ragapp retrieve "$(Q)" --mode elastic

retrieve-rerank: ## Elasticsearch + 리랭크 검색
	cp .env.local .env
	docker compose --profile server run --rm app python -m ragapp retrieve "$(Q)" --mode elastic --rerank

retrieve-json: ## 검색 결과 JSON 저장
	cp .env.local .env
	docker compose --profile server run --rm app python -m ragapp retrieve "$(Q)" --mode elastic \
		--output results_retrieve.json

retrieve-elastic: ## Elasticsearch 검색 - 사용: make retrieve-elastic Q="질문"
	cp .env.server .env
	docker compose --profile server run --rm app python -m ragapp retrieve "$(Q)" --mode elastic

retrieve-elastic-rerank: ## Elasticsearch + 리랭크
	docker compose --profile server run --rm app python -m ragapp retrieve "$(Q)" --mode elastic --rerank

# ================================
# 개발 & 테스트
# ================================

test-connection: ## Docker 환경 연결 테스트
	cp .env.local .env 2>/dev/null || true
	docker compose --profile server run --rm app python --version
	docker compose --profile server run --rm app python -c "import torch; import sentence_transformers; print('✅ Dependencies OK')"

test: ## pytest 실행
	cp .env.local .env 2>/dev/null || true
	docker compose --profile server run --rm app pytest tests/ -v

test-cov: ## 테스트 커버리지
	docker compose --profile local run --rm app pytest tests/ -v --cov=src --cov-report=html

test-e2e: ## E2E 테스트 (전체 파이프라인)
	@bash scripts/test_e2e.sh

shell: ## 앱 컨테이너 bash 접속
	cp .env.local .env 2>/dev/null || true
	docker compose --profile server run --rm app bash

# ================================
# RAG 파이프라인 (추후 구현)
# ================================

ingest-local: ## 문서 인제스트 (.env.local 사용, chunks.jsonl 생성)
	@echo "⏳ 문서 인제스트 중..."
	cp .env.local .env
	docker compose --profile server run --rm app python -m ragapp ingest

query-local: ## 질의 (Elasticsearch + 개인 LLM)
	@echo "💬 질의: $(Q)"
	cp .env.local .env
	docker compose --profile server run --rm app python -m ragapp ask "$(Q)"

ingest-server: ## 서버 모드로 문서 인덱싱 (.env.server 사용)
	@echo "⏳ 문서 인덱싱 중... (Elasticsearch)"
	cp .env.server .env
	docker compose --profile server run --rm app python -m ragapp ingest

query-server: ## 서버 모드 질의 (.env.server 사용)
	@echo "💬 질의: $(Q)"
	cp .env.server .env
	docker compose --profile server run --rm app python -m ragapp ask "$(Q)"

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
