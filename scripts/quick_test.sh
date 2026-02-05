#!/bin/bash
# Quick test script for RAG system
# Uses small sample and lightweight model

set -e

echo "🚀 Quick Test Setup"
echo "=================="
echo ""

# Create sample chunks (first 10)
echo "📝 Creating sample chunks (first 10)..."
head -n 10 data/processed/chunks.jsonl > data/processed/chunks_sample.jsonl

SAMPLE_COUNT=$(wc -l < data/processed/chunks_sample.jsonl)
echo "✅ Created sample with $SAMPLE_COUNT chunks"
echo ""

# Build index with small model
echo "🔨 Building index with lightweight model..."
echo "Model: BAAI/bge-small-en-v1.5 (134MB, fast)"
echo ""

docker compose --profile local run --rm app python -m ragapp index \
  --chunks data/processed/chunks_sample.jsonl \
  --output data/index_test \
  --model BAAI/bge-small-en-v1.5 \
  --batch-size 8

echo ""
echo "✅ Index built successfully!"
echo ""

# Test retrieval
echo "🔍 Testing retrieval..."
docker compose --profile local run --rm app python -m ragapp retrieve \
  "What is RAG?" \
  --index-dir data/index_test \
  --top-n 5

echo ""
echo "🎉 Quick test complete!"
echo ""
echo "To test with full data, run:"
echo "  make index"
