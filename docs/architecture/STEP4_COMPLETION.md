# Refactor Step 4: Default env profiles - 완료 보고서

## 📋 목표

로컬 개발과 운영 서버에서 기본 환경 프로파일을 명확히 분리:
- 로컬 개발: 기본 `local_api` (개인 계정)
- 운영(App 서버): 기본 `server_http` (GPU vLLM)

## ✅ 완료된 작업

### 1. .env.local 확인 및 설정

**파일**: `.env.local`

**상태**: ✅ 이미 `LLM_PROVIDER=local_api`로 설정되어 있음

```bash
LLM_PROVIDER=local_api  # local_api | server_http
```

### 2. .env.server 업데이트

**파일**: `.env.server`

**변경 사항**:
- `LLM_PROVIDER=server_http` 확인 (이미 설정됨)
- `SERVER_LLM_ENDPOINT` → `SERVER_LLM_BASE_URL`로 업데이트 (Step 3 반영)

**최종 설정**:
```bash
LLM_PROVIDER=server_http  # local_api | server_http
SERVER_LLM_BASE_URL=http://host.docker.internal:8000
SERVER_LLM_MODEL=meta-llama/Llama-2-7b-chat-hf
```

### 3. Makefile 타겟 업데이트

**파일**: `Makefile`

**변경 사항**: 모든 타겟이 올바른 `.env` 파일을 사용하도록 수정

#### 로컬 모드 타겟 (`.env.local` 사용)
- `up-local`: `.env.local` → `.env` 복사 후 시작
- `ask-local`: `.env.local` → `.env` 복사 후 실행
- `ask-rerank`: `.env.local` → `.env` 복사 후 실행
- `index`: `.env.local` → `.env` 복사 후 실행
- `index-local`: `.env.local` → `.env` 복사 후 실행
- `index-small`: `.env.local` → `.env` 복사 후 실행
- `retrieve`: `.env.local` → `.env` 복사 후 실행
- `retrieve-rerank`: `.env.local` → `.env` 복사 후 실행
- `retrieve-json`: `.env.local` → `.env` 복사 후 실행
- `retrieve-sample`: `.env.local` → `.env` 복사 후 실행
- `config-local`: `.env.local` → `.env` 복사 후 실행
- `version`: `.env.local` → `.env` 복사 후 실행
- `ingest-local`: `.env.local` → `.env` 복사 후 실행
- `query-local`: `.env.local` → `.env` 복사 후 실행
- `ui-local`: `.env.local` → `.env` 복사 후 실행

#### 서버 모드 타겟 (`.env.server` 사용)
- `up-server`: `.env.server` → `.env` 복사 후 시작
- `ask-elastic`: `.env.server` → `.env` 복사 후 실행
- `ask-server`: `ask-elastic` 별칭
- `index-elastic`: `.env.server` → `.env` 복사 후 실행
- `index-elastic-recreate`: `.env.server` → `.env` 복사 후 실행
- `retrieve-elastic`: `.env.server` → `.env` 복사 후 실행
- `config-server`: `.env.server` → `.env` 복사 후 실행
- `ingest-server`: `.env.server` → `.env` 복사 후 실행
- `query-server`: `.env.server` → `.env` 복사 후 실행
- `ui-server`: `.env.server` → `.env` 복사 후 실행

**패턴**:
```makefile
target-name: ## 설명 (.env.local 또는 .env.server 사용)
	cp .env.local .env  # 또는 cp .env.server .env
	docker compose --profile <local|server> run --rm app ...
```

### 4. docker-compose.yml 확인

**파일**: `docker-compose.yml`

**상태**: ✅ 이미 올바르게 설정됨

- `app` 서비스: `env_file: [.env.local, .env]` - `.env.local`을 먼저 읽고, `.env`가 있으면 덮어씀
- `ui` 서비스: `env_file: [.env]` - Makefile에서 복사한 `.env` 사용

## ✅ 완료 기준 검증

### 1. 운영 서버에서 실수로 local_api 키 요구하지 않음

**검증**:
- ✅ `make up-server`: `.env.server` 사용 → `LLM_PROVIDER=server_http`
- ✅ `make ask-server`: `.env.server` 사용 → `LLM_PROVIDER=server_http`
- ✅ `make index-elastic`: `.env.server` 사용 → `LLM_PROVIDER=server_http`

**결과**: 운영 서버 명령어는 모두 `.env.server`를 사용하므로 `local_api` 키를 요구하지 않음

### 2. 로컬에서 GPU 서버 없이도 개발 가능

**검증**:
- ✅ `make up-local`: `.env.local` 사용 → `LLM_PROVIDER=local_api`
- ✅ `make ask-local`: `.env.local` 사용 → `LLM_PROVIDER=local_api`
- ✅ `make index`: `.env.local` 사용 → `LLM_PROVIDER=local_api`

**결과**: 로컬 명령어는 모두 `.env.local`을 사용하므로 GPU 서버 없이도 개발 가능

## 📝 변경 파일 목록

1. `.env.server` - `SERVER_LLM_BASE_URL`로 업데이트
2. `Makefile` - 모든 타겟에 `.env` 파일 복사 로직 추가
   - 로컬 타겟: `cp .env.local .env`
   - 서버 타겟: `cp .env.server .env`

## 🔍 검증 방법

### 로컬 모드 검증

```bash
# 1. 로컬 설정 확인
make config-local
# 출력에서 LLM_PROVIDER=local_api 확인

# 2. 로컬 모드 질의 (GPU 서버 없이도 동작)
make ask-local Q="test"
# OpenAI API 키만 있으면 동작
```

### 서버 모드 검증

```bash
# 1. 서버 설정 확인
make config-server
# 출력에서 LLM_PROVIDER=server_http 확인
# 출력에서 SERVER_LLM_BASE_URL 확인

# 2. 서버 모드 질의 (외부 vLLM 호출)
make ask-server Q="test"
# 외부 GPU 서버 vLLM으로 요청 나감
```

## 🎯 주요 개선 사항

1. **명확한 환경 분리**: 로컬/서버 명령어가 각각 올바른 `.env` 파일 사용
2. **실수 방지**: 운영 서버에서 `local_api` 키를 요구하지 않음
3. **개발 편의성**: 로컬에서 GPU 서버 없이도 개발 가능
4. **일관성**: 모든 Makefile 타겟이 동일한 패턴 사용

## 📊 타겟 분류

| 타겟 | 환경 파일 | LLM Provider | 용도 |
|------|----------|--------------|------|
| `up-local` | `.env.local` | `local_api` | 로컬 개발 환경 시작 |
| `up-server` | `.env.server` | `server_http` | 운영 서버 환경 시작 |
| `ask-local` | `.env.local` | `local_api` | 로컬 RAG 질의 |
| `ask-server` | `.env.server` | `server_http` | 서버 RAG 질의 |
| `index` | `.env.local` | `local_api` | 로컬 인덱스 빌드 |
| `index-elastic` | `.env.server` | `server_http` | Elasticsearch 인덱스 빌드 |

## 🚀 다음 단계

Step 4 완료 후:
- Step 5: 추가 검증 및 문서화 (선택 사항)
- 또는 사용자 요청에 따라 추가 리팩토링 진행
