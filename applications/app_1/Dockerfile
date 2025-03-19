FROM python:3.12-bookworm

RUN apt-get update \
    && apt-get -y install libpq-dev gcc netcat-traditional \
    && pip install psycopg2
WORKDIR /app

COPY requirements.txt /app

RUN --mount=type=cache,target=/root/.cache/pip \
    pip3 install -r requirements.txt

COPY src /app/src
COPY test /app/test
COPY e2e_tests /app/e2e_tests
COPY entrypoints /app/entrypoints

RUN chmod +x entrypoints/*.sh

ENTRYPOINT ["/app/entrypoints/entrypoint.sh"]
