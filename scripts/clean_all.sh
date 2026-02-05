#!/bin/bash
# Clean all processed data and index

echo "🧹 Cleaning processed data and index..."
echo ""

# Remove chunks
if [ -f data/processed/chunks.jsonl ]; then
    rm data/processed/chunks.jsonl
    echo "✅ Removed chunks.jsonl"
else
    echo "ℹ️  No chunks.jsonl found"
fi

# Remove index
if [ -d data/index ] && [ "$(ls -A data/index)" ]; then
    rm -rf data/index/*
    echo "✅ Removed index files"
else
    echo "ℹ️  No index files found"
fi

# Remove sample files if exist
if [ -f data/processed/chunks_sample.jsonl ]; then
    rm data/processed/chunks_sample.jsonl
    echo "✅ Removed sample chunks"
fi

if [ -d data/index_sample ] && [ "$(ls -A data/index_sample)" ]; then
    rm -rf data/index_sample/*
    echo "✅ Removed sample index"
fi

if [ -d data/index_test ] && [ "$(ls -A data/index_test)" ]; then
    rm -rf data/index_test/*
    echo "✅ Removed test index"
fi

echo ""
echo "✅ Clean complete!"
echo ""
echo "Current raw files:"
ls -lh data/raw/*.pdf 2>/dev/null || echo "No PDF files in data/raw/"
echo ""
echo "Ready for fresh start!"
echo "Next steps:"
echo "  1. Keep only 1-2 PDF files in data/raw/"
echo "  2. make ingest"
echo "  3. make index-small"
