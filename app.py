import streamlit as st
import pandas as pd
from datetime import datetime, date
import io

from database import (
    init_db,
    get_connection,
    hash_password,
    verify_password,
    verify_legacy_password,
    is_shop_configured,
    get_settings,
    save_shop_setup,
)

# ============================================================================
# Page Configuration
# ============================================================================
st.set_page_config(
    page_title="Retail Shop Management Software",
    page_icon="🛒",
    layout="wide"
)

# Custom CSS for Multicolour Buttons & Gorgeous Dashboard UI
st.markdown("""
    <style>
    /* Sidebar styling */
    section[data-testid="stSidebar"] {
        background-color: #f0f2f6;
    }

    /* Multicolour Sidebar Menu Buttons */
    /* 1. Dashboard - Blue */
    div.stButton > button:nth-of-type(1) {background: linear-gradient(135deg, #00c6ff, #0072ff); color: white; border-radius: 8px; font-weight: bold; border: none;}
    /* 2. POS - Purple */
    div.stButton > button:nth-of-type(2) {background: linear-gradient(135deg, #7f7fd5, #86a8e7, #91eae4); color: white; border-radius: 8px; font-weight: bold; border: none;}
    /* 3. Product Master - Orange */
    div.stButton > button:nth-of-type(3) {background: linear-gradient(135deg, #f12711, #f5af19); color: white; border-radius: 8px; font-weight: bold; border: none;}
    /* 4. Supplier - Green */
    div.stButton > button:nth-of-type(4) {background: linear-gradient(135deg, #11998e, #38ef7d); color: white; border-radius: 8px; font-weight: bold; border: none;}
    /* 5. Customer - Pink */
    div.stButton > button:nth-of-type(5) {background: linear-gradient(135deg, #ff416c, #ff4b2b); color: white; border-radius: 8px; font-weight: bold; border: none;}
    /* 6. Stock Purchase - Indigo */
    div.stButton > button:nth-of-type(6) {background: linear-gradient(135deg, #4e54c8, #8f94fb); color: white; border-radius: 8px; font-weight: bold; border: none;}
    /* 7. Expense - Teal */
    div.stButton > button:nth-of-type(7) {background: linear-gradient(135deg, #203a43, #2c5364); color: white; border-radius: 8px; font-weight: bold; border: none;}
    /* 8. Reports - Amber */
    div.stButton > button:nth-of-type(8) {background: linear-gradient(135deg, #f7b733, #fc4a1a); color: white; border-radius: 8px; font-weight: bold; border: none;}
    /* 9. Low Stock - Red Alert */
    div.stButton > button:nth-of-type(9) {background: linear-gradient(135deg, #cb356b, #bd3f32); color: white; border-radius: 8px; font-weight: bold; border: none;}
    /* 10. Settings - Dark Blue/Grey */
    div.stButton > button:nth-of-type(10) {background: linear-gradient(135deg, #3a6073, #16222a); color: white; border-radius: 8px; font-weight: bold; border: none;}

    /* General Button Hover Effect */
    div.stButton > button:hover {
        opacity: 0.9;
        transform: scale(1.02);
        transition: all 0.3s ease;
    }

    /* Multicolour Dashboard Metric Cards */
    div[data-testid="stMetric"]:nth-of-type(1) { background: linear-gradient(135deg, #e3f2fd, #bbdefb); border-left: 6px solid #1e88e5; }
    div[data-testid="stMetric"]:nth-of-type(2) { background: linear-gradient(135deg, #f3e5f5, #e1bee7); border-left: 6px solid #8e24aa; }
    div[data-testid="stMetric"]:nth-of-type(3) { background: linear-gradient(135deg, #e8f5e9, #c8e6c9); border-left: 6px solid #43a047; }
    div[data-testid="stMetric"]:nth-of-type(4) { background: linear-gradient(135deg, #fff3e0, #ffe0b2); border-left: 6px solid #fb8c00; }
    div[data-testid="stMetric"]:nth-of-type(5) { background: linear-gradient(135deg, #ffebee, #ffcdd2); border-left: 6px solid #e53935; }

    div[data-testid="stMetric"] {
        padding: 15px;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    }
    div[data-testid="stMetric"] label {
        font-size: 15px !important;
        color: #333333 !important;
        font-weight: 700 !important;
    }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
        font-size: 24px !important;
        color: #111111 !important;
        font-weight: 800 !important;
    }
    </style>
""", unsafe_allow_html=True)

# Extra CSS for the colorful Dashboard navigation tiles. These are REAL
# st.button widgets (not <a href> links) — an <a> tag causes a full browser
# page reload which resets Streamlit's session and logs the user out. Real
# buttons stay inside Streamlit's normal websocket interaction, so the
# session (and login) is never lost. Colors are applied via nth-of-type,
# scoped to this one container so they never clash with sidebar buttons.
st.markdown("""
    <style>
    .st-key-dash_nav_tiles div[data-testid="stHorizontalBlock"] {
        gap: 14px;
    }
    .st-key-dash_nav_tiles div.stButton > button {
        min-height: 92px;
        width: 100%;
        border-radius: 16px;
        border: none;
        color: white;
        font-weight: 700;
        font-size: 14px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.18);
        transition: transform 0.15s ease, box-shadow 0.15s ease, opacity 0.15s ease;
        white-space: normal;
    }
    .st-key-dash_nav_tiles div.stButton > button:hover {
        transform: translateY(-4px) scale(1.02);
        box-shadow: 0 9px 18px rgba(0,0,0,0.26);
        opacity: 0.95;
    }
    </style>
""", unsafe_allow_html=True)

# Initialize Database
init_db()

# ============================================================================
# Role-Based Access Control
# ============================================================================
ROLES = ["Admin", "Manager", "Cashier"]

PAGE_PERMISSIONS = {
    "Dashboard": ["Admin", "Manager", "Cashier"],
    "Billing System (POS)": ["Admin", "Manager", "Cashier"],
    "Product Master": ["Admin", "Manager"],
    "Supplier Management": ["Admin", "Manager"],
    "Customer Management": ["Admin", "Manager", "Cashier"],
    "Stock Purchase": ["Admin", "Manager"],
    "Expense Management": ["Admin", "Manager"],
    "Complete Reports Hub": ["Admin", "Manager"],
    "Low Stock Alerts": ["Admin", "Manager", "Cashier"],
    "Settings": ["Admin"],
}

PAGE_STYLES = {
    "Dashboard": ("📊", "#00c6ff", "#0072ff"),
    "Billing System (POS)": ("🧾", "#7f7fd5", "#38ef7d"),
    "Product Master": ("📦", "#f12711", "#f5af19"),
    "Supplier Management": ("🏭", "#11998e", "#38ef7d"),
    "Customer Management": ("👥", "#ff416c", "#ff4b2b"),
    "Stock Purchase": ("📥", "#4e54c8", "#8f94fb"),
    "Expense Management": ("💸", "#485563", "#29323c"),
    "Complete Reports Hub": ("📈", "#f7b733", "#fc4a1a"),
    "Low Stock Alerts": ("⚠️", "#cb356b", "#bd3f32"),
    "Settings": ("⚙️", "#3a6073", "#16222a"),
}

MENU_ICONS = {
    "Dashboard": "📊 Dashboard",
    "Billing System (POS)": "🧾 Billing System (POS)",
    "Product Master": "📦 Product Master",
    "Supplier Management": "🏭 Supplier Management",
    "Customer Management": "👥 Customer Management",
    "Stock Purchase": "📥 Stock Purchase",
    "Expense Management": "💸 Expense Management",
    "Complete Reports Hub": "📈 Complete Reports Hub",
    "Low Stock Alerts": "⚠️ Low Stock Alerts",
    "Settings": "⚙️ Shop Settings",
}


def page_allowed(page, role):
    return role in PAGE_PERMISSIONS.get(page, [])


# ============================================================================
# Session State for Authentication & Navigation
# ============================================================================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.role = ""

if "current_page" not in st.session_state:
    st.session_state.current_page = "Dashboard"

if "cart" not in st.session_state:
    st.session_state.cart = []

if "confirm_delete" not in st.session_state:
    st.session_state.confirm_delete = {}


