# Windows에서 KSP RAG System 실행하기

맥에서 만든 레포를 윈도우로 가져와서 실행할 때 참고하는 가이드입니다.

## 점검 결과 요약

- **Python 코드**: `pathlib.Path` 사용으로 경로 처리 크로스 플랫폼 호환됨.
- **실행 환경**: 앱은 Docker 컨테이너 안에서 동작하므로 **Windows에서도 동일한 Linux 환경**으로 실행됩니다.
- **주의 사항**:
  - **Makefile / 셸 스크립트**(`make`, `setup.sh`, `scripts/*.sh`)는 Windows 기본 셸에서 동작하지 않습니다.
  - **해결**: 아래처럼 **PowerShell에서 Docker 명령만** 사용하거나, [Git Bash](https://git-scm.com/download/win)를 설치한 뒤 `make`를 사용할 수 있습니다.

---

## 필요 사항

- **Docker Desktop for Windows** 설치 및 실행 중
- (선택) Git for Windows 설치 시 Git Bash에서 `make` 사용 가능

---

## 1. 환경 설정 (최초 1회)

PowerShell을 **프로젝트 루트**에서 연 뒤:

```powershell
# 자동 설정 (권장)
.\setup.ps1
```

또는 수동으로:

```powershell
Copy-Item .env.local.example .env.local
Copy-Item .env.server.example .env.server
```

이후 **`.env.local`**을 열어 **OpenAI API 키**를 입력하세요.

```
LLM_API_KEY=sk-proj-your-actual-openai-key-here
```

로컬 모드에서 RAG 질의를 쓰려면 이 키가 필요합니다.

---

## 2. Docker 이미지 빌드

```powershell
docker compose build app
```

최초 빌드는 5~10분 정도 걸릴 수 있습니다.

---

## 3. 로컬 모드로 사용하기 (빠른 시작)

### 3.1 문서 인제스트 (PDF → chunks)

```powershell
# PDF는 data\raw\ 에 넣은 뒤
docker compose --profile local run --rm app python -m ragapp ingest
```

### 3.2 로컬 인덱스 빌드 (BM25 + FAISS)

```powershell
docker compose --profile local run --rm app python -m ragapp index --embedding-model BAAI/bge-small-en-v1.5
```

실행 전에 `.env`가 로컬 설정이어야 하므로:

```powershell
Copy-Item .env.local .env
docker compose --profile local run --rm app python -m ragapp index --embedding-model BAAI/bge-small-en-v1.5
```

> 💡 **bge-m3 사용 옵션 (고품질)**  
> - 정확도/다국어 지원을 더 중요하게 볼 경우:  
>   `docker compose --profile local run --rm app python -m ragapp index --embedding-model BAAI/bge-m3`  
> - 이 경우에도, 해당 인덱스를 쓸 때는 **검색 임베딩 모델도 BAAI/bge-m3로 맞춰야** 합니다.

### 3.3 RAG 질의 (CLI)

```powershell
Copy-Item .env.local .env
docker compose --profile local run --rm app python -m ragapp ask "What is the main topic?"
```

### 3.4 웹 UI 실행

```powershell
Copy-Item .env.local .env
docker compose --profile ui up -d
```

브라우저에서 **http://localhost:8501** 접속.

---

## 4. 서버 모드 (Elasticsearch + 외부 vLLM)

### 4.1 Elasticsearch + 앱 시작

```powershell
Copy-Item .env.server .env
docker compose --profile server up -d
```

### 4.2 Elasticsearch 인덱스 빌드

```powershell
Copy-Item .env.server .env
docker compose --profile server run --rm app python -m ragapp index-elastic
```

### 4.3 RAG 질의 (서버 모드)

```powershell
Copy-Item .env.server .env
docker compose --profile server run --rm app python -m ragapp ask "질문 내용" --mode elastic
```

### 4.4 서버 모드 웹 UI

```powershell
Copy-Item .env.server .env
docker compose --profile ui up -d
```

역시 **http://localhost:8501** 접속.

---

## 5. Makefile 대응표 (Windows에서 쓸 명령)

| 목적 | 맥/리눅스 (make) | Windows (PowerShell) |
|------|------------------|----------------------|
| 환경 설정 | `make setup` | `.\setup.ps1` |
| 빌드 | `make build` | `docker compose build app` |
| 인제스트 | `make ingest` | `Copy-Item .env.local .env; docker compose --profile local run --rm app python -m ragapp ingest` |
| 로컬 인덱스 (bge-small, 빠름) | `make index-small` | `Copy-Item .env.local .env; docker compose --profile local run --rm app python -m ragapp index --embedding-model BAAI/bge-small-en-v1.5` |
| 로컬 인덱스 (bge-m3, 고품질) | `make index` | `Copy-Item .env.local .env; docker compose --profile local run --rm app python -m ragapp index --embedding-model BAAI/bge-m3` |
| 로컬 질의 | `make ask-local Q="질문"` | `Copy-Item .env.local .env; docker compose --profile local run --rm app python -m ragapp ask "질문"` |
| UI (로컬) | `make ui-local` | `Copy-Item .env.local .env; docker compose --profile ui up -d` |
| 서버 시작 | `make up-server` | `Copy-Item .env.server .env; docker compose --profile server up -d` |
| ES 인덱스 | `make index-elastic` | `Copy-Item .env.server .env; docker compose --profile server run --rm app python -m ragapp index-elastic` |
| 테스트 | `make test` | `docker compose --profile local run --rm app pytest tests/ -v` |
| 컨테이너 종료 | `make down` | `docker compose down` |

---

## 6. 스모크 테스트 / 셸 스크립트

`make smoke-test`, `scripts/smoke_test.sh` 등은 **bash** 기반이라 Windows PowerShell에서는 실행되지 않습니다.

- **방법 1**: [Git for Windows](https://git-scm.com/download/win) 설치 후 **Git Bash**에서:
  ```bash
  make smoke-test
  ```
- **방법 2**: 수동으로 아래 순서로 확인:
  1. 인제스트 → `data\processed\chunks.jsonl` 생성 여부
  2. 로컬 인덱스 빌드 후 `docker compose --profile local run --rm app python -m ragapp retrieve "테스트 질문"`
  3. `docker compose --profile local run --rm app python -m ragapp ask "테스트 질문"`

---

## 7. 적용한 수정 사항 (맥→윈도우 호환)

- **Dockerfile**: `.env.local` / `.env.server`가 없어도 빌드되도록, 예제 파일(`.env.local.example`, `.env.server.example`)을 복사하도록 변경했습니다. 맥에서 첫 클론 후에도 동일하게 빌드 가능합니다.
- **setup.ps1**: Windows에서 한 번에 `.env.local`, `.env.server`를 생성하는 PowerShell 스크립트를 추가했습니다.

이제 윈도우에서는 **PowerShell + Docker 명령**만으로 동일하게 사용할 수 있습니다.
