FROM python:3.12-bookworm

WORKDIR /app

COPY requirements.txt /app

RUN --mount=type=cache,target=/root/.cache/pip \
    pip3 install -r requirements.txt

COPY src /app/src
COPY test /app/test
COPY test.sh /app

RUN chmod +x test.sh

ENTRYPOINT ["python", "-m", "streamlit", "run", "src/application.py"]
