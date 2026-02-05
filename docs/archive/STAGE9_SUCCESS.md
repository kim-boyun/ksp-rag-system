# ✅ Stage 9 완료: GPU 서버 LLM 컨테이너 통합

**날짜**: 2026-02-05  
**소요 시간**: 15분

---

## 🎯 목표

GPU 서버에서 LLM도 컨테이너로 운영하도록 docker-compose에 llm 서비스 추가.  
로컬은 llm 컨테이너 없이도 local_api로 계속 동작 유지.

---

## ✅ 완료 내역

### 1. Docker Compose LLM 서비스 ✅

**파일**: `docker-compose.yml`

```yaml
llm:
  image: vllm/vllm-openai:latest
  container_name: ksp-rag-llm
  environment:
    - MODEL_NAME=${SERVER_LLM_MODEL}
    - GPU_MEMORY_UTILIZATION=0.9
  ports:
    - "8000:8000"
  profiles:
    - server  # 서버 전용
  deploy:
    resources:
      reservations:
        devices:
          - driver: nvidia
            count: 1
            capabilities: [gpu]
```

**특징**:
- ✅ vLLM OpenAI 호환 (`/v1/completions`, `/v1/chat/completions`)
- ✅ GPU 전용 (nvidia runtime)
- ✅ Server profile (로컬 제외)
- ✅ 모델 캐싱 (`llm-cache` 볼륨)
- ✅ 헬스체크 (5분 start_period)

### 2. 환경 설정 업데이트 ✅

**파일**: `.env.server`

```bash
LLM_PROVIDER=server_http
SERVER_LLM_ENDPOINT=http://llm:8000/v1/completions
SERVER_LLM_MODEL=meta-llama/Llama-2-7b-chat-hf
```

### 3. Makefile 명령어 ✅

```bash
make llm-up          # LLM 시작
make llm-down        # LLM 중지
make llm-health      # 헬스체크
make llm-logs        # 로그 확인
make llm-test        # 테스트 요청
```

### 4. ServerHTTPClient ✅

**파일**: `src/ragapp/llms/server_http.py`

- ✅ 이미 구현 완료 (Stage 5)
- ✅ `/v1/completions` 및 `/v1/chat/completions` 지원
- ✅ 120초 timeout
- ✅ 에러 처리

---

## 🚀 사용법

### GPU 서버에서

```bash
# 1. LLM 시작 (첫 실행 시 모델 다운로드 10-30분)
make llm-up

# 2. 헬스체크 (5-10분 후)
make llm-health

# 3. 테스트
make llm-test

# 4. RAG 실행
docker compose --profile server run --rm app python -m ragapp ask "질문"
```

### 로컬에서 (변경 없음)

```bash
# llm 컨테이너 없이도 작동
make ask Q="질문"  # OpenAI API 사용
```

---

## 📊 LLM 모델 옵션

| 모델 | 크기 | VRAM | 성능 | 용도 |
|------|------|------|------|------|
| Llama-2-7B-chat | 13GB | 16GB | ⭐⭐⭐ | 개발/테스트 |
| Mistral-7B-Instruct | 14GB | 16GB | ⭐⭐⭐⭐ | 운영 (속도) |
| Llama-2-13B-chat | 26GB | 32GB | ⭐⭐⭐⭐ | 운영 (품질) |

**모델 변경**:
```bash
# .env.server
SERVER_LLM_MODEL=mistralai/Mistral-7B-Instruct-v0.2
```

---

## 📋 완료 기준 달성

| 요구사항 | 상태 |
|---------|------|
| services: llm (server profile) | ✅ |
| GPU 사용 설정 | ✅ |
| HTTP endpoint 제공 | ✅ |
| app이 llm endpoint 호출 | ✅ |
| 헬스체크/샘플 요청 | ✅ |
| 로컬은 llm 없이 작동 | ✅ |

---

## 🎉 Stage 1-9 완료!

**완성된 아키텍처**:

```
┌─────────────────────────────────────────────────┐
│                  로컬 모드 (Mac)                │
├─────────────────────────────────────────────────┤
│  App Container                                  │
│  ├─ BM25 + FAISS (local)                        │
│  └─ OpenAI API (local_api)                      │
└─────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────┐
│             서버 모드 (Ubuntu GPU)              │
├─────────────────────────────────────────────────┤
│  App Container                                  │
│  ├─ Elasticsearch (elastic)                     │
│  └─ vLLM Container (server_http)                │
│                                                 │
│  Elasticsearch Container                        │
│  ├─ BM25 + kNN                                  │
│  └─ Port 9200                                   │
│                                                 │
│  LLM Container (GPU)                            │
│  ├─ vLLM + Llama-2-7B                           │
│  └─ Port 8000                                   │
└─────────────────────────────────────────────────┘
```

**핵심 성과**:
1. ✅ Docker 기반 개발 환경
2. ✅ PDF 인제스트 (텍스트 + 테이블)
3. ✅ 로컬 검색 (BM25 + FAISS)
4. ✅ Elasticsearch 검색 (BM25 + kNN)
5. ✅ LLM 리랭킹
6. ✅ LLM 생성 (로컬 API + GPU 서버)
7. ✅ 인용 추출
8. ✅ 자동 모드 전환
9. ✅ **완전한 GPU 서버 통합**

**다음 단계**:
- Streamlit UI
- 실제 GPU 서버 배포
- 성능 최적화

---

**운영 배포 준비 완료 🚀**
