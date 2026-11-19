from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

DATA = Path(__file__).resolve().parent.parent / "dashboard" / "data"
LIGHT_BLUE = "#3B8BF5"
DARK_BLUE = "#1F2A9C"
ORANGE = "#E07B39"
PURPLE = "#7B2D8E"

MODEL = "Model: (1-p) x order value"
ORDER_ONLY = "Highest order value only"
RFM_RANK = "RFM rank: (1-score) x order value"
CEILING = "Hindsight ceiling"
STRATEGY_COLORS = {
    MODEL: DARK_BLUE,
    "Highest past spend": LIGHT_BLUE,
    "Random": ORANGE,
    "RFM at-risk rule": PURPLE,
}

st.set_page_config(page_title="Customer Retention & Revenue Intelligence", layout="wide")


@st.cache_data
def load(name):
    return pd.read_csv(DATA / name)


def short_date(d):
    d = pd.Timestamp(d)
    return f"{d.day} {d:%b %Y}"


# ---------------------------------------------------------------- page 1
def revenue_overview():
    monthly = load("monthly_revenue.csv")
    monthly["month"] = pd.to_datetime(monthly["month"])
    customers = load("customers_segments.csv")
    conc = load("revenue_concentration.csv")

    st.header("Revenue overview")

    c1, c2, c3 = st.columns(3)
    c1.metric("Total net revenue", f"{monthly['net_revenue'].sum() / 1e6:.2f}M")
    c2.metric("Total invoices", f"{monthly['invoices'].sum():,}")
    c3.metric("Total customers", f"{customers['customer_id'].nunique():,}")

    complete = monthly[~monthly["partial_month"]]

    left, right = st.columns(2)

    with left:
        fig1 = px.line(complete, x="month", y="net_revenue", title="Monthly net revenue")
        fig1.update_traces(line_color=LIGHT_BLUE)
        st.plotly_chart(fig1)

    with right:
        fig2 = make_subplots(specs=[[{"secondary_y": True}]])
        fig2.add_trace(
            go.Bar(x=conc["decile"], y=conc["pct_revenue"], name="Revenue share",
                   marker_color=LIGHT_BLUE),
            secondary_y=False,
        )
        fig2.add_trace(
            go.Scatter(x=conc["decile"], y=conc["cumulative_pct"], name="Cumulative share",
                       line=dict(color=DARK_BLUE)),
            secondary_y=True,
        )
        fig2.update_layout(
            title="Revenue concentration by customer decile",
            legend=dict(orientation="h", y=-0.25),
        )
        fig2.update_xaxes(title_text="Customer decile (1 = top 10%)", dtick=1)
        fig2.update_yaxes(range=[0, 100], ticksuffix="%", secondary_y=False)
        fig2.update_yaxes(range=[0, 100], ticksuffix="%", secondary_y=True)
        st.plotly_chart(fig2)


# ---------------------------------------------------------------- page 2
def customer_segments():
    seg = load("segment_summary.csv").sort_values("sort_order")
    order = seg["segment"].tolist()

    st.header("Customer segments")

    left, right = st.columns(2)

    with left:
        long = seg.melt(
            id_vars="segment",
            value_vars=["pct_customers", "pct_revenue"],
            var_name="measure",
            value_name="pct",
        )
        long["measure"] = long["measure"].map(
            {"pct_customers": "Share of customers", "pct_revenue": "Share of revenue"}
        )
        fig1 = px.bar(
            long, y="segment", x="pct", color="measure", barmode="group", orientation="h",
            category_orders={"segment": order},
            color_discrete_map={"Share of customers": LIGHT_BLUE, "Share of revenue": DARK_BLUE},
            title="Share of customers vs share of revenue by segment",
        )
        fig1.update_traces(texttemplate="%{x:.1f}%", textposition="outside")
        fig1.update_yaxes(categoryorder="array", categoryarray=order[::-1], title_text="")
        fig1.update_xaxes(ticksuffix="%", title_text="", range=[0, long["pct"].max() * 1.15])        
        fig1.update_layout(legend=dict(orientation="h", y=-0.15, title_text=""))
        st.plotly_chart(fig1)

    with right:
        fig2 = px.bar(
            seg, x="segment", y="revenue_per_customer",
            category_orders={"segment": order},
            title="Revenue per customer by segment",
        )
        fig2.update_traces(marker_color=LIGHT_BLUE, texttemplate="%{y:,.0f}", textposition="outside")
        fig2.update_xaxes(title_text="")
        fig2.update_yaxes(title_text="")
        st.plotly_chart(fig2)

    st.subheader("Segment summary and suggested actions")
    table = seg[["segment", "customers", "revenue_per_customer", "priority", "suggested_action"]]
    table = table.rename(columns={
        "segment": "Segment",
        "customers": "Customers",
        "revenue_per_customer": "Revenue per customer",
        "priority": "Priority",
        "suggested_action": "Suggested action",
    })
    st.dataframe(table, hide_index=True)

    s = seg.set_index("segment")
    st.markdown(
        f"**Takeaway:** Champions are {s.loc['Champions', 'pct_customers']:.1f}% of customers "
        f"but {s.loc['Champions', 'pct_revenue']:.1f}% of revenue. Lapsed customers are "
        f"{s.loc['Lapsed', 'pct_customers']:.1f}% of customers but only "
        f"{s.loc['Lapsed', 'pct_revenue']:.1f}% of revenue, so retention effort should go to "
        f"Champions and the high-value \"Cannot lose\" group first."
    )


