import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
from datetime import datetime

# ---------------------------------------------------------
# 0. CONFIGURATION
# ---------------------------------------------------------
TYPE_MAPPING = {
    1: "Alguém já fez prova com o professor X?",
    2: "Pedindo contato de alguém",
    3: "Tem alguém em tal hospital?",
    4: "Figurinas / Stickers",
    5: "Foto / Vídeo / Áudio",
    6: "Conversas gerais",
    7: "Anúncios de ligas",
    8: "Anúncios de festas",
    9: "Venda/Compra de ingressos",
    10: "Propaganda de cursos e materiais",
    11: "Anúncios gerais",
}

DB_NAME = "chat_data.db"

# ---------------------------------------------------------
# 1. DATA LOADING
# ---------------------------------------------------------
@st.cache_data
def load_data():
    conn = sqlite3.connect(DB_NAME)
    query = """
        SELECT m.id, u.ssn as user_ssn, m.timestamp, m.content, m.type
        FROM messages m JOIN users u ON m.user_id = u.id
        ORDER BY m.timestamp DESC
    """
    try:
        df = pd.read_sql_query(query, conn)
        conn.close()
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['content'] = df['content'].fillna("").astype(str)
        df['user_ssn'] = df['user_ssn'].fillna("Unknown").astype(str)

        # Mapping Logic
        df['type_raw'] = df['type'].fillna(-1).astype(int)
        def get_label(x):
            if x == -1: return "Untagged"
            return TYPE_MAPPING.get(x, f"Type {x}")
        df['type'] = df['type_raw'].apply(get_label)
        
        return df
    except Exception:
        return pd.DataFrame()

# ---------------------------------------------------------
# 2. PAGE SETUP
# ---------------------------------------------------------
st.set_page_config(page_title="Database Inspector", layout="wide")
st.title("📂 Análise das mensagens do Canal MEDFundão")

df = load_data()
if df.empty:
    st.warning("No data found.")
    st.stop()

# ---------------------------------------------------------
# 3. URL PARAMETER UTILS
# ---------------------------------------------------------
def get_param_list(key):
    if key not in st.query_params: return []
    val = st.query_params[key]
    return val if isinstance(val, list) else [val]

def get_param_bool(key, default=False):
    if key not in st.query_params: return default
    return st.query_params[key].lower() == 'true'

def get_param_date(key, default_date):
    if key not in st.query_params: return default_date
    try: return datetime.strptime(st.query_params[key], '%Y-%m-%d').date()
    except ValueError: return default_date

# --- CALCULATE DEFAULTS ---
if not df['timestamp'].isnull().all():
    min_db_date = df['timestamp'].min().date()
    max_db_date = df['timestamp'].max().date()
else:
    min_db_date = max_db_date = pd.to_datetime("today").date()

all_users_list = sorted(df['user_ssn'].unique().tolist())
all_types_list = sorted(df['type'].unique().tolist())

# --- RESTORE STATE FROM URL ---
if "init" not in st.session_state:
    st.session_state["init"] = True
    
    # Date
    st.session_state["date_enabled"] = get_param_bool("date_enabled", False)
    st.session_state["start_date"] = get_param_date("start", min_db_date)
    st.session_state["end_date"] = get_param_date("end", max_db_date)

    # Users
    # Logic: If 'all_users' is true (or missing), we default to ALL and ignore the list.
    # If 'all_users' is false, we look for the specific list in URL.
    st.session_state["all_users_check"] = get_param_bool("all_users", True)
    url_users = get_param_list("users")
    if st.session_state["all_users_check"]:
        st.session_state["selected_users"] = all_users_list
    else:
        st.session_state["selected_users"] = url_users if url_users else all_users_list

    # Types
    st.session_state["all_types_check"] = get_param_bool("all_types", True)
    url_types = get_param_list("types")
    if st.session_state["all_types_check"]:
        st.session_state["selected_types"] = all_types_list
    else:
        st.session_state["selected_types"] = url_types if url_types else all_types_list

# ---------------------------------------------------------
# 4. SIDEBAR (FILTERS)
# ---------------------------------------------------------
st.sidebar.header("Filter Options")

