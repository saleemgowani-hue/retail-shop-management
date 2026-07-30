import sqlite3
import hashlib
import os
import binascii
import uuid


def _resolve_db_name():
    """
    Decide which SQLite file THIS installation should use.

    Priority:
      1. RETAIL_SHOP_DB_NAME environment variable (for technical setups)
      2. A local shop_config.txt file next to this script, first
         non-comment line = the database filename (no coding needed —
         a reseller/installer can just drop a text file per shop)
      3. Falls back to "retail_shop.db"

    This exists so that if two shops are ever accidentally installed in
    the same folder (or on the same machine), they still get separate
    database files instead of silently sharing one.
    """
    env_name = os.environ.get("RETAIL_SHOP_DB_NAME")
    if env_name and env_name.strip():
        return env_name.strip()

    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "shop_config.txt")
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        return line
        except OSError:
            pass

    return "retail_shop.db"


DB_NAME = _resolve_db_name()


def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# ---------------------------------------------------------------------------
# Password Hashing (PBKDF2-HMAC-SHA256 with per-user salt, stdlib only)
# ---------------------------------------------------------------------------
def hash_password(password, salt=None):
    """Return (hash_hex, salt_hex). Generates a new salt if none is given."""
    if salt is None:
        salt = binascii.hexlify(os.urandom(16)).decode("utf-8")
    pwd_hash = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), 100_000
    )
    return binascii.hexlify(pwd_hash).decode("utf-8"), salt


def verify_password(password, salt, stored_hash):
    """Verify against the new salted scheme."""
    if not salt:
        return False
    new_hash, _ = hash_password(password, salt)
    return new_hash == stored_hash


def verify_legacy_password(password, stored_hash):
    """Verify against the OLD unsalted sha256 scheme (for migration only)."""
    return hashlib.sha256(password.encode()).hexdigest() == stored_hash


def _column_exists(cursor, table, column):
    cursor.execute(f"PRAGMA table_info({table})")
    return any(row["name"] == column for row in cursor.fetchall())


