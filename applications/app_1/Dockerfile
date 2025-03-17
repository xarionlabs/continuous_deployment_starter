FROM python:3.12-bookworm

RUN apt-get update \
    && apt-get -y install libpq-dev gcc \
    && pip install psycopg2
WORKDIR /app

COPY requirements.txt /app

RUN --mount=type=cache,target=/root/.cache/pip \
    pip3 install -r requirements.txt

COPY src /app/src
COPY test /app/test
COPY entrypoint.sh /app
COPY entrypoint_api.sh /app
COPY entrypoint_test.sh /app
COPY entrypoint_migrations.sh /app

RUN chmod +x entrypoint.sh
RUN chmod +x entrypoint_api.sh
RUN chmod +x entrypoint_test.sh
RUN chmod +x entrypoint_migrations.sh

ENTRYPOINT ["/app/entrypoint.sh"]
