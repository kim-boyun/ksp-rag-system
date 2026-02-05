# Step 2 완료: Docker Compose 분리

**날짜**: 2026-02-05  
**목표**: 운영 서버와 GPU 서버 compose 파일 분리

---

## ✅ 변경 사항

### 1. docker-compose.gpu.yml 생성 ✅

**파일**: `docker-compose.gpu.yml` (신규)

**내용**:
- `llm` 서비스 정의 (vLLM)
- GPU 리소스 예약 (nvidia runtime)
- `llm-cache` 볼륨
- 독립 네트워크 (`rag-network`)

**사용법**:
```bash
# GPU 서버에서
docker compose -f docker-compose.gpu.yml up -d
# 또는
make gpu-up
```

### 2. docker-compose.yml 정리 ✅

**변경사항**:
- ✅ llm 서비스 없음 (이미 제거됨)
- ✅ llm-cache 볼륨 없음 (이미 제거됨)
- ✅ nvidia runtime 없음
- ✅ 주석 수정: "LLM" → "외부 vLLM"

**현재 서비스**:
- `app`: RAG 애플리케이션
- `elasticsearch`: 검색 엔진
- `kibana`: Elasticsearch UI (선택)
- `ui`: Streamlit UI

### 3. Makefile 업데이트 ✅

**추가된 타겟**:
```makefile
gpu-up        # GPU 서버에서 vLLM 시작
gpu-down      # GPU 서버에서 vLLM 중지
gpu-health    # GPU 서버 vLLM 헬스체크
gpu-logs      # GPU 서버 vLLM 로그
```

### 4. README.md 업데이트 ✅

**변경사항**:
- 아키텍처 섹션: GPU 서버 분리 명시
- 배포 가이드: 운영 서버 / GPU 서버 분리
- 명령어 요약: 운영 서버 / GPU 서버 구분

---

## 🚀 검증

### 1. 기본 compose 검증

```bash
docker compose config
# ✅ 정상 출력 (llm 없음)
```

**서비스 목록**:
- app
- elasticsearch
- kibana
- ui

### 2. GPU compose 검증

```bash
docker compose -f docker-compose.gpu.yml config
# ✅ 정상 출력 (llm만 있음)
```

**서비스 목록**:
- llm

### 3. 서비스 시작 테스트

```bash
# Elasticsearch 시작
docker compose up -d elasticsearch
# ✅ 정상

# Streamlit UI 시작
docker compose --profile ui up -d
# ✅ 정상 (LLM 호출은 외부 endpoint 사용)
```

---

## ✅ 완료 기준 달성

| 기준 | 상태 | 검증 |
|------|------|------|
| 기본 compose에서 GPU 의존 제거 | ✅ | `docker compose config` (llm 없음) |
| GPU compose 파일 별도 생성 | ✅ | `docker-compose.gpu.yml` 존재 |
| README 업데이트 | ✅ | 아키텍처/배포 가이드 분리 |
| Makefile GPU 타겟 추가 | ✅ | `make gpu-up` 등 |
| compose config 정상 출력 | ✅ | 검증 완료 |
| 서비스 시작 정상 | ✅ | elastic, ui 정상 |

---

## 📋 파일 변경 목록

### 신규 파일
- `docker-compose.gpu.yml`: GPU 서버용 compose 파일

### 수정 파일
- `docker-compose.yml`: 주석 수정 (LLM → 외부 vLLM)
- `Makefile`: GPU 타겟 추가
- `README.md`: 아키텍처/배포 가이드 업데이트

---

## 🎯 다음 단계

Step 3: 코드 정리 및 최종 검증

---

**Step 2 완료!** ✅
