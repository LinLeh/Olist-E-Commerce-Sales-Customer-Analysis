"""Olist E-Commerce Dashboard.

Run:  streamlit run app.py
The dashboard reads the clean data saved by olist_analysis.ipynb (data/*.csv).
"""
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Olist E-Commerce Dashboard", page_icon="🛒", layout="wide")

DATA_DIR = Path(__file__).parent / "data"
PURPLE, PINK = "#7C3AED", "#EC4899"
DARK = "linear-gradient(180deg, #1E1238 0%, #2A1350 70%, #3A1258 100%)"  # sidebar and card colour
WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

# Number cards use the same colour as the sidebar
st.markdown(f"""
<style>
[data-testid="stSidebar"] {{ background: {DARK}; }}
[data-testid="stMetric"] {{ background: {DARK}; border-radius: 12px; padding: 14px 16px; }}
[data-testid="stMetricLabel"] p {{ color: #C4B5FD; font-weight: 600; }}
[data-testid="stMetricValue"] {{ color: #FFFFFF; font-size: 1.6rem; }}
.block-container {{ padding-top: 2rem; }}
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------- helpers
def money(value):
    """15371741 -> 'R$ 15.37M'"""
    if value >= 1_000_000:
        return f"R$ {value / 1_000_000:,.2f}M"
    if value >= 1_000:
        return f"R$ {value / 1_000:,.1f}K"
    return f"R$ {value:,.0f}"


def md_money(value):
    # In markdown, two "$" signs would turn the text into a math formula, so escape them
    return money(value).replace("$", "\\$")


def show(fig, height=380):
    fig.update_layout(height=height, margin=dict(l=10, r=10, t=50, b=10))
    st.plotly_chart(fig)


# ---------------------------------------------------------------- data
@st.cache_data
def load_data():
    orders = pd.read_csv(DATA_DIR / "orders_clean.csv", parse_dates=["order_purchase_timestamp"])
    items = pd.read_csv(DATA_DIR / "items_clean.csv")
    payments = pd.read_csv(DATA_DIR / "payments_clean.csv")

    orders["purchase_month"] = orders["order_purchase_timestamp"].dt.to_period("M").dt.to_timestamp()
    orders["weekday"] = orders["order_purchase_timestamp"].dt.day_name()
    orders["hour"] = orders["order_purchase_timestamp"].dt.hour
    return orders, items, payments


if not (DATA_DIR / "orders_clean.csv").exists():
    st.error("Clean data not found. Open olist_analysis.ipynb and run all cells first.")
    st.stop()

orders, items, payments = load_data()

# ---------------------------------------------------------------- sidebar filters
st.sidebar.title("Filters")
first_day = orders["order_purchase_timestamp"].min().date()
last_day = orders["order_purchase_timestamp"].max().date()
dates = st.sidebar.date_input("Order date", value=(first_day, last_day), min_value=first_day,
                              max_value=last_day, format="DD/MM/YYYY")
states = st.sidebar.multiselect("Customer state", sorted(orders["customer_state"].unique()),
                                placeholder="All states")
st.sidebar.caption("Data: delivered orders, Jan 2017 – Aug 2018. Revenue = product price + delivery fee.")

if len(dates) != 2:
    st.info("Please choose an end date.")
    st.stop()

start, end = dates
keep = (orders["order_purchase_timestamp"].dt.date >= start) & (orders["order_purchase_timestamp"].dt.date <= end)
if states:
    keep &= orders["customer_state"].isin(states)

df = orders[keep]
df_items = items[items["order_id"].isin(df["order_id"])]
df_payments = payments[payments["order_id"].isin(df["order_id"])]

if df.empty:
    st.warning("No orders match these filters.")
    st.stop()

# ---------------------------------------------------------------- header and KPI cards
st.title("🛒 Olist E-Commerce Dashboard")
st.caption("Sales and customer analysis of the Olist Brazilian marketplace · "
           "[Dataset on Kaggle](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce)")

revenue = df["order_value"].sum()
n_orders = len(df)
n_customers = df["customer_unique_id"].nunique()
late_rate = df["is_late"].mean()

c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("Revenue", money(revenue))
c2.metric("Orders", f"{n_orders:,}")
c3.metric("Customers", f"{n_customers:,}")
c4.metric("Average order", money(revenue / n_orders))
c5.metric("Average review", f"{df['review_score'].mean():.2f} ★")
c6.metric("Late deliveries", f"{late_rate:.1%}")

tab_sales, tab_products, tab_customers, tab_delivery, tab_payments, tab_insights = st.tabs(
    ["📈 Sales", "📦 Products", "🗺️ Customers", "🚚 Delivery & Reviews", "💳 Payments", "💡 Insights"])

# ---------------------------------------------------------------- sales
with tab_sales:
    monthly = df.groupby("purchase_month").agg(revenue=("order_value", "sum"),
                                               orders=("order_id", "count")).reset_index()
    fig = px.bar(monthly, x="purchase_month", y="revenue", title="Monthly revenue",
                 labels={"purchase_month": "", "revenue": "Revenue (R$)"}, hover_data={"orders": ":,"})
    fig.update_traces(marker_color=PURPLE)
    show(fig)

    left, right = st.columns(2)
    by_weekday = df["weekday"].value_counts().reindex(WEEKDAYS, fill_value=0).reset_index()
    fig = px.bar(by_weekday, x="weekday", y="count", title="Orders by day of the week",
                 labels={"weekday": "", "count": "Orders"})
    fig.update_traces(marker_color=PURPLE)
    with left:
        show(fig, 340)

    by_hour = df["hour"].value_counts().reindex(range(24), fill_value=0).reset_index()
    fig = px.bar(by_hour, x="hour", y="count", title="Orders by hour of the day",
                 labels={"hour": "Hour", "count": "Orders"})
    fig.update_traces(marker_color=PINK)
    with right:
        show(fig, 340)

# ---------------------------------------------------------------- products
with tab_products:
    category_sales = (df_items.groupby("category")
                      .agg(revenue=("item_value", "sum"), orders=("order_id", "nunique"), avg_price=("price", "mean"))
                      .sort_values("revenue", ascending=False).reset_index())
    category_sales["share_%"] = category_sales["revenue"] / category_sales["revenue"].sum() * 100

    left, right = st.columns(2)
    top = category_sales.head(10).sort_values("revenue")
    fig = px.bar(top, x="revenue", y="category", orientation="h", title="Top 10 categories by revenue",
                 labels={"revenue": "Revenue (R$)", "category": ""})
    fig.update_traces(marker_color=PURPLE)
    with left:
        show(fig, 420)

    top = category_sales.sort_values("orders", ascending=False).head(10).sort_values("orders")
    fig = px.bar(top, x="orders", y="category", orientation="h", title="Top 10 categories by orders",
                 labels={"orders": "Orders", "category": ""})
    fig.update_traces(marker_color=PINK)
    with right:
        show(fig, 420)

    with st.expander("See all categories"):
        st.dataframe(category_sales, hide_index=True, width="stretch",
                     column_config={"category": "Category",
                                    "revenue": st.column_config.NumberColumn("Revenue", format="R$ %.0f"),
                                    "orders": "Orders",
                                    "avg_price": st.column_config.NumberColumn("Average price", format="R$ %.2f"),
                                    "share_%": st.column_config.NumberColumn("Share of revenue", format="%.1f%%")})

# ---------------------------------------------------------------- customers
with tab_customers:
    state_sales = (df.groupby("customer_state")
                   .agg(revenue=("order_value", "sum"), customers=("customer_unique_id", "nunique"))
                   .sort_values("revenue", ascending=False).reset_index())

    left, right = st.columns([2, 1])
    fig = px.bar(state_sales.head(10), x="customer_state", y="revenue", title="Top 10 states by revenue",
                 labels={"customer_state": "State", "revenue": "Revenue (R$)"}, hover_data={"customers": ":,"})
    fig.update_traces(marker_color=PURPLE)
    with left:
        show(fig)

    orders_per_customer = df.groupby("customer_unique_id")["order_id"].count()
    repeat = pd.DataFrame({"type": ["1 order", "2+ orders"],
                           "customers": [(orders_per_customer == 1).sum(), (orders_per_customer > 1).sum()]})
    fig = px.pie(repeat, names="type", values="customers", title="Customers by number of orders", hole=0.5,
                 color_discrete_sequence=[PURPLE, PINK])
    with right:
        show(fig)

# ---------------------------------------------------------------- delivery and reviews
with tab_delivery:
    d1, d2, d3 = st.columns(3)
    d1.metric("Average delivery time", f"{df['delivery_days'].mean():.1f} days")
    d2.metric("Average promised time", f"{df['promised_days'].mean():.1f} days")
    d3.metric("Late deliveries", f"{late_rate:.1%}")

    left, right = st.columns(2)
    fig = px.histogram(df, x=df["delivery_days"].clip(upper=60), nbins=60, title="Delivery time (60+ days grouped)",
                       labels={"x": "Days from purchase to delivery"})
    fig.update_traces(marker_color=PURPLE)
    fig.update_layout(yaxis_title="Orders")
    with left:
        show(fig)

    state_days = (df.groupby("customer_state")["delivery_days"].mean().sort_values(ascending=False)
                  .reset_index())
    fig = px.bar(state_days, x="customer_state", y="delivery_days", title="Average delivery days by state",
                 labels={"customer_state": "State", "delivery_days": "Days"})
    fig.update_traces(marker_color=PINK)
    with right:
        show(fig)

    left, right = st.columns(2)
    status = df.assign(status=df["is_late"].map({False: "On time", True: "Late"}))
    late_vs = status.groupby("status")["review_score"].mean().reindex(["On time", "Late"]).dropna().reset_index()
    fig = px.bar(late_vs, x="status", y="review_score", title="Average review: on time vs late",
                 labels={"status": "", "review_score": "Average review"}, text_auto=".2f",
                 color="status", color_discrete_map={"On time": PURPLE, "Late": PINK})
    fig.update_layout(showlegend=False, yaxis_range=[0, 5])
    with left:
        show(fig)

    groups = pd.cut(df["delivery_days"], bins=[-1, 7, 14, 21, 30, 1000],
                    labels=["0-7 days", "8-14 days", "15-21 days", "22-30 days", "31+ days"])
    by_time = df.groupby(groups, observed=True)["review_score"].mean().reset_index()
    fig = px.bar(by_time, x="delivery_days", y="review_score", title="Average review by delivery time",
                 labels={"delivery_days": "", "review_score": "Average review"}, text_auto=".2f")
    fig.update_traces(marker_color=PURPLE)
    fig.update_layout(yaxis_range=[0, 5])
    with right:
        show(fig)

# ---------------------------------------------------------------- payments
with tab_payments:
    payment_share = (df_payments.groupby("payment_type")["order_id"].nunique()
                     / df_payments["order_id"].nunique() * 100).sort_values().reset_index(name="share")

    left, right = st.columns(2)
    fig = px.bar(payment_share, x="share", y="payment_type", orientation="h", title="Share of orders by payment type",
                 labels={"share": "% of orders", "payment_type": ""}, text_auto=".1f")
    fig.update_traces(marker_color=PURPLE)
    with left:
        show(fig)

    cards = df_payments[df_payments["payment_type"] == "Credit card"]
    installments = (cards["payment_installments"].clip(upper=10).value_counts(normalize=True).sort_index() * 100
                    ).reset_index(name="share")
    fig = px.bar(installments, x="payment_installments", y="share",
                 title="Credit card payments by installments (10 = 10+)",
                 labels={"payment_installments": "Installments", "share": "% of card payments"})
    fig.update_traces(marker_color=PINK)
    fig.update_xaxes(dtick=1)
    with right:
        show(fig)

# ---------------------------------------------------------------- insights
with tab_insights:
    st.subheader("Key findings")
    st.caption("These numbers update with the filters.")

    best = monthly.loc[monthly["revenue"].idxmax()]
    top_category = category_sales.iloc[0]
    top3_states = state_sales.head(3)
    repeat_rate = (orders_per_customer > 1).mean()
    findings = [
        f"📈 **Best month:** {best['purchase_month']:%B %Y} with {md_money(best['revenue'])} in revenue.",
        f"📦 **Best category:** {top_category['category']} ({top_category['share_%']:.0f}% of revenue). "
        f"The top 10 categories make {category_sales.head(10)['share_%'].sum():.0f}% of revenue.",
        f"🗺️ **Top states:** {', '.join(top3_states['customer_state'])} make "
        f"{top3_states['revenue'].sum() / state_sales['revenue'].sum():.0%} of revenue.",
        f"🔁 **Repeat customers:** only {repeat_rate:.1%} of customers ordered more than once.",
        f"🚚 **Delivery:** orders take {df['delivery_days'].mean():.0f} days on average and "
        f"{late_rate:.1%} arrive late.",
    ]
    if len(late_vs) == 2:
        findings.append(f"⭐ **Reviews:** late orders get {late_vs['review_score'].iloc[1]:.2f} ★, "
                        f"on-time orders get {late_vs['review_score'].iloc[0]:.2f} ★.")
    if len(payment_share):
        top_payment = payment_share.iloc[-1]
        findings.append(f"💳 **Payments:** {top_payment['payment_type']} is used in {top_payment['share']:.0f}% of orders.")
    for finding in findings:
        st.markdown("- " + finding)

    st.subheader("Recommendations")
    st.markdown("""
1. **Improve delivery first.** Late orders get much lower reviews. Set a shipping time limit for sellers and
   tell customers early when an order will be late.
2. **Get closer to far-away customers.** Customers in the North and Northeast wait the longest, because most
   sellers are in São Paulo. Find sellers or warehouses in those regions.
3. **Bring customers back.** Very few customers buy again. Try follow-up emails, a discount on the second
   order and a loyalty programme.
4. **Prepare for Black Friday.** November is the best month. Plan stock, sellers and delivery early.
5. **Protect the top categories.** A few categories make most of the revenue, so keep them in stock and
   promote them.
6. **Keep installments and boleto.** Most customers pay by credit card, often in installments, and boleto
   helps customers without a card.
""")
    st.caption("Full analysis: olist_analysis.ipynb")
