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
| **둘 다 없음** | 기본값 (elasticsearch, llm) | `make up-server` |
| **Elastic만 있음** | ELASTIC_HOST=host.docker.internal | `make up-server` (LLM만 띄움) |
| **LLM만 있음** | SERVER_LLM_ENDPOINT=http://host.docker.internal:8000/... | `make up-server` (Elastic만 띄움) |
| **둘 다 있음** | 둘 다 host.docker.internal | `make up-server-app-only` |

**기존 서비스 사용 시 .env.server 예시**:
```bash
# 호스트에서 Elasticsearch (9200), LLM (8000) 실행 중인 경우
ELASTIC_HOST=host.docker.internal
ELASTIC_PORT=9200
SERVER_LLM_ENDPOINT=http://host.docker.internal:8000/v1/completions
```

---

## 📋 사전 요구사항

### 하드웨어
- **GPU**: NVIDIA GPU (CUDA 지원)
- **메모리**: 최소 16GB RAM
- **디스크**: 최소 50GB 여유 공간

### 소프트웨어
- **OS**: Ubuntu 20.04+ (또는 NVIDIA Docker 지원 OS)
- **Docker**: 20.10+
- **Docker Compose**: 2.0+
- **NVIDIA Container Toolkit**: GPU 지원용

---

## 🔧 1단계: 환경 준비

### 1.1 NVIDIA Container Toolkit 설치

```bash
# NVIDIA Docker 런타임 설치
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list

sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit
sudo systemctl restart docker

# 설치 확인
docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi
```

### 1.2 저장소 클론

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

**기본 설정 (Elastic/LLM 새로 띄우는 경우)**:
```bash
# .env.server
MODE=server
RETRIEVER_MODE=elastic

# Elasticsearch
ELASTIC_HOST=elasticsearch
ELASTIC_PORT=9200
ELASTIC_INDEX_NAME=ksp_rag_index

# LLM (vLLM GPU 서버)
LLM_PROVIDER=server_http
SERVER_LLM_ENDPOINT=http://llm:8000/v1/completions
SERVER_LLM_MODEL=meta-llama/Llama-2-7b-chat-hf

# 검색 설정
TOP_K=12
RERANK_TOP_K=5
```

**기존 서비스 사용 시** (`make check-server` 결과 참고):
```bash
# 호스트에서 Elasticsearch(9200), LLM(8000) 실행 중이면
ELASTIC_HOST=host.docker.internal
SERVER_LLM_ENDPOINT=http://host.docker.internal:8000/v1/completions
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
# 서버 모드 전체 시작 (Elasticsearch + LLM + App)
make up-server

# 또는
docker compose --profile server up -d
```

**실행되는 서비스**:
- `elasticsearch`: 검색 엔진 (포트 9200)
- `llm`: vLLM GPU 서버 (포트 8000)

### 3.3 서비스 상태 확인

```bash
# 컨테이너 상태
docker compose ps

# 로그 확인
docker compose logs -f elasticsearch
docker compose logs -f llm

# Elasticsearch 헬스체크
curl 'http://localhost:9200/_cluster/health?pretty'

# vLLM 헬스체크
curl http://localhost:8000/health
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
# Elasticsearch + vLLM RAG
make ask-elastic Q="What are the main features of the Honduras pension system?"

# 또는
docker compose --profile server run --rm app \
  python -m ragapp ask "What are the main features of the Honduras pension system?" --mode elastic
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

### 문제 2: vLLM GPU 메모리 부족

**증상**:
```
CUDA out of memory
```

**해결**:
```bash
# .env.server에서 GPU 메모리 사용량 조정
GPU_MEMORY_UTILIZATION=0.7  # 기본 0.9에서 감소

# 또는 더 작은 모델 사용
SERVER_LLM_MODEL=meta-llama/Llama-2-7b-chat-hf  # 현재
# SERVER_LLM_MODEL=TinyLlama/TinyLlama-1.1B-Chat-v1.0  # 대안
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

### 문제 4: vLLM 모델 다운로드 느림

**증상**:
모델 다운로드가 너무 오래 걸림 (수 GB)

**해결**:
```bash
# 로컬에서 미리 다운로드 후 서버로 복사
# 1. 로컬에서
docker compose --profile server run --rm llm \
  python -c "from transformers import AutoModel; AutoModel.from_pretrained('meta-llama/Llama-2-7b-chat-hf')"

# 2. 캐시 복사
rsync -avz ~/.cache/huggingface/ user@server:~/.cache/huggingface/

# 3. 서버에서 볼륨 마운트 확인
docker compose --profile server up -d llm
```

---

## ✅ 체크리스트

### 배포 전
- [ ] NVIDIA Container Toolkit 설치 완료
- [ ] `.env.server` 설정 완료
- [ ] PDF 파일 준비 (`data/raw/`)
- [ ] Docker Compose 2.0+ 확인

### 배포 중
- [ ] `make build` 성공
- [ ] `make up-server` 실행
- [ ] Elasticsearch 헬스체크 통과
- [ ] vLLM 헬스체크 통과
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
- **WORKFLOW.md**: RAG 워크플로우 상세
- **docs/ELASTICSEARCH_GUIDE.md**: Elasticsearch 운영 가이드
- **docs/STAGE9_COMPLETION.md**: GPU LLM 통합 문서

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