# ============================================================================
# Auth Helper Functions
# ============================================================================
def check_login(username, password):
    """Verify credentials. Transparently upgrades legacy (unsalted) password
    hashes to the new salted scheme on successful login."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        if not user:
            return None

        if user["salt"]:
            valid = verify_password(password, user["salt"], user["password"])
        else:
            # Legacy unsalted SHA-256 hash from the old scheme
            valid = verify_legacy_password(password, user["password"])
            if valid:
                new_hash, new_salt = hash_password(password)
                cursor.execute(
                    "UPDATE users SET password = ?, salt = ? WHERE id = ?",
                    (new_hash, new_salt, user["id"]),
                )
                conn.commit()

        return user if valid else None
    finally:
        conn.close()


def register_user(username, password, role):
    if not username or not username.strip():
        return False, "Username cannot be empty."
    if len(password) < 4:
        return False, "Password must be at least 4 characters."

    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        if cursor.fetchone():
            return False, "Username already exists!"

        hashed_password, salt = hash_password(password)
        cursor.execute(
            "INSERT INTO users (username, password, role, salt) VALUES (?, ?, ?, ?)",
            (username, hashed_password, role, salt),
        )
        conn.commit()
        return True, "User registered successfully!"
    finally:
        conn.close()


def change_password(username, old_pass, new_pass):
    if len(new_pass) < 4:
        return False, "New password must be at least 4 characters."

    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        if not user:
            return False, "User not found!"

        if user["salt"]:
            valid = verify_password(old_pass, user["salt"], user["password"])
        else:
            valid = verify_legacy_password(old_pass, user["password"])

        if not valid:
            return False, "Current password is incorrect!"

        new_hash, new_salt = hash_password(new_pass)
        cursor.execute(
            "UPDATE users SET password = ?, salt = ? WHERE username = ?",
            (new_hash, new_salt, username),
        )
        conn.commit()
        return True, "Password changed successfully!"
    finally:
        conn.close()


# ============================================================================
# Login / Registration Screen
# ============================================================================
# ============================================================================
# First-Run Shop Setup Wizard
# ============================================================================
def shop_setup_screen():
    """
    Runs once per installation, before login even exists. Makes sure every
    copy of this app is tied to one specific shop's own details/database —
    this is the human checkpoint that stops a reseller/installer from ever
    accidentally reusing another shop's data file.
    """
    st.markdown("<h1 style='text-align: center; color: #2b2d42;'>🛒 Welcome — Let's Set Up Your Shop</h1>", unsafe_allow_html=True)
    st.markdown(
        "<p style='text-align: center; color: gray;'>This runs only once for this installation. "
        "Each shop should have its own separate installation and its own database file.</p>",
        unsafe_allow_html=True
    )
    st.markdown("<br>", unsafe_allow_html=True)

    settings_row = get_settings()

    col1, col2, col3 = st.columns([1, 1.4, 1])
    with col2:
        with st.form("shop_setup_form"):
            shop_name = st.text_input("Shop Name *", value=(settings_row['shop_name'] if settings_row else ""))
            address = st.text_area("Address", value=(settings_row['address'] if settings_row else ""))
            mobile = st.text_input("Mobile", value=(settings_row['mobile'] if settings_row else ""))
            gst_number = st.text_input("GST Number (optional)", value=(settings_row['gst_number'] if settings_row else ""))
            footer_message = st.text_input(
                "Receipt Footer Message",
                value=(settings_row['footer_message'] if settings_row else "Thank You, Visit Again!")
            )
            terms = st.text_area(
                "Terms & Conditions",
                value=(settings_row['terms'] if settings_row else "Goods once sold will not be taken back.")
            )
            submitted = st.form_submit_button("✅ Save & Continue", use_container_width=True)

            if submitted:
                if not shop_name.strip():
                    st.warning("Shop Name is required.")
                else:
                    save_shop_setup(shop_name.strip(), address, mobile, gst_number, footer_message, terms)
                    st.success("Shop set up successfully! Redirecting to login...")
                    st.rerun()

        if settings_row and settings_row["shop_id"]:
            st.caption(f"Installation ID: `{settings_row['shop_id']}` (useful for support — this is unique to this install)")


def login_screen():
    st.markdown("<h1 style='text-align: center; color: #2b2d42;'>🛒 Retail Shop Management Software</h1>", unsafe_allow_html=True)
    st.markdown("<h4 style='text-align: center; color: gray;'>Welcome! Please Login or Register to continue</h4>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        tab_login, tab_signup = st.tabs(["🔑 Login", "📝 Sign Up / Register"])

        with tab_login:
            with st.form("login_form"):
                username = st.text_input("Username")
                password = st.text_input("Password", type="password")
                submit = st.form_submit_button("Login to System", use_container_width=True)

                if submit:
                    user = check_login(username, password)
                    if user:
                        st.session_state.logged_in = True
                        st.session_state.username = user["username"]
                        st.session_state.role = user["role"]
                        st.success("Login Successful!")
                        st.rerun()
                    else:
                        st.error("Invalid Username or Password")

        with tab_signup:
            with st.form("signup_form"):
                new_user = st.text_input("Choose Username")
                new_pass = st.text_input("Choose Password", type="password")
                role_choice = st.selectbox("Select Role", ROLES)
                reg_submit = st.form_submit_button("Register New User", use_container_width=True)

                if reg_submit:
                    if new_user and new_pass:
                        success, msg = register_user(new_user, new_pass, role_choice)
                        if success:
                            st.success(msg)
                        else:
                            st.error(msg)
                    else:
                        st.warning("Please fill all fields.")


# ============================================================================
# Cached, read-only lookups (short TTL so data stays effectively live while
# still saving repeated queries on every widget interaction/rerun)
# ============================================================================
@st.cache_data(ttl=5)
def fetch_active_products():
    conn = get_connection()
    try:
        return pd.read_sql(
            "SELECT * FROM products WHERE is_active = 1 ORDER BY name", conn
        )
    finally:
        conn.close()


@st.cache_data(ttl=5)
def fetch_active_suppliers():
    conn = get_connection()
    try:
        return pd.read_sql(
            "SELECT * FROM suppliers WHERE is_active = 1 ORDER BY name", conn
        )
    finally:
        conn.close()


@st.cache_data(ttl=5)
def fetch_active_customers():
    conn = get_connection()
    try:
        return pd.read_sql(
            "SELECT * FROM customers WHERE is_active = 1 ORDER BY name", conn
        )
    finally:
        conn.close()


def clear_lookup_caches():
    fetch_active_products.clear()
    fetch_active_suppliers.clear()
    fetch_active_customers.clear()


def get_live_stock(conn, product_id):
    """Always-fresh (uncached) stock check — used right before any write
    that depends on current stock, to avoid over-selling on stale data."""
    row = conn.execute(
        "SELECT opening_stock FROM products WHERE id = ?", (product_id,)
    ).fetchone()
    return row["opening_stock"] if row else 0


def df_to_excel_bytes(df, sheet_name="Sheet1"):
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)
    return buffer.getvalue()


# ============================================================================
# Main Application
# ============================================================================
def main_app():
    role = st.session_state.role

    # The colorful Dashboard tiles are plain HTML links (?nav=PageName) so
    # their color/layout isn't at the mercy of Streamlit's button DOM order.
    # Catch that click here before rendering anything else.
    st.sidebar.markdown(f"### 👤 Welcome, **{st.session_state.username}**")
    st.sidebar.markdown(f"**Role:** `{role}`")

    if st.sidebar.button("🚪 Logout", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.session_state.role = ""
        st.session_state.cart = []
        st.rerun()

    st.sidebar.markdown("---")
    st.sidebar.subheader("🔒 Security & Settings")

    with st.sidebar.expander("🔑 Change Password"):
        with st.form("pwd_change_form"):
            old_p = st.text_input("Current Password", type="password")
            new_p = st.text_input("New Password", type="password")
            p_sub = st.form_submit_button("Update Password", use_container_width=True)
            if p_sub:
                if old_p and new_p:
                    succ, message = change_password(st.session_state.username, old_p, new_p)
                    if succ:
                        st.success(message)
                    else:
                        st.error(message)
                else:
                    st.warning("Please fill all fields.")

    st.sidebar.markdown("---")
    st.sidebar.subheader("📌 Desktop Main Menu")

    menu_options = list(MENU_ICONS.keys())
    allowed_pages = [p for p in menu_options if page_allowed(p, role)]

    # Defense in depth: if current page isn't allowed for this role
    # (e.g. role changed, or stale session), bounce back to Dashboard.
    if st.session_state.current_page not in allowed_pages:
        st.session_state.current_page = "Dashboard"

    for key in menu_options:
        if key not in allowed_pages:
            continue
        button_label = MENU_ICONS[key]
        if st.sidebar.button(button_label, use_container_width=True, key=f"btn_{key}"):
            st.session_state.current_page = key
            st.rerun()

    page = st.session_state.current_page

    if not page_allowed(page, role):
        st.error("🚫 You don't have permission to view this page.")
        return

    conn = get_connection()
    try:
        if page == "Dashboard":
            render_dashboard(conn)
        elif page == "Billing System (POS)":
            render_pos(conn)
        elif page == "Product Master":
            render_product_master(conn, role)
        elif page == "Supplier Management":
            render_supplier_management(conn)
        elif page == "Customer Management":
            render_customer_management(conn)
        elif page == "Stock Purchase":
            render_stock_purchase(conn)
        elif page == "Expense Management":
            render_expense_management(conn)
        elif page == "Complete Reports Hub":
            render_reports_hub(conn)
        elif page == "Low Stock Alerts":
            render_low_stock_alerts(conn)
        elif page == "Settings":
            render_settings(conn, role)
    finally:
        conn.close()


# ============================================================================
# 1. DASHBOARD
# ============================================================================
def render_dashboard(conn):
    role = st.session_state.role

    st.markdown("<h2 style='color: #2b2d42;'>📊 Executive Shop Dashboard</h2>", unsafe_allow_html=True)
    st.markdown("Here is a quick overview of your retail store performance today.")

    # ---- Colorful navigation tiles for every option this role can access ----
    st.markdown("#### 🚀 Quick Navigation")
    tile_pages = [p for p in MENU_ICONS.keys() if p != "Dashboard" and page_allowed(p, role)]
    cols_per_row = 3
    css_rules = []
    with st.container(key="dash_nav_tiles"):
        for r in range(0, len(tile_pages), cols_per_row):
            row_pages = tile_pages[r:r + cols_per_row]
            row_key = f"dash_nav_row_{r // cols_per_row}"
            with st.container(key=row_key):
                cols = st.columns(len(row_pages))
                for idx, (col, page_name) in enumerate(zip(cols, row_pages), start=1):
                    icon, color1, color2 = PAGE_STYLES.get(page_name, ("🔗", "#667eea", "#764ba2"))
                    css_rules.append(
                        f'.st-key-{row_key} div[data-testid="stHorizontalBlock"] > div:nth-child({idx}) '
                        f'div.stButton button {{background: linear-gradient(135deg, {color1}, {color2});}}'
                    )
                    with col:
                        if st.button(f"{icon}  {page_name}", key=f"navtile_{page_name}", use_container_width=True):
                            st.session_state.current_page = page_name
                            st.rerun()
        st.markdown(f"<style>{''.join(css_rules)}</style>", unsafe_allow_html=True)

    # ---- KPI metric cards ----
    p_count = pd.read_sql("SELECT COUNT(*) as cnt FROM products WHERE is_active = 1", conn).iloc[0]['cnt']
    c_count = pd.read_sql("SELECT COUNT(*) as cnt FROM customers WHERE is_active = 1", conn).iloc[0]['cnt']
    s_count = pd.read_sql("SELECT COUNT(*) as cnt FROM suppliers WHERE is_active = 1", conn).iloc[0]['cnt']

    sales_df = pd.read_sql("SELECT SUM(grand_total) as total_sales FROM bills", conn)
    total_sales = sales_df.iloc[0]['total_sales'] if sales_df.iloc[0]['total_sales'] else 0.0

    exp_df = pd.read_sql("SELECT SUM(amount) as total_exp FROM expenses", conn)
    total_exp = exp_df.iloc[0]['total_exp'] if exp_df.iloc[0]['total_exp'] else 0.0

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("📦 Products", p_count)
    col2.metric("👥 Customers", c_count)
    col3.metric("🏭 Suppliers", s_count)
    col4.metric("💰 Total Sales", f"₹ {total_sales:,.2f}")
    col5.metric("💸 Total Expense", f"₹ {total_exp:,.2f}")

    # ---- Current stock valuation: at cost (purchase rate) vs at sale rate ----
    stock_val_df = pd.read_sql(
        "SELECT COALESCE(SUM(opening_stock * purchase_price), 0) as cost_val, "
        "COALESCE(SUM(opening_stock * selling_price), 0) as sale_val "
        "FROM products WHERE is_active = 1", conn
    )
    stock_cost_value = stock_val_df.iloc[0]['cost_val']
    stock_sale_value = stock_val_df.iloc[0]['sale_val']
    potential_profit = stock_sale_value - stock_cost_value

    st.markdown("<br>", unsafe_allow_html=True)
    vcol1, vcol2, vcol3 = st.columns(3)
    vcol1.metric("📥 Total Stock Value (Purchase Rate)", f"₹ {stock_cost_value:,.2f}")
    vcol2.metric("📤 Total Stock Value (Sale Rate)", f"₹ {stock_sale_value:,.2f}")
    vcol3.metric("📊 Potential Profit (if all stock sold)", f"₹ {potential_profit:,.2f}")

    st.markdown("<br><hr>", unsafe_allow_html=True)

    st.subheader("⚠️ Low Stock Alert Items")
    low_stock_df = pd.read_sql(
        "SELECT name, opening_stock, minimum_stock, unit FROM products "
        "WHERE is_active = 1 AND opening_stock <= minimum_stock", conn
    )
    if not low_stock_df.empty:
        st.warning("⚠️ Below items need immediate re-stocking!")
        st.dataframe(low_stock_df, use_container_width=True)
    else:
        st.success("✨ Excellent! All products have sufficient stock levels.")


# ============================================================================
# 2. BILLING SYSTEM (POS)
# ============================================================================
def render_pos(conn):
    st.header("🧾 Billing System & POS")

    products = fetch_active_products()
    if products.empty:
        st.warning("No active products available. Add products in Product Master first!")
        return

    col1, col2 = st.columns([2, 1])

    with col1:
        search = st.text_input("🔍 Search Product", placeholder="Type product name...")
        filtered = products[products['name'].str.contains(search, case=False, na=False)] if search else products
        filtered = filtered[filtered['opening_stock'] > 0]

        if filtered.empty:
            st.info("No matching in-stock products found.")
        else:
            prod_dict = dict(zip(
                filtered['name'] + " (Stock: " + filtered['opening_stock'].astype(str) + " " + filtered['unit'].fillna('') + ")",
                filtered['id']
            ))
            sel_prod_label = st.selectbox("Select Product to Add", list(prod_dict.keys()))
            sel_prod_id = int(prod_dict[sel_prod_label])
            prod_info = filtered[filtered['id'] == sel_prod_id].iloc[0]

            already_in_cart = sum(i['qty'] for i in st.session_state.cart if i['product_id'] == sel_prod_id)
            live_stock = get_live_stock(conn, sel_prod_id)
            remaining = max(live_stock - already_in_cart, 0.0)

            st.caption(f"In cart already: {already_in_cart} | Available to add: {remaining}")

            if remaining <= 0:
                st.warning("All available stock for this product is already in the cart.")
            else:
                qty = st.number_input("Quantity", min_value=0.01, max_value=float(remaining), value=min(1.0, float(remaining)), step=1.0)

                if st.button("➕ Add to Cart", use_container_width=True, key="add_cart_btn"):
                    found = False
                    for item in st.session_state.cart:
                        if item['product_id'] == sel_prod_id:
                            item['qty'] += qty
                            item['total'] = round(item['qty'] * item['selling_price'], 2)
                            found = True
                            break
                    if not found:
                        st.session_state.cart.append({
                            "product_id": sel_prod_id,
                            "name": prod_info['name'],
                            "selling_price": prod_info['selling_price'],
                            "qty": qty,
                            "gst": prod_info['gst'],
                            "total": round(qty * prod_info['selling_price'], 2)
                        })
                    st.success("Added to cart!")
                    st.rerun()

    with col2:
        st.subheader("Customer Details")
        customer_mode = st.radio("Customer", ["Walk-in Customer", "Existing / New Customer"], horizontal=True)

        if customer_mode == "Walk-in Customer":
            cust_name = "Walk-in Customer"
            cust_mobile = "0000000000"
            save_customer = False
        else:
            customers_df = fetch_active_customers()
            cust_name = st.text_input("Customer Name")
            cust_mobile = st.text_input("Customer Mobile")
            existing_match = customers_df[customers_df['mobile'] == cust_mobile] if cust_mobile else pd.DataFrame()
            if not existing_match.empty:
                st.caption(f"✅ Existing customer: {existing_match.iloc[0]['name']}")
                save_customer = False
            else:
                save_customer = st.checkbox("💾 Save this as a new customer", value=bool(cust_mobile))

        pay_mode = st.selectbox("Payment Mode", ["Cash", "UPI", "Card", "Mixed"])
        discount_amt = st.number_input("Discount (₹)", min_value=0.0, value=0.0, step=1.0)

    if st.session_state.cart:
        st.markdown("---")
        st.subheader("🛒 Current Cart Items")

        for idx, item in enumerate(st.session_state.cart):
            c1, c2, c3, c4, c5 = st.columns([3, 1.5, 1.5, 1.5, 1])
            c1.write(item['name'])
            c2.write(f"₹ {item['selling_price']:,.2f}")
            c3.write(f"Qty: {item['qty']}")
            c4.write(f"₹ {item['total']:,.2f}")
            if c5.button("🗑️", key=f"remove_item_{idx}"):
                st.session_state.cart.pop(idx)
                st.rerun()

        subtotal = sum(i['total'] for i in st.session_state.cart)
        total_gst = sum(i['total'] * i['gst'] / 100 for i in st.session_state.cart)
        discount_amt = min(discount_amt, subtotal)
        grand_total = subtotal - discount_amt + total_gst

        st.write(f"**Subtotal:** ₹ {subtotal:,.2f}")
        st.write(f"**Discount:** ₹ {discount_amt:,.2f}")
        st.write(f"**GST Amount:** ₹ {total_gst:,.2f}")
        st.markdown(f"### **Grand Total: ₹ {grand_total:,.2f}**")

        col_b1, col_b2 = st.columns(2)
        with col_b1:
            if st.button("💾 Save & Complete Bill", use_container_width=True, key="save_bill_btn"):
                # Re-verify stock live, right before writing, to avoid over-selling
                shortages = []
                for item in st.session_state.cart:
                    live_stock = get_live_stock(conn, item['product_id'])
                    if item['qty'] > live_stock:
                        shortages.append(f"{item['name']} (need {item['qty']}, have {live_stock})")

                if shortages:
                    st.error("⚠️ Insufficient stock for: " + "; ".join(shortages) + ". Please adjust the cart.")
                else:
                    try:
                        cursor = conn.cursor()
                        bill_no = "BILL-" + datetime.now().strftime("%Y%m%d%H%M%S")
                        bill_date = datetime.now().strftime("%Y-%m-%d")

                        cursor.execute("""
                            INSERT INTO bills (bill_number, bill_date, customer_name, customer_mobile, payment_mode, subtotal, discount, gst, grand_total)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (bill_no, bill_date, cust_name or "Walk-in Customer", cust_mobile or "0000000000",
                              pay_mode, subtotal, discount_amt, total_gst, grand_total))
                        bill_id = cursor.lastrowid

                        for item in st.session_state.cart:
                            cursor.execute("""
                                INSERT INTO bill_items (bill_id, product_id, quantity, selling_price, total)
                                VALUES (?, ?, ?, ?, ?)
                            """, (bill_id, item['product_id'], item['qty'], item['selling_price'], item['total']))

                            cursor.execute(
                                "UPDATE products SET opening_stock = opening_stock - ? WHERE id = ? AND opening_stock >= ?",
                                (item['qty'], item['product_id'], item['qty'])
                            )
                            if cursor.rowcount == 0:
                                raise ValueError(f"Stock changed concurrently for {item['name']}. Bill aborted.")

                        if customer_mode == "Existing / New Customer" and save_customer and cust_mobile:
                            cursor.execute(
                                "INSERT OR IGNORE INTO customers (name, mobile, address, is_active) VALUES (?, ?, '', 1)",
                                (cust_name or "Customer", cust_mobile)
                            )

                        conn.commit()
                        clear_lookup_caches()
                        st.success(f"✅ Bill Generated Successfully! Bill No: {bill_no}")

                        # Printable receipt
                        settings_row = conn.execute("SELECT * FROM settings WHERE id = 1").fetchone()
                        receipt_lines = []
                        if settings_row:
                            receipt_lines.append(settings_row['shop_name'] or "Retail Shop")
                            receipt_lines.append(settings_row['address'] or "")
                            receipt_lines.append(f"Mobile: {settings_row['mobile'] or ''}  GSTIN: {settings_row['gst_number'] or ''}")
                        receipt_lines.append("-" * 40)
                        receipt_lines.append(f"Bill No: {bill_no}   Date: {bill_date}")
                        receipt_lines.append(f"Customer: {cust_name or 'Walk-in Customer'} ({cust_mobile or '-'})")
                        receipt_lines.append(f"Payment Mode: {pay_mode}")
                        receipt_lines.append("-" * 40)
                        for item in st.session_state.cart:
                            receipt_lines.append(f"{item['name']} x{item['qty']} @ ₹{item['selling_price']:.2f} = ₹{item['total']:.2f}")
                        receipt_lines.append("-" * 40)
                        receipt_lines.append(f"Subtotal: ₹{subtotal:.2f}")
                        receipt_lines.append(f"Discount: ₹{discount_amt:.2f}")
                        receipt_lines.append(f"GST: ₹{total_gst:.2f}")
                        receipt_lines.append(f"Grand Total: ₹{grand_total:.2f}")
                        if settings_row and settings_row['footer_message']:
                            receipt_lines.append("-" * 40)
                            receipt_lines.append(settings_row['footer_message'])
                        receipt_text = "\n".join(receipt_lines)

                        st.download_button(
                            "🧾 Download Receipt", receipt_text,
                            file_name=f"{bill_no}.txt", mime="text/plain", key="download_receipt"
                        )

                        st.session_state.cart = []
                    except Exception as e:
                        conn.rollback()
                        st.error(f"❌ Could not save bill: {e}")

        with col_b2:
            if st.button("🗑️ Clear Cart", use_container_width=True, key="clear_cart_btn"):
                st.session_state.cart = []
                st.rerun()


