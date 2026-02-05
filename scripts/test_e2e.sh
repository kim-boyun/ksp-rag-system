#!/bin/bash
# End-to-end test script for RAG pipeline

set -e

echo "🧪 RAG System E2E Test"
echo "======================"
echo ""

# Check if PDF files exist
PDF_COUNT=$(ls data/raw/*.pdf 2>/dev/null | wc -l)
if [ "$PDF_COUNT" -eq 0 ]; then
    echo "❌ No PDF files found in data/raw/"
    echo "Please add at least one PDF file for testing."
    exit 1
fi

echo "✅ Found $PDF_COUNT PDF file(s) in data/raw/"
echo ""

# Step 1: Ingest
echo "📥 Step 1: Ingesting PDFs..."
make ingest
echo ""

# Step 2: Index
echo "🔨 Step 2: Building index (using small model for speed)..."
make index-small
echo ""

# Step 3: Retrieve (no rerank)
echo "🔍 Step 3: Testing retrieval..."
TEST_QUERY="온두라스 연금"
make retrieve Q="$TEST_QUERY"
echo ""

# Step 4: Ask (no rerank)
echo "💬 Step 4: Testing RAG (no rerank)..."
make ask Q="$TEST_QUERY"
echo ""

# Step 5: Ask with rerank
echo "💬 Step 5: Testing RAG (with rerank)..."
make ask-rerank Q="온두라스 연금 개혁"
echo ""

echo "🎉 E2E Test Complete!"
echo ""
echo "Summary:"
echo "  ✅ PDF Ingestion"
echo "  ✅ Index Building"
echo "  ✅ Hybrid Retrieval (BM25 + FAISS + RRF)"
echo "  ✅ LLM Reranking"
echo "  ✅ Answer Generation"
echo "  ✅ Citation Extraction"
