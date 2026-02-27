# GPU 서버 배포 가이드

이 디렉토리는 **GPU 서버에서만 사용**됩니다. 운영 서버(이 레포의 루트)에서는 사용하지 않습니다.

## 📋 목적

GPU 서버에서 vLLM inference API만 제공하는 용도입니다.

## 🚀 빠른 시작

### 1. 사전 요구사항

- Docker & Docker Compose
- NVIDIA GPU (CUDA 지원)
- NVIDIA Container Toolkit 설치
- 최소 16GB GPU 메모리 (모델에 따라 다름)

### 2. 환경 설정 (선택 사항)

```bash
cd ops/gpu
cp .env.gpu.example .env.gpu
vim .env.gpu  # 필요시 수정
```

### 3. vLLM 시작

```bash
# 방법 1: ops/gpu 디렉토리에서 실행
cd ops/gpu
docker compose up -d

# 방법 2: 루트 디렉토리에서 실행
docker compose -f ops/gpu/docker-compose.yml up -d
```

### 4. 헬스체크

```bash
# 방법 1: curl로 직접 확인
curl http://localhost:8000/health

# 방법 2: /v1/models 엔드포인트 확인
curl http://localhost:8000/v1/models
```

## 📝 주요 명령어

### 서비스 관리

```bash
# 시작
docker compose -f ops/gpu/docker-compose.yml up -d

# 중지
docker compose -f ops/gpu/docker-compose.yml down

# 로그 확인
docker compose -f ops/gpu/docker-compose.yml logs -f llm

# 상태 확인
docker compose -f ops/gpu/docker-compose.yml ps
```

### 헬스체크

```bash
# 기본 헬스체크
curl http://localhost:8000/health

# 모델 목록 확인
curl http://localhost:8000/v1/models

# 간단한 추론 테스트
curl -X POST http://localhost:8000/v1/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "openai/gpt-oss-120b",
    "prompt": "Hello, ",
    "max_tokens": 20
  }'
```

## 🔧 환경 변수

`.env.gpu` 파일에서 다음 변수를 설정할 수 있습니다:

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `SERVER_LLM_MODEL` | `openai/gpt-oss-120b` | 사용할 LLM 모델 |
| `TENSOR_PARALLEL_SIZE` | `1` | 텐서 병렬 크기 |
| `GPU_MEMORY_UTILIZATION` | `0.9` | GPU 메모리 사용률 (0.0-1.0) |
| `MAX_MODEL_LEN` | `4096` | 최대 모델 길이 |

## 🌐 포트 및 네트워크

- **포트**: 8000 (vLLM API)
- **네트워크**: `rag-network` (독립 네트워크)

**방화벽 규칙**:
- 인바운드: 8000 (운영 서버에서만 접근 가능하도록 제한)
- 아웃바운드: 인터넷 (모델 다운로드)

## 🔗 운영 서버 연결

운영 서버에서 이 GPU 서버를 사용하려면:

1. 운영 서버의 `.env.server`에 다음 설정:
   ```bash
   LLM_PROVIDER=server_http
   SERVER_LLM_BASE_URL=http://<GPU_SERVER_IP>:8000
   ```

2. 네트워크 연결 확인:
   ```bash
   # 운영 서버에서 실행
   curl http://<GPU_SERVER_IP>:8000/health
   ```

## 🐛 트러블슈팅

### GPU 메모리 부족

```bash
# GPU_MEMORY_UTILIZATION을 낮춤
GPU_MEMORY_UTILIZATION=0.7
```

### 모델 다운로드 실패

```bash
# 로그 확인
docker compose -f ops/gpu/docker-compose.yml logs llm

# 볼륨 확인
docker volume ls | grep llm-cache
```

### 포트 충돌

```bash
# 다른 서비스가 8000 포트를 사용 중인지 확인
sudo lsof -i :8000

# docker-compose.yml에서 포트 변경
ports:
  - "8001:8000"  # 호스트 포트 변경
```

## 📚 관련 문서

- **운영 서버 배포**: [../../README.md](../../README.md)
- **아키텍처 개요**: [../../docs/architecture/overview.md](../../docs/architecture/overview.md)
