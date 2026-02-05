# 환경 변수 파일 가이드

이 레포지토리에는 3개의 환경 변수 파일이 있습니다. 각각의 역할과 사용 방법을 설명합니다.

## 📁 파일 구조

```
.env                    # 런타임 파일 (자동 생성, gitignore)
.env.local              # 로컬 개발 템플릿 (gitignore, 직접 생성)
.env.server             # 서버 운영 템플릿 (gitignore, 직접 생성)
.env.local.example      # 로컬 개발 예시 (git에 커밋)
.env.server.example     # 서버 운영 예시 (git에 커밋)
```

## 🔄 각 파일의 역할

### 1. `.env` (런타임 파일)

**역할**: Docker 컨테이너가 실제로 사용하는 환경 변수 파일

**특징**:
- **자동 생성**: Makefile이 `.env.local` 또는 `.env.server`를 복사하여 생성
- **gitignore**: Git에 커밋되지 않음 (개인 설정 포함)
- **우선순위**: Docker Compose에서 `.env.local`보다 우선순위가 높음

**사용 방법**:
```bash
# Makefile이 자동으로 생성
make ask-local    # → cp .env.local .env
make ask-server   # → cp .env.server .env
```

**docker-compose.yml 설정**:
```yaml
env_file:
  - .env.local  # 기본값
  - .env        # 있으면 덮어씀 (우선순위 높음)
```

### 2. `.env.local` (로컬 개발 템플릿)

**역할**: 로컬 개발 환경 설정 템플릿

**설정 내용**:
- `MODE=local`
- `RETRIEVER_MODE=local` (BM25 + FAISS)
- `LLM_PROVIDER=local_api` (OpenAI API)
- `LLM_API_KEY=your-key` (실제 API 키 필요)

**사용 시나리오**:
- Mac에서 로컬 개발
- GPU 서버 없이 개발
- OpenAI API 사용

**생성 방법**:
```bash
cp .env.local.example .env.local
vim .env.local  # LLM_API_KEY 입력
```

**사용 명령어**:
```bash
make ask-local      # .env.local → .env 복사 후 실행
make index          # .env.local → .env 복사 후 실행
make ui-local       # .env.local → .env 복사 후 실행
```

### 3. `.env.server` (서버 운영 템플릿)

**역할**: 서버 운영 환경 설정 템플릿

**설정 내용**:
- `MODE=server`
- `RETRIEVER_MODE=elastic` (Elasticsearch)
- `LLM_PROVIDER=server_http` (외부 vLLM)
- `SERVER_LLM_BASE_URL=http://172.16.0.52:8000` (GPU 서버 주소)
- `ELASTIC_HOST=elasticsearch` (또는 `host.docker.internal`)

**사용 시나리오**:
- 운영 서버 배포
- Elasticsearch 사용
- 외부 GPU 서버 vLLM 사용

**생성 방법**:
```bash
cp .env.server.example .env.server
vim .env.server  # SERVER_LLM_BASE_URL 설정
```

**사용 명령어**:
```bash
make ask-server       # .env.server → .env 복사 후 실행
make index-elastic    # .env.server → .env 복사 후 실행
make ui-server        # .env.server → .env 복사 후 실행
```

## 🔄 동작 원리

### Makefile의 자동 전환

각 Makefile 타겟은 자동으로 올바른 템플릿을 `.env`로 복사합니다:

```makefile
# 로컬 모드 타겟
ask-local:
	cp .env.local .env  # ← 템플릿을 .env로 복사
	docker compose --profile local run --rm app python -m ragapp ask "$(Q)"

# 서버 모드 타겟
ask-server:
	cp .env.server .env  # ← 템플릿을 .env로 복사
	docker compose --profile server run --rm app python -m ragapp ask "$(Q)"
```

### Docker Compose의 환경 변수 로드

`docker-compose.yml`에서 환경 변수를 로드하는 순서:

```yaml
env_file:
  - .env.local  # 1순위: 기본값
  - .env        # 2순위: 있으면 덮어씀 (우선순위 높음)
```

**로드 순서**:
1. `.env.local` 로드 (기본값)
2. `.env` 로드 (있으면 덮어씀)

## 📊 파일 비교

| 항목 | `.env.local` | `.env.server` | `.env` |
|------|--------------|---------------|--------|
| **용도** | 로컬 개발 템플릿 | 서버 운영 템플릿 | 런타임 파일 |
| **Git** | ❌ 커밋 안됨 | ❌ 커밋 안됨 | ❌ 커밋 안됨 |
| **생성** | 수동 생성 | 수동 생성 | 자동 생성 (Makefile) |
| **MODE** | `local` | `server` | 복사된 파일에 따라 다름 |
| **Retriever** | `local` (BM25+FAISS) | `elastic` (Elasticsearch) | 복사된 파일에 따라 다름 |
| **LLM** | `local_api` (OpenAI) | `server_http` (vLLM) | 복사된 파일에 따라 다름 |

## ✅ 사용 가이드

### 로컬 개발 시

```bash
# 1. .env.local 생성 (최초 1회)
cp .env.local.example .env.local
vim .env.local  # LLM_API_KEY 입력

# 2. 로컬 모드 명령어 사용
make ask-local Q="질문"
make index
make ui-local
```

### 서버 배포 시

```bash
# 1. .env.server 생성 (최초 1회)
cp .env.server.example .env.server
vim .env.server  # SERVER_LLM_BASE_URL 설정

# 2. 서버 모드 명령어 사용
make ask-server Q="질문"
make index-elastic
make ui-server
```

## ⚠️ 주의사항

1. **`.env`는 수동으로 편집하지 마세요**
   - Makefile이 자동으로 생성/업데이트
   - 수동 편집 시 다음 명령어 실행 시 덮어써짐

2. **`.env.local`과 `.env.server`는 템플릿 파일**
   - 실제 사용되는 파일은 `.env`
   - 필요시 직접 수정 가능

3. **Git에 커밋되지 않음**
   - 모든 `.env*` 파일은 `.gitignore`에 포함
   - `.env*.example` 파일만 Git에 커밋됨

## 🔍 현재 상태 확인

```bash
# 현재 .env 파일 내용 확인
cat .env | grep MODE
cat .env | grep LLM_PROVIDER

# 어떤 템플릿에서 복사되었는지 확인
ls -la .env .env.local .env.server
```

## 📝 요약

- **`.env.local`**: 로컬 개발용 템플릿 (OpenAI API)
- **`.env.server`**: 서버 운영용 템플릿 (외부 vLLM)
- **`.env`**: 런타임 파일 (Makefile이 자동 생성)

**사용 방법**: Makefile 명령어만 사용하면 자동으로 올바른 파일이 사용됩니다!
