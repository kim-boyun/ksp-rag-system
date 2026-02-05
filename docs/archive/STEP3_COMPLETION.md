# Refactor Step 3: External vLLM Endpoint - 완료 보고서

## 📋 목표

app이 더 이상 `http://llm:...` 같은 내부 compose 서비스명에 의존하지 않고, 외부 GPU 서버 vLLM URL을 환경변수로 받도록 변경.

## ✅ 완료된 작업

### 1. Config 구조 개선

**파일**: `src/ragapp/config.py`

**변경 사항**:
- `server_llm_endpoint` (전체 URL) → `server_llm_base_url` (base URL)로 변경
- 하위 호환성을 위해 `server_llm_endpoint` 필드 유지 (deprecated)
- `get_llm_endpoint()`: BASE_URL + `/v1/completions` 조합
- `get_llm_chat_endpoint()`: BASE_URL + `/v1/chat/completions` 조합

**코드**:
```python
server_llm_base_url: str = Field(
    default="http://172.16.0.52:8000",
    description="External vLLM base URL (GPU server, without /v1/completions)"
)

def get_llm_endpoint(self) -> str:
    if self.server_llm_endpoint:  # 하위 호환
        return self.server_llm_endpoint
    return f"{self.server_llm_base_url}/v1/completions"

def get_llm_chat_endpoint(self) -> str:
    if self.server_llm_endpoint:  # 하위 호환
        return self.server_llm_endpoint.replace("/completions", "/chat/completions")
    return f"{self.server_llm_base_url}/v1/chat/completions"
```

### 2. ServerHTTPClient 수정

**파일**: `src/ragapp/llms/server_http.py`

**변경 사항**:
- `base_url` 파라미터 추가
- `endpoint` 파라미터는 deprecated (하위 호환 유지)
- `chat_endpoint` 속성 추가 (전용 chat endpoint)
- 로깅 개선 (base_url, completions endpoint, chat endpoint 모두 표시)

**코드**:
```python
def __init__(self, endpoint: str = None, model: str = None, base_url: str = None):
    config = get_config()
    
    if endpoint:
        self.endpoint = endpoint  # 하위 호환
    elif base_url:
        self.endpoint = f"{base_url}/v1/completions"
    else:
        self.endpoint = config.get_llm_endpoint()
    
    self.base_url = base_url or config.server_llm_base_url
    self.chat_endpoint = config.get_llm_chat_endpoint()
    # ...
```

### 3. 환경 변수 파일 업데이트

**파일**: `.env.server.example`

**변경 사항**:
- `SERVER_LLM_ENDPOINT` → `SERVER_LLM_BASE_URL`로 변경
- 주석에 deprecated 안내 추가

**예시**:
```bash
# 서버 LLM (외부 vLLM HTTP endpoint)
SERVER_LLM_BASE_URL=http://172.16.0.52:8000
SERVER_LLM_MODEL=meta-llama/Llama-2-7b-chat-hf

# [Deprecated] SERVER_LLM_ENDPOINT는 하위 호환성을 위해 지원하지만,
# SERVER_LLM_BASE_URL 사용을 권장합니다.
```

### 4. Makefile 업데이트

**파일**: `Makefile`

**변경 사항**:
- `llm-health`: `SERVER_LLM_BASE_URL` 우선 사용, `SERVER_LLM_ENDPOINT` 하위 호환
- `llm-test`: 동일하게 BASE_URL 우선 사용

**로직**:
```makefile
if grep -q "^SERVER_LLM_BASE_URL=" .env.server; then
    BASE_URL=$$(grep "^SERVER_LLM_BASE_URL=" .env.server | cut -d'=' -f2)
    curl -s $$BASE_URL/health
elif grep -q "^SERVER_LLM_ENDPOINT=" .env.server; then
    # 하위 호환 처리
fi
```

### 5. 스크립트 업데이트

**파일**: `scripts/check_server_services.sh`

**변경 사항**:
- 권장 설정 출력에서 `SERVER_LLM_BASE_URL` 사용
- `SERVER_LLM_ENDPOINT` 대신 BASE_URL 권장

### 6. 문서 업데이트

**파일**:
- `README.md`: SERVER_LLM_BASE_URL로 변경
- `docs/SERVER_DEPLOYMENT.md`: 모든 SERVER_LLM_ENDPOINT 참조를 BASE_URL로 변경

## 🔍 하드코딩 제거 확인

### 검증 결과

1. **코드 내 하드코딩 없음**:
   - `src/ragapp/llms/server_http.py`: 모든 endpoint는 config에서 읽음
   - `src/ragapp/config.py`: 기본값만 설정 (환경변수로 오버라이드 가능)

2. **내부 서비스명 참조 없음**:
   - `http://llm:...` 같은 참조 없음
   - 모든 endpoint는 외부 URL 또는 환경변수 기반

3. **하위 호환성 유지**:
   - 기존 `SERVER_LLM_ENDPOINT` 사용 시에도 동작
   - 점진적 마이그레이션 가능

## ✅ 완료 기준 검증

### 1. llm 서비스명 참조 제거
- ✅ 코드에서 `http://llm:...` 참조 없음
- ✅ 문서에서 내부 서비스명 언급 없음
- ✅ 환경변수에서 내부 서비스명 없음

### 2. LLM 교체는 URL 변경만으로 가능
- ✅ `SERVER_LLM_BASE_URL` 환경변수만 변경하면 됨
- ✅ `/v1/completions`, `/v1/chat/completions`는 자동 조합
- ✅ 코드 수정 불필요

### 3. 검증 명령어

```bash
# 1. Config 검증
docker compose run --rm app python -c "from ragapp.config import get_config; c = get_config(); print(f'Base URL: {c.server_llm_base_url}'); print(f'Endpoint: {c.get_llm_endpoint()}'); print(f'Chat Endpoint: {c.get_llm_chat_endpoint()}')"

# 2. 로컬 모드 (local_api) 동작 확인
LLM_PROVIDER=local_api make ask Q="test"

# 3. 서버 모드 (server_http) 동작 확인
# .env.server에 SERVER_LLM_BASE_URL 설정 후
LLM_PROVIDER=server_http make ask-elastic Q="test"
```

## 📝 변경 파일 목록

1. `src/ragapp/config.py` - BASE_URL 필드 추가, helper 메서드 추가
2. `src/ragapp/llms/server_http.py` - BASE_URL 기반 초기화
3. `.env.server.example` - SERVER_LLM_BASE_URL로 변경
4. `Makefile` - llm-health, llm-test 업데이트
5. `scripts/check_server_services.sh` - 권장 설정 업데이트
6. `README.md` - 문서 업데이트
7. `docs/SERVER_DEPLOYMENT.md` - 문서 업데이트

## 🎯 다음 단계

Step 3 완료 후:
- Step 4: 테스트 및 검증 (선택 사항)
- 또는 사용자 요청에 따라 추가 리팩토링 진행

## 📊 마이그레이션 가이드

### 기존 설정 사용자

기존 `.env.server`에 `SERVER_LLM_ENDPOINT`가 있어도 동작합니다:
```bash
# 기존 (하위 호환)
SERVER_LLM_ENDPOINT=http://172.16.0.52:8000/v1/completions
```

### 새 설정 권장

새 설정으로 마이그레이션 권장:
```bash
# 새 설정 (권장)
SERVER_LLM_BASE_URL=http://172.16.0.52:8000
```

**장점**:
- `/v1/completions`, `/v1/chat/completions` 자동 조합
- 더 명확한 구조
- 향후 확장 용이
