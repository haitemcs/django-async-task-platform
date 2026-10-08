import psycopg2

print("=== PostgreSQL Password Fix ===")
pg_pass = input("Enter your 'postgres' superuser password: ")
new_user_pass = input("Enter new password for 'async_tasks' user (e.g. haitem): ")

try:
    conn = psycopg2.connect(
        dbname="postgres",
        user="postgres",
        password=pg_pass,
        host="localhost",
        port="5432"
    )
    conn.autocommit = True
    cur = conn.cursor()
    
    # Update password inside PostgreSQL engine
    cur.execute(f"ALTER USER async_tasks WITH PASSWORD '{new_user_pass}';")
    
    print(f"\n SUCCESS! PostgreSQL password for 'async_tasks' is now set to: {new_user_pass}")
    cur.close()
    conn.close()

except Exception as e:
    print(f"\n FAILED: {e}")