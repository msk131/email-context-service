# Initial Data Instructions

This folder contains a SQL script with example rows to populate the database with minimal data required to run the service locally.

Files
- `initial_data.sql` — SQL insert statements for `firms`, `accountants`, `clients`, `emails`, `email_summaries`, and `summarization_logs`.

How to run

1. Ensure your database schema/migrations have been applied and the database is running.
2. Run the SQL file with your preferred SQL client. Examples:

Postgres (psql):

```
psql -h <host> -U <user> -d <dbname> -f docs/initial_data.sql
```

Docker Compose (example service name `db`):

```
docker-compose exec db psql -U <user> -d <dbname> -f /app/docs/initial_data.sql
```

Notes
- The script uses explicit IDs. If your DB uses sequences (SERIAL), adjust sequences after running to avoid conflicts (see commented note in the SQL file).
- `password_hash` values are placeholders — replace with real password hashes when creating real users.
- `summary_encrypted` is a placeholder string; the app expects an encrypted summary in production.
