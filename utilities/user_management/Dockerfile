FROM python:3.12-bookworm

RUN apt-get update \
    && apt-get -y install libpq-dev gcc postgresql \
    && pip install psycopg2==2.9.10

WORKDIR /app

COPY requirements.txt /app

RUN pip3 install -r requirements.txt

COPY src /app/src
COPY test /app/test

COPY entrypoint_test.sh /app
COPY entrypoint.sh /app

RUN chmod +x entrypoint_test.sh
RUN chmod +x entrypoint.sh

RUN useradd -ms /bin/bash py_postgres

USER py_postgres

ENTRYPOINT ["python"]
