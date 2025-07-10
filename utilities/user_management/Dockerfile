FROM python:3.12-bookworm

RUN apt-get update \
    && apt-get -y install libpq-dev gcc postgresql \
    && pip install psycopg2==2.9.10

WORKDIR /app

COPY requirements.txt /app

RUN pip3 install -r requirements.txt

COPY src /app/src
COPY test /app/test

RUN mkdir /app/entrypoints
COPY entrypoint_test.sh /app/entrypoints
COPY entrypoint.sh /app/entrypoints

RUN chmod +x entrypoints/*

RUN useradd -ms /bin/bash py_postgres

RUN chown -R py_postgres:py_postgres /app

USER py_postgres

ENTRYPOINT ["./entrypoints/entrypoint.sh"]
