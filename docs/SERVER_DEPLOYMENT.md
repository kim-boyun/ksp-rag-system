# 🚀 GPU 서버 배포 가이드

**목표**: Mac 로컬에서 개발/테스트한 시스템을 Ubuntu GPU 서버로 완전 이식

---

## 🔍 0단계: 기존 서비스 확인 (배포 전 필수)

서버에 **Elasticsearch**나 **LLM**이 이미 Docker로 실행 중일 수 있습니다.  
먼저 확인 후 `.env.server` 설정을 결정하세요.

```bash
cd ~/ksp-rag-system
make check-server
```

**또는**:
```bash
bash scripts/check_server_services.sh
```

**확인 항목**:
- `localhost:9200` → Elasticsearch 응답 여부
- `localhost:8000` → LLM (vLLM/OpenAI 호환) 응답 여부
- Docker 컨테이너 목록 (elastic, vllm, llm 등)

**결과에 따른 설정**:

| 상황 | .env.server 설정 | 실행 명령 |
|------|-----------------|----------|
| **Elastic 없음** | ELASTIC_HOST=elasticsearch | `make up-server` (Elastic 띄움) |
| **Elastic 있음** | ELASTIC_HOST=host.docker.internal | `make up-server-app-only` (app만 띄움) |
| **vLLM** | SERVER_LLM_BASE_URL=http://172.16.0.52:8000 | (외부 GPU 서버, 별도 운영) |

**중요**: vLLM은 **외부 GPU 서버에서 별도로 운영**됩니다. 이 레포에서는 vLLM 컨테이너를 띄우지 않습니다.

**.env.server 예시**:
```bash
# Elasticsearch는 이 레포에서 띄움 (또는 기존 서비스 사용)
ELASTIC_HOST=elasticsearch  # 또는 host.docker.internal
ELASTIC_PORT=9200

# vLLM은 외부 GPU 서버에서 운영
SERVER_LLM_BASE_URL=http://172.16.0.52:8000  # GPU 서버 base URL (vLLM)
```

---

## 📋 사전 요구사항

### 아키텍처 분리

**이 레포 (운영 서버)**:
- Elasticsearch (검색 엔진)
- RAG 애플리케이션
- Streamlit UI
- 인덱싱/임베딩

**GPU 서버 (별도 운영)**:
- vLLM (OpenAI-compatible inference API)
- GPU 리소스 전담

### 하드웨어 (운영 서버)
- **메모리**: 최소 16GB RAM
- **디스크**: 최소 50GB 여유 공간
- **GPU**: 불필요 (vLLM은 외부 GPU 서버 사용)

### 소프트웨어
- **OS**: Ubuntu 20.04+ (또는 Linux)
- **Docker**: 20.10+
- **Docker Compose**: 2.0+

---

## 🔧 1단계: 환경 준비

### 1.1 GPU 서버 확인 (별도 운영)

**중요**: vLLM은 **외부 GPU 서버에서 별도로 운영**됩니다.

GPU 서버에서:
- vLLM 컨테이너 실행 중
- OpenAI-compatible API 제공 (`/v1/completions`, `/v1/chat/completions`)
- 접근 가능한 IP 주소 확인 (예: `172.16.0.52:8000`)

### 1.2 저장소 클론 (운영 서버)

```bash
# 저장소 클론
cd ~
git clone <repository-url> ksp-rag-system
cd ksp-rag-system

# 기존 서비스 확인 (배포 전 필수!)
make check-server
```

---

## ⚙️ 2단계: 설정

### 2.1 환경 변수 설정

```bash
# .env.server 파일 생성
cp .env.server.example .env.server

# check-server 결과를 참고하여 편집
vim .env.server
```

**기본 설정**:
```bash
# .env.server
MODE=server
RETRIEVER_MODE=elastic

# Elasticsearch (이 레포에서 띄움)
ELASTIC_HOST=elasticsearch
ELASTIC_PORT=9200
ELASTIC_INDEX_NAME=ksp_rag_index

# LLM (외부 GPU 서버의 vLLM)
LLM_PROVIDER=server_http
SERVER_LLM_BASE_URL=http://172.16.0.52:8000  # GPU 서버 base URL (vLLM)
SERVER_LLM_MODEL=meta-llama/Llama-2-7b-chat-hf

# 검색 설정
TOP_K=12
RERANK_TOP_K=5
```

**기존 Elasticsearch 사용 시** (`make check-server` 결과 참고):
```bash
# 호스트에서 Elasticsearch(9200) 실행 중이면
ELASTIC_HOST=host.docker.internal
ELASTIC_PORT=9200

# vLLM은 항상 외부 GPU 서버
SERVER_LLM_ENDPOINT=http://172.16.0.52:8000/v1/completions
```

### 2.2 로컬 API 키 (선택 사항)

