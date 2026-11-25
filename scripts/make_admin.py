"""Give an existing account the admin role:  python scripts/make_admin.py someone@example.com
Works on SQLite (default) or PostgreSQL (set DATABASE_URL)."""
import os, sys
from datetime import datetime
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import main

email = sys.argv[1].lower()
c = main.db()
u = c.execute('SELECT id FROM users WHERE email=?', (email,)).fetchone()
if not u:
    sys.exit('no such user')
if not c.execute("SELECT 1 FROM user_roles WHERE user_id=? AND role='admin'", (u['id'],)).fetchone():
    c.execute("INSERT INTO user_roles(user_id,role,granted_at) VALUES(?,?,?)", (u['id'], 'admin', datetime.utcnow().isoformat()))
c.commit(); c.close()
print('admin role granted to', email)
