import streamlit as st
import pandas as pd
from datetime import datetime, date

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

# Page Configuration
st.set_page_config(
    page_title="Retail Shop Management Software",
    page_icon="🛒",
    layout="wide"
)

# Custom CSS for UI
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
    </style>
""", unsafe_allow_html=True)

init_db()

# RBAC Roles & Permissions
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

# Session States
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.role = ""

if "current_page" not in st.session_state:
    st.session_state.current_page = "Dashboard"

if "cart" not in st.session_state:
    st.session_state.cart = []

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

def shop_setup_screen():
    st.markdown("<h1 style='text-align: center; color: #2b2d42;'>🛒 Welcome — Let's Set Up Your Shop</h1>", unsafe_allow_html=True)
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
    st.sidebar.subheader("📌 Desktop Main Menu")

    menu_options = list(MENU_ICONS.keys())
    allowed_pages = [p for p in menu_options if page_allowed(p, role)]

    if st.session_state.current_page not in allowed_pages:
        st.session_state.current_page = "Dashboard"

    for key in menu_options:
        if key not in allowed_pages:
            continue
        if st.sidebar.button(MENU_ICONS[key], use_container_width=True, key=f"btn_{key}"):
            st.session_state.current_page = key
            st.rerun()

    page = st.session_state.current_page
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

def render_dashboard(conn):
    st.markdown("<h2 style='color: #2b2d42;'>📊 Executive Shop Dashboard</h2>", unsafe_allow_html=True)
    p_count = pd.read_sql("SELECT COUNT(*) as cnt FROM products WHERE is_active = 1", conn).iloc[0]['cnt']
    c_count = pd.read_sql("SELECT COUNT(*) as cnt FROM customers WHERE is_active = 1", conn).iloc[0]['cnt']
    s_count = pd.read_sql("SELECT COUNT(*) as cnt FROM suppliers WHERE is_active = 1", conn).iloc[0]['cnt']
    
    sales_df = pd.read_sql("SELECT SUM(grand_total) as total_sales FROM bills", conn)
    total_sales = sales_df.iloc[0]['total_sales'] if sales_df.iloc[0]['total_sales'] else 0.0

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("📦 Products", p_count)
    col2.metric("👥 Customers", c_count)
    col3.metric("🏭 Suppliers", s_count)
    col4.metric("💰 Total Sales", f"₹ {total_sales:,.2f}")

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

def render_product_master(conn, role):
    st.header("📦 Product Master Management")
    tab_list, tab_add = st.tabs(["📋 Product Inventory", "➕ Add New Product"])
    
    with tab_list:
        products_df = pd.read_sql("SELECT * FROM products ORDER BY name", conn)
        if products_df.empty:
            st.info("No products found.")
        else:
            st.dataframe(products_df, use_container_width=True)

    with tab_add:
        with st.form("add_product_form"):
            name = st.text_input("Product Name *")
            category = st.text_input("Category")
            unit = st.text_input("Unit (pcs, kg)", value="pcs")
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
                        INSERT INTO products (name, category, unit, purchase_price, selling_price, opening_stock, min_stock_level, is_active)
                        VALUES (?, ?, ?, ?, ?, ?, ?, 1)
                    """, (name.strip(), category, unit, purchase_price, selling_price, opening_stock, min_stock_level))
                    conn.commit()
                    st.success("Product added successfully!")
                    clear_lookup_caches()
                    st.rerun()

def render_supplier_management(conn):
    st.header("🏭 Supplier Management")
    suppliers_df = pd.read_sql("SELECT * FROM suppliers ORDER BY name", conn)
    if suppliers_df.empty:
        st.info("No suppliers found.")
    else:
        st.dataframe(suppliers_df, use_container_width=True)

def render_customer_management(conn):
    st.header("👥 Customer Management")
    cust_df = pd.read_sql("SELECT * FROM customers ORDER BY name", conn)
    if cust_df.empty:
        st.info("No customers found.")
    else:
        st.dataframe(cust_df, use_container_width=True)

def render_stock_purchase(conn):
    st.header("📥 Stock Purchase Management")
    hist_df = pd.read_sql("SELECT * FROM purchases ORDER BY id DESC", conn)
    if hist_df.empty:
        st.info("No purchase history found.")
    else:
        st.dataframe(hist_df, use_container_width=True)

def render_expense_management(conn):
    st.header("💸 Expense Management")
    exp_df = pd.read_sql("SELECT * FROM expenses ORDER BY id DESC", conn)
    if exp_df.empty:
        st.info("No expenses recorded.")
    else:
        st.dataframe(exp_df, use_container_width=True)

def render_reports_hub(conn):
    st.header("📈 Complete Reports Hub")
    bills_df = pd.read_sql("SELECT * FROM bills ORDER BY id DESC", conn)
    st.dataframe(bills_df, use_container_width=True)

def render_low_stock_alerts(conn):
    st.header("⚠️ Low Stock Alerts")
    query = "SELECT * FROM products WHERE is_active = 1 AND opening_stock <= min_stock_level ORDER BY opening_stock ASC"
    low_stock_df = pd.read_sql(query, conn)
    if low_stock_df.empty:
        st.success("🎉 All products have sufficient stock levels!")
    else:
        st.dataframe(low_stock_df, use_container_width=True)

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

if not is_shop_configured():
    shop_setup_screen()
elif not st.session_state.logged_in:
    login_screen()
else:
    main_app()