개발/테스트용으로 OpenAI API를 사용하려면:

```bash
cp .env.local.example .env.local
# .env.local에 LLM_API_KEY 입력
```

---

## 🐳 3단계: Docker 빌드 및 실행

### 3.1 이미지 빌드

```bash
# 앱 이미지 빌드
make build

# 또는
docker compose build app
```

**예상 시간**: 5-10분

### 3.2 서버 프로파일 시작

```bash
# 서버 모드 시작 (Elasticsearch + App, vLLM은 외부 GPU 서버 사용)
make up-server

# 또는
docker compose --profile server up -d
```

**실행되는 서비스**:
- `elasticsearch`: 검색 엔진 (포트 9200)
- `app`: RAG 애플리케이션
- `ui`: Streamlit UI (선택)

**외부 서비스**:
- `vLLM`: GPU 서버에서 별도 운영 (예: `172.16.0.52:8000`)

### 3.3 서비스 상태 확인

```bash
# 컨테이너 상태
docker compose ps

# 로그 확인
docker compose logs -f elasticsearch
docker compose logs -f app

# Elasticsearch 헬스체크
curl 'http://localhost:9200/_cluster/health?pretty'

# 외부 vLLM 헬스체크
make llm-health
# 또는
curl http://172.16.0.52:8000/health
```

---

## 📥 4단계: 데이터 인제스트

### 4.1 PDF 파일 배치

```bash
# data/raw/ 디렉토리에 PDF 파일 복사
cp /path/to/pdfs/*.pdf data/raw/
```

### 4.2 인제스트 실행

```bash
# PDF → chunks (로컬 실행, profile 불필요)
make ingest

# 또는
docker compose run --rm app python -m ragapp ingest
```

**출력**:
```
✅ Loaded 1829 chunks → data/processed/chunks.jsonl
```

---

## 🔍 5단계: Elasticsearch 인덱스 빌드

### 5.1 인덱스 생성

```bash
# Elasticsearch 인덱스 빌드
make index-elastic

# 또는
docker compose --profile server run --rm app python -m ragapp index-elastic
```

**출력**:
```
✅ Elasticsearch index built: ksp_rag_index
   - 1829 documents indexed
   - Index size: 14.6MB
```

### 5.2 인덱스 확인

```bash
# 인덱스 정보 조회
curl 'http://localhost:9200/ksp_rag_index/_count?pretty'

# 샘플 검색
curl -X POST 'http://localhost:9200/ksp_rag_index/_search?pretty' \
  -H 'Content-Type: application/json' \
  -d '{"query": {"match": {"content": "pension"}}, "size": 3}'
```

---

## 🧪 6단계: 스모크 테스트

### 6.1 검색 테스트 (Elasticsearch)

```bash
# Elasticsearch 검색
docker compose --profile server run --rm app \
  python -m ragapp retrieve "What is the pension system?" --mode elastic
```

**예상 출력**:
```
✅ Retrieved 12 documents
Top 3:
#1 (score: 0.8542) - Honduras Pension Report, p.45
#2 (score: 0.7891) - Pension Reform Recommendations, p.52
...
```

### 6.2 RAG 질의 테스트

```bash
# Elasticsearch + 외부 vLLM RAG
make ask-elastic Q="What are the main features of the Honduras pension system?"

# 또는
docker compose --profile server run --rm app \
  python -m ragapp ask "What are the main features of the Honduras pension system?" --mode elastic
```

**중요**: 외부 vLLM이 정상 작동하는지 먼저 확인:
```bash
make llm-health
make llm-test
```

**예상 출력**:
```
💬 Answer:
The Honduras pension system has the following main features:
1. Two-pillar structure [Source: Document 1]
2. Defined contribution scheme [Source: Document 2]
...

📚 Citations:
• 문서 1: Honduras_Report.pdf (페이지: 45)
• 문서 2: Pension_Reform.pdf (페이지: 52)
```

### 6.3 자동 스모크 테스트

```bash
# 3가지 핵심 기능 자동 테스트
make smoke-test
```

**테스트 항목**:
1. ✅ Ingest (PDF → chunks)
2. ✅ Retrieve (Elasticsearch 검색)
3. ✅ Ask (RAG 질의응답)

---

## 🎨 7단계: Streamlit UI 실행

### 7.1 UI 시작

```bash
# 서버 모드 UI 시작
make ui-server

# 또는
cp .env.server .env
docker compose --profile ui up -d
```

### 7.2 브라우저 접속

```
http://<server-ip>:8501
```

**UI 기능**:
- ✅ 질문 입력
- ✅ 답변 + 인용 표시
- ✅ 검색 문서 확인
- ✅ 설정 표시 (사이드바)

---

## 📊 8단계: 성능 모니터링

### 8.1 리소스 사용량