# ---------------------------------------------------------------- page 3
def cohort_retention():
    df = load("cohort_retention.csv")
    df["cohort_month"] = pd.to_datetime(df["cohort_month"])
    df = df[(~df["inflated_cohort"]) & (~df["partial_period"])]

    pivot = df.pivot(
        index="cohort_month", columns="month_index", values="retention_pct"
    ).sort_index()
    labels = [d.strftime("%b %Y") for d in pivot.index]
    text = [["" if pd.isna(v) else f"{v:.0f}%" for v in row] for row in pivot.values]

    st.header("Cohort retention")

    fig = go.Figure(
        go.Heatmap(
            z=pivot.values,
            x=pivot.columns.tolist(),
            y=labels,
            text=text,
            texttemplate="%{text}",
            colorscale=[[0, "#F2F7FD"], [1, "#4F86D4"]],
            zmin=0,
            zmax=50,
            showscale=False,
            xgap=1,
            ygap=1,
            hoverongaps=False,
        )
    )
    fig.update_yaxes(autorange="reversed", title_text="Cohort (first purchase month)")
    fig.update_xaxes(title_text="Months since first purchase", dtick=1, side="top")
    fig.update_layout(title="Monthly cohort retention (% of cohort still buying)", height=720)
    st.plotly_chart(fig)

    st.caption(
        "December 2009 cohort and incomplete final months excluded. "
        "The colour scale stops at 50%, so the month-0 column (always 100%) "
        "doesn't wash out the other cells."
    )


# ---------------------------------------------------------------- page 4
def net_by_strategy(df, title):
    df = df.copy()
    df["cutoff"] = pd.to_datetime(df["cutoff"])
    df["Cutoff"] = df["cutoff"].map(short_date)
    cutoffs = [short_date(c) for c in sorted(df["cutoff"].unique())]
    order = df.groupby("strategy")["net"].max().sort_values(ascending=False).index.tolist()

    fig = px.bar(
        df, y="strategy", x="net", color="Cutoff", barmode="group", orientation="h",
        category_orders={"strategy": order, "Cutoff": cutoffs},
        color_discrete_sequence=[LIGHT_BLUE, DARK_BLUE],
        title=title,
    )
    fig.update_traces(texttemplate="%{x:,.0f}", textposition="outside")
    fig.update_yaxes(categoryorder="array", categoryarray=order[::-1], title_text="")
    fig.update_xaxes(title_text="Net gain", range=[0, df["net"].max() * 1.15])    
    fig.update_layout(legend=dict(orientation="h", y=-0.2, title_text=""))
    return fig


def retention_decision():
    summ = load("backtest_summary.csv")
    ctrl = load("backtest_controls.csv")

    st.header("Retention decision")

    left, right = st.columns(2)
    with left:
        st.plotly_chart(net_by_strategy(summ, "Net gain by strategy (500 contacted, 5% response)"))
        st.caption("Hindsight ceiling = best possible, not a real strategy.")
    with right:
        st.plotly_chart(net_by_strategy(ctrl, "Controls: does the model beat simple rules?"))

    ctrl["cutoff"] = pd.to_datetime(ctrl["cutoff"])
    net = ctrl.pivot(index="strategy", columns="cutoff", values="net")

    lines = []
    for c in sorted(net.columns):
        model, ordv, rfm = net.loc[MODEL, c], net.loc[ORDER_ONLY, c], net.loc[RFM_RANK, c]
        lines.append(
            f"- **{short_date(c)} cutoff:** the model earned {model:,.0f} net, "
            f"{model / ordv - 1:.0%} more than ranking by order value alone ({ordv:,.0f}) "
            f"and {model / rfm - 1:.1%} more than the RFM rank rule ({rfm:,.0f})."
        )

    st.markdown(
        "**Takeaway:** most of the gain comes from ranking by order value.\n\n"
        + "\n".join(lines)
        + "\n\nA simple rule captures nearly all the benefit. "
        "The Hindsight ceiling is the best possible outcome, not a real strategy."
    )


