#!/bin/bash
# 환경 설정 스크립트

set -e

echo "🔧 KSP RAG System 환경 설정"
echo "================================"

# .env.local 생성
if [ ! -f .env.local ]; then
    echo "📝 .env.local 생성 중..."
    cp .env.local.example .env.local
    echo "✅ .env.local 생성 완료"
    echo ""
    echo "⚠️  중요: .env.local 파일을 열어서 다음을 설정하세요:"
    echo "   - LLM_API_KEY: OpenAI API 키 입력"
    echo ""
else
    echo "✅ .env.local 이미 존재함"
fi

# .env.server 생성
if [ ! -f .env.server ]; then
    echo "📝 .env.server 생성 중..."
    cp .env.server.example .env.server
    echo "✅ .env.server 생성 완료"
else
    echo "✅ .env.server 이미 존재함"
fi

echo ""
echo "✅ 설정 완료!"
echo ""
echo "다음 단계:"
echo "1. .env.local 파일을 열어서 LLM_API_KEY 설정"
echo "2. make build     # Docker 이미지 빌드"
echo "3. make ask Q=\"What is RAG?\"  # 테스트"