```bash
# Docker 리소스
docker stats

# GPU 사용량
nvidia-smi

# 디스크 사용량
du -sh data/*
```

### 8.2 Elasticsearch 모니터링

```bash
# 클러스터 상태
curl 'http://localhost:9200/_cluster/health?pretty'

# 인덱스 상태
curl 'http://localhost:9200/_cat/indices?v'

# 노드 상태
curl 'http://localhost:9200/_cat/nodes?v'
```

### 8.3 Kibana (선택 사항)

```bash
# Kibana 시작
docker compose --profile server up -d kibana

# 브라우저 접속
# http://<server-ip>:5601
```

---

## 🔄 9단계: 운영 관리

### 9.1 컨테이너 관리

```bash
# 전체 중지
make down

# 전체 재시작
docker compose --profile server restart

# 특정 서비스 재시작
docker compose restart elasticsearch
docker compose restart llm
```

### 9.2 인덱스 재빌드

```bash
# Elasticsearch 인덱스 삭제 후 재생성
make index-elastic-recreate

# 또는
docker compose --profile server run --rm app \
  python -m ragapp index-elastic --recreate
```

### 9.3 로그 관리

```bash
# 실시간 로그
docker compose logs -f

# 특정 서비스 로그
docker compose logs -f elasticsearch
docker compose logs -f llm
docker compose logs -f ui

# 로그 파일 크기 제한 (docker-compose.yml)
logging:
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "3"
```

---

## 🐛 트러블슈팅

### 문제 1: Elasticsearch 시작 실패

**증상**: 
```
elasticsearch exited with code 78
```

**해결**:
```bash
# vm.max_map_count 증가 (영구)
echo "vm.max_map_count=262144" | sudo tee -a /etc/sysctl.conf
sudo sysctl -p

# 또는 일시적
sudo sysctl -w vm.max_map_count=262144
```

### 문제 2: 외부 vLLM 연결 실패

**증상**:
```
ConnectionError: [Errno 111] Connection refused
또는
Failed to connect to 172.16.0.52:8000
```

**해결**:
```bash
# 1. GPU 서버에서 vLLM 실행 확인
ssh user@gpu-server
sudo docker ps | grep vllm

# 2. 네트워크 연결 확인
curl http://172.16.0.52:8000/health

# 3. .env.server의 SERVER_LLM_BASE_URL 확인
grep SERVER_LLM_BASE_URL .env.server

# 4. 방화벽 확인 (필요시)
# GPU 서버에서 포트 8000이 열려있는지 확인
```

### 문제 3: Elasticsearch 연결 거부

**증상**:
```
ConnectionError: [Errno 111] Connection refused
```

**해결**:
```bash
# Elasticsearch 상태 확인
docker compose logs elasticsearch

# 헬스체크
curl http://localhost:9200/_cluster/health

# 컨테이너 재시작
docker compose restart elasticsearch

# 30초 대기 후 재시도
sleep 30
```

---

## ✅ 체크리스트

### 배포 전
- [ ] 외부 GPU 서버의 vLLM 실행 확인
- [ ] `.env.server` 설정 완료 (SERVER_LLM_BASE_URL)
- [ ] PDF 파일 준비 (`data/raw/`)
- [ ] Docker Compose 2.0+ 확인

### 배포 중
- [ ] `make build` 성공
- [ ] `make up-server` 실행
- [ ] Elasticsearch 헬스체크 통과
- [ ] 외부 vLLM 헬스체크 통과 (`make llm-health`)
- [ ] `make ingest` 완료
- [ ] `make index-elastic` 완료

### 배포 후
- [ ] `make ask-elastic Q="test"` 성공
- [ ] `make smoke-test` 통과
- [ ] `make ui-server` 실행
- [ ] 브라우저 UI 접속 확인

---

## 📚 추가 참고자료

- **README.md**: 전체 시스템 개요
- **docs/ELASTICSEARCH_GUIDE.md**: Elasticsearch 운영 가이드
- **docs/LLM_SWITCHING_GUIDE.md**: LLM 전환 가이드
- **docs/NETWORK_ACCESS_GUIDE.md**: 네트워크 접근 권한 가이드
- **docs/architecture/overview.md**: 시스템 아키텍처 개요

---

## 🎉 배포 완료!

축하합니다! GPU 서버에 KSP RAG 시스템 배포가 완료되었습니다.

**다음 단계**:
1. 프로덕션 데이터 인제스트
2. 성능 튜닝 (TOP_K, RERANK_TOP_K 조정)
3. 모니터링 대시보드 설정
4. 백업 및 복구 계획 수립

**운영 명령어 요약**:
```bash
make up-server        # 서버 시작
make ingest           # 데이터 인제스트
make index-elastic    # 인덱스 빌드
make ask-elastic Q="질문"  # RAG 테스트
make ui-server        # UI 시작
make smoke-test       # 스모크 테스트
```
