# 맥북에서 처음부터 세팅하기 (인제스트 제외)

윈도우에서 만든 인제스트 결과(`chunks.jsonl`)만 가져왔을 때, 맥북에서 **인제스트 없이** 임베딩·검색·질의까지 하는 방법입니다.

---

## 1. 필요한 것

- **Docker Desktop** (Mac용 설치 후 실행)
- 프로젝트 폴더 (클론했거나 복사해 둔 `ksp-rag-system`)
- 윈도우에서 가져온 **`data/processed/chunks.jsonl`** 파일

---

## 2. 프로젝트 열기

```bash
cd /경로/ksp-rag-system
```

(또는 Finder에서 폴더 열고 터미널에서 `cd`로 해당 경로로 이동)

---

## 3. 환경 설정

### 3.1 env 파일 만들기

```bash
make setup
```

- 없으면 `.env.local`, `.env.server`가 예시 파일에서 복사됩니다.

### 3.2 로컬용 설정 수정

`.env.local` 파일을 열어서 **반드시** 다음만 넣거나 확인하세요.

- **`LLM_API_KEY`**  
  OpenAI API 키 (로컬에서 질의응답 쓰려면 필요).  
  예: `LLM_API_KEY=sk-...`

나머지 값은 기본값 그대로 둬도 됩니다.

---

## 4. 청크 파일 위치 확인 (인제스트 생략)

윈도우에서 가져온 파일을 아래 위치에 두세요.

```
ksp-rag-system/
  data/
    processed/
      chunks.jsonl   ← 여기에 넣기
```

다른 경로에 두었다면, 뒤에서 나오는 `make index` 대신 아래처럼 경로만 지정해서 실행하면 됩니다.

```bash
docker compose --profile local run --rm app python -m ragapp index --chunks /app/data/processed/chunks.jsonl
```

(컨테이너 안에서는 프로젝트 루트가 `/app`이므로, 호스트의 `data/processed/chunks.jsonl`은 `/app/data/processed/chunks.jsonl`로 보입니다.)

---

## 5. Docker 이미지 빌드

```bash
make build
```

한 번만 하면 됩니다.

---

## 6. 인덱스 빌드 (임베딩) — 인제스트 대신 하는 단계

`chunks.jsonl`이 `data/processed/chunks.jsonl`에 있다고 가정하면:

```bash
make index
```

- 기본 임베딩 모델: **BAAI/bge-m3**
- 결과: `data/index/` 에 FAISS + BM25 인덱스 생성

다른 경로의 청크 파일을 쓰려면:

```bash
cp .env.local .env
docker compose --profile local run --rm app python -m ragapp index \
  --chunks data/processed/chunks.jsonl \
  --output data/index
```

(호스트의 `data/processed`가 컨테이너의 `/app/data/processed`로 마운트되므로 위 경로로 지정하면 됩니다.)

---

## 7. 동작 확인

### 7.1 설정/버전

```bash
make config-local   # 설정 확인
make version       # 버전 확인
```

### 7.2 CLI로 질의

```bash
make ask-local Q="궁금한 질문 한 문장"
# 또는
make ask Q="궁금한 질문 한 문장"
```

### 7.3 Streamlit UI (선택)

```bash
cp .env.local .env
make ui-local
```

브라우저에서 **http://localhost:8501** 로 접속해서 질의할 수 있습니다.

---

## 8. 자주 쓰는 명령 정리 (인제스트 제외)

| 목적 | 명령 |
|------|------|
| 설정 확인 | `make config-local` |
| 인덱스 빌드 (임베딩) | `make index` |
| CLI 질의 | `make ask Q="질문"` |
| UI 실행 | `make ui-local` |
| UI 종료 | `make ui-down` |
| Docker 종료 | `make down` |

---

## 9. 문제 생겼을 때

- **`Chunks file not found`**  
  → `data/processed/chunks.jsonl` 존재 여부 확인.  
  → Docker 사용 시 `docker compose` 실행 위치가 프로젝트 루트인지 확인.

- **`Index not found`**  
  → `make index` 를 먼저 실행했는지 확인.  
  → `data/index/` 에 파일이 생성됐는지 확인.

- **API 키 오류**  
  → `.env.local` 의 `LLM_API_KEY` 가 올바른지 확인.

이 가이드는 **인제스트는 하지 않고**, 가져온 `chunks.jsonl`만으로 **임베딩(인덱스 빌드) → 검색/질의**까지 하는 흐름만 설명합니다.
