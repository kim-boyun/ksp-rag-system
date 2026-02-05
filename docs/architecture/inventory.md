# GPU/vLLM 관련 요소 인벤토리

**생성일**: 2026-02-05  
**목적**: GPU 서버 분리 리팩토링을 위한 현재 상태 파악

---

## 📋 인벤토리 목록

| 항목 | 위치 (파일:라인) | 역할 | 현재 상태 | 조치 |
|------|-----------------|------|----------|------|
| **1. docker-compose.yml llm 서비스** | docker-compose.yml | vLLM 컨테이너 정의 | ❌ **이미 제거됨** | ✅ 완료 |
| **2. docker-compose.yml llm-cache 볼륨** | docker-compose.yml:147 | LLM 모델 캐시 | ❌ **이미 제거됨** | ✅ 완료 |
| **3. docker-compose.yml nvidia runtime** | docker-compose.yml | GPU 리소스 예약 | ❌ **없음** | ✅ 완료 |
| **4. Dockerfile CUDA/NVIDIA** | Dockerfile | GPU 관련 빌드 | ❌ **없음** | ✅ 완료 |
| **5. .env.server.example 내부 endpoint** | .env.server.example:20 | 내부 서비스명 참조 | ✅ **외부로 변경됨** | ✅ 완료 |
| **6. config.py 기본값** | src/ragapp/config.py:65 | 기본 endpoint | ✅ **외부로 변경됨** | ✅ 완료 |
| **7. 코드 하드코딩** | src/ | http://llm 같은 하드코딩 | ✅ **없음** | ✅ 완료 |
| **8. Makefile llm 타겟** | Makefile:152-170 | llm 컨테이너 관리 | ✅ **외부 체크로 변경됨** | ✅ 완료 |
| **9. 주석/문서 참조** | 여러 파일 | 과거 llm 서비스 언급 | ⚠️ **일부 남아있음** | 🔄 정리 필요 |

---

## 🔍 상세 분석

### 1. docker-compose.yml

#### ✅ llm 서비스 (제거 완료)

**위치**: `docker-compose.yml` (이전 76-112줄)  
**상태**: ❌ **이미 제거됨**  
**조치**: ✅ 완료

**확인**:
```bash
docker compose config --profile server | grep -i llm
# (아무것도 출력되지 않음)
```

#### ✅ llm-cache 볼륨 (제거 완료)

**위치**: `docker-compose.yml` (이전 147줄)  
**상태**: ❌ **이미 제거됨**  
**조치**: ✅ 완료

**현재 볼륨**:
- `elastic-data`: Elasticsearch 데이터
- `model-cache`: 임베딩 모델 캐시
- `llm-cache`: ❌ 제거됨

#### ✅ nvidia runtime 설정 (없음)

**위치**: `docker-compose.yml`  
**상태**: ❌ **없음** (이미 제거됨)  
**조치**: ✅ 완료

**확인**:
```bash
grep -i "nvidia\|gpu\|deploy.*resources" docker-compose.yml
# (아무것도 출력되지 않음)
```

---

### 2. Dockerfile

#### ✅ CUDA/NVIDIA 관련 (없음)

**위치**: `Dockerfile` 전체  
**상태**: ❌ **없음**  
**조치**: ✅ 완료

**확인**:
- CUDA base image 사용 안 함
- NVIDIA 관련 패키지 설치 안 함
- GPU 관련 설정 없음

**내용**: Python 3.11-slim 기반, 일반적인 Python 패키지만 설치

---

### 3. 환경 변수 설정

#### ✅ .env.server.example

**위치**: `.env.server.example:20`  
**역할**: 서버 모드 LLM endpoint 설정  
**현재 값**: `SERVER_LLM_ENDPOINT=http://172.16.0.52:8000/v1/completions`  
**상태**: ✅ **외부 GPU 서버로 설정됨**  
**조치**: ✅ 완료

**이전 값** (문서 참조):
- `http://llm:8000/v1/completions` (내부 서비스명)
- `http://vllm:8000/v1/completions` (내부 서비스명)

#### ✅ .env.server (실제 파일)

**위치**: `.env.server:16`  
**역할**: 실제 서버 설정  
**현재 값**: `SERVER_LLM_ENDPOINT=http://host.docker.internal:8000/v1/completions`  
**상태**: ✅ **외부 endpoint 사용**  
**조치**: ✅ 완료

**설명**: `host.docker.internal`은 호스트에서 실행 중인 외부 vLLM을 가리킴

---

### 4. 코드 내부

#### ✅ config.py 기본값

**위치**: `src/ragapp/config.py:64-66`  
**역할**: 서버 LLM endpoint 기본값  
**현재 값**: `http://172.16.0.52:8000/v1/completions`  
**상태**: ✅ **외부 GPU 서버로 설정됨**  
**조치**: ✅ 완료

**코드**:
```python
server_llm_endpoint: str = Field(
    default="http://172.16.0.52:8000/v1/completions",
    description="External vLLM HTTP endpoint (GPU server)"
)
```

#### ✅ 하드코딩된 내부 서비스명 (없음)

**위치**: `src/` 전체  
**역할**: 코드에서 직접 `http://llm:8000` 같은 하드코딩  
**상태**: ✅ **없음** (모두 config에서 동적 로드)  
**조치**: ✅ 완료

**확인**:
```bash
grep -r "http://llm\|http://vllm\|llm:8000\|vllm:8000" src/
# (아무것도 출력되지 않음)
```

**사용 패턴**:
- `config.server_llm_endpoint` 사용 (동적)
- `ServerHTTPClient`가 endpoint를 파라미터로 받음

#### ✅ server_http.py 구현

