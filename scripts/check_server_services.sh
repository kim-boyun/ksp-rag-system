#!/bin/bash
# ================================
# 서버 기존 서비스 확인 스크립트
# ================================
# Elasticsearch, LLM이 이미 Docker로 실행 중인지 확인
# 배포 전 실행하여 .env.server 설정 참고용

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo ""
echo "=================================================="
echo "🔍 KSP RAG - 서버 기존 서비스 확인"
echo "=================================================="
echo ""

# Default ports (수정 가능)
ELASTIC_PORT=${ELASTIC_PORT:-9200}
LLM_PORT=${LLM_PORT:-8000}

# Results
ELASTIC_FOUND=0
LLM_FOUND=0
ELASTIC_SOURCE=""
LLM_SOURCE=""

# ================================
# 1. Elasticsearch 확인
# ================================
echo -e "${BLUE}[1/4] Elasticsearch 확인 (포트 ${ELASTIC_PORT})${NC}"

# 1-1. 로컬 포트에서 응답 확인
if curl -s --connect-timeout 2 "http://localhost:${ELASTIC_PORT}/_cluster/health" > /dev/null 2>&1; then
    echo -e "  ${GREEN}✓${NC} localhost:${ELASTIC_PORT} 에 Elasticsearch 응답 있음"
    ELASTIC_FOUND=1
    ELASTIC_SOURCE="localhost"
fi

# 1-2. Docker 컨테이너 확인 (ksp-rag 자체 제외)
if [ $ELASTIC_FOUND -eq 0 ]; then
    ES_CONTAINERS=$(docker ps --format '{{.Names}}' 2>/dev/null | grep -i elastic | grep -v ksp-rag || true)
    if [ -n "$ES_CONTAINERS" ]; then
        echo -e "  ${GREEN}✓${NC} Elasticsearch Docker 컨테이너 실행 중 (외부):"
        echo "$ES_CONTAINERS" | while read name; do
            echo -e "    - ${CYAN}$name${NC}"
        done
        ELASTIC_FOUND=1
        ELASTIC_SOURCE="docker"
    fi
fi

# 1-3. ksp-rag 자체 Elasticsearch 확인
if [ $ELASTIC_FOUND -eq 1 ] && curl -s "http://localhost:${ELASTIC_PORT}/_cluster/health" 2>/dev/null | grep -q "cluster_name"; then
    if docker ps --format '{{.Names}}' 2>/dev/null | grep -q ksp-rag-elastic; then
        echo -e "  ${CYAN}ℹ${NC} (ksp-rag-elastic: 본 프로젝트 컨테이너 - elasticsearch 호스트명 사용)"
        ELASTIC_SOURCE="ksp-rag"
    fi
fi

if [ $ELASTIC_FOUND -eq 0 ]; then
    echo -e "  ${YELLOW}○${NC} Elasticsearch 미발견 (ksp-rag-system에서 새로 띄울 예정)"
fi
echo ""

# ================================
# 2. LLM (vLLM/OpenAI 호환) 확인
# ================================
echo -e "${BLUE}[2/4] LLM 엔드포인트 확인 (포트 ${LLM_PORT})${NC}"

# 2-1. 로컬 포트에서 응답 확인
if curl -s --connect-timeout 2 "http://localhost:${LLM_PORT}/health" > /dev/null 2>&1; then
    echo -e "  ${GREEN}✓${NC} localhost:${LLM_PORT} 에 LLM health 응답 있음"
    LLM_FOUND=1
    LLM_SOURCE="localhost"
elif curl -s --connect-timeout 2 "http://localhost:${LLM_PORT}/v1/models" > /dev/null 2>&1; then
    echo -e "  ${GREEN}✓${NC} localhost:${LLM_PORT} 에 OpenAI 호환 API 응답 있음"
    LLM_FOUND=1
    LLM_SOURCE="localhost"
fi