def _add_column_if_missing(cursor, table, column, coltype):
    if not _column_exists(cursor, table, column):
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {coltype}")


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    # Users Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL
        )
    ''')

    # Products Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            barcode TEXT,
            category TEXT,
            brand TEXT,
            unit TEXT,
            purchase_price REAL,
            selling_price REAL,
            gst REAL,
            opening_stock REAL,
            minimum_stock REAL
        )
    ''')

    # Suppliers Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS suppliers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            mobile TEXT,
            address TEXT,
            gst_number TEXT
        )
    ''')

    # Customers Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            mobile TEXT UNIQUE,
            address TEXT
        )
    ''')

    # Purchases Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS purchases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            purchase_date TEXT,
            supplier_id INTEGER,
            product_id INTEGER,
            quantity REAL,
            purchase_price REAL,
            discount REAL,
            gst REAL,
            transport REAL,
            total_amount REAL,
            FOREIGN KEY(supplier_id) REFERENCES suppliers(id),
            FOREIGN KEY(product_id) REFERENCES products(id)
        )
    ''')

    # Bills Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bills (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bill_number TEXT UNIQUE,
            bill_date TEXT,
            customer_name TEXT,
            customer_mobile TEXT,
            payment_mode TEXT,
            subtotal REAL,
            discount REAL,
            gst REAL,
            grand_total REAL
        )
    ''')

    # Bill Items Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bill_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bill_id INTEGER,
            product_id INTEGER,
            quantity REAL,
            selling_price REAL,
            total REAL,
            FOREIGN KEY(bill_id) REFERENCES bills(id),
            FOREIGN KEY(product_id) REFERENCES products(id)
        )
    ''')

    # Expenses Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            expense_date TEXT,
            expense_type TEXT,
            amount REAL,
            remarks TEXT
        )
    ''')

    # Settings Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            shop_name TEXT,
            address TEXT,
            mobile TEXT,
            gst_number TEXT,
            footer_message TEXT,
            terms TEXT
        )
    ''')

    conn.commit()

    # -----------------------------------------------------------------
    # Safe, additive migrations (never drop/rename existing columns)
    # -----------------------------------------------------------------
    _add_column_if_missing(cursor, "users", "salt", "TEXT")
    _add_column_if_missing(cursor, "products", "is_active", "INTEGER DEFAULT 1")
    _add_column_if_missing(cursor, "suppliers", "is_active", "INTEGER DEFAULT 1")
    _add_column_if_missing(cursor, "customers", "is_active", "INTEGER DEFAULT 1")
    _add_column_if_missing(cursor, "settings", "configured", "INTEGER DEFAULT 0")
    _add_column_if_missing(cursor, "settings", "shop_id", "TEXT")
    paid_amount_is_new = not _column_exists(cursor, "purchases", "paid_amount")
    _add_column_if_missing(cursor, "purchases", "paid_amount", "REAL DEFAULT 0")
    conn.commit()

    if paid_amount_is_new:
        # Purchases recorded before payment-tracking existed: assume they
        # were already settled the old way (outside this system), so we
        # don't suddenly show scary "pending balance" for old history.
        # Anyone can correct an individual entry from the Supplier Ledger.
        cursor.execute("UPDATE purchases SET paid_amount = total_amount WHERE paid_amount IS NULL OR paid_amount = 0")
        conn.commit()

    # Backfill for installs that already have real shop data from before
    # this column existed — don't force the setup wizard on them again.
    cursor.execute(
        "UPDATE settings SET configured = 1 "
        "WHERE (configured IS NULL OR configured = 0) "
        "AND shop_name IS NOT NULL AND TRIM(shop_name) != '' AND shop_name != 'My Retail Shop'"
    )
    cursor.execute("SELECT shop_id FROM settings WHERE id = 1")
    row = cursor.fetchone()
    if row and not row["shop_id"]:
        cursor.execute("UPDATE settings SET shop_id = ? WHERE id = 1", (uuid.uuid4().hex[:12],))
    conn.commit()

    # Backfill is_active for any pre-existing rows that migrated in as NULL
    cursor.execute("UPDATE products SET is_active = 1 WHERE is_active IS NULL")
    cursor.execute("UPDATE suppliers SET is_active = 1 WHERE is_active IS NULL")
    cursor.execute("UPDATE customers SET is_active = 1 WHERE is_active IS NULL")
    conn.commit()

    # Default Admin User (new salted scheme)
    cursor.execute("SELECT * FROM users WHERE username = 'admin'")
    if not cursor.fetchone():
        hashed_password, salt = hash_password("password")
        cursor.execute(
            "INSERT INTO users (username, password, role, salt) VALUES (?, ?, ?, ?)",
            ("admin", hashed_password, "Admin", salt),
        )

    # Default Settings — no fake placeholder data anymore. A brand-new
    # install starts "not configured"; app.py shows a one-time Shop Setup
    # screen (before login) that collects the real shop details.
    cursor.execute("SELECT * FROM settings WHERE id = 1")
    if not cursor.fetchone():
        cursor.execute(
            "INSERT INTO settings (shop_name, address, mobile, gst_number, footer_message, terms, configured, shop_id) "
            "VALUES (?, ?, ?, ?, ?, ?, 0, ?)",
            ("", "", "", "", "Thank You, Visit Again!", "Goods once sold will not be taken back.",
             uuid.uuid4().hex[:12]),
        )

    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Shop Setup helpers (used by the first-run wizard in app.py)
# ---------------------------------------------------------------------------
def get_settings():
    conn = get_connection()
    try:
        return conn.execute("SELECT * FROM settings WHERE id = 1").fetchone()
    finally:
        conn.close()


def is_shop_configured():
    row = get_settings()
    return bool(row and row["configured"])


def save_shop_setup(shop_name, address, mobile, gst_number, footer_message, terms):
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE settings SET shop_name=?, address=?, mobile=?, gst_number=?, "
            "footer_message=?, terms=?, configured=1 WHERE id=1",
            (shop_name, address, mobile, gst_number, footer_message, terms),
        )
        conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    init_db()
    print("Database initialized successfully!")
