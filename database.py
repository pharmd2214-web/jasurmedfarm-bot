import sqlite3
from datetime import datetime

DB_FILE = "dorixona.db"

def get_conn():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn()
    c = conn.cursor()

    # Mijozlar
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id     INTEGER PRIMARY KEY,
            full_name   TEXT,
            phone       TEXT,
            address     TEXT,
            balls       INTEGER DEFAULT 0,
            total_spent INTEGER DEFAULT 0,
            joined_at   TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Dorilar katalogi
    c.execute("""
        CREATE TABLE IF NOT EXISTS medicines (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT NOT NULL,
            category    TEXT,
            price       INTEGER NOT NULL,
            stock       INTEGER DEFAULT 0,
            unit        TEXT DEFAULT 'quti',
            description TEXT
        )
    """)

    # Buyurtmalar
    c.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER,
            items       TEXT,
            total       INTEGER,
            discount    INTEGER DEFAULT 0,
            balls_used  INTEGER DEFAULT 0,
            balls_earned INTEGER DEFAULT 0,
            address     TEXT,
            status      TEXT DEFAULT 'yangi',
            created_at  TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    """)

    # Demo dorilar qo'shish
    existing = c.execute("SELECT COUNT(*) FROM medicines").fetchone()[0]
    if existing == 0:
        demo = [
            ("Paracetamol 500mg", "Og'riq qoldiruvchi", 9000,  50, "quti", "Isitma va og'riqqa qarshi"),
            ("Amoxicillin 250mg", "Antibiotik",         32000, 30, "quti", "Bakterial infeksiyalarga qarshi"),
            ("Ibuprofen 400mg",   "Yallig'lanishga qarshi", 8000, 40, "quti", "Og'riq va yallig'lanishga"),
            ("Vitamin C 1000mg",  "Vitamin",             8000,  60, "quti", "Immunitetni kuchaytirish"),
            ("Metformin 500mg",   "Diabet dori",        45000, 20, "quti", "Qon shakarini kamaytirish"),
            ("Enalapril 10mg",    "Yurak-tomir",        28000, 25, "quti", "Qon bosimini pasaytirish"),
            ("Noshpa 40mg",       "Spazmolitik",        12000, 35, "quti", "Spazm va og'riqqa qarshi"),
            ("Suprastin 25mg",    "Allergiya",          15000, 30, "quti", "Allergik reaktsiyalarga"),
        ]
        c.executemany(
            "INSERT INTO medicines (name, category, price, stock, unit, description) VALUES (?,?,?,?,?,?)",
            demo
        )

    conn.commit()
    conn.close()

# ── USERS ──────────────────────────────────────────
def get_user(user_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

def create_user(user_id, full_name):
    conn = get_conn()
    conn.execute(
        "INSERT OR IGNORE INTO users (user_id, full_name) VALUES (?,?)",
        (user_id, full_name)
    )
    conn.commit()
    conn.close()

def update_user_field(user_id, field, value):
    conn = get_conn()
    conn.execute(f"UPDATE users SET {field}=? WHERE user_id=?", (value, user_id))
    conn.commit()
    conn.close()

def add_balls(user_id, balls, spent):
    conn = get_conn()
    conn.execute("""
        UPDATE users
        SET balls = balls + ?,
            total_spent = total_spent + ?
        WHERE user_id = ?
    """, (balls, spent, user_id))
    conn.commit()
    conn.close()

def use_balls(user_id, balls):
    conn = get_conn()
    conn.execute("UPDATE users SET balls = balls - ? WHERE user_id=?", (balls, user_id))
    conn.commit()
    conn.close()

# ── MEDICINES ──────────────────────────────────────
def get_all_medicines():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM medicines WHERE stock > 0 ORDER BY category, name").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_medicine(med_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM medicines WHERE id=?", (med_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

def search_medicines(query):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM medicines WHERE (name LIKE ? OR category LIKE ?) AND stock > 0",
        (f"%{query}%", f"%{query}%")
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def reduce_stock(med_id, qty):
    conn = get_conn()
    conn.execute("UPDATE medicines SET stock = stock - ? WHERE id=?", (qty, med_id))
    conn.commit()
    conn.close()

# ── ORDERS ─────────────────────────────────────────
def create_order(user_id, items_str, total, discount, balls_used, balls_earned, address):
    conn = get_conn()
    cursor = conn.execute("""
        INSERT INTO orders (user_id, items, total, discount, balls_used, balls_earned, address)
        VALUES (?,?,?,?,?,?,?)
    """, (user_id, items_str, total, discount, balls_used, balls_earned, address))
    order_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return order_id

def get_user_orders(user_id, limit=5):
    conn = get_conn()
    rows = conn.execute("""
        SELECT * FROM orders WHERE user_id=? ORDER BY created_at DESC LIMIT ?
    """, (user_id, limit)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_all_orders(status=None):
    conn = get_conn()
    if status:
        rows = conn.execute("SELECT * FROM orders WHERE status=? ORDER BY created_at DESC", (status,)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM orders ORDER BY created_at DESC LIMIT 50").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def update_order_status(order_id, status):
    conn = get_conn()
    conn.execute("UPDATE orders SET status=? WHERE id=?", (status, order_id))
    conn.commit()
    conn.close()
