# Refactor Step 6: Smoke tests - 완료 보고서

## 📋 목표

외부 vLLM이 준비됐을 때 end-to-end가 깨지지 않음을 빠르게 확인:
- 운영 시 배포 후 1분 내 상태 확인 가능
- Elasticsearch와 vLLM 연결 상태 체크

## ✅ 완료된 작업

### 1. health CLI 명령어 추가

**파일**: `src/ragapp/cli.py`

**기능**:
- Elasticsearch ping 체크 (서버 모드 또는 retriever가 elastic일 때)
- vLLM `/v1/models` 체크 (SERVER_LLM_BASE_URL이 설정되어 있고 `server_http` provider일 때)
- 각 서비스의 상태를 색상으로 표시 (✅ 성공, ❌ 실패, ⏭️ 스킵)
- 종료 코드 반환 (0: 모두 정상, 1: 일부 실패)

**코드**:
```python
@app.command()
def health():
    """
    Check health status of external services (Elasticsearch, vLLM)
    """
    # Elasticsearch 체크
    if config.is_server_mode or config.retriever_mode == "elastic":
        es = Elasticsearch([f"http://{config.elastic_host}:{config.elastic_port}"])
        if es.ping():
            console.print("[bold green]✅ Elasticsearch[/bold green] - Connected")
        else:
            console.print("[bold red]❌ Elasticsearch[/bold red] - Ping failed")
    
    # vLLM 체크
    if config.llm_provider == "server_http" and config.server_llm_base_url:
        response = httpx.get(f"{base_url}/v1/models", timeout=10.0)
        # 모델 정보 표시
```

**출력 예시**:
```
🏥 Health Check

✅ Elasticsearch - Connected
   Version: 8.12.0
✅ vLLM - Connected
   Model: meta-llama/Llama-2-7b-chat-hf
   Endpoint: http://172.16.0.52:8000

✅ All services are healthy
```

### 2. Makefile 타겟 추가

**파일**: `Makefile`

**추가된 타겟**:
- `health-local`: 로컬 모드 헬스체크 (`.env.local` 사용)
  - Elasticsearch는 스킵 (로컬 모드)
  - vLLM은 스킵 (local_api 사용)
- `health-server`: 서버 모드 헬스체크 (`.env.server` 사용)
  - Elasticsearch ping 체크
  - vLLM `/v1/models` 체크
- `health`: `health-server`의 별칭 (기본값)

**코드**:
```makefile
health-local: ## 헬스체크 (로컬 모드, .env.local 사용)
	cp .env.local .env
	docker compose --profile local run --rm app python -m ragapp health

health-server: ## 헬스체크 (서버 모드, .env.server 사용) - Elasticsearch + vLLM 체크
	cp .env.server .env
	docker compose --profile server run --rm app python -m ragapp health

health: health-server ## 헬스체크 (기본=서버 모드)
```

### 3. 검증

**간단한 문서/인덱스가 준비된 상태에서**:
- `make ask-elastic Q="test"` (server_http) 실행 시 동작 확인
- `make health-server` 실행 시 모든 서비스 정상 확인

## ✅ 완료 기준 검증

### 1. 운영 시 배포 후 1분 내 상태 확인 가능

**검증**:
- ✅ `make health-server` 명령어로 빠른 상태 확인 가능
- ✅ Elasticsearch와 vLLM 모두 체크
- ✅ 종료 코드로 자동화 스크립트에서 사용 가능 (0: 성공, 1: 실패)

**사용 예시**:
```bash
# 배포 후 즉시 확인
make health-server

# 자동화 스크립트에서 사용
make health-server && echo "✅ All services healthy" || echo "❌ Health check failed"
```

### 2. Elasticsearch ping 체크

**검증**:
- ✅ 서버 모드 또는 retriever가 elastic일 때만 체크
- ✅ 연결 실패 시 명확한 에러 메시지 표시
- ✅ 버전 정보 표시

### 3. vLLM 체크

**검증**:
- ✅ `SERVER_LLM_BASE_URL`이 설정되어 있고 `server_http` provider일 때만 체크
- ✅ `/v1/models` 엔드포인트로 체크
- ✅ 모델 정보 표시
- ✅ 타임아웃 및 에러 처리

## 📝 변경 파일 목록

1. `src/ragapp/cli.py` - `health` 명령어 추가
2. `Makefile` - `health-local`, `health-server`, `health` 타겟 추가

## 🔍 검증 방법

### 로컬 모드 헬스체크

```bash
# 로컬 모드 (Elasticsearch, vLLM 스킵)
make health-local

# 예상 출력:
# 🏥 Health Check
# ⏭️  Elasticsearch - Skipped (local mode)
# ⏭️  vLLM - Skipped (using local_api)
# ✅ All services are healthy
```

### 서버 모드 헬스체크

```bash
# 서버 모드 (Elasticsearch + vLLM 체크)
make health-server

# 예상 출력:
# 🏥 Health Check
# ✅ Elasticsearch - Connected
#    Version: 8.12.0
# ✅ vLLM - Connected
#    Model: meta-llama/Llama-2-7b-chat-hf
#    Endpoint: http://172.16.0.52:8000
# ✅ All services are healthy
```

### End-to-end 테스트

```bash
# 1. 헬스체크
make health-server

# 2. RAG 질의 (server_http)
make ask-elastic Q="test"

# 3. 모든 것이 정상 동작하는지 확인
```

## 🎯 주요 개선 사항

1. **빠른 상태 확인**: 배포 후 1분 내 모든 서비스 상태 확인 가능
2. **명확한 출력**: 색상과 아이콘으로 상태를 직관적으로 표시
3. **자동화 지원**: 종료 코드로 CI/CD 파이프라인에서 사용 가능
4. **선택적 체크**: 모드에 따라 필요한 서비스만 체크 (불필요한 체크 스킵)

## 📊 체크 로직

```
health 명령어 실행
    ↓
모드 확인 (local/server)
    ↓
┌─────────────────────────┬─────────────────────────┐
│ 서버 모드 또는           │ 로컬 모드                │
│ retriever=elastic       │                         │
├─────────────────────────┼─────────────────────────┤
│ Elasticsearch ping      │ Elasticsearch 스킵      │
│ ✅/❌                   │ ⏭️                      │
└─────────────────────────┴─────────────────────────┘
    ↓
LLM Provider 확인
    ↓
┌─────────────────────────┬─────────────────────────┐
│ server_http +            │ local_api               │
│ SERVER_LLM_BASE_URL     │                         │
├─────────────────────────┼─────────────────────────┤
│ vLLM /v1/models 체크    │ vLLM 스킵              │
│ ✅/❌                   │ ⏭️                      │
└─────────────────────────┴─────────────────────────┘
    ↓
종료 코드 반환 (0: 성공, 1: 실패)
```

## 🚀 다음 단계

Step 6 완료 후:
- 배포 후 빠른 상태 확인 가능
- CI/CD 파이프라인에 통합 가능
- 추가 리팩토링이 필요하면 사용자 요청에 따라 진행