# ============================================================================
# 3. PRODUCT MASTER
# ============================================================================
def render_product_master(conn, role):
    st.header("📦 Product Master (Manage Products)")
    tab1, tab2, tab3 = st.tabs(["➕ Add Product", "✏️ View / Edit Product", "🗑️ Delete Product"])

    with tab1:
        with st.form("add_prod_form"):
            c1, c2, c3 = st.columns(3)
            with c1:
                name = st.text_input("Product Name")
                barcode = st.text_input("Barcode (Optional)")
                category = st.text_input("Category")
            with c2:
                brand = st.text_input("Brand")
                unit = st.selectbox("Unit", ["Pcs", "Kg", "Gram", "Litre", "Packet", "Box"])
                purchase_price = st.number_input("Purchase Price (₹)", min_value=0.0)
            with c3:
                selling_price = st.number_input("Selling Price (₹)", min_value=0.0)
                gst = st.number_input("GST %", min_value=0.0, value=5.0)
                opening_stock = st.number_input("Opening Stock", min_value=0.0)
                minimum_stock = st.number_input("Minimum Stock Alert", min_value=0.0, value=5.0)

            if st.form_submit_button("Save New Product"):
                if name:
                    b_val = barcode if barcode.strip() != "" else None
                    try:
                        cursor = conn.cursor()
                        cursor.execute("""
                            INSERT INTO products (name, barcode, category, brand, unit, purchase_price, selling_price, gst, opening_stock, minimum_stock, is_active)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
                        """, (name, b_val, category, brand, unit, purchase_price, selling_price, gst, opening_stock, minimum_stock))
                        conn.commit()
                        clear_lookup_caches()
                        st.success("Product added successfully!")
                        st.rerun()
                    except Exception as e:
                        conn.rollback()
                        st.error(f"Could not save product: {e}")
                else:
                    st.warning("Product Name is required.")

    with tab2:
        st.subheader("Browse Products")
        search_term = st.text_input("🔍 Search by name / category", key="prod_search")
        all_prods = pd.read_sql("SELECT * FROM products ORDER BY name", conn)
        view_df = all_prods
        if search_term:
            mask = (
                all_prods['name'].str.contains(search_term, case=False, na=False) |
                all_prods['category'].str.contains(search_term, case=False, na=False)
            )
            view_df = all_prods[mask]
        st.dataframe(
            view_df[['id', 'name', 'category', 'brand', 'unit', 'purchase_price', 'selling_price',
                     'gst', 'opening_stock', 'minimum_stock', 'is_active']],
            use_container_width=True, hide_index=True
        )

        st.markdown("---")
        st.subheader("Edit Product Details")
        if all_prods.empty:
            st.info("No products yet.")
        else:
            sel_p_name = st.selectbox("Select Product to Edit", all_prods['name'])
            p_row = all_prods[all_prods['name'] == sel_p_name].iloc[0]

            with st.form("edit_prod_form"):
                e_c1, e_c2, e_c3 = st.columns(3)
                with e_c1:
                    e_name = st.text_input("Product Name", value=p_row['name'])
                    e_barcode = st.text_input("Barcode", value=p_row['barcode'] or "")
                    e_cat = st.text_input("Category", value=p_row['category'] or "")
                with e_c2:
                    e_brand = st.text_input("Brand", value=p_row['brand'] or "")
                    unit_options = ["Pcs", "Kg", "Gram", "Litre", "Packet", "Box"]
                    default_unit_idx = unit_options.index(p_row['unit']) if p_row['unit'] in unit_options else 0
                    e_unit = st.selectbox("Unit", unit_options, index=default_unit_idx)
                    e_purchase_price = st.number_input("Purchase Price (₹)", min_value=0.0, value=float(p_row['purchase_price'] or 0))
                with e_c3:
                    e_selling_price = st.number_input("Selling Price (₹)", min_value=0.0, value=float(p_row['selling_price'] or 0))
                    e_gst = st.number_input("GST %", min_value=0.0, value=float(p_row['gst'] or 0))
                    e_opening_stock = st.number_input("Current Stock", min_value=0.0, value=float(p_row['opening_stock'] or 0))
                    e_minimum_stock = st.number_input("Minimum Stock Alert", min_value=0.0, value=float(p_row['minimum_stock'] or 0))

                e_active = st.checkbox("Active (visible in POS)", value=bool(p_row['is_active']))

                if st.form_submit_button("💾 Update Product", use_container_width=True):
                    if not e_name.strip():
                        st.warning("Product Name is required.")
                    else:
                        try:
                            cursor = conn.cursor()
                            cursor.execute("""
                                UPDATE products SET name=?, barcode=?, category=?, brand=?, unit=?,
                                       purchase_price=?, selling_price=?, gst=?, opening_stock=?,
                                       minimum_stock=?, is_active=?
                                WHERE id=?
                            """, (e_name, e_barcode or None, e_cat, e_brand, e_unit, e_purchase_price,
                                  e_selling_price, e_gst, e_opening_stock, e_minimum_stock,
                                  1 if e_active else 0, int(p_row['id'])))
                            conn.commit()
                            clear_lookup_caches()
                            st.success("Product updated successfully!")
                            st.rerun()
                        except Exception as e:
                            conn.rollback()
                            st.error(f"Could not update product: {e}")

    with tab3:
        st.subheader("Delete Product")
        st.caption("Products already used in a bill or purchase can't be hard-deleted (it would break historical records) — they'll be deactivated instead.")
        all_prods = pd.read_sql("SELECT * FROM products ORDER BY name", conn)
        if all_prods.empty:
            st.info("No products yet.")
        else:
            del_name = st.selectbox("Select Product to Delete", all_prods['name'], key="del_prod_select")
            del_row = all_prods[all_prods['name'] == del_name].iloc[0]
            pid = int(del_row['id'])

            used_in_bills = conn.execute("SELECT COUNT(*) c FROM bill_items WHERE product_id = ?", (pid,)).fetchone()['c']
            used_in_purchases = conn.execute("SELECT COUNT(*) c FROM purchases WHERE product_id = ?", (pid,)).fetchone()['c']
            in_use = used_in_bills > 0 or used_in_purchases > 0

            if in_use:
                st.warning(f"'{del_name}' is referenced in {used_in_bills} bill item(s) and {used_in_purchases} purchase(s).")
                if st.button("🚫 Deactivate Product Instead", use_container_width=True, key="deactivate_prod"):
                    conn.execute("UPDATE products SET is_active = 0 WHERE id = ?", (pid,))
                    conn.commit()
                    clear_lookup_caches()
                    st.success(f"'{del_name}' deactivated. It will no longer appear in POS.")
                    st.rerun()
            else:
                confirm_key = f"prod_{pid}"
                if not st.session_state.confirm_delete.get(confirm_key):
                    if st.button("🗑️ Delete Product", use_container_width=True, key="del_prod_btn"):
                        st.session_state.confirm_delete[confirm_key] = True
                        st.rerun()
                else:
                    st.error(f"Are you sure you want to permanently delete '{del_name}'?")
                    cc1, cc2 = st.columns(2)
                    if cc1.button("✅ Yes, Delete Permanently", use_container_width=True, key="confirm_del_prod"):
                        conn.execute("DELETE FROM products WHERE id = ?", (pid,))
                        conn.commit()
                        clear_lookup_caches()
                        st.session_state.confirm_delete.pop(confirm_key, None)
                        st.success(f"'{del_name}' deleted.")
                        st.rerun()
                    if cc2.button("❌ Cancel", use_container_width=True, key="cancel_del_prod"):
                        st.session_state.confirm_delete.pop(confirm_key, None)
                        st.rerun()


