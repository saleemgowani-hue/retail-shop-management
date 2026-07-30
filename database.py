import sqlite3
import hashlib
import os
import binascii
import uuid


def _resolve_db_name():
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


def hash_password(password, salt=None):
    if salt is None:
        salt = binascii.hexlify(os.urandom(16)).decode("utf-8")
    pwd_hash = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), 100_000
    )
    return binascii.hexlify(pwd_hash).decode("utf-8"), salt


def verify_password(password, salt, stored_hash):
    if not salt:
        return False
    new_hash, _ = hash_password(password, salt)
    return new_hash == stored_hash


def verify_legacy_password(password, stored_hash):
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
            min_stock_level REAL
        )
    ''')

    # Suppliers Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS suppliers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            contact_person TEXT,
            phone TEXT,
            email TEXT,
            address TEXT,
            gst_number TEXT
        )
    ''')

    # Customers Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT,
            email TEXT,
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
            total_amount REAL,
            paid_amount REAL,
            balance_amount REAL,
            FOREIGN KEY(supplier_id) REFERENCES suppliers(id),
            FOREIGN KEY(product_id) REFERENCES products(id)
        )
    ''')

    # Bills Table (Updated with all POS columns)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bills (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT,
            subtotal REAL,
            tax_percentage REAL,
            tax_amount REAL,
            grand_total REAL,
            payment_mode TEXT,
            created_at TEXT
        )
    ''')

    # Bill Items Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bill_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bill_id INTEGER,
            product_id INTEGER,
            product_name TEXT,
            price REAL,
            quantity REAL,
            total REAL,
            FOREIGN KEY(bill_id) REFERENCES bills(id),
            FOREIGN KEY(product_id) REFERENCES products(id)
        )
    ''')

    # Expenses Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            amount REAL,
            category TEXT,
            expense_date TEXT
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

    # Migrations & Additive Columns
    _add_column_if_missing(cursor, "users", "salt", "TEXT")
    _add_column_if_missing(cursor, "products", "is_active", "INTEGER DEFAULT 1")
    _add_column_if_missing(cursor, "suppliers", "is_active", "INTEGER DEFAULT 1")
    _add_column_if_missing(cursor, "customers", "is_active", "INTEGER DEFAULT 1")
    _add_column_if_missing(cursor, "settings", "configured", "INTEGER DEFAULT 0")
    _add_column_if_missing(cursor, "settings", "shop_id", "TEXT")
    
    conn.commit()

    # Default Admin User
    cursor.execute("SELECT * FROM users WHERE username = 'admin'")
    if not cursor.fetchone():
        hashed_password, salt = hash_password("password")
        cursor.execute(
            "INSERT INTO users (username, password, role, salt) VALUES (?, ?, ?, ?)",
            ("admin", hashed_password, "Admin", salt),
        )

    # Default Settings
    cursor.execute("SELECT * FROM settings WHERE id = 1")
    if not cursor.fetchone():
        cursor.execute(
            "INSERT INTO settings (shop_name, address, mobile, gst_number, footer_message, terms, configured) "
            "VALUES (?, ?, ?, ?, ?, ?, 0)",
            ("", "", "", "", "Thank You, Visit Again!", "Goods once sold will not be taken back."),
        )

    conn.commit()
    conn.close()


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
