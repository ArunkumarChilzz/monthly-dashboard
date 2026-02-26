import streamlit as st
import pandas as pd
import plotly.express as px
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="Customer Executive Dashboard", layout="wide")

# ---------------------------------------------------
# GOOGLE SHEETS CONNECTION
# ---------------------------------------------------

@st.cache_resource
def connect():
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ],
    )
    return gspread.authorize(creds)


@st.cache_data(ttl=300)
def load_data():
    client = connect()
    sheet = client.open("Utility Cloud Enrolled Volume_January 2026")
    worksheet = sheet.worksheet("Accounts")
    data = worksheet.get_all_records()
    return pd.DataFrame(data)


df = load_data()

# ---------------------------------------------------
# CLEANING
# ---------------------------------------------------

df.columns = df.columns.str.strip()

df["account_created_date"] = pd.to_datetime(
    df["account_created_date"],
    format="%d-%m-%Y %H:%M",
    errors="coerce"
)

df["Month"] = df["account_created_date"].dt.strftime("%b-%Y")

df["credential_count"] = df["credential_id"].apply(
    lambda x: len(str(x).split(",")) if pd.notnull(x) else 0
)

# ---------------------------------------------------
# SIDEBAR FILTERS
# ---------------------------------------------------

st.sidebar.title("Filters")

orgs = sorted(df["organization_name"].dropna().unique())
selected_org = st.sidebar.multiselect(
    "Organization", orgs, default=orgs
)

cust_types = sorted(df["Customer_Type"].dropna().unique())
selected_type = st.sidebar.multiselect(
    "Customer Type", cust_types, default=cust_types
)

filtered_df = df[
    (df["organization_name"].isin(selected_org)) &
    (df["Customer_Type"].isin(selected_type))
]

# ---------------------------------------------------
# TITLE
# ---------------------------------------------------

st.title("📊 Customer Executive Dashboard")

# ---------------------------------------------------
# KPI SECTION
# ---------------------------------------------------

total_accounts = filtered_df["account_id"].nunique()
total_orgs = filtered_df["organization_name"].nunique()
total_credentials = filtered_df["credential_count"].sum()

col1, col2, col3 = st.columns(3)

col1.metric("Total Accounts", f"{total_accounts:,}")
col2.metric("Organizations", f"{total_orgs:,}")
col3.metric("Total Credentials", f"{total_credentials:,}")

st.markdown("---")

# ---------------------------------------------------
# ROW 1
# ---------------------------------------------------

col1, col2 = st.columns(2)

top10 = (
    filtered_df["organization_name"]
    .value_counts()
    .head(10)
    .reset_index()
)

top10.columns = ["Organization", "Count"]

fig_pie = px.pie(
    top10,
    names="Organization",
    values="Count",
    title="Top 10 Customer Volume"
)

col1.plotly_chart(fig_pie, use_container_width=True)

cust_type = (
    filtered_df["Customer_Type"]
    .value_counts()
    .reset_index()
)

cust_type.columns = ["Customer_Type", "Count"]

fig_bar = px.bar(
    cust_type,
    x="Customer_Type",
    y="Count",
    text="Count",
    title="Customer Type Distribution"
)

col2.plotly_chart(fig_bar, use_container_width=True)

# ---------------------------------------------------
# ROW 2
# ---------------------------------------------------

col3, col4 = st.columns(2)

status_dist = (
    filtered_df["account_status"]
    .value_counts()
    .reset_index()
)

status_dist.columns = ["Status", "Count"]

fig_donut = px.pie(
    status_dist,
    names="Status",
    values="Count",
    hole=0.5,
    title="Account Status"
)

col3.plotly_chart(fig_donut, use_container_width=True)

monthly = (
    filtered_df.groupby("Month")
    .size()
    .reset_index(name="Volume")
)

fig_month = px.bar(
    monthly,
    x="Month",
    y="Volume",
    text="Volume",
    title="Monthly Volume Trend"
)

col4.plotly_chart(fig_month, use_container_width=True)
