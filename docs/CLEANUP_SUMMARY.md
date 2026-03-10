# 정리 요약 (BGE-Small 제거, M3 단일화)

## 개요

- **BGE-Small(bge-small-en-v1.5)** 사용을 중단하고 **BGE-M3**만 사용하도록 프로젝트를 정리했습니다.
- Elasticsearch 인덱스는 **ksp_rag_index_m3** 하나만 사용합니다.

---

## 1. Makefile 변경

| 변경 | 내용 |
|------|------|
| **제거** | `index-small`, `index-sample` (중복·미지원 타깃) |
| **제거** | `index-elastic-small`, `index-elastic-recreate-small` |
| **제거** | `elastic-delete-index-small` |
| **제거** | `ask-elastic` 중복 정의, `retrieve-sample` |
| **수정** | `index-elastic` / `index-elastic-recreate` → BGE-M3 기준으로 주석 정리 |
| **수정** | `elastic-index-status` → `ksp_rag_index_m3` 문서 수만 표시 |
| **수정** | `elastic-index-model` → `ksp_rag_index_m3`(1024차원)만 표시 |
| **이름 변경** | `index-elastic-m3-native` → `index-elastic-native` (M3 네이티브 빌드) |

---

## 2. 설정 기본값

| 항목 | 변경 전 | 변경 후 |
|------|---------|---------|
| **config.py** `elastic_index_name` | `ksp_rag_index` | `ksp_rag_index_m3` |
| **.env.server.example** | 주석 포함 | `ELASTIC_INDEX_NAME=ksp_rag_index_m3`, `LOCAL_EMBEDDING_MODEL=BAAI/bge-m3` 로 단순화 |
| **.env.local.example** | `ELASTIC_INDEX_NAME=ksp_rag_index_m3` 만 | `LOCAL_EMBEDDING_MODEL=BAAI/bge-m3` 추가 (검색 시 인덱스와 동일 모델) |

---

## 3. 사용 시 참고

- **인덱스 빌드**: `make index-elastic` 또는 `make index-elastic-recreate` → 항상 **BGE-M3**로 `ELASTIC_INDEX_NAME`(기본 `ksp_rag_index_m3`)에 빌드됩니다.
- **환경 변수**: `.env` / `.env.server` / `.env.local` 에서  
  `ELASTIC_INDEX_NAME=ksp_rag_index_m3`, `LOCAL_EMBEDDING_MODEL=BAAI/bge-m3` 로 두면 됩니다.
- **인덱스 확인**: `make elastic-index-status`, `make elastic-index-model` 로 문서 수·임베딩 차원(1024) 확인 가능합니다.

---

## 4. 제거된 타깃 (복구가 필요할 때)

- **bge-small로 인덱스 빌드**: 코드 상 기본은 M3이므로, small이 필요하면  
  `docker compose run ... python -m ragapp index-elastic --model BAAI/bge-small-en-v1.5 --index-name ksp_rag_index` 로 직접 실행해야 합니다. Make 타깃은 더 이상 제공하지 않습니다.
