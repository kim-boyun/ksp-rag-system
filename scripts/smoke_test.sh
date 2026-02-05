#!/bin/bash
# ================================
# Smoke Test for KSP RAG System
# ================================
# 최소 3가지 핵심 기능 검증:
# 1. Ingest (PDF → chunks)
# 2. Retrieve (검색)
# 3. Ask (RAG 질의응답)

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "$PROJECT_ROOT"

echo "=================================================="
echo "🧪 KSP RAG System - Smoke Test"
echo "=================================================="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test counters
TESTS_PASSED=0
TESTS_FAILED=0

# Helper functions
print_test() {
    echo -e "${BLUE}[TEST]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[✓]${NC} $1"
    ((TESTS_PASSED++))
}

print_failure() {
    echo -e "${RED}[✗]${NC} $1"
    ((TESTS_FAILED++))
}

print_info() {
    echo -e "${YELLOW}[INFO]${NC} $1"
}

# ================================
# Test 1: Ingest (PDF → chunks)
# ================================
test_ingest() {
    print_test "Test 1: PDF 인제스트"
    
    # Check if PDF exists
    if [ ! -f "data/raw/2016_17 KSP 엘살바도르 혁신역량 강화를 위한 정책제언_영문최종보고서(영문).pdf" ]; then
        print_failure "Test 1: PDF 파일이 없습니다 (data/raw/)"
        return 1
    fi
    
    # Run ingest
    print_info "인제스트 실행 중..."
    if docker compose --profile local run --rm app python -m ragapp ingest > /tmp/ingest_output.log 2>&1; then
        # Check if chunks.jsonl exists and has content
        if [ -f "data/processed/chunks.jsonl" ]; then
            CHUNK_COUNT=$(wc -l < data/processed/chunks.jsonl | tr -d ' ')
            if [ "$CHUNK_COUNT" -gt 100 ]; then
                print_success "Test 1: 인제스트 성공 ($CHUNK_COUNT chunks)"
                return 0
            else
                print_failure "Test 1: 청크 수가 너무 적음 ($CHUNK_COUNT chunks)"
                return 1
            fi
        else
            print_failure "Test 1: chunks.jsonl 파일이 생성되지 않음"
            return 1
        fi
    else
        print_failure "Test 1: 인제스트 실행 실패"
        cat /tmp/ingest_output.log
        return 1
    fi
}

# ================================
# Test 2: Retrieve (검색)
# ================================
test_retrieve() {
    print_test "Test 2: 로컬 검색 (BM25+FAISS)"
    
    # Build local index if not exists
    if [ ! -d "data/index" ]; then
        print_info "로컬 인덱스 빌드 중..."
        if ! docker compose --profile local run --rm app python -m ragapp index > /tmp/index_output.log 2>&1; then
            print_failure "Test 2: 인덱스 빌드 실패"
            cat /tmp/index_output.log
            return 1
        fi
    fi
    
    # Run retrieve
    print_info "검색 실행 중..."
    OUTPUT=$(docker compose --profile local run --rm app python -m ragapp retrieve "What is the pension system?" --output json 2>&1)
    
    if echo "$OUTPUT" | grep -q '"retrieved_docs"'; then
        DOC_COUNT=$(echo "$OUTPUT" | grep -o '"retrieved_docs"' | wc -l)
        print_success "Test 2: 검색 성공 (문서 검색됨)"
        return 0
    else
        print_failure "Test 2: 검색 결과 없음"
        echo "$OUTPUT"
        return 1
    fi
}

# ================================
# Test 3: Ask (RAG 질의응답)
# ================================
test_ask() {
    print_test "Test 3: RAG 질의응답"
    
    # Run ask
    print_info "RAG 질의 실행 중..."
    OUTPUT=$(docker compose --profile local run --rm app python -m ragapp ask "What is the main topic of the document?" --output json 2>&1)
    
    if echo "$OUTPUT" | grep -q '"answer"'; then
        # Check if answer is not empty
        if echo "$OUTPUT" | grep -q '"answer".*[a-zA-Z]'; then
            print_success "Test 3: RAG 질의응답 성공"
            return 0
        else
            print_failure "Test 3: 답변이 비어있음"
            return 1
        fi
    else
        print_failure "Test 3: RAG 실행 실패"
        echo "$OUTPUT"
        return 1
    fi
}

# ================================
# Run all tests
# ================================
echo "=================================================="
echo "🚀 테스트 시작"
echo "=================================================="
echo ""

# Test 1: Ingest
test_ingest || true
echo ""

# Test 2: Retrieve
test_retrieve || true
echo ""

# Test 3: Ask
test_ask || true
echo ""

# ================================
# Summary
# ================================
echo "=================================================="
echo "📊 테스트 결과"
echo "=================================================="
echo -e "${GREEN}통과:${NC} $TESTS_PASSED"
echo -e "${RED}실패:${NC} $TESTS_FAILED"
echo "총 테스트: $((TESTS_PASSED + TESTS_FAILED))"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ 모든 스모크 테스트 통과!${NC}"
    exit 0
else
    echo -e "${RED}❌ $TESTS_FAILED 개의 테스트 실패${NC}"
    exit 1
fi
