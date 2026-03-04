# KSP RAG System — 문서 가이드

이 디렉터리는 프로젝트의 **모든 문서**를 정리한 인덱스입니다.  
레포 전체 요약은 루트의 **[PROJECT_OVERVIEW.md](../PROJECT_OVERVIEW.md)** 를 참고하세요.

---

## 📚 문서 분류

### 🚀 배포·운영

| 문서 | 설명 |
|------|------|
| [**SERVER_DEPLOYMENT.md**](SERVER_DEPLOYMENT.md) | 운영 서버 배포 절차, 환경 설정, 서비스 기동, 인덱스 빌드, vLLM 연동, 트러블슈팅 |
| [**ELASTICSEARCH_GUIDE.md**](ELASTICSEARCH_GUIDE.md) | Elasticsearch 사용법, 인덱스 빌드/재생성, 검색 테스트, Kibana, 백업/복원 |
| [**RUN_WITH_M3_INDEX.md**](RUN_WITH_M3_INDEX.md) | bge-m3 인덱스 import 후 실행·확인 방법, ELASTIC_INDEX_NAME / LOCAL_EMBEDDING_MODEL 설정 |
| [**GUIDE_ELASTIC_LOCAL_FULL.md**](GUIDE_ELASTIC_LOCAL_FULL.md) | .env.local 기준 Elasticsearch + 개인 LLM으로 인제스트부터 UI까지 한 번에 진행 |
| [**SETUP_MAC_FROM_SCRATCH.md**](SETUP_MAC_FROM_SCRATCH.md) | 맥에서 인제스트 없이 chunks.jsonl만 가져와 임베딩·검색·질의 세팅 |

---

### 📖 사용 가이드

| 문서 | 설명 |
|------|------|
| [**LOGIC_AND_QUICKSTART.md**](LOGIC_AND_QUICKSTART.md) | 로직 요약, 로컬/서버 모드 빠른 시작, 한 번에 보는 순서 표 |
| [**WINDOWS.md**](WINDOWS.md) | Windows(PowerShell)에서의 설정·실행, Makefile 대응 명령 표 |
| [**ENV_FILES_GUIDE.md**](ENV_FILES_GUIDE.md) | .env / .env.local / .env.server 역할, 사용 시나리오, 동작 원리 |
| [**LLM_SWITCHING_GUIDE.md**](LLM_SWITCHING_GUIDE.md) | 로컬(OpenAI API) ↔ 서버(vLLM) 전환 방법, Makefile·코드 동작 |
| [**NETWORK_ACCESS_GUIDE.md**](NETWORK_ACCESS_GUIDE.md) | 운영 서버–GPU 서버 네트워크 접근, 방화벽, 터널링, 에러 해석 |

---

### 🏗️ 아키텍처·사양

| 문서 | 설명 |
|------|------|
| [**architecture/overview.md**](architecture/overview.md) | 시스템 구조, 운영/GPU 서버 역할, 네트워크·포트, 데이터 흐름, 보안 |
| [**RAG_SYSTEM_METADATA.md**](RAG_SYSTEM_METADATA.md) | 전 단계 메타정보: 인제스트, 임베딩(bge-small/bge-m3), 인덱싱, 검색, RRF, 리랭킹, LLM, 프롬프트, 캐시, 환경 변수 요약 |

---

### 🔧 고도화·기타

| 문서 | 설명 |
|------|------|
| [**RAG_고도화_방안_총정리.md**](RAG_고도화_방안_총정리.md) | Contextual Retrieval, 쿼리 확장, 리랭킹, 프롬프트 등 RAG 개선 로드맵 |

---

## 📁 아카이브 (archive/)

과거 개발 단계별 기록·완료 문서는 [**archive/**](archive/) 에 보관되어 있습니다.

- **STAGE*_COMPLETION.md / STAGE*_SUCCESS.md**: 단계별 완료·성공 기록  
- **STEP*_COMPLETION.md**: 리팩터링/환경 변수 변경 등 단계 기록  
- **WORKFLOW.md**, **PROJECT_COMPLETE.md**, **SYSTEM_COMPLETE.md**: 워크플로·프로젝트/시스템 완료 요약  
- **inventory.md**, **REFACTORING_COMPLETE.md**: 인벤토리·리팩터 정리  

참고용으로만 활용하면 됩니다.

---

## 🔗 루트 문서

- **[../README.md](../README.md)** — 프로젝트 소개, 배포 토폴로지, 빠른 시작, CLI·Makefile, 구현 현황  
- **[../PROJECT_OVERVIEW.md](../PROJECT_OVERVIEW.md)** — 전체 총정리(구조, env, 명령, 임베딩/LLM/RRF 요약, 문서 인덱스)

---

이 인덱스만 보면 docs 폴더와 주요 루트 문서를 한눈에 파악할 수 있습니다.
