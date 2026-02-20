# 환경 변수 파일 가이드

이 레포지토리에는 로컬(Elasticsearch + 개인 LLM)과 서버(Elasticsearch + vLLM)용 환경 변수 파일을 사용합니다.

## 📁 파일 구조

```
.env                    # 런타임 파일 (Makefile이 복사하여 생성, gitignore)
.env.local       # 로컬 개발 템플릿 (Elasticsearch + 개인 LLM, gitignore)
.env.server             # 서버 운영 템플릿 (gitignore)
.env.local.example  # 로컬 개발 예시 (git에 커밋)
.env.server.example     # 서버 운영 예시 (git에 커밋)
```

## 🔄 각 파일의 역할

### 1. `.env` (런타임 파일)

**역할**: Docker 컨테이너가 실제로 사용하는 환경 변수 파일

**특징**:
- **자동 생성**: Makefile이 `.env.local` 또는 `.env.server`를 복사하여 생성
- **gitignore**: Git에 커밋되지 않음
- 앱 설정(`config`)은 `.env`를 읽음

**사용 방법**:
```bash
make ask-local    # → cp .env.local .env 후 실행
make ask-server   # → cp .env.server .env 후 실행
```

**docker-compose.yml**:
```yaml
env_file:
  - .env  # Makefile에서 .env.local 또는 .env.server를 .env로 복사
```

### 2. `.env.local` (로컬 개발 템플릿)

**역할**: 로컬 개발 환경 — Elasticsearch 검색 + 개인 LLM(OpenAI 등)

**설정 내용**:
- `MODE=local`
- `RETRIEVER_MODE=elastic` (Elasticsearch)
- `LLM_PROVIDER=local_api` (OpenAI API)
- `ELASTIC_HOST`, `ELASTIC_PORT`, `ELASTIC_INDEX_NAME`
- `LLM_API_KEY=your-key` (실제 API 키 필요)

**사용 시나리오**:
- Mac/Windows에서 로컬 개발
- Elasticsearch(Docker) + OpenAI API 조합
- GPU 서버(vLLM) 없이 개발

**생성 방법**:
```bash
cp .env.local.example .env.local
vim .env.local  # LLM_API_KEY 입력
```

**사용 명령어**:
```bash
make up-local       # .env.local → .env 복사 후 Elasticsearch + 앱 시작
make ask-local      # .env.local → .env 복사 후 질의
make index-local    # Elasticsearch 인덱스 빌드
make ui-local       # Streamlit UI (Elastic + 개인 LLM)
```

### 3. `.env.server` (서버 운영 템플릿)

**역할**: 서버 운영 환경 — Elasticsearch + 외부 vLLM

**설정 내용**:
- `MODE=server`
- `RETRIEVER_MODE=elastic` (Elasticsearch)
- `LLM_PROVIDER=server_http` (외부 vLLM)
- `SERVER_LLM_BASE_URL`, `SERVER_LLM_MODEL`
- `ELASTIC_HOST=elasticsearch` 등

**사용 시나리오**:
- 운영 서버 배포
- Elasticsearch + GPU 서버 vLLM 사용

**생성 방법**:
```bash
cp .env.server.example .env.server
vim .env.server  # SERVER_LLM_BASE_URL 등 설정
```

**사용 명령어**:
```bash
make ask-server       # .env.server → .env 복사 후 실행
make index-elastic    # .env.server → .env 복사 후 Elasticsearch 인덱스 빌드
make ui-server        # .env.server → .env 복사 후 UI 실행
```

## 🔄 동작 원리

1. **설정 로드**: 앱은 `src/ragapp/config.py`에서 **`.env`** 만 읽습니다.
2. **Makefile**: 각 타깃 실행 전에 `.env.local` 또는 `.env.server`를 `.env`로 복사합니다.
3. **Docker Compose**: 컨테이너에 `.env`를 전달하므로, 복사된 내용이 그대로 적용됩니다.

요약: **로컬 개발 = .env.local (Elasticsearch + 개인 LLM), 서버 = .env.server (Elasticsearch + vLLM)** 입니다.
