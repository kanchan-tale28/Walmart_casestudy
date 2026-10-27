import io
import re
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(
    page_title="Walmart | Big Data Analytics",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------- Styling ----------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@500;600;700;800&display=swap');
html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
.stApp { background: #f5f7f6; color: #172b24; }
[data-testid="stSidebar"] { background: #102f24; }
[data-testid="stSidebar"] * { color: #f4f8f5 !important; }
/* Keep uploader controls readable: their surfaces are light, so their text must be dark. */
[data-testid="stSidebar"] [data-testid="stFileUploader"] {
  background: #f8faf9 !important;
  border-radius: 12px !important;
  padding: 8px !important;
}
[data-testid="stSidebar"] [data-testid="stFileUploader"] * {
  color: #20372c !important;
}
[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] {
  background: #f8faf9 !important;
  border: 1px dashed #aabbb1 !important;
  border-radius: 10px !important;
}
[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] button {
  background: #ffffff !important;
  border: 1px solid #cbd6cf !important;
}
[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] button * {
  color: #20372c !important;
}
.block-container { padding-top: 1.7rem; padding-bottom: 2rem; max-width: 1500px; }
.hero {
  background: linear-gradient(120deg, #103c2b 0%, #176443 65%, #2d8058 100%);
  padding: 28px 32px; border-radius: 22px; color: white; margin-bottom: 22px;
  box-shadow: 0 12px 30px rgba(16,47,36,.12);
}
.hero h1 { font-family: 'Manrope', sans-serif; font-size: 2.15rem; margin: 0 0 8px 0; color: white; }
.hero p { color: #d6eadf; margin: 0; font-size: 1rem; }
.eyebrow { color: #c9f0d9; font-weight: 700; text-transform: uppercase; letter-spacing: .13em; font-size: .72rem; margin-bottom: 9px; }
.kpi {
  background: white; border: 1px solid #e5ebe7; border-radius: 16px;
  padding: 18px 20px; min-height: 118px; box-shadow: 0 3px 12px rgba(25,50,39,.035);
}
.kpi-label { color: #718078; font-size: .82rem; font-weight: 600; margin-bottom: 9px; }
.kpi-value { color: #153b2c; font-family: 'Manrope', sans-serif; font-size: 1.7rem; font-weight: 800; line-height: 1.2; }
.kpi-sub { color: #7d8982; font-size: .76rem; margin-top: 7px; }
.section-title { font-family: 'Manrope', sans-serif; font-size: 1.22rem; font-weight: 800; color: #173b2d; margin: 10px 0 4px; }
.section-sub { color: #75837b; font-size: .88rem; margin-bottom: 14px; }
.panel {
  background: white; border: 1px solid #e5ebe7; border-radius: 16px;
  padding: 18px 20px; box-shadow: 0 3px 12px rgba(25,50,39,.035);
}
.pill { display: inline-block; background: #e2f4e9; color: #176443; border-radius: 999px; padding: 5px 10px; font-size: .75rem; font-weight: 700; }
div[data-testid="stMetric"] { background: white; border: 1px solid #e5ebe7; padding: 15px; border-radius: 14px; }
.stTabs [data-baseweb="tab-list"] { gap: 8px; }
.stTabs [data-baseweb="tab"] { background: white; border-radius: 10px 10px 0 0; padding: 10px 18px; }
footer { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# ---------- Data helpers ----------
@st.cache_data(show_spinner=False)
def read_sales(file_bytes):
    df = pd.read_csv(io.BytesIO(file_bytes))
    required = {"Store", "Dept", "Date", "Weekly_Sales", "IsHoliday"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError("Missing required columns: " + ", ".join(sorted(missing)))
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df["Weekly_Sales"] = pd.to_numeric(df["Weekly_Sales"], errors="coerce")
    df["Store"] = pd.to_numeric(df["Store"], errors="coerce")
    df["Dept"] = pd.to_numeric(df["Dept"], errors="coerce")
    df = df.dropna(subset=["Date", "Weekly_Sales", "Store", "Dept"]).copy()
    df["Store"] = df["Store"].astype(int)
    df["Dept"] = df["Dept"].astype(int)
    df["Holiday_Label"] = df["IsHoliday"].astype(str).str.lower().map(
        {"true": "Holiday", "false": "Non-holiday", "1": "Holiday", "0": "Non-holiday"}
    ).fillna("Unknown")
    return df

def money_short(x):
    x = float(x)
    if abs(x) >= 1e9: return f"${x/1e9:.2f}B"
    if abs(x) >= 1e6: return f"${x/1e6:.2f}M"
    if abs(x) >= 1e3: return f"${x/1e3:.1f}K"
    return f"${x:,.0f}"

def metric_card(label, value, sub):
    st.markdown(
        f'<div class="kpi"><div class="kpi-label">{label}</div>'
        f'<div class="kpi-value">{value}</div><div class="kpi-sub">{sub}</div></div>',
        unsafe_allow_html=True
    )

def parse_mapreduce(text):
    rows = []
    for line in text.splitlines():
        parts = re.split(r"\s+", line.strip())
        if len(parts) >= 2:
            try:
                store_id = int(parts[0])
                sales = float(parts[1])
                rows.append((store_id, sales))
            except (ValueError, OverflowError):
                continue
    return pd.DataFrame(rows, columns=["Store", "Total_Sales"]).drop_duplicates("Store")

# ---------- Sidebar ----------
with st.sidebar:
    st.markdown("## 🛒 Walmart Analytics")
    st.caption("BIG DATA • RETAIL INTELLIGENCE")
    page = st.radio(
        "NAVIGATION",
        ["Executive Overview", "Sales Explorer", "Store & Department", "Holiday Insights", "ML Prediction", "Hadoop Pipeline"],
        label_visibility="visible",
    )
    st.markdown("---")
    st.markdown("### Dataset")
    sales_upload = st.file_uploader("Upload Walmart train.csv", type=["csv"], key="sales_csv")
    st.caption("Use the same `train.csv` file from your Colab implementation.")
    st.markdown("---")
    st.markdown("### Hadoop output (optional)")
    mr_upload = st.file_uploader("Upload MapReduce part-r-00000", type=["txt", "csv"], key="mr_output")
    st.caption("Optional: export `/walmart/output/part-r-00000` from HDFS and upload it here.")
    st.markdown("---")
    st.caption("Student project • Historical Walmart sales data")

# Try default local file; otherwise ask for upload
if sales_upload is not None:
    raw_bytes = sales_upload.getvalue()
else:
    default_path = Path("train.csv")
    raw_bytes = default_path.read_bytes() if default_path.exists() else None

if raw_bytes is None:
    st.markdown("""
    <div class="hero">
      <div class="eyebrow">Retail intelligence platform</div>
      <h1>Walmart Big Data Analytics</h1>
      <p>Explore sales performance, seasonal patterns and distributed processing results in one place.</p>
    </div>
    """, unsafe_allow_html=True)
    st.warning("Upload your `train.csv` using the left sidebar to open the dashboard.")
    st.markdown("#### What this app includes")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown('<div class="panel"><h3>📊 Sales analytics</h3><p>Store rankings, department performance, weekly trends and holiday comparisons.</p></div>', unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="panel"><h3>🤖 ML evaluation</h3><p>Display the evaluation metrics from your existing Spark MLlib model.</p></div>', unsafe_allow_html=True)
    with c3:
        st.markdown('<div class="panel"><h3>⚙️ Hadoop processing</h3><p>Review the HDFS → Mapper → Shuffle & Sort → Reducer workflow and results.</p></div>', unsafe_allow_html=True)
    st.stop()

try:
    df = read_sales(raw_bytes)
except Exception as e:
    st.error(f"Could not load the sales dataset: {e}")
    st.stop()

total_sales = df["Weekly_Sales"].sum()
store_count = df["Store"].nunique()
dept_count = df["Dept"].nunique()
record_count = len(df)
date_min, date_max = df["Date"].min(), df["Date"].max()
store_sales = df.groupby("Store", as_index=False)["Weekly_Sales"].sum().sort_values("Weekly_Sales", ascending=False)
dept_sales = df.groupby("Dept", as_index=False)["Weekly_Sales"].sum().sort_values("Weekly_Sales", ascending=False)
weekly = df.groupby("Date", as_index=False)["Weekly_Sales"].sum().sort_values("Date")
holiday = (
    df.groupby("Holiday_Label")["Weekly_Sales"]
    .agg(Average_Sales="mean", Total_Sales="sum", Records="count")
    .reset_index()
)

# ---------- Hero ----------
st.markdown(f"""
<div class="hero">
  <div class="eyebrow">Retail intelligence platform · Historical dataset</div>
  <h1>Walmart Big Data Analytics</h1>
  <p>Retail Sales Optimization Dashboard &nbsp; <span style="opacity:.75">|</span> &nbsp; {date_min:%b %Y} — {date_max:%b %Y}</p>
</div>
""", unsafe_allow_html=True)

if page == "Executive Overview":
    st.markdown('<div class="section-title">Executive overview</div><div class="section-sub">A snapshot of sales performance across the historical Walmart dataset.</div>', unsafe_allow_html=True)
    cols = st.columns(4)
    with cols[0]: metric_card("TOTAL WEEKLY SALES", money_short(total_sales), f"{total_sales:,.2f} summed across records")
    with cols[1]: metric_card("STORES ANALYZED", f"{store_count}", "Unique store locations")
    with cols[2]: metric_card("DEPARTMENTS", f"{dept_count}", "Unique departments")
    with cols[3]: metric_card("SALES RECORDS", f"{record_count:,}", "Store × department × week rows")

    left, right = st.columns([1.35, 1])
    with left:
        st.markdown('<div class="section-title">Sales trend</div><div class="section-sub">Weekly sales aggregated across all stores and departments.</div>', unsafe_allow_html=True)
        fig = px.line(weekly, x="Date", y="Weekly_Sales", template="plotly_white")
        fig.update_traces(line=dict(color="#16734a", width=2.5), hovertemplate="%{x|%d %b %Y}<br>Sales: $%{y:,.0f}<extra></extra>")
        fig.update_layout(margin=dict(l=5,r=5,t=10,b=5), height=350, xaxis_title="", yaxis_title="Total weekly sales")
        st.plotly_chart(fig, use_container_width=True)
    with right:
        st.markdown('<div class="section-title">Top 5 stores</div><div class="section-sub">Ranked by total recorded weekly sales.</div>', unsafe_allow_html=True)
        top = store_sales.head(5).sort_values("Weekly_Sales")
        fig = px.bar(top, x="Weekly_Sales", y=top["Store"].astype(str), orientation="h", template="plotly_white",
                     color="Weekly_Sales", color_continuous_scale=["#b9dfc9", "#176443"])
        fig.update_layout(showlegend=False, coloraxis_showscale=False, height=350, margin=dict(l=5,r=5,t=10,b=5), xaxis_title="Total sales", yaxis_title="Store")
        st.plotly_chart(fig, use_container_width=True)

    st.markdown('<div class="section-title">Business highlights</div>', unsafe_allow_html=True)
    best_store = store_sales.iloc[0]
    best_dept = dept_sales.iloc[0]
    c1, c2, c3 = st.columns(3)
    with c1: st.markdown(f'<div class="panel"><span class="pill">TOP STORE</span><h2>Store {int(best_store.Store)}</h2><p>{money_short(best_store.Weekly_Sales)} in summed weekly sales</p></div>', unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="panel"><span class="pill">TOP DEPARTMENT</span><h2>Dept {int(best_dept.Dept)}</h2><p>{money_short(best_dept.Weekly_Sales)} in summed weekly sales</p></div>', unsafe_allow_html=True)
    with c3:
        holiday_mean = holiday.loc[holiday["Holiday_Label"] == "Holiday", "Average_Sales"]
        non_mean = holiday.loc[holiday["Holiday_Label"] == "Non-holiday", "Average_Sales"]
        if len(holiday_mean) and len(non_mean):
            delta = (holiday_mean.iloc[0] / non_mean.iloc[0] - 1) * 100
            msg = f"{delta:+.1f}% vs non-holiday average"
        else: msg = "Compare holiday and non-holiday weeks"
        st.markdown(f'<div class="panel"><span class="pill">HOLIDAY PATTERN</span><h2>Seasonality</h2><p>{msg}</p></div>', unsafe_allow_html=True)

elif page == "Sales Explorer":
    st.markdown('<div class="section-title">Sales explorer</div><div class="section-sub">Filter historical sales records and inspect the underlying data.</div>', unsafe_allow_html=True)
    a, b, c = st.columns(3)
    with a:
        selected_stores = st.multiselect("Stores", sorted(df.Store.unique()), default=[])
    with b:
        selected_depts = st.multiselect("Departments", sorted(df.Dept.unique()), default=[])
    with c:
        holiday_options = st.multiselect("Week type", sorted(df.Holiday_Label.unique()), default=[])
    filtered = df.copy()
    if selected_stores: filtered = filtered[filtered.Store.isin(selected_stores)]
    if selected_depts: filtered = filtered[filtered.Dept.isin(selected_depts)]
    if holiday_options: filtered = filtered[filtered.Holiday_Label.isin(holiday_options)]
    m1, m2, m3 = st.columns(3)
    with m1: st.metric("Filtered sales", money_short(filtered.Weekly_Sales.sum()))
    with m2: st.metric("Records", f"{len(filtered):,}")
    with m3: st.metric("Average sales / record", f"${filtered.Weekly_Sales.mean():,.2f}" if len(filtered) else "$0")
    st.dataframe(filtered[["Store","Dept","Date","Weekly_Sales","IsHoliday"]].sort_values("Date", ascending=False), use_container_width=True, hide_index=True)
    st.download_button("Download filtered records", filtered.to_csv(index=False).encode(), "walmart_filtered_sales.csv", "text/csv")

elif page == "Store & Department":
    st.markdown('<div class="section-title">Store & department performance</div><div class="section-sub">Compare the highest-performing stores and departments.</div>', unsafe_allow_html=True)
    tab1, tab2 = st.tabs(["Store ranking", "Department ranking"])
    with tab1:
        fig = px.bar(store_sales.head(15).sort_values("Weekly_Sales"), x="Weekly_Sales", y=store_sales.head(15).sort_values("Weekly_Sales")["Store"].astype(str),
                     orientation="h", template="plotly_white", color="Weekly_Sales", color_continuous_scale=["#b9dfc9","#176443"])
        fig.update_layout(coloraxis_showscale=False, height=520, xaxis_title="Total sales", yaxis_title="Store", yaxis_title_text="Store")
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(store_sales.head(15).rename(columns={"Weekly_Sales":"Total_Sales"}), use_container_width=True, hide_index=True)
    with tab2:
        fig = px.bar(dept_sales.head(15).sort_values("Weekly_Sales"), x="Weekly_Sales", y=dept_sales.head(15).sort_values("Weekly_Sales")["Dept"].astype(str),
                     orientation="h", template="plotly_white", color="Weekly_Sales", color_continuous_scale=["#b9dfc9","#176443"])
        fig.update_layout(coloraxis_showscale=False, height=520, xaxis_title="Total sales", yaxis_title="Department")
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(dept_sales.head(15).rename(columns={"Weekly_Sales":"Total_Sales"}), use_container_width=True, hide_index=True)

elif page == "Holiday Insights":
    st.markdown('<div class="section-title">Holiday insights</div><div class="section-sub">Compare average sales per record for holiday and non-holiday weeks.</div>', unsafe_allow_html=True)
    fig = px.bar(holiday, x="Holiday_Label", y="Average_Sales", color="Holiday_Label",
                 color_discrete_map={"Holiday":"#e4a93a","Non-holiday":"#176443","Unknown":"#8c9891"},
                 template="plotly_white", text_auto=".3s")
    fig.update_layout(showlegend=False, height=400, xaxis_title="", yaxis_title="Average sales per record")
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(holiday, use_container_width=True, hide_index=True)
    st.info("This compares average sales per store-department-week record. Total holiday sales alone are not a fair comparison because the groups contain different numbers of records.")

elif page == "ML Prediction":
    st.markdown('<div class="section-title">Spark MLlib prediction results</div><div class="section-sub">Enter the evaluation metrics from your completed Spark notebook. The app displays the saved model results; it does not retrain Spark here.</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        rmse = st.number_input("RMSE", min_value=0.0, value=21765.638806249888, step=100.0, format="%.2f")
    with c2:
        r2 = st.number_input("R² score", min_value=-10.0, max_value=1.0, value=0.08435788301150993, step=0.01, format="%.4f")
    m1, m2 = st.columns(2)
    with m1: metric_card("ROOT MEAN SQUARED ERROR", f"{rmse:,.2f}", "Lower is generally better")
    with m2: metric_card("R-SQUARED", f"{r2:.4f}", f"{r2*100:.1f}% of test-set variance explained (approx.)")
    if r2 < 0.2:
        st.warning("The current model has a weak fit. It is suitable as a basic MLlib implementation demonstration, but should not be presented as an accurate production forecast.")
    st.markdown("#### Example predictions")
    st.caption("These are not live model predictions. Upload or export your Spark prediction results if you want to show actual predicted-vs-actual rows here.")
    st.markdown('<div class="panel"><b>Model workflow</b><br>Feature selection → VectorAssembler → Linear Regression → Test split → RMSE and R² evaluation</div>', unsafe_allow_html=True)

elif page == "Hadoop Pipeline":
    st.markdown('<div class="section-title">Hadoop processing pipeline</div><div class="section-sub">A demonstration view of the HDFS and Java MapReduce work completed in your separate Colab notebook.</div>', unsafe_allow_html=True)
    stages = st.columns(4)
    labels = [
        ("01", "HDFS", "train.csv stored at /walmart/train.csv"),
        ("02", "Mapper", "Emit (Store, Weekly_Sales)"),
        ("03", "Shuffle & Sort", "Group sales values by Store"),
        ("04", "Reducer", "Sum sales and write output to HDFS"),
    ]
    for col, (num, title, desc) in zip(stages, labels):
        with col:
            st.markdown(f'<div class="panel"><span class="pill">STEP {num}</span><h3>{title}</h3><p>{desc}</p></div>', unsafe_allow_html=True)
    st.markdown("#### MapReduce results")
    if mr_upload is not None:
        text = mr_upload.getvalue().decode("utf-8", errors="replace")
        mr_df = parse_mapreduce(text)
        if mr_df.empty:
            st.warning("No rows were parsed. Upload the plain text content of part-r-00000, one Store ID and sales total per line.")
        else:
            st.success(f"Loaded {len(mr_df)} store totals from your MapReduce output.")
            fig = px.bar(mr_df.sort_values("Total_Sales").tail(15), x="Total_Sales", y=mr_df.sort_values("Total_Sales").tail(15)["Store"].astype(str),
                         orientation="h", template="plotly_white", color="Total_Sales", color_continuous_scale=["#b9dfc9","#176443"])
            fig.update_layout(coloraxis_showscale=False, height=500, xaxis_title="Total sales", yaxis_title="Store")
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(mr_df.sort_values("Total_Sales", ascending=False), use_container_width=True, hide_index=True)
            st.download_button("Download parsed MapReduce results", mr_df.to_csv(index=False).encode(), "walmart_mapreduce_results.csv", "text/csv")
    else:
        st.info("To display actual Hadoop output, download `/walmart/output/part-r-00000` from HDFS in your Hadoop notebook and upload that text file using the sidebar.")
    st.markdown("#### Technology roles")
    tech = pd.DataFrame([
        ["HDFS", "Distributed file storage", "Implemented in Hadoop notebook"],
        ["Java MapReduce", "Batch aggregation by store", "Implemented in Hadoop notebook"],
        ["Apache Spark", "Sales analytics and MLlib model", "Implemented in Spark notebook"],
        ["Kafka / Cassandra / Hive / YARN", "Shown in the case-study architecture", "Discussed, not deployed in this prototype"],
    ], columns=["Technology", "Role", "Project status"])
    st.dataframe(tech, use_container_width=True, hide_index=True)

st.markdown("---")
st.caption("Walmart Big Data Analytics • Academic prototype • Historical data • Spark and Hadoop run in separate notebooks.")