# ---------------------------------------------------------------- page 5
def sensitivity():
    sens = load("backtest_sensitivity.csv")
    sens["cutoff"] = pd.to_datetime(sens["cutoff"])
    cost = load("backtest_cost_sensitivity.csv")
    summ = load("backtest_summary.csv")

    st.header("Sensitivity")

    cutoffs = sens["cutoff"].drop_duplicates().sort_values().tolist()
    targets = sorted(sens["n_target"].unique().tolist())
    rates = sorted(cost["response_rate"].unique().tolist())

    left, right = st.columns(2)

    with left:
        f1, f2 = st.columns(2)
        cutoff = f1.radio("Cutoff date", cutoffs, format_func=short_date, horizontal=True)
        n_target = f2.radio(
            "Customers contacted", targets,
            index=targets.index(500) if 500 in targets else 0, horizontal=True,
        )
        d = sens[
            (sens["cutoff"] == cutoff)
            & (sens["n_target"] == n_target)
            & (sens["strategy"] != CEILING)
        ].sort_values("response_rate")
        d["Response rate"] = d["response_rate"].map(lambda r: f"{r:.0%}")
        fig1 = px.line(
            d, x="Response rate", y="net", color="strategy", markers=True,
            color_discrete_map=STRATEGY_COLORS, title="Net gain by response rate",
        )
        fig1.update_xaxes(
            type="category",
            categoryorder="array",
            categoryarray=[f"{r:.0%}" for r in sorted(d["response_rate"].unique())],
        )
        fig1.update_yaxes(title_text="Net gain")
        fig1.update_layout(legend=dict(orientation="h", y=-0.25, title_text=""))
        st.plotly_chart(fig1)

    with right:
        rate = st.radio(
            "Response rate", rates,
            index=rates.index(0.05) if 0.05 in rates else 0,
            format_func=lambda r: f"{r:.0%}", horizontal=True,
        )
        c = cost[(cost["response_rate"] == rate) & (cost["strategy"] != CEILING)]
        c = c.sort_values("cost_per_contact").copy()
        c["Cost per contact"] = c["cost_per_contact"].map(lambda v: f"£{v:g}")
        # TODO: confirm the cutoff and number contacted behind this table in the
        # notebook, then add them to the title.
        fig2 = px.line(
            c, x="Cost per contact", y="net", color="strategy", markers=True,
            color_discrete_map=STRATEGY_COLORS, title="Net gain by cost per contact",
        )
        fig2.update_xaxes(
            categoryorder="array",
            categoryarray=[f"£{v:g}" for v in sorted(c["cost_per_contact"].unique())],
        )
        fig2.add_hline(y=0, line_dash="dot", line_color="#999999")
        fig2.update_yaxes(title_text="Net gain")
        fig2.update_layout(legend=dict(orientation="h", y=-0.25, title_text=""))
        st.plotly_chart(fig2)

    top = c["cost_per_contact"].max()
    at_top = c[c["cost_per_contact"] == top]
    model_net = at_top.loc[at_top["strategy"] == MODEL, "net"].iloc[0]
    others = at_top.loc[at_top["strategy"] != MODEL, "net"]
    if others.max() < 0:
        others_text = "while the other strategies lose money"
    else:
        others_text = f"while the best other strategy nets {others.max():,.0f}"

    be = summ.loc[summ["strategy"] == MODEL, "break_even_response"]
    st.markdown(
        f"**Takeaway:** at £{top:g} per contact and {rate:.0%} response, the model nets about "
        f"{model_net:,.0f}, {others_text}. Break-even needs only about "
        f"{be.min():.2%}–{be.max():.2%} of contacted customers to respond."
    )


# ---------------------------------------------------------------- main
HOME = "Revenue overview"
PAGES = {
    HOME: revenue_overview,
    "Customer segments": customer_segments,
    "Cohort retention": cohort_retention,
    "Retention decision": retention_decision,
    "Sensitivity": sensitivity,
}
EXPLORE = {
    "Customer segments": "Who the customers are and what to do about each group",
    "Cohort retention": "How many customers from each month keep buying",
    "Retention decision": "Does model-based targeting beat simple rules?",
    "Sensitivity": "Does the campaign still pay off at lower response and higher cost?",
}

if "page" not in st.session_state:
    st.session_state.page = HOME


def go_to(name):
    st.session_state.page = name


st.title("Customer Retention & Revenue Intelligence")

if st.session_state.page == HOME:
    cols = st.columns(len(EXPLORE))
    for col, (name, blurb) in zip(cols, EXPLORE.items()):
        with col:
            st.button(f"{name} →", on_click=go_to, args=(name,), key=f"go_{name}")
            st.caption(blurb)
else:
    st.button("← Back to overview", on_click=go_to, args=(HOME,), key="back")

PAGES[st.session_state.page]()