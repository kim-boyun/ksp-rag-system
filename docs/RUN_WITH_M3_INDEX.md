# bge-m3 인덱스로 실행 및 확인

m3 백업(import) 후 서버 모드에서 **bge-m3로 만든 인덱스**를 쓰는 방법입니다.

## 1. 설정 (.env.server)

m3 인덱스는 **1024차원**이므로, 검색 시에도 **같은 임베딩 모델**을 써야 합니다.

```bash
# 인덱스명: 집에서 m3를 ksp_rag_index 로 만들었다면 그대로. 별도 이름(ksp_rag_index_m3)이면 그 이름으로
ELASTIC_INDEX_NAME=ksp_rag_index

# 검색 시 임베딩 모델 (인덱스 빌드 시 쓴 모델과 동일 필수)
LOCAL_EMBEDDING_MODEL=BAAI/bge-m3
```

**인덱스 이름은 꼭 바꿀 필요 없습니다.** 집에서 `ksp_rag_index` 로 m3 인덱싱했다면 `ELASTIC_INDEX_NAME=ksp_rag_index` 그대로 두고, `LOCAL_EMBEDDING_MODEL=BAAI/bge-m3` 만 맞추면 됩니다.

## 2. Elasticsearch 실행 (import 직후라면 이미 완료)

```bash
# 아직 안 올렸다면
make elastic-up

# 30초 정도 뒤 헬스체크
make elastic-health
```

초록색 `"status" : "green"` (또는 yellow) 이면 OK.

## 3. 인덱스/임베딩 차원 확인

**1) 실제 있는 인덱스 이름 확인**

```bash
curl -s "http://localhost:9200/_cat/indices?v"
```

여기 나오는 `index` 이름(예: `ksp_rag_index` 또는 `ksp_rag_index_m3`)을 사용하면 됩니다.

**2) 해당 인덱스가 1024차원(m3)인지 확인**

`INDEX`를 위에서 본 인덱스 이름으로 바꿔서:

```bash
curl -s "http://localhost:9200/INDEX/_mapping?pretty" | grep -E '"dims"|"embedding"'
```

또는 전체 매핑을 보고 `embedding` → `dims` 값 확인:

```bash
curl -s "http://localhost:9200/INDEX/_mapping?pretty"
```

- `"dims" : 1024` → m3 인덱스. `LOCAL_EMBEDDING_MODEL=BAAI/bge-m3` 로 사용.
- `"dims" : 384` → bge-small 인덱스. `LOCAL_EMBEDDING_MODEL=BAAI/bge-small-en-v1.5` 로 사용.

(인덱스가 하나도 없으면 `make elastic-import` 로 백업 복원이 된 뒤인지 확인하세요.)

## 4. 앱/UI 실행

```bash
# .env.server → .env 복사 후 서버 프로파일로 기동
make up-server
# 또는 UI까지 같이
docker compose --profile server up -d
```

UI만 따로:

```bash
cp .env.server .env
make ui-server
# 또는
docker compose --profile server up -d ui
```

브라우저: **http://localhost:8501**

## 5. 동작 확인

- **CLI 질의**
  ```bash
  cp .env.server .env
  make ask-server Q="문서에서 중요한 정책을 요약해줘"
  # 또는
  docker compose --profile server run --rm app python -m ragapp ask "문서에서 중요한 정책을 요약해줘"
  ```
- **UI**: 사이드바에 설정한 인덱스명이 보이고, 질문 시 참고 문서/답변이 나오면 정상.

## 6. 문제 시 체크리스트

| 현상 | 확인 |
|------|------|
| 인덱스 없음 | `make elastic-import` 실행했는지, `data/elastic-data-backup.tar.gz` 내용에 `indices/` 등이 있는지 |
| 검색/임베딩 에러 | `.env.server`에 `LOCAL_EMBEDDING_MODEL=BAAI/bge-m3`, `ELASTIC_INDEX_NAME`이 실제 인덱스 이름과 같은지 |
| LLM 응답 없음 | `make llm-health` 로 GPU 서버 vLLM 연결 여부 확인 |
