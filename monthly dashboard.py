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

df = df.dropna(subset=["account_created_date"])

df["Month"] = df["account_created_date"].dt.to_period("M").astype(str)

df["credential_count"] = df["credential_id"].apply(
    lambda x: len(str(x).split(",")) if pd.notnull(x) else 0
)

# ---------------------------------------------------
# SIDEBAR FILTERS
# ---------------------------------------------------

st.sidebar.title("🔎 Filters")

# Date range
min_date = df["account_created_date"].min()
max_date = df["account_created_date"].max()

date_range = st.sidebar.date_input(
    "Select Date Range",
    [min_date, max_date]
)

# Organization
orgs = sorted(df["organization_name"].dropna().unique())
selected_org = st.sidebar.multiselect("Organization", orgs, default=orgs)

# Provider
providers = sorted(df["provider_alias"].dropna().unique())
selected_provider = st.sidebar.multiselect("Provider", providers, default=providers)

# Customer Type
cust_types = sorted(df["Customer_Type"].dropna().unique())
selected_type = st.sidebar.multiselect("Customer Type", cust_types, default=cust_types)

# Customer Category
cust_cat = sorted(df["Customer_Category"].dropna().unique())
selected_cat = st.sidebar.multiselect("Customer Category", cust_cat, default=cust_cat)

# Metric Toggle
metric_type = st.sidebar.radio("Metric Type", ["Accounts", "Credentials"])

# Top N selector
top_n = st.sidebar.selectbox("Top N Customers", [5, 10, 15], index=1)

# ---------------------------------------------------
# FILTER DATA
# ---------------------------------------------------

filtered_df = df[
    (df["account_created_date"] >= pd.to_datetime(date_range[0])) &
    (df["account_created_date"] <= pd.to_datetime(date_range[1])) &
    (df["organization_name"].isin(selected_org)) &
    (df["provider_alias"].isin(selected_provider)) &
    (df["Customer_Type"].isin(selected_type)) &
    (df["Customer_Category"].isin(selected_cat))
]

# ---------------------------------------------------
# TITLE
# ---------------------------------------------------

st.title("📊 Interactive Customer Executive Dashboard")

# ---------------------------------------------------
# KPI SECTION WITH MOM GROWTH
# ---------------------------------------------------

current_month = filtered_df["Month"].max()
previous_month = (
    pd.Period(current_month) - 1
).strftime("%Y-%m")

current_data = filtered_df[filtered_df["Month"] == current_month]
previous_data = filtered_df[filtered_df["Month"] == previous_month]

if metric_type == "Accounts":
    current_value = current_data["account_id"].nunique()
    previous_value = previous_data["account_id"].nunique()
else:
    current_value = current_data["credential_count"].sum()
    previous_value = previous_data["credential_count"].sum()

growth = 0
if previous_value > 0:
    growth = round(((current_value - previous_value) / previous_value) * 100, 2)

col1, col2, col3 = st.columns(3)

col1.metric("Current Month Volume", f"{current_value:,}", f"{growth}% MoM")
col2.metric("Organizations", filtered_df["organization_name"].nunique())
col3.metric("Providers", filtered_df["provider_alias"].nunique())

st.markdown("---")

# ---------------------------------------------------
# TOP N CUSTOMER PIE
# ---------------------------------------------------

col1, col2 = st.columns(2)

if metric_type == "Accounts":
    top_customers = (
        filtered_df.groupby("organization_name")["account_id"]
        .nunique()
        .sort_values(ascending=False)
        .head(top_n)
        .reset_index(name="Count")
    )
else:
    top_customers = (
        filtered_df.groupby("organization_name")["credential_count"]
        .sum()
        .sort_values(ascending=False)
        .head(top_n)
        .reset_index(name="Count")
    )

fig_pie = px.pie(
    top_customers,
    names="organization_name",
    values="Count",
    title=f"Top {top_n} Customers"
)

col1.plotly_chart(fig_pie, use_container_width=True)

# ---------------------------------------------------
# CUSTOMER TYPE BAR
# ---------------------------------------------------

cust_type = (
    filtered_df.groupby("Customer_Type")
    .size()
    .reset_index(name="Count")
)

fig_bar = px.bar(
    cust_type,
    x="Customer_Type",
    y="Count",
    text="Count",
    title="Customer Type Distribution"
)

col2.plotly_chart(fig_bar, use_container_width=True)

# ---------------------------------------------------
# MONTHLY TREND (SORTED PROPERLY)
# ---------------------------------------------------

monthly = (
    filtered_df.groupby("Month")
    .size()
    .reset_index(name="Volume")
    .sort_values("Month")
)

fig_month = px.line(
    monthly,
    x="Month",
    y="Volume",
    markers=True,
    title="Monthly Volume Trend"
)

st.plotly_chart(fig_month, use_container_width=True)

# ---------------------------------------------------
# ACCOUNT STATUS DONUT
# ---------------------------------------------------

status = (
    filtered_df.groupby("account_status")
    .size()
    .reset_index(name="Count")
)

fig_donut = px.pie(
    status,
    names="account_status",
    values="Count",
    hole=0.5,
    title="Account Status Distribution"
)

st.plotly_chart(fig_donut, use_container_width=True)

# ---------------------------------------------------
# DOWNLOAD BUTTON
# ---------------------------------------------------

st.download_button(
    label="📥 Download Filtered Data",
    data=filtered_df.to_csv(index=False),
    file_name="filtered_data.csv",
    mime="text/csv",
)

# ---------------------------------------------------
# DRILL-DOWN TABLE
# ---------------------------------------------------

with st.expander("🔍 View Detailed Data"):
    st.dataframe(filtered_df, use_container_width=True)
