FROM python:3.11-slim as builder
WORKDIR /app 
# 사용자가 지정한 /app 디렉토리에서 작업 수행
COPY requirements.txt .
RUN python -m pip install --user --no-cache-dir -r requirements.txt
# -m: 파이썬에 내장되어 있는 모듈을 사용하세요. --user: 모든 프로젝트가 아닌 현재 사용중인 환경에만 설치하세요
# -r: 다음 파일 이름에 있는 패키지를 설치하세요. --no-cache-dir: 캐시를 남기지 마세요. (이미지 크기를 줄이기 위해)



FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /root/.local /root/.local
# builder에서 만든 파일들 중 /root/.local 디렉토리만 현재 이미지의 /root/.local 디렉토리에 복사
ENV PATH=/root/.local/bin:$PATH
# 복사해온 라이브러리들을 사용할 수 있도록 PATH 환경변수에 추가
ENV PYTHONUNBUFFERED=1
#파이썬 로그 버퍼링 없이 출력
ENV PYTHONDONTWRITEBYTECODE=1
#컨테이너를 가볍게 하기 위해 파이썬이 .pyc 파일을 생성하지 않도록 설정

COPY . . 
#현재 내 컴퓨터에 있는 실제 소스 코드를 컨테이너 내부로 복사
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
# 30초 마다 검사 실시, 10초 안에 응답 없으면 실패, 컨테이너 시작 후 5초 후부터 검사 시작, 3회 연속 실패 시 컨테이너를 비정상으로 간주
    CMD python -c "import requests; requests.get('http://localhost:8000/health')" || exit 1
    #파일 실행하지 말고 "서버 살아 있는지 확인하는 코드"안의 코드 바로 실행 ||  실패시 에러 1번 후 종료
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
#컨테이너가 정상일때 실행할 명령어, main.py 파일의 app 객체를 uvicorn으로 실행