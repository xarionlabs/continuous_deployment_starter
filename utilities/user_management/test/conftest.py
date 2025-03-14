import csv
import os
from functools import partial

import psycopg2
from pytest_postgresql import factories

from manage_users import create_user_management_sql

TEST_SQL_FILE = "/tmp/test_users.sql"
TEST_CSV_FILE = "/tmp/test_users.csv"

TEST_USERS = [
    {"username": "test_reader", "database": "testdb1", "role": "read"},
    {"username": "test_writer", "database": "testdb1", "role": "write"},
    {"username": "test_admin", "database": "testdb1", "role": "admin"},
    {"username": "test_qareader", "database": "testdb2", "role": "read"},
]

USER_PASSWORDS = {
    "test_reader": "readerpass",
    "test_writer": "writerpass",
    "test_admin": "adminpass",
    "test_qareader": "qapass"
}


def create_test_csv():
    for user, password in USER_PASSWORDS.items():
        os.environ[f"PSQL_{user.upper()}_PASSWORD"] = password

    with open(TEST_CSV_FILE, "w", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=["username", "database", "role"])
        writer.writeheader()
        writer.writerows(TEST_USERS)


def generate_sql_file():
    create_test_csv()
    return create_user_management_sql(TEST_CSV_FILE, TEST_SQL_FILE)


file_paths = generate_sql_file()


def create_load_function_from_sql(sql_file, db_name):
    # read the SQL file
    with open(sql_file, "r") as file:
        sql_content = file.read()
    # parameterize the database name
    sql_content = sql_content.replace(db_name, "{db}")

    sql_content = f"""
    -- Create a test table for user permission testing
    CREATE SCHEMA IF NOT EXISTS public;

    CREATE TABLE IF NOT EXISTS public.test_table (
        id SERIAL PRIMARY KEY,
        data TEXT NOT NULL,
        created_at TIMESTAMPTZ DEFAULT NOW()
    );
    """ + sql_content

    # return a callable that executes the SQL with the following parameters host, port, user, dbname, password
    def load_function(host, port, user, dbname, password, sql=sql_content):
        sql = sql.replace("{db}", dbname)
        conn = psycopg2.connect(host=host, port=port, user=user, dbname=dbname, password=password)
        with conn.cursor() as cursor:
            cursor.execute(sql)
        conn.commit()
        conn.close()

    return partial(load_function, sql=sql_content)


postgresql_testdb1_proc = factories.postgresql_proc(load=[create_load_function_from_sql(file_paths["testdb1"], "testdb1")],
                                               dbname="testdb1")
postgresql_testdb2_proc = factories.postgresql_proc(load=[create_load_function_from_sql(file_paths["testdb2"], "testdb2")],
                                               dbname="testdb2")

postgresql_testdb1 = factories.postgresql("postgresql_testdb1_proc")
postgresql_testdb2 = factories.postgresql("postgresql_testdb2_proc")