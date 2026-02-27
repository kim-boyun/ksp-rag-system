#!/bin/bash
# GPU 서버용 인덱싱 패키지 생성 스크립트
# 실행: bash scripts/pack_for_gpu_server.sh
# 결과: ksp-indexer.tar.gz (약 2GB)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
OUTPUT="$PROJECT_ROOT/ksp-indexer.tar.gz"

echo "📦 GPU 서버용 인덱싱 패키지 생성 중..."
echo "   소스: $PROJECT_ROOT"
echo "   출력: $OUTPUT"
echo ""

CHUNKS="$PROJECT_ROOT/data/processed/chunks.jsonl"
if [ ! -f "$CHUNKS" ]; then
    echo "❌ chunks.jsonl 없음: $CHUNKS"
    echo "   먼저 make ingest 를 실행하세요."
    exit 1
fi

CHUNKS_LINES=$(wc -l < "$CHUNKS")
CHUNKS_SIZE=$(du -sh "$CHUNKS" | cut -f1)
echo "✅ chunks.jsonl 확인: $CHUNKS_LINES 줄 / $CHUNKS_SIZE"
echo ""

cd "$PROJECT_ROOT"

tar czf "$OUTPUT" \
    --exclude='data/raw' \
    --exclude='data/index' \
    --exclude='data/cache' \
    --exclude='data/elastic-data-backup.tar.gz' \
    --exclude='models' \
    --exclude='ops' \
    --exclude='docs' \
    --exclude='tests' \
    --exclude='src/ui' \
    --exclude='.git' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.env' \
    --exclude='.env.local' \
    src/ragapp \
    docker-compose.yml \
    Dockerfile \
    Makefile \
    pyproject.toml \
    poetry.lock \
    .env.server \
    data/processed/chunks.jsonl

OUTPUT_SIZE=$(du -sh "$OUTPUT" | cut -f1)
echo ""
echo "✅ 패키지 생성 완료: $OUTPUT ($OUTPUT_SIZE)"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📋 다음 단계:"
echo ""
echo "1) GPU 서버로 전송:"
echo "   scp ksp-indexer.tar.gz user@gpu-server:~/"
echo ""
echo "2) GPU 서버에서 압축 해제:"
echo "   tar xzf ksp-indexer.tar.gz -C ksp-indexer && cd ksp-indexer"
echo ""
echo "3) .env 설정 (Elasticsearch 호스트 확인):"
echo "   cp .env.server .env"
echo "   # ELASTIC_HOST=elasticsearch  ← docker-compose 내부 서비스명이므로 그대로 OK"
echo ""
echo "4) bge-m3로 인덱싱 (GPU 활용):"
echo "   make index-elastic-recreate"
echo ""
echo "5) 인덱스 백업:"
echo "   make elastic-export"
echo "   # → data/elastic-data-backup.tar.gz 생성"
echo ""
echo "6) 로컬로 전송:"
echo "   scp user@gpu-server:~/ksp-indexer/data/elastic-data-backup.tar.gz data/"
echo ""
echo "7) [로컬 Mac] Elasticsearch 복원:"
echo "   make elastic-import"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
