#!/bin/bash
# ============================================================
# M4 Pro (또는 CUDA GPU) 네이티브 bge-m3 인덱싱 스크립트
# - Docker 없이 직접 실행 → MPS/CUDA 자동 감지
# - 인덱스명: ksp_rag_index_m3  (small 인덱스와 완전 분리)
# - 실행 전 Elasticsearch만 Docker로 띄워야 함
#
# 사용법:
#   bash scripts/index_m3_native.sh
# ============================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

INDEX_NAME="ksp_rag_index_m3"
MODEL="BAAI/bge-m3"
# MPS 메모리 절약: 임베딩 배치 작게 (OOM 방지). CUDA/메모리 넉넉하면 32 등으로 올려도 됨.
BATCH_SIZE="${BGE_BATCH_SIZE:-8}"
INDEX_BATCH_SIZE="${BGE_INDEX_BATCH_SIZE:-2000}"
ELASTIC_HOST="${ELASTIC_HOST:-localhost}"
ELASTIC_PORT="${ELASTIC_PORT:-9200}"
CHUNKS_FILE="data/processed/chunks.jsonl"

echo "============================================================"
echo "  KSP RAG - bge-m3 네이티브 인덱싱 (MPS/CUDA 자동 감지)"
echo "============================================================"
echo "  인덱스명 : $INDEX_NAME  (small 인덱스와 분리)"
echo "  모델     : $MODEL"
echo "  배치     : embedding=$BATCH_SIZE, streaming=$INDEX_BATCH_SIZE (MPS OOM 방지)"
echo "  ES 호스트: $ELASTIC_HOST:$ELASTIC_PORT"
echo "  청크 파일: $CHUNKS_FILE"
echo "============================================================"
echo ""

# 1) chunks.jsonl 확인
if [ ! -f "$CHUNKS_FILE" ]; then
    echo "❌ chunks.jsonl 없음: $CHUNKS_FILE"
    echo "   먼저 make ingest 를 실행하세요."
    exit 1
fi
LINES=$(wc -l < "$CHUNKS_FILE")
echo "✅ chunks.jsonl: $LINES 줄"

# 2) Elasticsearch 연결 확인
echo ""
echo "🔌 Elasticsearch 연결 확인 중..."
for i in 1 2 3 4 5; do
    if curl -sf "http://$ELASTIC_HOST:$ELASTIC_PORT/_cluster/health" > /dev/null 2>&1; then
        echo "✅ Elasticsearch 연결 성공"
        break
    fi
    if [ $i -eq 5 ]; then
        echo "❌ Elasticsearch 에 연결할 수 없습니다: http://$ELASTIC_HOST:$ELASTIC_PORT"
        echo ""
        echo "   Elasticsearch를 먼저 실행하세요:"
        echo "   docker compose --profile server up elasticsearch -d"
        exit 1
    fi
    echo "   재시도 $i/5 ..."
    sleep 3
done

# 3) Python 환경 확인
echo ""
echo "🐍 Python 환경 확인..."
if command -v poetry &> /dev/null; then
    PYTHON_CMD="poetry run python"
    echo "✅ poetry 사용"
elif command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
    echo "✅ python3 사용"
else
    echo "❌ Python을 찾을 수 없습니다."
    exit 1
fi

# 디바이스 감지 미리 출력
$PYTHON_CMD -c "
import torch
if torch.cuda.is_available():
    print('🚀 디바이스: CUDA (GPU)')
elif torch.backends.mps.is_available():
    print('🚀 디바이스: MPS (Apple Silicon)')
else:
    print('⚠️  디바이스: CPU (느릴 수 있음)')
" 2>/dev/null || echo "⚠️  torch 미설치 - poetry install 먼저 실행하세요"

# 4) 기존 m3 인덱스 존재 여부 확인
echo ""
EXISTS=$(curl -s -o /dev/null -w "%{http_code}" "http://$ELASTIC_HOST:$ELASTIC_PORT/$INDEX_NAME")
if [ "$EXISTS" = "200" ]; then
    echo "⚠️  기존 인덱스 '$INDEX_NAME' 가 존재합니다. --recreate 로 삭제 후 재생성합니다."
fi

# 5) 인덱싱 실행
echo ""
echo "🤖 인덱싱 시작... (시간이 오래 걸릴 수 있습니다)"
echo ""

ELASTIC_HOST=$ELASTIC_HOST \
ELASTIC_PORT=$ELASTIC_PORT \
ELASTIC_INDEX_NAME=$INDEX_NAME \
$PYTHON_CMD -m ragapp index-elastic \
    --recreate \
    --model "$MODEL" \
    --index-name "$INDEX_NAME" \
    --host "$ELASTIC_HOST" \
    --port "$ELASTIC_PORT" \
    --batch-size "$BATCH_SIZE" \
    --index-batch-size "$INDEX_BATCH_SIZE"

echo ""
echo "============================================================"
echo "✅ 인덱싱 완료!"
echo ""
echo "📋 다음 단계:"
echo ""
echo "1) 인덱스 확인:"
echo "   curl http://$ELASTIC_HOST:$ELASTIC_PORT/$INDEX_NAME/_count"
echo ""
echo "2) Elasticsearch 백업 (이 머신에서):"
echo "   make elastic-export"
echo "   # → data/elastic-data-backup.tar.gz"
echo ""
echo "3) 회사 맥으로 전송 후 복원:"
echo "   scp data/elastic-data-backup.tar.gz user@work-mac:~/ksp-rag-system/data/"
echo "   # 회사 맥에서: make elastic-import"
echo ""
echo "4) 회사 맥 .env 또는 UI에서 인덱스 전환:"
echo "   ELASTIC_INDEX_NAME=$INDEX_NAME"
echo "============================================================"