# ============================================================================
# 4. SUPPLIER MANAGEMENT
# ============================================================================
def render_supplier_management(conn):
    st.header("🏭 Supplier Management")
    tab1, tab2, tab3, tab4 = st.tabs(["➕ Add Supplier", "✏️ View / Edit Supplier", "🗑️ Delete Supplier", "💳 Supplier Ledger"])

    with tab1:
        with st.form("add_supplier_form"):
            s_name = st.text_input("Supplier Name")
            s_mobile = st.text_input("Mobile")
            s_address = st.text_area("Address")
            s_gst = st.text_input("GST Number")
            if st.form_submit_button("Save Supplier"):
                if s_name.strip():
                    conn.execute(
                        "INSERT INTO suppliers (name, mobile, address, gst_number, is_active) VALUES (?, ?, ?, ?, 1)",
                        (s_name, s_mobile, s_address, s_gst)
                    )
                    conn.commit()
                    clear_lookup_caches()
                    st.success("Supplier added successfully!")
                    st.rerun()
                else:
                    st.warning("Supplier Name is required.")

    with tab2:
        suppliers_df = pd.read_sql("SELECT * FROM suppliers ORDER BY name", conn)
        st.dataframe(suppliers_df, use_container_width=True, hide_index=True)
        st.markdown("---")
        if suppliers_df.empty:
            st.info("No suppliers yet.")
        else:
            sel_name = st.selectbox("Select Supplier to Edit", suppliers_df['name'])
            row = suppliers_df[suppliers_df['name'] == sel_name].iloc[0]
            with st.form("edit_supplier_form"):
                e_name = st.text_input("Supplier Name", value=row['name'])
                e_mobile = st.text_input("Mobile", value=row['mobile'] or "")
                e_address = st.text_area("Address", value=row['address'] or "")
                e_gst = st.text_input("GST Number", value=row['gst_number'] or "")
                e_active = st.checkbox("Active", value=bool(row['is_active']))
                if st.form_submit_button("💾 Update Supplier", use_container_width=True):
                    conn.execute(
                        "UPDATE suppliers SET name=?, mobile=?, address=?, gst_number=?, is_active=? WHERE id=?",
                        (e_name, e_mobile, e_address, e_gst, 1 if e_active else 0, int(row['id']))
                    )
                    conn.commit()
                    clear_lookup_caches()
                    st.success("Supplier updated successfully!")
                    st.rerun()

    with tab3:
        suppliers_df = pd.read_sql("SELECT * FROM suppliers ORDER BY name", conn)
        if suppliers_df.empty:
            st.info("No suppliers yet.")
        else:
            del_name = st.selectbox("Select Supplier to Delete", suppliers_df['name'], key="del_sup_select")
            row = suppliers_df[suppliers_df['name'] == del_name].iloc[0]
            sid = int(row['id'])
            used = conn.execute("SELECT COUNT(*) c FROM purchases WHERE supplier_id = ?", (sid,)).fetchone()['c']
            if used > 0:
                st.warning(f"'{del_name}' has {used} purchase record(s) linked. Deactivating instead of deleting.")
                if st.button("🚫 Deactivate Supplier Instead", use_container_width=True, key="deactivate_sup"):
                    conn.execute("UPDATE suppliers SET is_active = 0 WHERE id = ?", (sid,))
                    conn.commit()
                    clear_lookup_caches()
                    st.success(f"'{del_name}' deactivated.")
                    st.rerun()
            else:
                confirm_key = f"sup_{sid}"
                if not st.session_state.confirm_delete.get(confirm_key):
                    if st.button("🗑️ Delete Supplier", use_container_width=True, key="del_sup_btn"):
                        st.session_state.confirm_delete[confirm_key] = True
                        st.rerun()
                else:
                    st.error(f"Are you sure you want to permanently delete '{del_name}'?")
                    cc1, cc2 = st.columns(2)
                    if cc1.button("✅ Yes, Delete Permanently", use_container_width=True, key="confirm_del_sup"):
                        conn.execute("DELETE FROM suppliers WHERE id = ?", (sid,))
                        conn.commit()
                        clear_lookup_caches()
                        st.session_state.confirm_delete.pop(confirm_key, None)
                        st.success(f"'{del_name}' deleted.")
                        st.rerun()
                    if cc2.button("❌ Cancel", use_container_width=True, key="cancel_del_sup"):
                        st.session_state.confirm_delete.pop(confirm_key, None)
                        st.rerun()

    with tab4:
        st.subheader("💳 Supplier Ledger — Payments & Balance")

        summary_df = pd.read_sql("""
            SELECT s.id, s.name,
                   COALESCE(SUM(pu.total_amount), 0) as total_purchased,
                   COALESCE(SUM(pu.paid_amount), 0) as total_paid,
                   COALESCE(SUM(pu.total_amount - pu.paid_amount), 0) as balance_due
            FROM suppliers s
            LEFT JOIN purchases pu ON pu.supplier_id = s.id
            GROUP BY s.id, s.name
            ORDER BY balance_due DESC
        """, conn)

        if summary_df.empty:
            st.info("No suppliers yet.")
        else:
            m1, m2, m3 = st.columns(3)
            m1.metric("📥 Total Purchased (All Suppliers)", f"₹ {summary_df['total_purchased'].sum():,.2f}")
            m2.metric("✅ Total Paid", f"₹ {summary_df['total_paid'].sum():,.2f}")
            m3.metric("⏳ Total Balance Pending", f"₹ {summary_df['balance_due'].sum():,.2f}")

            st.markdown("##### Overview — All Suppliers")
            st.dataframe(
                summary_df[['name', 'total_purchased', 'total_paid', 'balance_due']].rename(columns={
                    'name': 'Supplier', 'total_purchased': 'Total Purchased',
                    'total_paid': 'Total Paid', 'balance_due': 'Balance Due'
                }),
                use_container_width=True, hide_index=True
            )

            st.markdown("---")
            st.markdown("##### Transaction Details for One Supplier")
            sel_sup_name = st.selectbox("Select Supplier", summary_df['name'], key="ledger_sup_select")
            sel_sup_id = int(summary_df[summary_df['name'] == sel_sup_name].iloc[0]['id'])

            tx_df = pd.read_sql("""
                SELECT pu.id, pu.purchase_date, p.name as product, pu.quantity, pu.total_amount,
                       pu.paid_amount, (pu.total_amount - pu.paid_amount) as balance
                FROM purchases pu
                LEFT JOIN products p ON pu.product_id = p.id
                WHERE pu.supplier_id = ?
                ORDER BY pu.purchase_date DESC
            """, conn, params=(sel_sup_id,))

            if tx_df.empty:
                st.info(f"No transactions recorded yet for '{sel_sup_name}'.")
            else:
                display_df = tx_df.copy()
                display_df['status'] = display_df['balance'].apply(
                    lambda b: "✅ Paid" if b <= 0.005 else "⏳ Pending/Partial"
                )
                st.dataframe(
                    display_df[['purchase_date', 'product', 'quantity', 'total_amount', 'paid_amount', 'balance', 'status']].rename(columns={
                        'purchase_date': 'Date', 'product': 'Product', 'quantity': 'Qty',
                        'total_amount': 'Amount', 'paid_amount': 'Paid', 'balance': 'Balance', 'status': 'Status'
                    }),
                    use_container_width=True, hide_index=True
                )

                st.markdown("###### 💰 Record a Payment")
                pending_tx = tx_df[tx_df['balance'] > 0.005]
                if pending_tx.empty:
                    st.success("All transactions with this supplier are fully paid. 🎉")
                else:
                    tx_options = {
                        f"{r['purchase_date']} | {r['product']} | Balance ₹{r['balance']:.2f}": r['id']
                        for _, r in pending_tx.iterrows()
                    }
                    sel_tx_label = st.selectbox("Select Pending Transaction", list(tx_options.keys()), key="ledger_tx_select")
                    sel_tx_id = tx_options[sel_tx_label]
                    max_balance = float(pending_tx[pending_tx['id'] == sel_tx_id].iloc[0]['balance'])
                    pay_amount = st.number_input("Payment Amount (₹)", min_value=0.01, max_value=max_balance, value=max_balance, key="ledger_pay_amt")

                    if st.button("💾 Record Payment", key="ledger_record_payment"):
                        conn.execute(
                            "UPDATE purchases SET paid_amount = paid_amount + ? WHERE id = ?",
                            (pay_amount, sel_tx_id)
                        )
                        conn.commit()
                        st.success(f"Payment of ₹{pay_amount:,.2f} recorded for '{sel_sup_name}'.")
                        st.rerun()


