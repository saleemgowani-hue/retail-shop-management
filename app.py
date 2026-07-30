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
    section[data-testid="stSidebar"] {
        background-color: #f0f2f6;
    }
    div.stButton > button:hover {
        opacity: 0.9;
        transform: scale(1.02);
        transition: all 0.3s ease;
    }
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
# 2. BILLING SYSTEM (POS)
# ============================================================================
def render_pos(conn):
    st.header("🧾 Billing System (POS)")
    
    products = fetch_active_products()
    customers = fetch_active_customers()
    
    if products.empty:
        st.warning("No active products available. Please add products in Product Master first.")
        return

    col_pos1, col_pos2 = st.columns([1.3, 1])

    with col_pos1:
        st.subheader("🛒 Add Items to Cart")
        prod_dict = {f"{row['name']} (Stock: {row['opening_stock']} | ₹{row['selling_price']})": row for _, row in products.iterrows()}
        selected_prod_label = st.selectbox("Select Product", list(prod_dict.keys()))
        selected_prod = prod_dict[selected_prod_label]

        max_stock = int(selected_prod['opening_stock'])
        qty = st.number_input("Quantity", min_value=1, max_value=max(1, max_stock), value=1, step=1)
        disc_pct = st.number_input("Discount (%)", min_value=0.0, max_value=100.0, value=0.0, step=1.0)

        if st.button("➕ Add to Cart", use_container_width=True):
            if max_stock <= 0:
                st.error("Out of stock!")
            else:
                unit_price = selected_prod['selling_price']
                discount_amt = (unit_price * qty * disc_pct) / 100.0
                total_price = (unit_price * qty) - discount_amt

                item = {
                    "id": selected_prod['id'],
                    "name": selected_prod['name'],
                    "price": unit_price,
                    "qty": qty,
                    "discount_pct": disc_pct,
                    "total": total_price
                }
                st.session_state.cart.append(item)
                st.success(f"Added {selected_prod['name']} to cart!")
                st.rerun()

    with col_pos2:
        st.subheader("🛍️ Current Cart")
        if not st.session_state.cart:
            st.info("Cart is empty.")
        else:
            cart_df = pd.DataFrame(st.session_state.cart)
            st.dataframe(cart_df[['name', 'price', 'qty', 'total']], use_container_width=True)

            if st.button("🗑️ Clear Cart", use_container_width=True):
                st.session_state.cart = []
                st.rerun()

    if st.session_state.cart:
        st.markdown("---")
        st.subheader("💳 Checkout & Payment")
        
        cust_names = ["Walk-in Customer"] + list(customers['name']) if not customers.empty else ["Walk-in Customer"]
        sel_cust = st.selectbox("Select Customer", cust_names)
        
        subtotal = sum([item['total'] for item in st.session_state.cart])
        tax_pct = st.number_input("Tax / GST (%)", min_value=0.0, max_value=28.0, value=0.0, step=0.5)
        tax_amount = (subtotal * tax_pct) / 100.0
        grand_total = subtotal + tax_amount

        st.markdown(f"### Subtotal: ₹{subtotal:,.2f} | Tax: ₹{tax_amount:,.2f} | **Grand Total: ₹{grand_total:,.2f}**")

        payment_mode = st.selectbox("Payment Mode", ["Cash", "UPI / QR", "Credit / Card", "Due / Udhar"])
        
        if st.button("✅ Complete Bill & Print Receipt", use_container_width=True):
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO bills (customer_name, subtotal, tax_percentage, tax_amount, grand_total, payment_mode, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (sel_cust, subtotal, tax_pct, tax_amount, grand_total, payment_mode, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            bill_id = cursor.lastrowid

            for item in st.session_state.cart:
                cursor.execute("""
                    INSERT INTO bill_items (bill_id, product_id, product_name, price, quantity, total)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (bill_id, item['id'], item['name'], item['price'], item['qty'], item['total']))

                cursor.execute("""
                    UPDATE products SET opening_stock = opening_stock - ? WHERE id = ?
                """, (item['qty'], item['id']))

            conn.commit()
            st.success(f"Bill #{bill_id} generated successfully!")
            st.session_state.cart = []
            clear_lookup_caches()
            st.rerun()

# ============================================================================
# 3. PRODUCT MASTER
# ============================================================================
def render_product_master(conn, role):
    st.header("📦 Product Master Management")
    
    tab_list, tab_add = st.tabs(["📋 Product Inventory", "➕ Add New Product"])
    
    with tab_list:
        products_df = pd.read_sql("SELECT * FROM products ORDER BY name", conn)
        if products_df.empty:
            st.info("No products found.")
        else:
            st.dataframe(products_df, use_container_width=True)
            
            st.markdown("### ✏️ Edit or Delete Product")
            prod_options = {row['name']: row['id'] for _, row in products_df.iterrows()}
            selected_prod_name = st.selectbox("Select Product to Edit/Delete", list(prod_options.keys()))
            prod_id = prod_options[selected_prod_name]
            
            p_row = products_df[products_df['id'] == prod_id].iloc[0]
            
            with st.form("edit_product_form"):
                new_name = st.text_input("Product Name", value=p_row['name'])
                new_barcode = st.text_input("Barcode / SKU", value=p_row['barcode'] if p_row['barcode'] else "")
                new_category = st.text_input("Category", value=p_row['category'] if p_row['category'] else "")
                new_unit = st.text_input("Unit (pcs, kg, etc.)", value=p_row['unit'] if p_row['unit'] else "pcs")
                new_pur_price = st.number_input("Purchase Price", value=float(p_row['purchase_price']), min_value=0.0)
                new_sel_price = st.number_input("Selling Price", value=float(p_row['selling_price']), min_value=0.0)
                new_stock = st.number_input("Stock", value=float(p_row['opening_stock']), min_value=0.0)
                new_min_stock = st.number_input("Low Stock Alert Limit", value=float(p_row['min_stock_level']), min_value=0.0)
                
                update_sub = st.form_submit_button("💾 Update Product", use_container_width=True)
                if update_sub:
                    cursor = conn.cursor()
                    cursor.execute("""
                        UPDATE products SET name = ?, barcode = ?, category = ?, unit = ?, purchase_price = ?, selling_price = ?, opening_stock = ?, min_stock_level = ?
                        WHERE id = ?
                    """, (new_name, new_barcode, new_category, new_unit, new_pur_price, new_sel_price, new_stock, new_min_stock, prod_id))
                    conn.commit()
                    st.success("Product updated successfully!")
                    clear_lookup_caches()
                    st.rerun()

    with tab_add:
        with st.form("add_product_form"):
            name = st.text_input("Product Name *")
            barcode = st.text_input("Barcode / SKU")
            category = st.text_input("Category")
            unit = st.text_input("Unit (pcs, kg, packet)", value="pcs")
            purchase_price = st.number_input("Purchase Price", min_value=0.0, step=1.0)
            selling_price = st.number_input("Selling Price", min_value=0.0, step=1.0)
            opening_stock = st.number_input("Opening Stock", min_value=0.0, step=1.0)
            min_stock_level = st.number_input("Low Stock Warning Limit", min_value=0.0, value=5.0, step=1.0)
            
            submitted = st.form_submit_button("➕ Save Product", use_container_width=True)
            if submitted:
                if not name.strip():
                    st.warning("Product Name is required.")
                else:
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO products (name, barcode, category, unit, purchase_price, selling_price, opening_stock, min_stock_level, is_active)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
                    """, (name.strip(), barcode, category, unit, purchase_price, selling_price, opening_stock, min_stock_level))
                    conn.commit()
                    st.success("Product added successfully!")
                    clear_lookup_caches()
                    st.rerun()

# ============================================================================
# 4. SUPPLIER MANAGEMENT
# ============================================================================
def render_supplier_management(conn):
    st.header("🏭 Supplier Management")
    
    tab_list, tab_add = st.tabs(["📋 Supplier List", "➕ Add Supplier"])
    
    with tab_list:
        suppliers_df = pd.read_sql("SELECT * FROM suppliers ORDER BY name", conn)
        if suppliers_df.empty:
            st.info("No suppliers found.")
        else:
            st.dataframe(suppliers_df, use_container_width=True)
            
    with tab_add:
        with st.form("add_supplier_form"):
            name = st.text_input("Supplier Name *")
            contact_person = st.text_input("Contact Person")
            phone = st.text_input("Phone Number")
            email = st.text_input("Email")
            address = st.text_area("Address")
            
            submitted = st.form_submit_button("💾 Save Supplier", use_container_width=True)
            if submitted:
                if not name.strip():
                    st.warning("Supplier Name is required.")
                else:
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO suppliers (name, contact_person, phone, email, address, is_active)
                        VALUES (?, ?, ?, ?, ?, 1)
                    """, (name.strip(), contact_person, phone, email, address))
                    conn.commit()
                    st.success("Supplier added successfully!")
                    clear_lookup_caches()
                    st.rerun()

# ============================================================================
# 5. CUSTOMER MANAGEMENT
# ============================================================================
def render_customer_management(conn):
    st.header("👥 Customer Management")
    
    tab_list, tab_add = st.tabs(["📋 Customer Directory", "➕ Add Customer"])
    
    with tab_list:
        cust_df = pd.read_sql("SELECT * FROM customers ORDER BY name", conn)
        if cust_df.empty:
            st.info("No customers found.")
        else:
            st.dataframe(cust_df, use_container_width=True)
            
    with tab_add:
        with st.form("add_customer_form"):
            name = st.text_input("Customer Name *")
            phone = st.text_input("Phone Number *")
            email = st.text_input("Email")
            address = st.text_area("Address")
            
            submitted = st.form_submit_button("💾 Save Customer", use_container_width=True)
            if submitted:
                if not name.strip() or not phone.strip():
                    st.warning("Name and Phone Number are required.")
                else:
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO customers (name, phone, email, address, is_active)
                        VALUES (?, ?, ?, ?, 1)
                    """, (name.strip(), phone.strip(), email, address))
                    conn.commit()
                    st.success("Customer added successfully!")
                    clear_lookup_caches()
                    st.rerun()

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

# ============================================================================
# 7. EXPENSE MANAGEMENT
# ============================================================================
def render_expense_management(conn):
    st.header("💸 Expense Management")
    
    tab_list, tab_add = st.tabs(["📋 Expense History", "➕ Add Expense"])
    
    with tab_list:
        exp_df = pd.read_sql("SELECT * FROM expenses ORDER BY expense_date DESC", conn)
        if exp_df.empty:
            st.info("No expenses recorded.")
        else:
            st.dataframe(exp_df, use_container_width=True)
            
    with tab_add:
        with st.form("add_expense_form"):
            title = st.text_input("Expense Title / Description *")
            amount = st.number_input("Amount (₹)", min_value=0.0, step=10.0)
            category = st.selectbox("Category", ["Rent", "Electricity", "Salary", "Transport", "Maintenance", "Tea/Refreshment", "Others"])
            exp_date = st.date_input("Expense Date", value=date.today())
            
            submitted = st.form_submit_button("💾 Save Expense", use_container_width=True)
            if submitted:
                if not title.strip() or amount <= 0:
                    st.warning("Please provide a valid title and amount.")
                else:
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO expenses (title, amount, category, expense_date)
                        VALUES (?, ?, ?, ?)
                    """, (title.strip(), amount, category, str(exp_date)))
                    conn.commit()
                    st.success("Expense recorded successfully!")
                    st.rerun()

# ============================================================================
# 8. COMPLETE REPORTS HUB
# ============================================================================
def render_reports_hub(conn):
    st.header("📈 Complete Reports Hub")
    
    tab_sales, tab_stock, tab_exp = st.tabs(["💰 Sales Report", "📦 Stock Report", "💸 Expense Report"])
    
    with tab_sales:
        st.subheader("Sales History")
        bills_df = pd.read_sql("SELECT * FROM bills ORDER BY created_at DESC", conn)
        if bills_df.empty:
            st.info("No sales records found.")
        else:
            st.dataframe(bills_df, use_container_width=True)
            
    with tab_stock:
        st.subheader("Current Stock Valuation")
        stock_df = pd.read_sql("SELECT id, name, category, opening_stock, purchase_price, selling_price FROM products WHERE is_active = 1", conn)
        if stock_df.empty:
            st.info("No products found.")
        else:
            stock_df['Total Valuation'] = stock_df['opening_stock'] * stock_df['purchase_price']
            st.dataframe(stock_df, use_container_width=True)
            st.metric("Total Inventory Valuation (Purchase Price)", f"₹ {stock_df['Total Valuation'].sum():,.2f}")
            
    with tab_exp:
        st.subheader("Expense Breakdown")
        exp_df = pd.read_sql("SELECT * FROM expenses ORDER BY expense_date DESC", conn)
        if exp_df.empty:
            st.info("No expense records found.")
        else:
            st.dataframe(exp_df, use_container_width=True)
            st.metric("Total Expenses", f"₹ {exp_df['amount'].sum():,.2f}")

# ============================================================================
# 9. LOW STOCK ALERTS
# ============================================================================
def render_low_stock_alerts(conn):
    st.header("⚠️ Low Stock Alerts")
    
    query = "SELECT * FROM products WHERE is_active = 1 AND opening_stock <= min_stock_level ORDER BY opening_stock ASC"
    low_stock_df = pd.read_sql(query, conn)
    
    if low_stock_df.empty:
        st.success("🎉 All products have sufficient stock levels!")
    else:
        st.warning("The following items are running low on stock and need reordering:")
        st.dataframe(low_stock_df[['name', 'category', 'opening_stock', 'min_stock_level', 'unit']], use_container_width=True)

# ============================================================================
# 10. SETTINGS
# ============================================================================
def render_settings(conn, role):
    st.header("⚙️ Shop Settings")
    
    settings = get_settings()
    
    with st.form("settings_form"):
        shop_name = st.text_input("Shop Name", value=(settings['shop_name'] if settings else ""))
        address = st.text_area("Address", value=(settings['address'] if settings else ""))
        mobile = st.text_input("Mobile", value=(settings['mobile'] if settings else ""))
        gst_number = st.text_input("GST Number", value=(settings['gst_number'] if settings else ""))
        footer_message = st.text_input("Receipt Footer Message", value=(settings['footer_message'] if settings else ""))
        terms = st.text_area("Terms & Conditions", value=(settings['terms'] if settings else ""))
        
        submitted = st.form_submit_button("💾 Save Settings", use_container_width=True)
        if submitted:
            save_shop_setup(shop_name, address, mobile, gst_number, footer_message, terms)
            st.success("Settings updated successfully!")
            st.rerun()

# ============================================================================
# Entry Point Control Flow
# ============================================================================
if not is_shop_configured():
    shop_setup_screen()
elif not st.session_state.logged_in:
    login_screen()
else:
    main_app()