**위치**: `src/ragapp/llms/server_http.py`  
**역할**: 외부 HTTP endpoint 클라이언트  
**상태**: ✅ **외부 endpoint 지원**  
**조치**: ✅ 완료 (변경 불필요)

**특징**:
- `endpoint` 파라미터로 동적 설정
- config에서 기본값 로드
- OpenAI-compatible API 지원

---

### 5. Makefile

#### ✅ llm 관련 타겟

**위치**: `Makefile:149-170`  
**역할**: LLM 서비스 관리 명령어  
**상태**: ✅ **외부 endpoint 체크로 변경됨**  
**조치**: ✅ 완료

**변경 사항**:
- ❌ 제거: `llm-up`, `llm-down`, `llm-logs` (내부 컨테이너 관리)
- ✅ 유지: `llm-health`, `llm-test` (외부 endpoint 체크)

**현재 구현**:
```makefile
llm-health: ## 외부 LLM 헬스체크 (.env.server의 SERVER_LLM_ENDPOINT 사용)
	@echo "Checking external LLM health..."
	@if [ -f .env.server ]; then \
		ENDPOINT=$$(grep SERVER_LLM_ENDPOINT .env.server | cut -d'=' -f2 | sed 's|/v1/completions||'); \
		curl -s $$ENDPOINT/health || echo "❌ External LLM not accessible"; \
	else \
		echo "⚠️  .env.server not found. Using default endpoint..."; \
		curl -s http://172.16.0.52:8000/health || echo "❌ External LLM not accessible"; \
	fi
```

---

### 6. 스크립트

#### ✅ check_server_services.sh

**위치**: `scripts/check_server_services.sh`  
**역할**: 서버 기존 서비스 확인  
**상태**: ✅ **외부 vLLM 확인으로 업데이트됨**  
**조치**: ✅ 완료

**변경 사항**:
- ksp-rag-llm 컨테이너 확인 제거
- 외부 vLLM 서비스 확인으로 변경
- 권장 설정에 외부 GPU 서버 endpoint 표시

---

### 7. 주석 및 문서

#### ⚠️ docker-compose.yml 주석

**위치**: `docker-compose.yml:23, 98`  
**내용**: `# 기존 Elastic/LLM 사용 시`  
**상태**: ⚠️ **LLM 언급 남아있음**  
**조치**: 🔄 **정리 필요** (LLM → 외부 vLLM)

**현재**:
```yaml
profiles:
  - app-only  # 기존 Elastic/LLM 사용 시 app만 실행
```

**권장**:
```yaml
profiles:
  - app-only  # 기존 Elastic/외부 vLLM 사용 시 app만 실행
```

#### ⚠️ 문서 파일들

**위치**: 여러 문서 파일  
**내용**: 과거 llm 서비스 관련 내용  
**상태**: ⚠️ **일부 남아있음** (히스토리 문서)  
**조치**: 🔄 **선택적 정리** (히스토리는 유지 가능)

**파일 목록**:
- `docs/STAGE9_COMPLETION.md`: Stage 9 완료 문서 (히스토리)
- `STAGE9_SUCCESS.md`: Stage 9 요약 (히스토리)
- `PROJECT_COMPLETE.md`: 프로젝트 완성 문서 (히스토리)
- `SYSTEM_COMPLETE.md`: 시스템 완성 문서 (히스토리)

**권장 조치**:
- 히스토리 문서는 유지 (과거 상태 기록)
- 현재 가이드 문서만 업데이트 (이미 완료)

---

## 📊 요약

### ✅ 완료된 항목 (9개)

| 항목 | 상태 |
|------|------|
| docker-compose.yml llm 서비스 제거 | ✅ 완료 |
| docker-compose.yml llm-cache 볼륨 제거 | ✅ 완료 |
| docker-compose.yml nvidia runtime 제거 | ✅ 완료 |
| Dockerfile CUDA/NVIDIA 제거 | ✅ 완료 |
| .env.server.example 외부 endpoint | ✅ 완료 |
| config.py 외부 endpoint 기본값 | ✅ 완료 |
| 코드 하드코딩 없음 | ✅ 완료 |
| Makefile 외부 체크로 변경 | ✅ 완료 |
| check_server_services.sh 업데이트 | ✅ 완료 |

### ⚠️ 정리 필요한 항목 (2개)

| 항목 | 위치 | 조치 |
|------|------|------|
| 주석의 "LLM" 언급 | docker-compose.yml:23, 98 | "외부 vLLM"으로 명확화 |
| 히스토리 문서 | docs/STAGE9*.md 등 | 선택적 (유지 가능) |

---

## 🎯 다음 단계

### 즉시 조치 필요

1. **docker-compose.yml 주석 수정**
   - `# 기존 Elastic/LLM 사용 시` → `# 기존 Elastic/외부 vLLM 사용 시`

### 선택적 조치

2. **히스토리 문서 업데이트** (선택)
   - Stage 9 문서에 "현재는 제거됨" 주석 추가
   - 또는 그대로 유지 (히스토리 기록)

---

## ✅ 완료 기준 달성

| 기준 | 상태 |
|------|------|
| GPU 관련 구성요소 빠짐없이 정리 | ✅ |
| 다음 단계에서 무엇을 옮기고/지울지 명확 | ✅ |
| 코드 변경 없이 문서만 생성 | ✅ |

---

## 📝 참고

**현재 아키텍처**:
- **GPU 서버**: vLLM (별도 운영, `172.16.0.52:8000`)
- **운영 서버 (이 레포)**: Elasticsearch + RAG app + Streamlit
- **연결**: HTTP endpoint로 외부 vLLM 호출

**리팩토링 상태**: ✅ **대부분 완료됨** (주석 정리만 남음)

---

**인벤토리 완료!** 다음 단계로 진행 가능합니다.
