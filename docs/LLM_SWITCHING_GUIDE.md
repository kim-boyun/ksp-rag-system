# LLM 전환 가이드

로컬 개발 시 OpenAI API를 사용하고, 서버 배포 시 외부 vLLM을 사용하는 방법을 설명합니다.

## 🔄 전환 방법

시스템은 **환경 변수 파일**을 통해 자동으로 LLM을 전환합니다. 별도의 코드 수정 없이 Makefile 명령어만 사용하면 됩니다.

### 1. 로컬 개발 모드 (OpenAI API)

**설정 파일**: `.env.local`

```bash
LLM_PROVIDER=local_api  # OpenAI API 사용
LLM_API_KEY=sk-proj-your-key-here
LLM_MODEL=gpt-3.5-turbo
```

**사용 명령어**:
```bash
# 질의응답
make ask-local Q="질문"

# 인덱스 빌드
make index

# UI 실행
make ui-local
```

**동작**:
- OpenAI API를 직접 호출
- GPU 서버 불필요
- 인터넷 연결 필요 (OpenAI API 접근)

### 2. 서버 운영 모드 (외부 vLLM)

**설정 파일**: `.env.server`

```bash
LLM_PROVIDER=server_http  # 외부 vLLM 사용
SERVER_LLM_BASE_URL=http://172.16.0.52:8000  # GPU 서버 주소
SERVER_LLM_MODEL=meta-llama/Llama-2-7b-chat-hf
```

**사용 명령어**:
```bash
# 질의응답
make ask-server Q="질문"
# 또는
make ask-elastic Q="질문"

# 인덱스 빌드
make index-elastic

# UI 실행
make ui-server
```

**동작**:
- 외부 GPU 서버의 vLLM API 호출
- GPU 서버가 실행 중이어야 함
- 네트워크 연결 필요 (GPU 서버 접근)

## 📋 자동 전환 메커니즘

### Makefile이 자동으로 처리

각 Makefile 타겟은 자동으로 올바른 `.env` 파일을 사용합니다:

**로컬 모드 타겟** (`.env.local` 사용):
```makefile
ask-local:
	cp .env.local .env  # ← 자동으로 .env.local 복사
	docker compose --profile local run --rm app python -m ragapp ask "$(Q)"
```

**서버 모드 타겟** (`.env.server` 사용):
```makefile
ask-server:
	cp .env.server .env  # ← 자동으로 .env.server 복사
	docker compose --profile server run --rm app python -m ragapp ask "$(Q)"
```

### 코드에서의 처리

`RAGPipeline`이 `LLM_PROVIDER` 환경 변수를 읽어 자동으로 LLM 클라이언트를 선택합니다:

```python
# src/ragapp/pipeline/rag_pipeline.py
if self.config.llm_provider == "local_api":
    from ragapp.llms.local_api import LocalAPIClient
    self.llm = LocalAPIClient()
elif self.config.llm_provider == "server_http":
    from ragapp.llms.server_http import ServerHTTPClient
    self.llm = ServerHTTPClient()
```

## 🎯 사용 시나리오

### 시나리오 1: 로컬에서 개발

```bash
# 1. .env.local 설정 확인
cat .env.local | grep LLM_PROVIDER
# 출력: LLM_PROVIDER=local_api

# 2. 로컬 모드로 질의
make ask-local Q="테스트 질문"
# → OpenAI API 사용

# 3. 로컬 모드로 UI 실행
make ui-local
# → 브라우저에서 OpenAI API로 질의
```

### 시나리오 2: 서버에 배포

```bash
# 1. .env.server 설정 확인
cat .env.server | grep LLM_PROVIDER
# 출력: LLM_PROVIDER=server_http

# 2. GPU 서버 vLLM 확인
make llm-health
# → 외부 vLLM 연결 확인

# 3. 서버 모드로 질의
make ask-server Q="테스트 질문"
# → 외부 vLLM 사용

# 4. 서버 모드로 UI 실행
make ui-server
# → 브라우저에서 외부 vLLM으로 질의
```

### 시나리오 3: 로컬에서 서버 vLLM 테스트

로컬 개발 중에도 서버 vLLM을 테스트하고 싶다면:

```bash
# 1. .env.local 수정
vim .env.local
# LLM_PROVIDER=server_http로 변경
# SERVER_LLM_BASE_URL=http://<GPU_SERVER_IP>:8000 설정

# 2. 로컬 모드로 질의 (하지만 server_http 사용)
make ask-local Q="테스트 질문"
# → 외부 vLLM 사용 (로컬에서 실행하지만)
```

## 🔍 현재 설정 확인

### 현재 LLM Provider 확인

```bash
# 로컬 모드 설정 확인
make config-local | grep "LLM Provider"

# 서버 모드 설정 확인
make config-server | grep "LLM Provider"
```

### 헬스체크로 확인

```bash
# 로컬 모드 헬스체크
make health-local
# → vLLM은 스킵됨 (local_api 사용)

# 서버 모드 헬스체크
make health-server
# → Elasticsearch + vLLM 모두 체크
```

## 📊 명령어 매핑

| 목적 | 로컬 모드 (local_api) | 서버 모드 (server_http) |
|------|----------------------|----------------------|
| 질의응답 | `make ask-local` | `make ask-server` |
| 인덱스 빌드 | `make index` | `make index-elastic` |
| UI 실행 | `make ui-local` | `make ui-server` |
| 설정 확인 | `make config-local` | `make config-server` |
| 헬스체크 | `make health-local` | `make health-server` |

## ⚠️ 주의사항

1. **환경 변수 파일 분리**: `.env.local`과 `.env.server`는 서로 다른 용도입니다. 혼동하지 마세요.

2. **GPU 서버 연결**: `server_http` 모드 사용 시 GPU 서버가 실행 중이어야 합니다.

3. **네트워크 접근**: 
   - `local_api`: 인터넷에서 OpenAI API 접근 필요
   - `server_http`: GPU 서버 네트워크 접근 필요

4. **비용**: 
   - `local_api`: OpenAI API 사용량에 따라 비용 발생
   - `server_http`: GPU 서버 운영 비용 (자체 호스팅)

## 🚀 빠른 참조

```bash
# 로컬 개발 시작
make ask-local Q="질문"

# 서버 배포 후 테스트
make ask-server Q="질문"

# 현재 설정 확인
make config-local  # 또는 make config-server
```
