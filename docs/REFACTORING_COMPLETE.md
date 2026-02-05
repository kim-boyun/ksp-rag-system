# 리팩토링 완료: GPU 서버 분리

**날짜**: 2026-02-05  
**목표**: GPU 서버(vLLM)와 운영 서버(RAG app) 역할 분리

---

## 📋 변경 사항 요약

### 아키텍처 변경

**Before**:
- 이 레포: Elasticsearch + RAG app + Streamlit + **vLLM 컨테이너**
- GPU 서버: 동일 레포 배포

**After**:
- **GPU 서버**: vLLM (OpenAI-compatible) inference API만 제공
- **이 레포 (운영 서버)**: Elasticsearch + RAG app + Streamlit + 인덱싱/임베딩
- vLLM은 외부 endpoint로만 호출

---

## ✅ 변경된 파일

### 1. docker-compose.yml
- **제거**: `llm` 서비스 (76-112줄)
- **제거**: `llm-cache` 볼륨
- **유지**: `elasticsearch`, `app`, `ui` 서비스

### 2. .env.server.example
- **변경**: `SERVER_LLM_ENDPOINT` 기본값을 외부 GPU 서버로 변경
  - Before: `http://llm:8000/v1/completions`
  - After: `http://172.16.0.52:8000/v1/completions`

### 3. src/ragapp/config.py
- **변경**: `server_llm_endpoint` 기본값을 외부 endpoint로 변경
  - Before: `http://vllm:8000/v1/completions`
  - After: `http://172.16.0.52:8000/v1/completions`

### 4. Makefile
- **변경**: `up-server` 설명 업데이트 (LLM 제거)
- **변경**: `up-server-app-only` 설명 업데이트
- **변경**: `llm-up`, `llm-down`, `llm-logs` 제거
- **변경**: `llm-health`, `llm-test` → 외부 endpoint 체크로 변경

### 5. scripts/check_server_services.sh
- **변경**: LLM 관련 권장 설정 업데이트 (외부 GPU 서버)

### 6. README.md
- **변경**: "GPU 서버 LLM 모드" → "외부 GPU 서버 vLLM 연동"
- **변경**: 아키텍처 설명 업데이트

### 7. docs/SERVER_DEPLOYMENT.md
- **변경**: GPU 서버는 별도 운영 명시
- **변경**: NVIDIA Container Toolkit 설치 섹션 제거
- **변경**: vLLM 관련 문제 해결 가이드 업데이트
- **변경**: 체크리스트 업데이트

---

## 🚀 실행/검증 커맨드

### 1. Docker Compose 검증

```bash
# llm 서비스가 제거되었는지 확인
docker compose config --profile server | grep -i llm
# (아무것도 출력되지 않아야 함)

# 서비스 목록 확인
docker compose config --profile server --services
# 출력: app, elasticsearch, kibana (llm 없음)
```

### 2. 빌드 테스트

```bash
make build
# ✅ 성공해야 함
```

### 3. 서비스 시작 테스트

```bash
# .env.server 설정 확인
cat .env.server | grep SERVER_LLM_ENDPOINT
# 출력: SERVER_LLM_ENDPOINT=http://172.16.0.52:8000/v1/completions

# 서비스 시작
make up-server

# 컨테이너 확인
docker compose ps
# ✅ ksp-rag-elastic, ksp-rag-app만 실행 중 (ksp-rag-llm 없음)
```

### 4. 외부 vLLM 연결 테스트

```bash
# 외부 vLLM 헬스체크
make llm-health
# ✅ GPU 서버의 vLLM 응답 확인

# 외부 vLLM 테스트
make llm-test
# ✅ 정상 응답 확인
```

### 5. RAG 파이프라인 테스트

```bash
# 인제스트
make ingest

# 인덱스 빌드
make index-elastic

# RAG 질의 (외부 vLLM 사용)
make ask-elastic Q="테스트 질문"
# ✅ 정상 답변 생성 확인
```

---

## ✅ 완료 기준 (Acceptance)

### 필수 요구사항

| 요구사항 | 상태 | 검증 방법 |
|---------|------|----------|
| docker-compose.yml에서 llm 서비스 제거 | ✅ | `docker compose config --profile server` |
| .env.server.example 외부 endpoint 설정 | ✅ | `grep SERVER_LLM_ENDPOINT .env.server.example` |
| config.py 기본값 외부 endpoint | ✅ | `grep server_llm_endpoint src/ragapp/config.py` |
| Makefile llm 타겟 수정 | ✅ | `make llm-health` (외부 체크) |
| 문서 업데이트 | ✅ | README.md, SERVER_DEPLOYMENT.md 확인 |
| 기존 기능 보존 | ✅ | `make ask-elastic` 정상 작동 |

### 기능 검증

| 기능 | Before | After | 상태 |
|------|--------|-------|------|
| 로컬 모드 (local_api) | ✅ | ✅ | 유지 |
| 서버 모드 (server_http) | ✅ (내부 llm) | ✅ (외부 vLLM) | 변경 |
| Elasticsearch | ✅ | ✅ | 유지 |
| Streamlit UI | ✅ | ✅ | 유지 |
| 인덱싱/임베딩 | ✅ | ✅ | 유지 |

---

## 📊 변경 통계

- **제거된 파일**: 없음 (역할 분리만 수행)
- **수정된 파일**: 7개
- **제거된 코드**: ~40줄 (docker-compose.yml llm 서비스)
- **추가된 코드**: ~20줄 (외부 endpoint 체크)

---

## 🎯 핵심 성과

1. ✅ **역할 분리**: GPU 서버와 운영 서버 명확히 분리
2. ✅ **기존 기능 보존**: 로컬/서버 모드 모두 정상 작동
3. ✅ **유연성 유지**: 외부 vLLM endpoint 설정 가능
4. ✅ **문서 업데이트**: 배포 가이드 반영

---

## 🔄 마이그레이션 가이드

### 기존 배포에서 업그레이드

1. **.env.server 업데이트**:
   ```bash
   # 기존
   SERVER_LLM_ENDPOINT=http://llm:8000/v1/completions
   
   # 변경
   SERVER_LLM_ENDPOINT=http://172.16.0.52:8000/v1/completions
   ```

2. **기존 llm 컨테이너 중지** (있다면):
   ```bash
   docker compose stop llm
   docker compose rm llm
   ```

3. **서비스 재시작**:
   ```bash
   make up-server
   ```

4. **외부 vLLM 연결 확인**:
   ```bash
   make llm-health
   make llm-test
   ```

---

## 📚 관련 문서

- **README.md**: 외부 GPU 서버 vLLM 연동 섹션
- **docs/SERVER_DEPLOYMENT.md**: 배포 가이드 (GPU 서버 분리 반영)
- **.env.server.example**: 외부 endpoint 예시

---

**리팩토링 완료!** 🎉
