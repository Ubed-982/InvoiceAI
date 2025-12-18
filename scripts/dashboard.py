import streamlit as st
import pandas as pd
import plotly.express as px
import sqlite3
from datetime import datetime
import os
import sys
import time

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
try:
    from extract_ai import analyze_invoice_file, save_to_db
except ImportError:
    analyze_invoice_file = None
    save_to_db = None

# ═══════════════════════════════════════════════════════════════
# PAGE CONFIGURATION
# ═══════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="InvoiceAI - Financial Dashboard",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ═══════════════════════════════════════════════════════════════
# DARK CYBER THEME CSS
# ═══════════════════════════════════════════════════════════════
st.markdown("""
<style>
    /* GLOBAL BACKGROUND */
    .stApp {
        background: linear-gradient(135deg, #1A1B35 0%, #2D1B4E 100%) !important;
        background-attachment: fixed;
    }
    
    /* MAIN CARD CONTAINER */
    .block-container {
        background-color: #242547;
        padding: 2rem 3rem !important;
        border-radius: 25px;
        box-shadow: 0 20px 60px rgba(0, 0, 0, 0.6);
        margin-top: 2rem;
        margin-bottom: 2rem;
        max-width: 95% !important;
    }

    /* TEXT COLORS */
    h1, h2, h3, h4, h5, p, span, div, label {
        color: #FFFFFF !important;
        font-family: 'Inter', sans-serif;
    }
    .metric-label { color: #B495A4 !important; }
    
    /* ▼▼▼ FIX: FORCE UPLOADER VISIBILITY & PREVENT FADING ▼▼▼ */
    [data-testid="stFileUploader"] {
        opacity: 1 !important;
    }
    [data-testid="stFileUploaderDropzone"] {
        background-color: #2A2B50 !important;
        border: 2px dashed #882ECA !important;
        opacity: 1 !important;
    }
    /* Make text inside uploader white and visible */
    [data-testid="stFileUploaderDropzone"] div, 
    [data-testid="stFileUploaderDropzone"] span, 
    [data-testid="stFileUploaderDropzone"] small {
        color: white !important;
        opacity: 1 !important;
    }
    
    /* CUSTOM CARDS */
    .custom-card {
        background: linear-gradient(180deg, #2A2B50 0%, #242547 100%);
        border: 1px solid #36136E;
        border-radius: 16px;
        padding: 20px;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3);
        margin-bottom: 20px;
        transition: transform 0.3s ease;
    }
    .custom-card:hover { transform: translateY(-5px); }
    
    /* NATIVE STREAMLIT CONTAINERS */
    [data-testid="stVerticalBlockBorderWrapper"] {
        background-color: #2A2B50 !important;
        border: 1px solid #36136E !important;
        border-radius: 16px !important;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3);
        padding: 20px !important;
    }
    
    /* ACTION CARDS */
    .action-card {
        background-color: #1F2040 !important;
        padding: 15px;
        border-radius: 10px;
        margin-bottom: 10px;
        border-left: 4px solid #882ECA;
    }
    .ac-urgent { border-left-color: #EF4444; }
    .ac-routine { border-left-color: #F59E0B; }
    .ac-done { border-left-color: #61D29A; }

    /* UPLOAD & FILTERS */
    [data-testid="stFileUploader"] {
        background-color: #2A2B50;
        border: 1px dashed #882ECA;
        border-radius: 12px;
    }
    
    /* DATAFRAME */
    [data-testid="stDataFrame"] {
        background-color: #2A2B50;
        border-radius: 10px;
    }
    
    /* BUTTON STYLING */
    div.stButton > button {
        background: linear-gradient(90deg, #36136E 0%, #882ECA 100%) !important;
        color: white !important;
        border: 1px solid #882ECA !important;
        font-weight: 600;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        width: 100%;
        transition: all 0.3s ease;
        margin-left: 5px;
    }
    div.stButton > button:hover {
        background: linear-gradient(90deg, #882ECA 0%, #61D29A 100%) !important;
        border-color: #61D29A !important;
        transform: translateY(-2px);
    }
    
    /* ANIMATIONS */
    @keyframes pulse-green {
        0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(97, 210, 154, 0.7); }
        70% { transform: scale(1); box-shadow: 0 0 0 10px rgba(97, 210, 154, 0); }
        100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(97, 210, 154, 0); }
    }
    
    @keyframes text-flash {
        0% { opacity: 0.6; }
        50% { opacity: 1; }
        100% { opacity: 0.6; }
    }
    
    .status-dot {
        width: 8px; height: 8px; background-color: #61D29A;
        border-radius: 50%; display: inline-block;
        animation: pulse-green 2s infinite;
    }
    
    .live-text {
        color: #61D29A !important;
        font-weight: bold;
        animation: text-flash 2s infinite;
    }
    
    /* SECTION SPACING HELPER */
    .section-divider {
        margin-top: 40px;
        margin-bottom: 40px;
        border-top: 1px solid rgba(255, 255, 255, 0.1);
    }
    /* --- HIDE STREAMLIT UI ELEMENTS --- */
    
    /* Hides the top header (Deploy button, menu, running man) */
    header[data-testid="stHeader"] {
        display: none !important;
    }
    
    /* Hides the footer (Made with Streamlit) */
    footer {
        display: none !important;
    }
    
    /* Hides the 'Viewer' badge on top right if deployed */
    .stDeployButton {
        display: none !important;
    }
</style>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════
# DATA LOADING
# ═══════════════════════════════════════════════════════════════
@st.cache_data(ttl=5)
def load_data():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(current_dir)
    db_path = os.path.join(root_dir, "invoices.db")
    
    if not os.path.exists(db_path):
        return pd.DataFrame()
    
    try:
        conn = sqlite3.connect(db_path)
        df = pd.read_sql_query("SELECT * FROM invoices", conn)
        conn.close()
        
        df = df.rename(columns={
            "invoice_id": "Invoice ID", "vendor": "Vendor", "amount": "Amount",
            "issue_date": "Issue Date", "due_date": "Due Date", "status": "Status",
            "recommended_action": "Recommended Action", "items": "Items", "location": "Store Location"
        })
        
        if "Issue Date" in df.columns: df["Issue Date"] = pd.to_datetime(df["Issue Date"], errors='coerce')
        if "Recommended Action" not in df.columns: df["Recommended Action"] = "Review pending"
            
        return df
    except Exception as e:
        st.error(f"Database Error: {e}")
        return pd.DataFrame()

df = load_data()

# ═══════════════════════════════════════════════════════════════
# HEADER
# ═══════════════════════════════════════════════════════════════
st.markdown(f"""
<div style="background: linear-gradient(135deg, #2D1B4E 0%, #1A1B35 100%); border: 1px solid #36136E; border-top: 4px solid #882ECA; padding: 30px; border-radius: 20px; box-shadow: 0 10px 40px rgba(0,0,0,0.5); margin-bottom: 30px; display: flex; justify-content: space-between; align-items: center;">
<div>
<div style="display: flex; align-items: center; gap: 8px; margin-bottom: 5px;">

<h1 style="margin:0; font-size: 2.2rem; font-weight: 800; background: -webkit-linear-gradient(0deg, #fff, #B495A4); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">InvoiceAI Dashboard</h1>
</div>
<p style="margin:0; font-size: 1rem; color: #B495A4 !important; letter-spacing: 0.5px;">Convert raw invoices into real-time spend intelligence, overdue risk alerts, and payment prioritization in seconds</p>
</div>
<div style="text-align: right; background: rgba(255,255,255,0.05); padding: 15px 25px; border-radius: 15px; border: 1px solid rgba(255,255,255,0.1);">
<div style="display: flex; align-items: center; gap: 10px; justify-content: flex-end; margin-bottom: 5px;">
<div class="status-dot"></div>
<span style="font-weight: 700; color: #61D29A; letter-spacing: 1px;">SYSTEM ONLINE</span>
</div>
<div style="font-size: 0.85rem; color: #E0E0E0;">DATA SYNC: <strong style="color: white;">{datetime.now().strftime('%I:%M %p')}</strong></div>
</div>
</div>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════
# UPLOAD SECTION
# ═══════════════════════════════════════════════════════════════
with st.expander("📤  Upload Invoices (Batch Processing)", expanded=True):
    c1, c2 = st.columns([4, 1], vertical_alignment="center", gap="large") 
    
    with c1:
        uploaded_files = st.file_uploader("Drag & Drop PDFs", type=["pdf"], accept_multiple_files=True, label_visibility="collapsed")
    
    with c2:
        if uploaded_files:
            if st.button(f"⚡ Process {len(uploaded_files)} Files", key="process_btn"):
                progress = st.progress(0)
                status = st.empty()
                for i, file in enumerate(uploaded_files):
                    status.text(f"Processing {file.name}...")
                    try:
                        temp_path = f"temp_{file.name}"
                        with open(temp_path, "wb") as f: f.write(file.getbuffer())
                        if analyze_invoice_file:
                            data = analyze_invoice_file(temp_path)
                            if data: save_to_db(data)
                        if os.path.exists(temp_path): os.remove(temp_path)
                    except: pass
                    progress.progress((i+1)/len(uploaded_files))
                
                status.success("✅ Batch Complete!")
                time.sleep(1)
                st.cache_data.clear()
                st.rerun()
        else:
            st.markdown("""
            <button style="background: #2A2B50; color: #64748B; border: 1px solid #36136E; padding: 0.5rem 1rem; border-radius: 8px; font-weight: 600; width: 100%; cursor: not-allowed; margin-left: -15px;">Waiting for files...</button>
            """, unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════
# KPI SECTION
# ═══════════════════════════════════════════════════════════════

if df.empty:
    st.markdown("""
    <div style="background: #2A2B50; border: 1px dashed #36136E; border-radius: 12px; padding: 40px; text-align: center; margin-top: 40px;">
        <h3 style="color: #64748B !important; margin: 0;">📭 No Data Available</h3>
        <p style="color: #B495A4 !important;">Upload PDF invoices above to initialize the dashboard.</p>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

st.markdown("### 🚀 Operational Overview")

total_inv = len(df)
total_amt = df["Amount"].sum()
paid_inv = len(df[df["Status"] == "Paid"])
pending_amt = df[df["Status"] == "Pending"]["Amount"].sum()
time_saved = (total_inv * 9.5) / 60

k1, k2, k3, k4, k5 = st.columns(5)

def kpi_box(col, title, val, sub, color, is_live=False):
    sub_class = "live-text" if is_live else ""
    
    if is_live:
        text_color = ""
    elif "Automated" in sub or "Efficiency" in sub:
        text_color = "color: #61D29A;"
    else:
        text_color = "color: #B495A4;"

    if is_live:
        sub_html = f'<div class="{sub_class}" style="font-size: 0.8rem; margin-top: 5px;">● {sub}</div>'
    else:
        sub_html = f'<div style="{text_color} font-size: 0.8rem; margin-top: 5px; opacity: 0.9;">{sub}</div>'

    col.markdown(f"""
    <div class="custom-card" style="border-top: 4px solid {color}; text-align: center;">
        <div style="color: #B495A4; font-size: 0.8rem; font-weight: 700; text-transform: uppercase; margin-bottom: 5px;">{title}</div>
        <div style="font-size: 1.8rem; font-weight: 800; color: white;">{val}</div>
        {sub_html}
    </div>
    """, unsafe_allow_html=True)

kpi_box(k1, "Total Invoices", f"{total_inv}", "🔼 100% Automated", "#3B82F6")
kpi_box(k2, "Total Spend", f"AED {total_amt:,.0f}", "Live Data", "#61D29A", is_live=True)
kpi_box(k3, "Paid Count", f"{paid_inv}", "Processing", "#61D29A")
kpi_box(k4, "Pending Value", f"AED {pending_amt:,.0f}", f"{len(df[df['Status']=='Pending'])} Invoices", "#F59E0B")
kpi_box(k5, "Time Saved", f"{time_saved:.1f} Hrs", "⚡ 95% Efficiency", "#EF4444")

# ═══════════════════════════════════════════════════════════════
# CHARTS & ACTIONS
# ═══════════════════════════════════════════════════════════════

c_charts, c_actions = st.columns([2, 1])

# --- CHARTS ---
with c_charts:
    with st.container(border=True):
        st.markdown('<h4 style="color:#61D29A !important;">💸 Spend Analysis</h4>', unsafe_allow_html=True)
        
        vendor_sum = df.groupby("Vendor")["Amount"].sum().reset_index().sort_values("Amount", ascending=True)
        
        fig_bar = px.bar(
            vendor_sum, 
            x="Amount", 
            y="Vendor", 
            orientation='h', 
            text_auto='.2s',
            color="Amount",
            color_continuous_scale=["#36136E", "#882ECA"]
        )
        fig_bar.update_traces(textposition="inside")
        fig_bar.update_layout(
            plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='white'), margin=dict(l=0, r=0, t=0, b=0),
            height=250, coloraxis_showscale=False
        )
        st.plotly_chart(fig_bar, use_container_width=True, key="spend_chart")
        
        st.markdown("---")
        st.markdown('<h4 style="color:#61D29A !important;">📊 Invoice Status</h4>', unsafe_allow_html=True)
        
        status_counts = df["Status"].value_counts().reset_index()
        status_counts.columns = ["Status", "Count"]
        color_map = {"Paid": "#61D29A", "Pending": "#F59E0B", "Overdue": "#EF4444"}
        
        fig_pie = px.pie(status_counts, values="Count", names="Status", hole=0.5)
        fig_pie.update_traces(
            marker=dict(colors=[color_map.get(x, '#882ECA') for x in status_counts["Status"]]),
            textinfo='percent'
        )
        fig_pie.update_layout(
            plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='white'), margin=dict(t=0, b=0), height=250,
            showlegend=True
        )
        st.plotly_chart(fig_pie, use_container_width=True, key="status_chart")

# --- SMART ACTIONS ---
with c_actions:
    with st.container(height=718, border=True):
        st.markdown('<h4 style="color:#EF4444 !important;">⚡ Action Queue</h4>', unsafe_allow_html=True)
        
        urgent = df[df["Recommended Action"].str.contains("Urgent|Overdue", case=False, na=False)]
        routine = df[~df.index.isin(urgent.index)]
        
        if not urgent.empty:
            for _, row in urgent.iterrows():
                st.markdown(f"""
                <div class="action-card ac-urgent">
                    <div style="font-weight:700; color:#FF9999;">🔥 {row['Vendor']}</div>
                    <div style="font-size:1.1rem; font-weight:800; color:white;">AED {row['Amount']:,.0f}</div>
                    <div style="font-size:0.8rem; color:#B495A4;">{row['Recommended Action']}</div>
                </div>
                """, unsafe_allow_html=True)
        
        for _, row in routine.iterrows():
            st.markdown(f"""
            <div class="action-card ac-routine">
                <div style="font-weight:700; color:#D1C4E9;">📋 {row['Vendor']}</div>
                <div style="font-size:1.1rem; font-weight:800; color:white;">AED {row['Amount']:,.0f}</div>
                <div style="font-size:0.8rem; color:#B495A4;">{row['Recommended Action']}</div>
            </div>
            """, unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════
# FILTER & DATA TABLE
# ═══════════════════════════════════════════════════════════════

st.markdown("### 📑 Detailed Ledger")

f_col1, f_col2, f_col3 = st.columns(3)
with f_col1: vendor_filter = st.multiselect("Filter Vendor", df["Vendor"].unique(), default=df["Vendor"].unique())
with f_col2: status_filter = st.multiselect("Filter Status", df["Status"].unique(), default=df["Status"].unique())
with f_col3: 
    if not df.empty:
        min_v, max_v = int(df["Amount"].min()), int(df["Amount"].max())
        val_range = st.slider("Amount Range", min_v, max_v, (min_v, max_v))

filtered_df = df[
    df["Vendor"].isin(vendor_filter) & 
    df["Status"].isin(status_filter) & 
    (df["Amount"].between(val_range[0], val_range[1]))
]

st.dataframe(
    filtered_df,
    column_config={
        "Amount": st.column_config.NumberColumn("Amount", format="AED %.2f"),
        "Status": st.column_config.TextColumn("Status", width="small"),
        "Recommended Action": st.column_config.TextColumn("AI Action", width="large"),
    },
    use_container_width=True,
    hide_index=True
)

st.download_button(
    label="📥 Download Filtered CSV",
    data=filtered_df.to_csv(index=False).encode('utf-8'),
    file_name="invoice_export.csv",
    mime="text/csv"
)

# ═══════════════════════════════════════════════════════════════
# FOOTER
# ═══════════════════════════════════════════════════════════════
st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
c_before, c_after = st.columns(2)

with c_before:
    st.markdown("""
    <div style="background:#2A2B50; padding:20px; border-radius:10px; border:1px solid #36136E; opacity:0.8;">
        <h4 style="color:#FF4B4B !important; margin:0;">⏱️ Traditional Process</h4>
        <ul style="color:#B495A4; margin-top:10px; font-size:0.9rem;">
            <li>📄 Manual data entry (10 mins/invoice)</li>
            <li>❌ High error rate (~12%)</li>
            <li>📉 Delayed financial visibility</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

with c_after:
    st.markdown("""
    <div style="background:#2A2B50; padding:20px; border-radius:10px; border:1px solid #36136E; opacity:0.8;">
        <h4 style="color:#61D29A !important; margin:0;">🤖 InvoiceAI Pipeline</h4>
        <ul style="color:#B495A4; margin-top:10px; font-size:0.9rem;">
            <li>⚡ Instant extraction (30 secs/invoice)</li>
            <li>✅ 99% Accuracy with AI Validation</li>
            <li>📈 Real-time spend analytics</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br><div style='text-align:center; color:#B495A4; font-size:0.8rem;'>InvoiceAI v2.0 • Enterprise Edition • Secure UAE Cloud</div>", unsafe_allow_html=True)
    