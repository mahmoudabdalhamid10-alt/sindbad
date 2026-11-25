"""One small database layer for SQLite (local default) and PostgreSQL (set DATABASE_URL, e.g. Neon).

The app is written in SQLite SQL with `?` placeholders. When DATABASE_URL is set, this module translates
the few dialect differences on the fly (placeholders, SERIAL ids, DOUBLE PRECISION, ILIKE, RETURNING id,
PRAGMA table_info) so both back ends run the same application code and the same tests.
"""
import os, re, sqlite3

DATABASE_URL = os.environ.get('DATABASE_URL', '').strip()
USE_PG = DATABASE_URL.startswith(('postgres://', 'postgresql://'))
SCHEMA = ''  # tests set this to an isolated schema
IDTABLES = {'users', 'products', 'orders', 'rfqs', 'messages', 'interactions', 'quotations', 'resources'}

if USE_PG:
    import psycopg2, psycopg2.extras, psycopg2.pool
    IntegrityError = (sqlite3.IntegrityError, psycopg2.IntegrityError)
    _pool = None
else:
    IntegrityError = (sqlite3.IntegrityError,)


class Row(dict):
    """dict that also supports row[0] like sqlite3.Row."""
    def __getitem__(self, k):
        return list(self.values())[k] if isinstance(k, int) else dict.__getitem__(self, k)


def _translate(sql):
    sql = re.sub(r'\bid INTEGER PRIMARY KEY\b', 'id SERIAL PRIMARY KEY', sql)
    sql = re.sub(r'\bREAL\b', 'DOUBLE PRECISION', sql)
    sql = re.sub(r'\bLIKE\b', 'ILIKE', sql)
    return sql


class Cursor:
    def __init__(self, conn):
        self.conn, self.cur, self.lastrowid = conn, None, None

    def execute(self, sql, args=()):
        if not USE_PG:
            self.cur = self.conn.raw.execute(sql, args)
            self.lastrowid = self.cur.lastrowid
            return self
        m = re.match(r"\s*PRAGMA table_info\((\w+)\)", sql)
        c = self.conn.raw.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        if m:
            c.execute("SELECT column_name AS name FROM information_schema.columns WHERE table_name=%s", (m.group(1),))
        else:
            sql = _translate(sql).replace('%', '%%').replace('?', '%s')
            ins = re.match(r"\s*INSERT INTO (\w+)", sql, re.I)
            if ins and ins.group(1).lower() in IDTABLES and 'RETURNING' not in sql.upper():
                sql += ' RETURNING id'
            c.execute(sql, tuple(args))
            if ins and 'RETURNING' in sql.upper():
                r = c.fetchone()
                self.lastrowid = r['id'] if r else None
        self.cur = c
        return self

    def executescript(self, script):
        if not USE_PG:
            self.conn.raw.executescript(script)
            return self
        c = self.conn.raw.cursor()
        c.execute(_translate(script).replace('%', '%%'))
        self.cur = c
        return self

    def executemany(self, sql, rows):
        rows = list(rows)
        if not USE_PG:
            self.conn.raw.executemany(sql, rows)
            return self
        c = self.conn.raw.cursor()
        tpl = sql.replace('?', '%s')
        head, _, _ = tpl.partition('VALUES')
        psycopg2.extras.execute_values(c, head + 'VALUES %s', rows, page_size=1000)
        self.cur = c
        return self

    def _row(self, r):
        return None if r is None else Row(r) if USE_PG else Row(dict(r))

    def fetchone(self):
        return self._row(self.cur.fetchone())

    def fetchall(self):
        return [self._row(r) for r in self.cur.fetchall()]

    @property
    def rowcount(self):
        return self.cur.rowcount

    def __iter__(self):
        return iter(self.fetchall())


class Conn:
    def __init__(self, raw):
        self.raw = raw

    def cursor(self):
        return Cursor(self)

    def execute(self, sql, args=()):
        return Cursor(self).execute(sql, args)

    def executescript(self, script):
        return Cursor(self).executescript(script)

    def executemany(self, sql, rows):
        return Cursor(self).executemany(sql, rows)

    def commit(self):
        self.raw.commit()

    def rollback(self):
        self.raw.rollback()

    def close(self):
        if USE_PG:
            global _pool
            try:
                self.raw.rollback()
                _pool.putconn(self.raw)
            except Exception:
                pass
        else:
            self.raw.close()


def connect(sqlite_path):
    if USE_PG:
        global _pool
        if _pool is None:
            _pool = psycopg2.pool.ThreadedConnectionPool(1, 8, DATABASE_URL, connect_timeout=20)
        raw = _pool.getconn()
        if SCHEMA:
            with raw.cursor() as c:
                c.execute('SET search_path TO ' + SCHEMA)
            raw.commit()
        return Conn(raw)
    raw = sqlite3.connect(sqlite_path)
    raw.row_factory = sqlite3.Row
    raw.execute('PRAGMA foreign_keys=ON')
    return Conn(raw)