# ============================================================================
# 5. CUSTOMER MANAGEMENT
# ============================================================================
def render_customer_management(conn):
    st.header("👥 Customer Management")
    tab1, tab2, tab3, tab4 = st.tabs(["➕ Add Customer", "✏️ View / Edit Customer", "🗑️ Delete Customer", "🧾 Purchase History"])

    with tab1:
        with st.form("add_customer_form"):
            c_name = st.text_input("Customer Name")
            c_mobile = st.text_input("Mobile")
            c_address = st.text_area("Address")
            if st.form_submit_button("Save Customer"):
                if c_name.strip():
                    try:
                        conn.execute(
                            "INSERT INTO customers (name, mobile, address, is_active) VALUES (?, ?, ?, 1)",
                            (c_name, c_mobile or None, c_address)
                        )
                        conn.commit()
                        clear_lookup_caches()
                        st.success("Customer added successfully!")
                        st.rerun()
                    except Exception as e:
                        conn.rollback()
                        st.error(f"Could not save customer (mobile may already exist): {e}")
                else:
                    st.warning("Customer Name is required.")

    with tab2:
        customers_df = pd.read_sql("SELECT * FROM customers ORDER BY name", conn)
        st.dataframe(customers_df, use_container_width=True, hide_index=True)
        st.markdown("---")
        if customers_df.empty:
            st.info("No customers yet.")
        else:
            sel_name = st.selectbox("Select Customer to Edit", customers_df['name'])
            row = customers_df[customers_df['name'] == sel_name].iloc[0]
            with st.form("edit_customer_form"):
                e_name = st.text_input("Customer Name", value=row['name'])
                e_mobile = st.text_input("Mobile", value=row['mobile'] or "")
                e_address = st.text_area("Address", value=row['address'] or "")
                e_active = st.checkbox("Active", value=bool(row['is_active']))
                if st.form_submit_button("💾 Update Customer", use_container_width=True):
                    try:
                        conn.execute(
                            "UPDATE customers SET name=?, mobile=?, address=?, is_active=? WHERE id=?",
                            (e_name, e_mobile or None, e_address, 1 if e_active else 0, int(row['id']))
                        )
                        conn.commit()
                        clear_lookup_caches()
                        st.success("Customer updated successfully!")
                        st.rerun()
                    except Exception as e:
                        conn.rollback()
                        st.error(f"Could not update customer: {e}")

    with tab3:
        customers_df = pd.read_sql("SELECT * FROM customers ORDER BY name", conn)
        if customers_df.empty:
            st.info("No customers yet.")
        else:
            del_name = st.selectbox("Select Customer to Delete", customers_df['name'], key="del_cust_select")
            row = customers_df[customers_df['name'] == del_name].iloc[0]
            mobile = row['mobile']
            used = 0
            if mobile:
                used = conn.execute("SELECT COUNT(*) c FROM bills WHERE customer_mobile = ?", (mobile,)).fetchone()['c']
            if used > 0:
                st.warning(f"'{del_name}' has {used} bill(s) on record. Deactivating instead of deleting.")
                if st.button("🚫 Deactivate Customer Instead", use_container_width=True, key="deactivate_cust"):
                    conn.execute("UPDATE customers SET is_active = 0 WHERE id = ?", (int(row['id']),))
                    conn.commit()
                    clear_lookup_caches()
                    st.success(f"'{del_name}' deactivated.")
                    st.rerun()
            else:
                confirm_key = f"cust_{int(row['id'])}"
                if not st.session_state.confirm_delete.get(confirm_key):
                    if st.button("🗑️ Delete Customer", use_container_width=True, key="del_cust_btn"):
                        st.session_state.confirm_delete[confirm_key] = True
                        st.rerun()
                else:
                    st.error(f"Are you sure you want to permanently delete '{del_name}'?")
                    cc1, cc2 = st.columns(2)
                    if cc1.button("✅ Yes, Delete Permanently", use_container_width=True, key="confirm_del_cust"):
                        conn.execute("DELETE FROM customers WHERE id = ?", (int(row['id']),))
                        conn.commit()
                        clear_lookup_caches()
                        st.session_state.confirm_delete.pop(confirm_key, None)
                        st.success(f"'{del_name}' deleted.")
                        st.rerun()
                    if cc2.button("❌ Cancel", use_container_width=True, key="cancel_del_cust"):
                        st.session_state.confirm_delete.pop(confirm_key, None)
                        st.rerun()

    with tab4:
        st.subheader("Customer Purchase History")
        search_mobile = st.text_input("Search by mobile number")
        if search_mobile:
            hist_df = pd.read_sql(
                "SELECT bill_number, bill_date, payment_mode, subtotal, discount, gst, grand_total "
                "FROM bills WHERE customer_mobile = ? ORDER BY bill_date DESC",
                conn, params=(search_mobile,)
            )
            if hist_df.empty:
                st.info("No bills found for this mobile number.")
            else:
                total_spent = hist_df['grand_total'].sum()
                st.metric("💰 Total Spent", f"₹ {total_spent:,.2f}")
                st.dataframe(hist_df, use_container_width=True, hide_index=True)