# --- DATE ---
st.sidebar.subheader("📅 Timeframe")
enable_date = st.sidebar.checkbox("Filter by specific dates", key="date_enabled")

if enable_date:
    date_range = st.sidebar.date_input(
        "Select Range",
        value=(st.session_state["start_date"], st.session_state["end_date"]),
        min_value=min_db_date, max_value=max_db_date,
        key="date_range_picker" 
    )
    if len(date_range) == 2: start_date, end_date = date_range
    else: start_date, end_date = date_range[0], date_range[0]
else:
    start_date, end_date = min_db_date, max_db_date
    st.sidebar.caption("✅ Showing full timeframe")

# --- USERS ---
st.sidebar.subheader("👤 Users")
all_users_check = st.sidebar.checkbox("Select All Users", key="all_users_check")

if all_users_check:
    selected_users = all_users_list
else:
    # Safely select defaults
    default_u = [u for u in st.session_state["selected_users"] if u in all_users_list]
    selected_users = st.sidebar.multiselect("Select Users", all_users_list, default=default_u, key="user_multiselect")

# --- TYPES ---
st.sidebar.subheader("🏷️ Message Types")
all_types_check = st.sidebar.checkbox("Select All Types", key="all_types_check")

if all_types_check:
    selected_types = all_types_list
else:
    default_t = [t for t in st.session_state["selected_types"] if t in all_types_list]
    selected_types = st.sidebar.multiselect("Select Types", all_types_list, default=default_t, key="type_multiselect")

# ---------------------------------------------------------
# 5. SMART URL SYNC (The Fix)
# ---------------------------------------------------------
current_params = {
    "date_enabled": str(enable_date).lower(),
    "start": start_date.strftime('%Y-%m-%d'),
    "end": end_date.strftime('%Y-%m-%d'),
    "all_users": str(all_users_check).lower(),
    "all_types": str(all_types_check).lower(),
}

# KEY CHANGE: Only add the list to the URL if "Select All" is unchecked
if not all_users_check:
    current_params["users"] = selected_users

if not all_types_check:
    current_params["types"] = selected_types

st.query_params.clear() # Optional: Clear old junk keys
st.query_params.update(current_params)

# ---------------------------------------------------------
# 6. DASHBOARD
# ---------------------------------------------------------
mask = (
    (df['timestamp'].dt.date >= start_date) & 
    (df['timestamp'].dt.date <= end_date) & 
    (df['user_ssn'].isin(selected_users)) & 
    (df['type'].isin(selected_types))
)
filtered_df = df.loc[mask]

col1, col2, col3 = st.columns(3)
col1.metric("Total Messages", len(filtered_df))
col2.metric("Unique Users", filtered_df['user_ssn'].nunique())
col3.metric("Msg Types Found", filtered_df['type'].nunique())

st.markdown("---")

tab1, tab2, tab3 = st.tabs(["📊 Analytics", "📄 Message Browser", "🔎 Search"])

with tab1:
    c1, c2 = st.columns(2)
    if not filtered_df.empty:
        fig_t = px.pie(filtered_df['type'].value_counts().reset_index(), values='count', names='type', hole=0.4, title="Distribution by Type")
        c1.plotly_chart(fig_t)
        
        user_counts = filtered_df['user_ssn'].value_counts().reset_index().head(10)
        fig_u = px.bar(user_counts, x='user_ssn', y='count', color='count', title="Top Users")
        c2.plotly_chart(fig_u)
        
        timeline = filtered_df.groupby(filtered_df['timestamp'].dt.date).size().reset_index(name='count')
        fig_time = px.line(timeline, x='timestamp', y='count', markers=True, title="Activity Timeline")
        st.plotly_chart(fig_time)

with tab2:
    st.dataframe(filtered_df[['timestamp', 'user_ssn', 'type', 'content']], width="stretch", hide_index=True)

with tab3:
    search = st.text_input("Search Content")
    if search:
        res = filtered_df[filtered_df['content'].str.contains(search, case=False, na=False)]
        st.write(f"Found {len(res)} matches")
        for i, row in res.iterrows():
            st.text(f"{row['timestamp']} | {row['type']} | {row['user_ssn']}: {row['content']}")