# 2-2. Docker 컨테이너 확인 (ksp-rag 자체 제외)
if [ $LLM_FOUND -eq 0 ]; then
    LLM_CONTAINERS=$(docker ps --format '{{.Names}}' 2>/dev/null | grep -iE 'vllm|llm|ollama|openai' | grep -v ksp-rag || true)
    if [ -n "$LLM_CONTAINERS" ]; then
        echo -e "  ${GREEN}✓${NC} LLM 관련 Docker 컨테이너 실행 중 (외부):"
        echo "$LLM_CONTAINERS" | while read name; do
            echo -e "    - ${CYAN}$name${NC}"
        done
        LLM_FOUND=1
        LLM_SOURCE="docker"
    fi
fi

# 2-3. 외부 vLLM 확인 (GPU 서버에서 별도 운영)
if [ $LLM_FOUND -eq 1 ]; then
    echo -e "  ${CYAN}ℹ${NC} (외부 vLLM 서비스 - GPU 서버에서 별도 운영)"
fi

if [ $LLM_FOUND -eq 0 ]; then
    echo -e "  ${YELLOW}○${NC} LLM 미발견 (외부 GPU 서버의 vLLM endpoint를 .env.server에 설정 필요)"
fi
echo ""

# ================================
# 3. Docker 컨테이너 전체 목록 (Elastic/LLM 관련)
# ================================
echo -e "${BLUE}[3/4] 실행 중인 Docker 컨테이너 (Elastic/LLM 관련)${NC}"
docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' 2>/dev/null | head -1
docker ps --format '{{.Names}}\t{{.Status}}\t{{.Ports}}' 2>/dev/null | grep -iE 'elastic|elasticsearch|vllm|llm|ollama|9200|8000' || echo "  (관련 컨테이너 없음)"
echo ""

# ================================
# 4. 권장 설정 출력
# ================================
echo "=================================================="
echo -e "${BLUE}[4/4] .env.server 권장 설정${NC}"
echo "=================================================="
echo ""

# ksp-rag 자체 서비스면 기본값 사용
if [ "$ELASTIC_SOURCE" = "ksp-rag" ]; then
    ELASTIC_USE_EXTERNAL=0
else
    ELASTIC_USE_EXTERNAL=$ELASTIC_FOUND
fi
if [ "$LLM_SOURCE" = "ksp-rag" ]; then
    LLM_USE_EXTERNAL=0
else
    LLM_USE_EXTERNAL=$LLM_FOUND
fi

# LLM은 항상 외부 GPU 서버에서 운영 (이 레포에서는 제거됨)
if [ $ELASTIC_USE_EXTERNAL -eq 1 ]; then
    echo -e "${GREEN}✅ 외부 Elasticsearch 사용 가능${NC}"
    echo ""
    echo "다음 .env.server 설정을 사용하세요:"
    echo ""
    echo "  ELASTIC_HOST=host.docker.internal"
    echo "  ELASTIC_PORT=${ELASTIC_PORT}"
    if [ $LLM_FOUND -eq 1 ]; then
        echo "  SERVER_LLM_BASE_URL=http://host.docker.internal:${LLM_PORT}  # 로컬 vLLM"
    else
        echo "  SERVER_LLM_BASE_URL=http://172.16.0.52:8000  # GPU 서버 vLLM"
    fi
    echo ""
    echo "  make up-server-app-only  # app, ui만 시작"
    echo ""
else
    echo -e "${CYAN}ℹ 기본 설정 (Elasticsearch는 ksp-rag에서 띄움)${NC}"
    echo ""
    echo "  ELASTIC_HOST=elasticsearch"
    echo "  ELASTIC_PORT=9200"
    if [ $LLM_FOUND -eq 1 ]; then
        echo "  SERVER_LLM_BASE_URL=http://host.docker.internal:${LLM_PORT}  # 로컬 vLLM"
    else
        echo "  SERVER_LLM_BASE_URL=http://172.16.0.52:8000  # GPU 서버 vLLM"
    fi
    echo ""
    echo "  make up-server  # Elasticsearch + app 시작 (vLLM은 외부 GPU 서버 사용)"
    echo ""
fi

echo "=================================================="
echo ""
