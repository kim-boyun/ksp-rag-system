# ================================
# Multi-stage Dockerfile
# ================================

# Stage 1: Builder
FROM python:3.11-slim AS builder

WORKDIR /app

# 시스템 의존성
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Poetry 설치
RUN pip install --no-cache-dir poetry==1.7.1

# Poetry 설정 (virtualenv 생성 안 함)
RUN poetry config virtualenvs.create false

# 의존성 파일 복사
COPY pyproject.toml poetry.lock* ./

# 의존성 설치 (개발 의존성 포함)
RUN poetry install --no-interaction --no-ansi --with dev || \
    (poetry lock && poetry install --no-interaction --no-ansi --with dev)

# Stage 2: Runtime
FROM python:3.11-slim

WORKDIR /app

# 필요한 시스템 패키지
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Python 패키지 복사
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# 환경 변수
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/src:$PYTHONPATH

# 기본 설정 파일 복사 (example 사용 → 맥/윈도우 첫 클론에서도 빌드 성공)
COPY .env.local.example .env
COPY .env.server.example .env.server

# 헬스체크
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

# 기본 명령어
CMD ["python", "-m", "ragapp", "--help"]
