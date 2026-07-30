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
    div.stButton > button:nth-of-type(1) {background: linear-gradient(135deg, #00c6ff, #0072ff); color: white; border-radius: 8px; font-weight: bold; border: none;}
    div.stButton > button:nth-of-type(2) {background: linear-gradient(135deg, #7f7fd5, #86a8e7, #91eae4); color: white; border-radius: 8px; font-weight: bold; border: none;}
    div.stButton > button:nth-of-type(3) {background: linear-gradient(135deg, #f12711, #f5af19); color: white; border-radius: 8px; font-weight: bold; border: none;}
    div.stButton > button:nth-of-type(4) {background: linear-gradient(135deg, #11998e, #38ef7d); color: white; border-radius: 8px; font-weight: bold; border: none;}
    div.stButton > button:nth-of-type(5) {background: linear-gradient(135deg, #ff416c, #ff4b2b); color: white; border-radius: 8px; font-weight: bold; border: none;}
    div.stButton > button:nth-of-type(6) {background: linear-gradient(135deg, #4e54c8, #8f94fb); color: white; border-radius: 8px; font-weight: bold; border: none;}
    div.stButton > button:nth-of-type(7) {background: linear-gradient(135deg, #203a43, #2c5364); color: white; border-radius: 8px; font-weight: bold; border: none;}
    div.stButton > button:nth-of-type(8) {background: linear-gradient(135deg, #f7b733, #fc4a1a); color: white; border-radius: 8px; font-weight: bold; border: none;}
    div.stButton > button:nth-of-type(9) {background: linear-gradient(135deg, #cb356b, #bd3f32); color: white; border-radius: 8px; font-weight: bold; border: none;}
    div.stButton > button:nth-of-type(10) {background: linear-gradient(135deg, #3a6073, #16222a); color: white; border-radius: 8px; font-weight: bold; border: none;}

    div.stButton > button:hover {
        opacity: 0.9;
        transform: scale(1.02);
        transition: all 0.3s ease;
    }

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
# Shop Setup & Login Screens
# ============================================================================
def shop_setup_screen():
    st.markdown("<h1 style='text-align: center; color: #2b2d42;'>🛒 Welcome — Let's Set Up Your Shop</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: gray;'>This runs only once for this installation.</p>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    settings_row = get_settings()

    col1, col2, col3 = st.columns([1, 1.4, 1])
    with col2:
        with st.form("shop_setup_form"):
            shop_name = st.text_input("Shop Name *", value=(settings_row['shop_name'] if settings_row else ""))
            address = st.text_area("Address", value=(settings_row['address'] if settings_row else ""))
            mobile = st.text_input("Mobile", value=(settings_row['mobile'] if settings_row else ""))
            gst_number = st.text_input("GST Number (optional)", value=(settings_row['gst_number'] if settings_row else ""))
            footer_message = st.text_input("Receipt Footer Message", value=(settings_row['footer_message'] if settings_row else "Thank You, Visit Again!"))
            terms = st.text_area("Terms & Conditions", value=(settings_row['terms'] if settings_row else "Goods once sold will not be taken back."))
            submitted = st.form_submit_button("✅ Save & Continue", use_container_width=True)

            if submitted:
                if not shop_name.strip():
                    st.warning("Shop Name is required.")
                else:
                    save_shop_setup(shop_name.strip(), address, mobile, gst_number, footer_message, terms)
                    st.success("Shop set up successfully! Redirecting...")
                    st.rerun()

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
# Cached Lookups & Helpers
# ============================================================================
@st.cache_data(ttl=5)
def fetch_active_products():
    conn = get_connection()
    try:
        return pd.read_sql("SELECT * FROM products WHERE is_active = 1 ORDER BY name", conn)
    finally:
        conn.close()

@st.cache_data(ttl=5)
def fetch_active_suppliers():
    conn = get_connection()
    try:
        return pd.read_sql("SELECT * FROM suppliers WHERE is_active = 1 ORDER BY name", conn)
    finally:
        conn.close()

@st.cache_data(ttl=5)
def fetch_active_customers():
    conn = get_connection()
    try:
        return pd.read_sql("SELECT * FROM customers WHERE is_active = 1 ORDER BY name", conn)
    finally:
        conn.close()

def clear_lookup_caches():
    fetch_active_products.clear()
    fetch_active_suppliers.clear()
    fetch_active_customers.clear()

def get_live_stock(conn, product_id):
    row = conn.execute("SELECT opening_stock FROM products WHERE id = ?", (product_id,)).fetchone()
    return row["opening_stock"] if row else 0

# ============================================================================
# Main Application Logic
# ============================================================================
def main_app():
    role = st.session_state.role

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

# ============================================================================
# 6. STOCK PURCHASE & PURCHASE HISTORY
# ============================================================================
def render_stock_purchase(conn):
    st.header("📥 Stock Purchase Management")
    
    tab_entry, tab_history = st.tabs(["➕ New Purchase Entry", "📋 Purchase History & Payment Edit"])
    
    with tab_entry:
        st.subheader("Add New Purchase")
        suppliers = fetch_active_suppliers()
        products = fetch_active_products()
        
        if suppliers.empty or products.empty:
            st.warning("Please add Suppliers and Products first before making a purchase entry.")
            return
            
        with st.form("purchase_form"):
            supplier_dict = dict(zip(suppliers['name'], suppliers['id']))
            sel_supplier = st.selectbox("Select Supplier", list(supplier_dict.keys()))
            
            product_dict = dict(zip(products['name'], products['id']))
            sel_product = st.selectbox("Select Product", list(product_dict.keys()))
            
            p_date = st.date_input("Purchase Date", value=date.today())
            qty = st.number_input("Quantity", min_value=0.01, step=1.0)
            purchase_price = st.number_input("Purchase Price (Per unit)", min_value=0.0, step=1.0)
            selling_price = st.number_input("Selling Price (Per unit)", min_value=0.0, step=1.0)
            
            paid_amount = st.number_input("Paid Amount (₹)", min_value=0.0, step=10.0)
            
            submitted = st.form_submit_button("Save Purchase Entry", use_container_width=True)
            
            if submitted:
                total_amt = qty * purchase_price
                balance_amount = max(0.0, total_amt - paid_amount)
                
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO purchases (supplier_id, product_id, purchase_date, quantity, purchase_price, total_amount, paid_amount, balance_amount)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (supplier_dict[sel_supplier], product_dict[sel_product], str(p_date), qty, purchase_price, total_amt, paid_amount, balance_amount))
                
                cursor.execute("""
                    UPDATE products SET opening_stock = opening_stock + ?, purchase_price = ?, selling_price = ? WHERE id = ?
                """, (qty, purchase_price, selling_price, product_dict[sel_product]))
                
                conn.commit()
                st.success("Purchase entry saved successfully and stock updated!")
                clear_lookup_caches()
                st.rerun()

    with tab_history:
        st.subheader("📋 Purchase History & Edit Balance")
        
        query = """
            SELECT p.id, p.purchase_date, s.name as supplier, pr.name as product, 
                   p.quantity, p.purchase_price, p.total_amount, p.paid_amount, p.balance_amount
            FROM purchases p
            JOIN suppliers s ON p.supplier_id = s.id
            JOIN products pr ON p.product_id = pr.id
            ORDER BY p.purchase_date DESC
        """
        hist_df = pd.read_sql(query, conn)
        
        if hist_df.empty:
            st.info("No purchase history found.")
        else:
            st.dataframe(hist_df, use_container_width=True)
            
            st.markdown("---")
            st.subheader("✏️ Update Balance Payment for an Entry")
            
            entry_options = {f"ID: {row['id']} | Date: {row['purchase_date']} | Supplier: {row['supplier']} | Product: {row['product']} | Balance: ₹{row['balance_amount']}": row['id'] for index, row in hist_df.iterrows()}
            
            selected_label = st.selectbox("Select Purchase Entry to Pay Balance", list(entry_options.keys()))
            selected_id = entry_options[selected_label]
            
            selected_row = hist_df[hist_df['id'] == selected_id].iloc[0]
            
            st.info(f"**Total Amount:** ₹{selected_row['total_amount']:,.2f} | **Already Paid:** ₹{selected_row['paid_amount']:,.2f} | **Current Balance:** ₹{selected_row['balance_amount']:,.2f}")
            
            additional_payment = st.number_input("Enter Amount to Pay Now (₹)", min_value=0.0, max_value=float(selected_row['balance_amount']), step=10.0)
            
            if st.button("Update Payment / Clear Balance", use_container_width=True):
                new_paid = selected_row['paid_amount'] + additional_payment
                new_balance = max(0.0, selected_row['total_amount'] - new_paid)
                
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE purchases SET paid_amount = ?, balance_amount = ? WHERE id = ?
                """, (new_paid, new_balance, selected_id))
                conn.commit()
                
                st.success(f"Payment updated successfully! New Paid: ₹{new_paid:,.2f}, Remaining Balance: ₹{new_balance:,.2f}")
                st.rerun()

# Placeholders for other required modules
def render_pos(conn): st.info("POS Module is loaded.")
def render_product_master(conn, role): st.info("Product Master Module is loaded.")
def render_supplier_management(conn): st.info("Supplier Management Module is loaded.")
def render_customer_management(conn): st.info("Customer Management Module is loaded.")
def render_expense_management(conn): st.info("Expense Management Module is loaded.")
def render_reports_hub(conn): st.info("Reports Hub Module is loaded.")
def render_low_stock_alerts(conn): st.info("Low Stock Alerts Module is loaded.")
def render_settings(conn, role): st.info("Settings Module is loaded.")

# ============================================================================
# Entry Point Control Flow
# ============================================================================
if not is_shop_configured():
    shop_setup_screen()
elif not st.session_state.logged_in:
    login_screen()
else:
    main_app()
