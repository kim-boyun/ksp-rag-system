# Elasticsearch 서버 모드 가이드

## 📌 개요

Elasticsearch를 사용한 서버 모드는 다음과 같은 장점이 있습니다:

- **확장성**: 대규모 문서 처리
- **하이브리드 검색**: BM25 + Dense Vector Search
- **클러스터 지원**: 분산 환경 운영
- **실시간 인덱싱**: 동적 문서 추가/업데이트

---

## 🚀 빠른 시작

### 1. Elasticsearch 시작

```bash
# Elasticsearch 컨테이너 시작
make elastic-up

# 헬스체크 (30초 후)
make elastic-health
```

**예상 출력**:
```json
{
  "cluster_name" : "docker-cluster",
  "status" : "green",
  "number_of_nodes" : 1,
  "number_of_data_nodes" : 1
}
```

### 2. 인덱스 빌드

```bash
# 1) 먼저 문서 인제스트 (로컬과 동일)
make ingest

# 2) Elasticsearch 인덱스 생성
make index-elastic
```

### 3. 검색 테스트

```bash
# Elasticsearch 기반 검색 (구현 예정)
RETRIEVER_MODE=elastic make retrieve Q="온두라스 연금"
```

---

## 🔑 Elasticsearch 검색 + 개인 LLM

검색만 Elasticsearch를 쓰고, LLM은 서버(vLLM)가 아니라 **본인 API 키(OpenAI 등)** 로 쓰고 싶을 때 사용합니다.

### 1. 설정 파일 만들기

```bash
cp .env.local.example .env.local
```

`.env.local` 을 열어서 다음만 수정합니다.

- **`LLM_API_KEY`**: OpenAI API 키 (또는 사용하는 서비스 키)
- **`LLM_MODEL`**: 모델명 (예: `gpt-3.5-turbo`, `gpt-4`)
- 필요하면 `LLM_API_TYPE` (예: `openai`)

Ollama 등 다른 API를 쓰면 해당 서비스에 맞게 `LLM_API_TYPE`, `LLM_API_KEY`, 엔드포인트 설정을 맞춥니다.

### 2. Elasticsearch 띄우기 + 인덱스 빌드

```bash
make elastic-up
make elastic-health   # 필요 시 30초 후 재시도
make index-elastic    # chunks.jsonl 기준으로 인덱스 생성 (기본값은 .env.server의 Elastic 설정 사용)
```

### 3. 질의/UI 실행

```bash
# CLI
make ask-local Q="궁금한 질문"

# Streamlit UI
make ui-local
# 브라우저: http://localhost:8501
```

정리: **검색 = Elasticsearch**, **LLM = .env.local 에 설정한 개인 LLM** 이 조합으로 동작합니다.

---

## 📊 Elasticsearch 관리

### 서비스 관리

```bash
# 시작
make elastic-up

# 중지
make elastic-down

# 로그 확인
make elastic-logs

# 헬스체크
make elastic-health
```

### 인덱스 관리

```bash
# 인덱스 생성
make index-elastic

# 인덱스 재생성 (기존 삭제 후 생성)
make index-elastic-recreate

# 인덱스 확인
curl http://localhost:9200/ksp_rag_index
```

### Kibana (선택)

Elasticsearch UI로 인덱스를 시각적으로 관리:

```bash
# Kibana 시작
make kibana-up

# 브라우저에서 접속
# http://localhost:5601
```

---

## 🔧 설정

### .env.server 설정

```bash
# Retriever 모드
RETRIEVER_MODE=elastic  # local | elastic

# Elasticsearch
ELASTIC_HOST=elasticsearch  # 컨테이너 이름 (도커 네트워크)
ELASTIC_PORT=9200
ELASTIC_INDEX_NAME=ksp_rag_index
```

### 로컬에서 Elasticsearch 테스트

로컬 개발 시에도 Elasticsearch를 사용할 수 있습니다:

```bash
# .env.local 수정
RETRIEVER_MODE=elastic

# Elasticsearch 시작
make elastic-up

# 인덱스 빌드
make index-elastic

# 검색 (구현 예정)
make retrieve Q="질문"
```

---

## 📋 Elasticsearch 인덱스 구조

### 필드 매핑

```json
{
  "mappings": {
    "properties": {
      "content": {
        "type": "text",
        "analyzer": "standard"
      },
      "embedding": {
        "type": "dense_vector",
        "dims": 384,
        "index": true,
        "similarity": "cosine"
      },
      "metadata": {
        "type": "object",
        "enabled": true
      },
      "chunk_id": {
        "type": "keyword"
      }
    }
  }
}
```

### 하이브리드 검색 전략

1. **BM25 검색**: `content` 필드 (텍스트)
2. **벡터 검색**: `embedding` 필드 (의미적 유사도)
3. **결합**: 두 결과를 점수 기반으로 융합

---

## 🐛 문제 해결

### Elasticsearch 연결 실패

**증상**: `Cannot connect to Elasticsearch`

**해결**:
```bash
# 1. 컨테이너 상태 확인
docker compose ps

# 2. 로그 확인
make elastic-logs

# 3. 재시작
make elastic-down
make elastic-up

# 4. 30초 대기 후 헬스체크
sleep 30
make elastic-health
```

### 메모리 부족 오류

**증상**: Elasticsearch 시작 실패

**해결**:
```bash
# docker-compose.yml에서 메모리 조정
environment:
  - "ES_JAVA_OPTS=-Xms1g -Xmx1g"  # 2g → 1g
```

### 인덱스 생성 실패

**증상**: `Index already exists`

**해결**:
```bash
# 기존 인덱스 삭제 후 재생성
make index-elastic-recreate
```

---

## 📈 성능 비교

| 항목 | 로컬 (BM25+FAISS) | Elasticsearch |
|------|-------------------|---------------|
| 인덱스 빌드 | ⚡⚡⚡ 빠름 | ⚡⚡ 보통 |
| 검색 속도 | ⚡⚡ 빠름 | ⚡⚡⚡ 매우 빠름 |
| 확장성 | ❌ 제한적 | ✅ 우수 |
| 메모리 사용 | 낮음 (~1GB) | 높음 (~2GB+) |
| 동적 업데이트 | ❌ 어려움 | ✅ 쉬움 |
| 적합 환경 | 개발/소규모 | 운영/대규모 |

---

## 🔄 로컬 vs 서버 모드 전환

### 로컬 → 서버 전환

```bash
# 1. .env 파일 변경
cp .env.server .env

# 2. Elasticsearch 시작
make elastic-up

# 3. 인덱스 빌드
make index-elastic

# 4. 앱 실행 (서버 모드)
docker compose --profile server run --rm app python -m ragapp --help
```

### 서버 → 로컬 전환

```bash
# 1. .env 파일 변경
cp .env.local .env

# 2. Elasticsearch 중지
make elastic-down

# 3. 로컬 인덱스 사용
make retrieve Q="질문"
```

---

## 📚 참고 자료

- [Elasticsearch 공식 문서](https://www.elastic.co/guide/en/elasticsearch/reference/8.12/index.html)
- [Dense Vector Search](https://www.elastic.co/guide/en/elasticsearch/reference/8.12/dense-vector.html)
- [Hybrid Search with RRF](https://www.elastic.co/guide/en/elasticsearch/reference/8.12/rrf.html)

---

**Stage 7 완료 ✅**
