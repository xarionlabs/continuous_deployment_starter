import os
import csv

# Paths
CSV_FILE = "/app/users.csv"
SQL_FILE = "/app/users.sql"

# Define role-based privileges at the **database level**
ROLE_PRIVILEGES = {
    "read": [
        "CONNECT ON DATABASE {db}",
        "USAGE ON SCHEMA public",
        "SELECT ON ALL TABLES IN SCHEMA public"
    ],
    "write": [
        "CONNECT ON DATABASE {db}",
        "USAGE ON SCHEMA public",
        "SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public"
    ],
    "admin": [
        "CONNECT ON DATABASE {db}",
        "USAGE ON SCHEMA public",
        "ALL PRIVILEGES ON ALL TABLES IN SCHEMA public",
        "ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public",
        "ALL PRIVILEGES ON SCHEMA public"
    ]
}


def get_password_from_env(username):
    """Retrieve password from environment variable."""
    return os.getenv(f"PSQL_{username}_PASSWORD".upper(), None)


import os
import csv


def create_user_management_sql(csv_file, sql_dir):
    """Generate SQL scripts for user and role management using role groups."""
    databases = {}  # Store users grouped by database
    all_users = set()
    output_files = {}

    with open(csv_file, newline="") as csvfile:
        reader = csv.DictReader(csvfile)

        for row in reader:
            db = row["database"].strip()
            username = row["username"].strip()
            all_users.add(username)

            if db not in databases:
                databases[db] = []
            databases[db].append(row)

    os.makedirs(sql_dir, exist_ok=True)

    for db, users in databases.items():
        sql_file = os.path.join(sql_dir, f"{db}.sql")
        with open(sql_file, "w") as sqlfile:
            sqlfile.write(f"-- SQL script for database {db}\n")

            # Step 1: Create role groups (if they don't exist)
            sqlfile.write(f"""
            DO $$ 
            BEGIN
                IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'read_group') THEN
                    CREATE ROLE read_group;
                END IF;

                IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'write_group') THEN
                    CREATE ROLE write_group;
                END IF;

                IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'admin_group') THEN
                    CREATE ROLE admin_group;
                END IF;
            END $$;
            """)

            # Step 2: Grant privileges to the groups
            sqlfile.write(f"""
            -- Grant read access to read_group
            GRANT CONNECT ON DATABASE {db} TO read_group;
            GRANT USAGE ON SCHEMA public TO read_group;
            GRANT SELECT ON ALL TABLES IN SCHEMA public TO read_group;

            -- Grant write access to write_group
            GRANT CONNECT ON DATABASE {db} TO write_group;
            GRANT USAGE ON SCHEMA public TO write_group;
            GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO write_group;
            GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA public TO write_group;

            -- Grant full admin access to admin_group
            GRANT CONNECT ON DATABASE {db} TO admin_group;
            GRANT USAGE ON SCHEMA public TO admin_group;
            GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO admin_group;
            GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO admin_group;
            DO $$ 
            DECLARE r RECORD;
            BEGIN
                FOR r IN SELECT tablename FROM pg_tables WHERE schemaname = 'public' LOOP
                    EXECUTE format('ALTER TABLE public.%I OWNER TO admin_group;', r.tablename);
                END LOOP;
            END $$;
            """)

            # Step 3: Create users and assign them to groups
            for user in users:
                username = user["username"].strip()
                role = user["role"].strip().lower()

                password_env_var = f"PSQL_{username.upper()}_PASSWORD"
                password = os.getenv(password_env_var, "defaultpassword")

                sqlfile.write(f"""
                DO $$ 
                BEGIN
                    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '{username}') THEN
                        CREATE ROLE {username} WITH LOGIN PASSWORD '{password}';
                    END IF;

                    -- Assign user to the appropriate group
                    GRANT {role}_group TO {username};
                END $$;
                """)
            print(f"Generated SQL script: {sql_file}")

        output_files[db] = sql_file
    return output_files


if __name__ == "__main__":
    create_user_management_sql()
