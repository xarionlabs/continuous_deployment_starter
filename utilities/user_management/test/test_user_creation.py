import pytest
import psycopg2

from conftest import TEST_USERS, USER_PASSWORDS


@pytest.mark.parametrize("user", TEST_USERS)
def test_user_permissions(user, postgresql_testdb1, postgresql_testdb2):
    """Verify users have correct access within their assigned database."""
    username = user["username"]
    db = user["database"]
    role = user["role"]
    password = USER_PASSWORDS[username]

    # Pick the right test database connection
    db_conn = postgresql_testdb1 if db == "testdb1" else postgresql_testdb2
    # Create a new connection using the user's credentials
    conn = psycopg2.connect(
        dbname=db_conn.info.dbname,
        user=username,
        password=password,
        host=db_conn.info.host,
        port=db_conn.info.port
    )
    conn.autocommit = True  # Ensure no implicit transactions
    cur = conn.cursor()

    # ✅ Should be able to SELECT
    cur.execute("SELECT * FROM public.test_table;")
    cur.fetchall()

    if role == "read":
        # ❌ Should NOT be able to INSERT, UPDATE, DELETE
        for query in [
            "INSERT INTO public.test_table (data) VALUES ('fail');",
            "UPDATE public.test_table SET data='fail' WHERE id=1;",
            "DELETE FROM public.test_table WHERE id=1;",
        ]:
            with pytest.raises(psycopg2.errors.InsufficientPrivilege):
                cur.execute(query)

    elif role == "write":
        # ✅ Should be able to INSERT, UPDATE, DELETE
        cur.execute("INSERT INTO public.test_table (data) VALUES ('test');")
        cur.execute("UPDATE public.test_table SET data='updated' WHERE id=1;")
        cur.execute("DELETE FROM public.test_table WHERE id=1;")

    elif role == "admin":
        # ✅ Should be able to ALTER and DROP tables
        cur.execute("ALTER TABLE public.test_table ADD COLUMN admin_extra TEXT;")
        cur.execute("DROP TABLE public.test_table;")

    cur.close()
