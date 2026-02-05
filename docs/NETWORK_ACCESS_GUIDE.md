# 네트워크 접근 권한 가이드

서버에 네트워크 접근 권한이 없으면 외부 서비스(vLLM, Elasticsearch)에 연결할 수 없습니다.

## ⚠️ 문제 상황

### 1. GPU 서버 vLLM 접근 불가

**증상**:
```bash
# 헬스체크 실패
make llm-health
# ❌ External LLM not accessible

# 질의 시 에러
make ask-server Q="테스트"
# ConnectionError: Connection refused
# 또는
# httpx.TimeoutException: Request timed out
```

**원인**:
- 방화벽에서 포트 8000 차단
- GPU 서버가 실행 중이지 않음
- 네트워크 경로 문제 (라우팅, VPN 필요)
- IP 주소가 잘못됨

### 2. Elasticsearch 접근 불가

**증상**:
```bash
# 헬스체크 실패
make health-server
# ❌ Elasticsearch - Connection failed

# 인덱싱 실패
make index-elastic
# ConnectionError: Cannot connect to Elasticsearch
```

**원인**:
- Elasticsearch 서비스가 실행 중이지 않음
- 포트 9200 접근 불가
- Docker 네트워크 문제

## 🔍 접근 권한 확인 방법

### 1. GPU 서버 vLLM 연결 확인

```bash
# 방법 1: 헬스체크 명령어 사용
make llm-health

# 방법 2: 직접 curl로 확인
curl http://172.16.0.52:8000/health

# 방법 3: 모델 목록 확인
curl http://172.16.0.52:8000/v1/models
```

**성공 시**:
```json
{"status":"ok"}
```

**실패 시**:
- `Connection refused`: 서버가 실행 중이지 않거나 포트가 닫혀있음
- `Connection timed out`: 방화벽 차단 또는 네트워크 경로 문제
- `Name or service not known`: IP 주소가 잘못됨

### 2. Elasticsearch 연결 확인

```bash
# 방법 1: 헬스체크 명령어 사용
make health-server

# 방법 2: 직접 curl로 확인
curl http://localhost:9200/_cluster/health

# 방법 3: Docker 컨테이너 확인
docker compose ps | grep elastic
```

**성공 시**:
```json
{"status":"green","number_of_nodes":1,...}
```

**실패 시**:
- `Connection refused`: Elasticsearch가 실행 중이지 않음
- `Connection timed out`: 네트워크 문제

## 🛠️ 해결 방법

### 방법 1: 로컬 개발 모드로 전환

네트워크 접근 권한이 없을 때는 로컬 개발 모드를 사용하세요:

```bash
# .env.local 사용 (OpenAI API)
make ask-local Q="질문"
make ui-local
```

**장점**:
- GPU 서버 불필요
- 네트워크 접근 권한 불필요
- 인터넷만 연결되면 됨 (OpenAI API)

**단점**:
- OpenAI API 비용 발생
- 인터넷 연결 필요

### 방법 2: 네트워크 접근 권한 요청

**GPU 서버 접근**:
1. 네트워크 관리자에게 포트 8000 접근 권한 요청
2. VPN 연결 필요 여부 확인
3. 방화벽 규칙 추가 요청

**요청 내용**:
```
- 출발지: 내 IP 주소 (또는 서브넷)
- 목적지: GPU 서버 IP (172.16.0.52)
- 포트: 8000
- 프로토콜: TCP
```

### 방법 3: 동일 서버에서 실행

운영 서버와 GPU 서버가 같은 서버라면:

```bash
# .env.server 설정
SERVER_LLM_BASE_URL=http://host.docker.internal:8000
```

`host.docker.internal`을 사용하면 Docker 컨테이너에서 호스트의 서비스를 접근할 수 있습니다.

### 방법 4: SSH 터널링 (임시 해결책)

SSH 접근 권한이 있다면:

```bash
# SSH 터널 생성
ssh -L 8000:localhost:8000 user@gpu-server

# 다른 터미널에서
# .env.server 설정
SERVER_LLM_BASE_URL=http://localhost:8000
```

## 📊 에러 메시지 해석

### Connection refused

```
ConnectionError: Connection refused
```

**의미**: 서버가 해당 포트에서 리스닝하지 않음

**해결**:
1. GPU 서버에서 vLLM이 실행 중인지 확인
2. 포트 번호 확인
3. 서비스 재시작

### Connection timed out

```
httpx.TimeoutException: Request timed out
```

**의미**: 네트워크 경로 문제 또는 방화벽 차단

**해결**:
1. 방화벽 규칙 확인
2. 네트워크 관리자에게 문의
3. VPN 연결 확인

### Name or service not known

```
httpx.ConnectError: Name or service not known
```

**의미**: IP 주소 또는 호스트명이 잘못됨

**해결**:
1. `.env.server`의 `SERVER_LLM_BASE_URL` 확인
2. IP 주소가 올바른지 확인
3. DNS 설정 확인

## 🔐 보안 고려사항

### 방화벽 설정

**권장 설정**:
- GPU 서버(8000 포트): 운영 서버 IP에서만 접근 허용
- 운영 서버(8501 포트): 필요한 사용자만 접근 허용

**예시 (iptables)**:
```bash
# GPU 서버에서 실행
# 운영 서버 IP에서만 접근 허용
iptables -A INPUT -p tcp --dport 8000 -s <운영서버_IP> -j ACCEPT
iptables -A INPUT -p tcp --dport 8000 -j DROP
```

### VPN 사용

내부 네트워크에 접근하려면 VPN 연결이 필요할 수 있습니다:

```bash
# VPN 연결 후
make llm-health  # 다시 시도
```

## 📝 체크리스트

연결 문제 해결을 위한 체크리스트:

- [ ] GPU 서버가 실행 중인가? (`make gpu-health` 또는 `curl http://<GPU_IP>:8000/health`)
- [ ] IP 주소가 올바른가? (`.env.server`의 `SERVER_LLM_BASE_URL` 확인)
- [ ] 포트가 열려있는가? (`telnet <GPU_IP> 8000` 또는 `nc -zv <GPU_IP> 8000`)
- [ ] 방화벽 규칙이 올바른가? (네트워크 관리자 확인)
- [ ] VPN 연결이 필요한가? (내부 네트워크인 경우)
- [ ] Docker 네트워크가 올바른가? (`docker network ls` 확인)

## 🚀 빠른 해결

**즉시 사용 가능한 방법**:
```bash
# 로컬 개발 모드로 전환
make ask-local Q="질문"
```

**장기적 해결**:
1. 네트워크 관리자에게 접근 권한 요청
2. 방화벽 규칙 추가
3. VPN 설정 (필요시)
