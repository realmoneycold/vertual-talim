import os
import sqlite3
from datetime import datetime
from config import Config

try:
    import psycopg2
    import psycopg2.extras
    HAS_PSYCOPG = True
except ImportError:
    HAS_PSYCOPG = False

class Database:
    def __init__(self):
        # Dynamically switch to PostgreSQL if DATABASE_URL is provided, fallback to SQLite
        self.use_postgres = bool(Config.DATABASE_URL) and HAS_PSYCOPG
        self.init_db()

    def _connect(self):
        if self.use_postgres:
            # Connect to Neon PostgreSQL
            conn = psycopg2.connect(Config.DATABASE_URL)
            return conn
        else:
            # Connect to SQLite
            conn = sqlite3.connect(Config.DB_FILE)
            conn.row_factory = sqlite3.Row
            return conn

    @property
    def q(self) -> str:
        """Returns the query placeholder: '%s' for PostgreSQL, '?' for SQLite."""
        return "%s" if self.use_postgres else "?"

    def init_db(self):
        """Initializes the database schema."""
        with self._connect() as conn:
            with conn.cursor() as cursor:
                if self.use_postgres:
                    # PostgreSQL syntax for creating table
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS users (
                            user_id BIGINT PRIMARY KEY,
                            username VARCHAR(255),
                            full_name VARCHAR(255),
                            status VARCHAR(50) DEFAULT 'pending',
                            created_at VARCHAR(100),
                            actioned_by BIGINT
                        )
                    """)
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS courses (
                            id SERIAL PRIMARY KEY,
                            name VARCHAR(255) UNIQUE,
                            description TEXT,
                            webapp_url VARCHAR(500)
                        )
                    """)
                else:
                    # SQLite syntax
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS users (
                            user_id INTEGER PRIMARY KEY,
                            username TEXT,
                            full_name TEXT,
                            status TEXT DEFAULT 'pending',
                            created_at TEXT,
                            actioned_by INTEGER
                        )
                    """)
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS courses (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            name TEXT UNIQUE,
                            description TEXT,
                            webapp_url TEXT
                        )
                    """)
                
                # Check if courses are already populated, if not, load defaults
                cursor.execute("SELECT COUNT(*) FROM courses")
                if cursor.fetchone()[0] == 0:
                    default_courses = [
                        ("1-kurs 📚", "1-kurs materiallari va darslari", None),
                        ("2-kurs 📚", "2-kurs materiallari va darslari", None),
                        ("3-kurs 📚", "Propedevtika darslari", Config.WEBAPP_URL)
                    ]
                    for name, desc, url in default_courses:
                        cursor.execute(f"""
                            INSERT INTO courses (name, description, webapp_url)
                            VALUES ({self.q}, {self.q}, {self.q})
                        """, (name, desc, url))
            conn.commit()

        # Legacy migration (SQLite text file only)
        if not self.use_postgres:
            txt_file = "allowed_users.txt"
            if os.path.exists(txt_file):
                try:
                    with open(txt_file, "r") as f:
                        legacy_ids = {int(line.strip()) for line in f if line.strip().isdigit()}
                    
                    now = datetime.utcnow().isoformat()
                    with self._connect() as conn:
                        with conn.cursor() as cursor:
                            for user_id in legacy_ids:
                                cursor.execute(f"""
                                    INSERT INTO users (user_id, username, full_name, status, created_at)
                                    VALUES ({self.q}, 'Legacy Migration', 'Legacy User', 'approved', {self.q})
                                    ON CONFLICT(user_id) DO NOTHING
                                """, (user_id, now))
                        conn.commit()
                    
                    os.rename(txt_file, "allowed_users.txt.bak")
                    import logging
                    logging.info(f"Successfully migrated legacy users from {txt_file} to SQLite!")
                except Exception as e:
                    import logging
                    logging.error(f"Error migrating legacy users from {txt_file}: {e}")

    def add_pending_user(self, user_id: int, username: str | None, full_name: str):
        """Adds a new user with pending status or updates their info if already exists."""
        now = datetime.utcnow().isoformat()
        with self._connect() as conn:
            with conn.cursor() as cursor:
                if self.use_postgres:
                    # Postgres UPSERT
                    cursor.execute(f"""
                        INSERT INTO users (user_id, username, full_name, status, created_at)
                        VALUES ({self.q}, {self.q}, {self.q}, 'pending', {self.q})
                        ON CONFLICT(user_id) DO UPDATE SET
                            username = EXCLUDED.username,
                            full_name = EXCLUDED.full_name,
                            status = 'pending',
                            created_at = EXCLUDED.created_at
                    """, (user_id, username, full_name, now))
                else:
                    # SQLite UPSERT
                    cursor.execute(f"""
                        INSERT INTO users (user_id, username, full_name, status, created_at)
                        VALUES ({self.q}, {self.q}, {self.q}, 'pending', {self.q})
                        ON CONFLICT(user_id) DO UPDATE SET
                            username = excluded.username,
                            full_name = excluded.full_name,
                            status = 'pending',
                            created_at = excluded.created_at
                    """, (user_id, username, full_name, now))
            conn.commit()

    def get_user_status(self, user_id: int) -> str | None:
        """Gets user status ('pending', 'approved', 'rejected', 'banned' or None)."""
        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(f"SELECT status FROM users WHERE user_id = {self.q}", (user_id,))
                row = cursor.fetchone()
                if row:
                    # sqlite row can be indexed by name, postgres cursor returns tuple by default
                    return row[0] if self.use_postgres else row["status"]
                return None

    def approve_user(self, user_id: int, admin_id: int) -> bool:
        """Approves a pending user."""
        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(f"""
                    UPDATE users 
                    SET status = 'approved', actioned_by = {self.q} 
                    WHERE user_id = {self.q}
                """, (admin_id, user_id))
                rowcount = cursor.rowcount
            conn.commit()
            return rowcount > 0

    def reject_user(self, user_id: int, admin_id: int) -> bool:
        """Rejects a user."""
        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(f"""
                    UPDATE users 
                    SET status = 'rejected', actioned_by = {self.q} 
                    WHERE user_id = {self.q}
                """, (admin_id, user_id))
                rowcount = cursor.rowcount
            conn.commit()
            return rowcount > 0

    def ban_user(self, user_id: int, admin_id: int) -> bool:
        """Bans a user from requesting again."""
        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(f"""
                    UPDATE users 
                    SET status = 'banned', actioned_by = {self.q} 
                    WHERE user_id = {self.q}
                """, (admin_id, user_id))
                rowcount = cursor.rowcount
            conn.commit()
            return rowcount > 0

    def get_users_by_status(self, status: str) -> list[dict]:
        """Gets all users with a specific status."""
        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(f"""
                    SELECT user_id, username, full_name, status, created_at, actioned_by 
                    FROM users WHERE status = {self.q}
                """, (status,))
                rows = cursor.fetchall()
                
                results = []
                for row in rows:
                    if self.use_postgres:
                        results.append({
                            "user_id": row[0],
                            "username": row[1],
                            "full_name": row[2],
                            "status": row[3],
                            "created_at": row[4],
                            "actioned_by": row[5]
                        })
                    else:
                        results.append(dict(row))
                return results

    def get_all_users(self) -> list[dict]:
        """Gets all registered users."""
        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT user_id, username, full_name, status, created_at FROM users")
                rows = cursor.fetchall()
                
                results = []
                for row in rows:
                    if self.use_postgres:
                        results.append({
                            "user_id": row[0],
                            "username": row[1],
                            "full_name": row[2],
                            "status": row[3],
                            "created_at": row[4]
                        })
                    else:
                        results.append(dict(row))
                return results

    def get_all_courses(self) -> list[dict]:
        """Gets all courses from the database."""
        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT id, name, description, webapp_url FROM courses ORDER BY id ASC")
                rows = cursor.fetchall()
                results = []
                for row in rows:
                    if self.use_postgres:
                        results.append({
                            "id": row[0],
                            "name": row[1],
                            "description": row[2],
                            "webapp_url": row[3]
                        })
                    else:
                        results.append(dict(row))
                return results

    def add_course(self, name: str, description: str | None = None, webapp_url: str | None = None) -> bool:
        """Adds a new course to the database."""
        try:
            with self._connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(f"""
                        INSERT INTO courses (name, description, webapp_url)
                        VALUES ({self.q}, {self.q}, {self.q})
                    """, (name, description, webapp_url))
                conn.commit()
                return True
        except Exception:
            return False

    def delete_course(self, course_id: int) -> bool:
        """Deletes a course from the database by its ID."""
        try:
            with self._connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(f"DELETE FROM courses WHERE id = {self.q}", (course_id,))
                conn.commit()
                return True
        except Exception:
            return False

    def update_course_url(self, course_id: int, webapp_url: str | None) -> bool:
        """Updates the webapp_url of a course."""
        try:
            with self._connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(f"UPDATE courses SET webapp_url = {self.q} WHERE id = {self.q}", (webapp_url, course_id))
                conn.commit()
                return True
        except Exception:
            return False