# ============================================================================
# 6. STOCK PURCHASE
# ============================================================================
def render_stock_purchase(conn):
    st.header("📥 Stock Purchase")
    tab1, tab2 = st.tabs(["➕ New Purchase Entry", "📜 Purchase History"])

    with tab1:
        suppliers_df = fetch_active_suppliers()
        products_df = fetch_active_products()

        if suppliers_df.empty or products_df.empty:
            st.warning("Add at least one active Supplier and one active Product before recording a purchase.")
        else:
            prefill_id = st.session_state.pop("prefill_purchase_product", None)

            c1, c2 = st.columns(2)
            with c1:
                sup_dict = dict(zip(suppliers_df['name'], suppliers_df['id']))
                sel_sup_name = st.selectbox("Supplier", list(sup_dict.keys()))
                sel_sup_id = int(sup_dict[sel_sup_name])
            with c2:
                prod_dict = dict(zip(products_df['name'], products_df['id']))
                prod_names = list(prod_dict.keys())
                default_idx = 0
                if prefill_id is not None:
                    match = products_df[products_df['id'] == prefill_id]
                    if not match.empty:
                        default_idx = prod_names.index(match.iloc[0]['name'])
                sel_prod_name = st.selectbox("Product", prod_names, index=default_idx)
                sel_prod_id = int(prod_dict[sel_prod_name])

            prod_row = products_df[products_df['id'] == sel_prod_id].iloc[0]

            c3, c4, c5 = st.columns(3)
            with c3:
                quantity = st.number_input("Quantity", min_value=0.01, value=1.0, step=1.0)
                purchase_price = st.number_input("Purchase Price / Unit (₹)", min_value=0.0, value=float(prod_row['purchase_price'] or 0))
            with c4:
                discount = st.number_input("Discount (₹)", min_value=0.0, value=0.0)
                gst_pct = st.number_input("GST %", min_value=0.0, value=float(prod_row['gst'] or 0))
            with c5:
                transport = st.number_input("Transport / Other Charges (₹)", min_value=0.0, value=0.0)
                update_price = st.checkbox("Update product's purchase price", value=True)

            base = quantity * purchase_price
            taxable = max(base - discount, 0)
            gst_amount = taxable * gst_pct / 100
            total_amount = taxable + gst_amount + transport

            st.info(f"**Computed Total: ₹ {total_amount:,.2f}**  (Base ₹{base:,.2f} − Discount ₹{discount:,.2f} + GST ₹{gst_amount:,.2f} + Transport ₹{transport:,.2f})")

            pay_col1, pay_col2 = st.columns(2)
            with pay_col1:
                mark_fully_paid = st.checkbox("💳 Mark as Fully Paid Now", value=False)
            with pay_col2:
                if mark_fully_paid:
                    paid_now = total_amount
                    st.number_input("Amount Paid Now (₹)", value=float(total_amount), disabled=True, key="paid_now_display")
                else:
                    paid_now = st.number_input("Amount Paid Now (₹)", min_value=0.0, value=0.0, key="paid_now_input")

            paid_now = min(paid_now, total_amount)
            balance_after = total_amount - paid_now
            if balance_after > 0:
                st.warning(f"⚠️ Balance to pay supplier: ₹ {balance_after:,.2f} — this will show as pending in the Supplier Ledger.")
            else:
                st.success("✅ This purchase will be recorded as fully paid.")

            if st.button("💾 Save Purchase Entry", use_container_width=True, key="save_purchase_btn"):
                try:
                    purchase_date = datetime.now().strftime("%Y-%m-%d")
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO purchases (purchase_date, supplier_id, product_id, quantity, purchase_price, discount, gst, transport, total_amount, paid_amount)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (purchase_date, sel_sup_id, sel_prod_id, quantity, purchase_price, discount, gst_pct, transport, total_amount, paid_now))

                    cursor.execute("UPDATE products SET opening_stock = opening_stock + ? WHERE id = ?", (quantity, sel_prod_id))
                    if update_price:
                        cursor.execute("UPDATE products SET purchase_price = ? WHERE id = ?", (purchase_price, sel_prod_id))

                    conn.commit()
                    clear_lookup_caches()
                    st.success(f"Purchase recorded! Stock for '{sel_prod_name}' increased by {quantity}.")
                    st.rerun()
                except Exception as e:
                    conn.rollback()
                    st.error(f"Could not save purchase: {e}")

    with tab2:
        c1, c2, c3 = st.columns(3)
        with c1:
            start_date = st.date_input("From", value=date.today().replace(day=1), key="pur_start")
        with c2:
            end_date = st.date_input("To", value=date.today(), key="pur_end")
        with c3:
            supplier_filter = st.selectbox(
                "Supplier Filter", ["All"] + list(fetch_active_suppliers()['name']), key="pur_sup_filter"
            )

        query = """
            SELECT pu.purchase_date, s.name as supplier, p.name as product, pu.quantity,
                   pu.purchase_price, pu.discount, pu.gst, pu.transport, pu.total_amount,
                   pu.paid_amount, (pu.total_amount - pu.paid_amount) as balance
            FROM purchases pu
            LEFT JOIN suppliers s ON pu.supplier_id = s.id
            LEFT JOIN products p ON pu.product_id = p.id
            WHERE pu.purchase_date BETWEEN ? AND ?
            ORDER BY pu.purchase_date DESC
        """
        hist_df = pd.read_sql(query, conn, params=(str(start_date), str(end_date)))
        if supplier_filter != "All":
            hist_df = hist_df[hist_df['supplier'] == supplier_filter]

        if hist_df.empty:
            st.info("No purchases found for the selected filters.")
        else:
            m1, m2 = st.columns(2)
            m1.metric("💰 Total Purchase Amount", f"₹ {hist_df['total_amount'].sum():,.2f}")
            m2.metric("⏳ Total Balance Pending", f"₹ {hist_df['balance'].sum():,.2f}")
            st.dataframe(hist_df, use_container_width=True, hide_index=True)
            st.download_button(
                "⬇️ Download as Excel", df_to_excel_bytes(hist_df, "Purchases"),
                file_name="purchase_report.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )


# ============================================================================
# 7. EXPENSE MANAGEMENT
# ============================================================================
def render_expense_management(conn):
    st.header("💸 Expense Management")
    tab1, tab2 = st.tabs(["➕ Add Expense", "📜 View / Delete Expenses"])

    with tab1:
        with st.form("add_expense_form"):
            exp_date = st.date_input("Date", value=date.today())
            exp_type_choice = st.selectbox(
                "Expense Type", ["Rent", "Electricity", "Salary", "Transport", "Maintenance", "Other"]
            )
            exp_type_custom = ""
            if exp_type_choice == "Other":
                exp_type_custom = st.text_input("Specify Expense Type")
            amount = st.number_input("Amount (₹)", min_value=0.0)
            remarks = st.text_area("Remarks")

            if st.form_submit_button("Save Expense", use_container_width=True):
                final_type = exp_type_custom.strip() if exp_type_choice == "Other" else exp_type_choice
                if not final_type:
                    st.warning("Please specify the expense type.")
                elif amount <= 0:
                    st.warning("Amount must be greater than zero.")
                else:
                    conn.execute(
                        "INSERT INTO expenses (expense_date, expense_type, amount, remarks) VALUES (?, ?, ?, ?)",
                        (str(exp_date), final_type, amount, remarks)
                    )
                    conn.commit()
                    st.success("Expense recorded successfully!")
                    st.rerun()

    with tab2:
        c1, c2 = st.columns(2)
        with c1:
            start_date = st.date_input("From", value=date.today().replace(day=1), key="exp_start")
        with c2:
            end_date = st.date_input("To", value=date.today(), key="exp_end")

        exp_df = pd.read_sql(
            "SELECT id, expense_date, expense_type, amount, remarks FROM expenses "
            "WHERE expense_date BETWEEN ? AND ? ORDER BY expense_date DESC",
            conn, params=(str(start_date), str(end_date))
        )

        if exp_df.empty:
            st.info("No expenses found for the selected range.")
        else:
            st.metric("💸 Total Expenses", f"₹ {exp_df['amount'].sum():,.2f}")
            st.dataframe(exp_df.drop(columns=['id']), use_container_width=True, hide_index=True)

            st.markdown("##### Delete an Expense Entry")
            del_options = {f"{r['expense_date']} | {r['expense_type']} | ₹{r['amount']:.2f}": r['id'] for _, r in exp_df.iterrows()}
            sel_label = st.selectbox("Select entry to delete", list(del_options.keys()))
            if st.button("🗑️ Delete Selected Expense", key="del_expense_btn"):
                conn.execute("DELETE FROM expenses WHERE id = ?", (del_options[sel_label],))
                conn.commit()
                st.success("Expense deleted.")
                st.rerun()

            st.download_button(
                "⬇️ Download as Excel", df_to_excel_bytes(exp_df.drop(columns=['id']), "Expenses"),
                file_name="expense_report.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )


# ============================================================================
# 8. COMPLETE REPORTS HUB
# ============================================================================
def render_reports_hub(conn):
    st.header("📈 Complete Reports Hub")
    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        ["💰 Sales Report", "📥 Purchase Report", "💸 Expense Report", "📊 Profit & Loss", "🏆 Top Products"]
    )

    with tab1:
        c1, c2 = st.columns(2)
        start_date = c1.date_input("From", value=date.today().replace(day=1), key="sales_start")
        end_date = c2.date_input("To", value=date.today(), key="sales_end")

        sales_df = pd.read_sql(
            "SELECT bill_number, bill_date, customer_name, customer_mobile, payment_mode, subtotal, discount, gst, grand_total "
            "FROM bills WHERE bill_date BETWEEN ? AND ? ORDER BY bill_date DESC",
            conn, params=(str(start_date), str(end_date))
        )
        if sales_df.empty:
            st.info("No sales found for the selected range.")
        else:
            m1, m2, m3 = st.columns(3)
            m1.metric("🧾 Bills", len(sales_df))
            m2.metric("💰 Revenue", f"₹ {sales_df['grand_total'].sum():,.2f}")
            m3.metric("🧮 GST Collected", f"₹ {sales_df['gst'].sum():,.2f}")
            st.dataframe(sales_df, use_container_width=True, hide_index=True)
            st.download_button(
                "⬇️ Download as Excel", df_to_excel_bytes(sales_df, "Sales"),
                file_name="sales_report.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

    with tab2:
        c1, c2 = st.columns(2)
        start_date = c1.date_input("From", value=date.today().replace(day=1), key="rep_pur_start")
        end_date = c2.date_input("To", value=date.today(), key="rep_pur_end")

        pur_df = pd.read_sql("""
            SELECT pu.purchase_date, s.name as supplier, p.name as product, pu.quantity, pu.total_amount
            FROM purchases pu
            LEFT JOIN suppliers s ON pu.supplier_id = s.id
            LEFT JOIN products p ON pu.product_id = p.id
            WHERE pu.purchase_date BETWEEN ? AND ?
            ORDER BY pu.purchase_date DESC
        """, conn, params=(str(start_date), str(end_date)))

        if pur_df.empty:
            st.info("No purchases found for the selected range.")
        else:
            st.metric("💰 Total Purchases", f"₹ {pur_df['total_amount'].sum():,.2f}")
            st.dataframe(pur_df, use_container_width=True, hide_index=True)
            st.download_button(
                "⬇️ Download as Excel", df_to_excel_bytes(pur_df, "Purchases"),
                file_name="purchase_report_hub.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

    with tab3:
        c1, c2 = st.columns(2)
        start_date = c1.date_input("From", value=date.today().replace(day=1), key="rep_exp_start")
        end_date = c2.date_input("To", value=date.today(), key="rep_exp_end")

        exp_df = pd.read_sql(
            "SELECT expense_date, expense_type, amount, remarks FROM expenses WHERE expense_date BETWEEN ? AND ?",
            conn, params=(str(start_date), str(end_date))
        )
        if exp_df.empty:
            st.info("No expenses found for the selected range.")
        else:
            st.metric("💸 Total Expenses", f"₹ {exp_df['amount'].sum():,.2f}")
            by_type = exp_df.groupby("expense_type")["amount"].sum().sort_values(ascending=False)
            st.bar_chart(by_type)
            st.dataframe(exp_df, use_container_width=True, hide_index=True)
            st.download_button(
                "⬇️ Download as Excel", df_to_excel_bytes(exp_df, "Expenses"),
                file_name="expense_report_hub.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

    with tab4:
        c1, c2 = st.columns(2)
        start_date = c1.date_input("From", value=date.today().replace(day=1), key="pl_start")
        end_date = c2.date_input("To", value=date.today(), key="pl_end")

        sales_total = conn.execute(
            "SELECT SUM(grand_total) t FROM bills WHERE bill_date BETWEEN ? AND ?",
            (str(start_date), str(end_date))
        ).fetchone()['t'] or 0.0
        purchase_total = conn.execute(
            "SELECT SUM(total_amount) t FROM purchases WHERE purchase_date BETWEEN ? AND ?",
            (str(start_date), str(end_date))
        ).fetchone()['t'] or 0.0
        expense_total = conn.execute(
            "SELECT SUM(amount) t FROM expenses WHERE expense_date BETWEEN ? AND ?",
            (str(start_date), str(end_date))
        ).fetchone()['t'] or 0.0

        net_profit = sales_total - purchase_total - expense_total

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("💰 Sales", f"₹ {sales_total:,.2f}")
        m2.metric("📥 Purchases", f"₹ {purchase_total:,.2f}")
        m3.metric("💸 Expenses", f"₹ {expense_total:,.2f}")
        m4.metric("📊 Net Profit", f"₹ {net_profit:,.2f}")

        if net_profit >= 0:
            st.success(f"✅ Net Profit for the period: ₹ {net_profit:,.2f}")
        else:
            st.error(f"⚠️ Net Loss for the period: ₹ {abs(net_profit):,.2f}")

    with tab5:
        c1, c2 = st.columns(2)
        start_date = c1.date_input("From", value=date.today().replace(day=1), key="top_start")
        end_date = c2.date_input("To", value=date.today(), key="top_end")

        top_df = pd.read_sql("""
            SELECT p.name as product, SUM(bi.quantity) as qty_sold, SUM(bi.total) as revenue
            FROM bill_items bi
            JOIN bills b ON bi.bill_id = b.id
            LEFT JOIN products p ON bi.product_id = p.id
            WHERE b.bill_date BETWEEN ? AND ?
            GROUP BY bi.product_id
            ORDER BY revenue DESC
            LIMIT 10
        """, conn, params=(str(start_date), str(end_date)))

        if top_df.empty:
            st.info("No sales found for the selected range.")
        else:
            st.dataframe(top_df, use_container_width=True, hide_index=True)
            st.bar_chart(top_df.set_index("product")["revenue"])


# ============================================================================
# 9. LOW STOCK ALERTS
# ============================================================================
def render_low_stock_alerts(conn):
    st.header("⚠️ Low Stock Alerts")

    low_df = pd.read_sql(
        "SELECT id, name, category, opening_stock, minimum_stock, unit FROM products "
        "WHERE is_active = 1 AND opening_stock <= minimum_stock "
        "ORDER BY (minimum_stock - opening_stock) DESC",
        conn
    )

    if low_df.empty:
        st.success("✨ Excellent! All active products have sufficient stock levels.")
        return

    st.warning(f"⚠️ {len(low_df)} product(s) need re-stocking.")

    role = st.session_state.role
    for _, row in low_df.iterrows():
        c1, c2, c3, c4 = st.columns([3, 1.5, 1.5, 1.5])
        c1.write(f"**{row['name']}** ({row['category'] or '-'})")
        c2.write(f"Stock: {row['opening_stock']} {row['unit'] or ''}")
        c3.write(f"Min: {row['minimum_stock']}")
        if page_allowed("Stock Purchase", role):
            if c4.button("📥 Restock", key=f"restock_{row['id']}"):
                st.session_state["prefill_purchase_product"] = int(row['id'])
                st.session_state.current_page = "Stock Purchase"
                st.rerun()


# ============================================================================
# 10. SETTINGS (Admin Only)
# ============================================================================
def render_settings(conn, role):
    st.header("⚙️ Shop Settings")

    settings_row = conn.execute("SELECT * FROM settings WHERE id = 1").fetchone()
    if settings_row and settings_row["shop_id"]:
        st.caption(f"🔑 Installation ID: `{settings_row['shop_id']}` — unique to this shop's database, share this if you contact support.")

    with st.form("settings_form"):
        shop_name = st.text_input("Shop Name", value=settings_row['shop_name'] or "")
        address = st.text_area("Address", value=settings_row['address'] or "")
        mobile = st.text_input("Mobile", value=settings_row['mobile'] or "")
        gst_number = st.text_input("GST Number", value=settings_row['gst_number'] or "")
        footer_message = st.text_input("Receipt Footer Message", value=settings_row['footer_message'] or "")
        terms = st.text_area("Terms & Conditions", value=settings_row['terms'] or "")

        if st.form_submit_button("💾 Save Settings", use_container_width=True):
            conn.execute(
                "UPDATE settings SET shop_name=?, address=?, mobile=?, gst_number=?, footer_message=?, terms=? WHERE id=1",
                (shop_name, address, mobile, gst_number, footer_message, terms)
            )
            conn.commit()
            st.success("Settings updated successfully!")
            st.rerun()

    st.markdown("---")
    st.subheader("👤 Manage Users")
    users_df = pd.read_sql("SELECT id, username, role FROM users ORDER BY username", conn)
    st.dataframe(users_df, use_container_width=True, hide_index=True)

    if not users_df.empty:
        other_users = users_df[users_df['username'] != st.session_state.username]
        if not other_users.empty:
            with st.expander("Change a User's Role"):
                sel_user = st.selectbox("User", other_users['username'])
                new_role = st.selectbox("New Role", ROLES, key="role_change_select")
                if st.button("Update Role", key="update_role_btn"):
                    conn.execute("UPDATE users SET role = ? WHERE username = ?", (new_role, sel_user))
                    conn.commit()
                    st.success(f"Role for '{sel_user}' updated to {new_role}.")
                    st.rerun()

            with st.expander("Remove a User"):
                admin_count = int((users_df['role'] == 'Admin').sum())
                del_user = st.selectbox("User to Remove", other_users['username'], key="del_user_select")
                del_user_role = users_df[users_df['username'] == del_user].iloc[0]['role']
                if del_user_role == 'Admin' and admin_count <= 1:
                    st.warning("Cannot remove the only remaining Admin.")
                else:
                    if st.button("🗑️ Remove User", key="del_user_btn"):
                        conn.execute("DELETE FROM users WHERE username = ?", (del_user,))
                        conn.commit()
                        st.success(f"User '{del_user}' removed.")
                        st.rerun()
        else:
            st.caption("No other users to manage yet.")


# ============================================================================
# App Entry Point
# ============================================================================
if not is_shop_configured():
    shop_setup_screen()
elif not st.session_state.logged_in:
    login_screen()
else:
    main_app()
