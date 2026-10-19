
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st


# --------------------------------------------------
# 1. Configuration
# --------------------------------------------------

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
INVOICE_FILE = DATA_DIR / "invoices.csv"
BANK_FILE = DATA_DIR / "bank_transactions.csv"

REQUIRED_INVOICE_COLUMNS = {
    "invoice_id",
    "invoice_date",
    "customer_name",
    "amount",
    "currency",
    "payment_status",
    "paid_date",
}

REQUIRED_BANK_COLUMNS = {
    "transaction_id",
    "transaction_date",
    "description",
    "reference",
    "amount",
    "currency",
    "transaction_type",
}

st.set_page_config(
    page_title="Qawafel | Financing Insights",
    page_icon="📊",
    layout="wide",
)


# --------------------------------------------------
# 2. Data loading and normalization
# --------------------------------------------------

def normalize_invoices(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize invoice fields without hiding invalid records."""
    df = df.copy()

    df["invoice_id"] = df["invoice_id"].fillna("").astype(str).str.strip()
    df["customer_name"] = df["customer_name"].fillna("").astype(str).str.strip()
    df["currency"] = df["currency"].fillna("").astype(str).str.strip().str.upper()
    df["payment_status"] = (
        df["payment_status"].fillna("").astype(str).str.strip().str.lower()
    )

    df["invoice_date"] = pd.to_datetime(
        df["invoice_date"], errors="coerce"
    )
    df["paid_date"] = pd.to_datetime(
        df["paid_date"], errors="coerce"
    )
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce")

    return df


def normalize_bank_transactions(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize bank transaction fields."""
    df = df.copy()

    for column in ["transaction_id", "reference", "currency", "transaction_type"]:
        df[column] = df[column].fillna("").astype(str).str.strip()

    df["currency"] = df["currency"].str.upper()
    df["transaction_type"] = df["transaction_type"].str.lower()
    df["transaction_date"] = pd.to_datetime(
        df["transaction_date"], errors="coerce"
    )
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce")

    return df


def read_invoice_file(uploaded_file) -> pd.DataFrame:
    """Read a CSV or Excel invoice file and validate its columns."""
    if uploaded_file.name.lower().endswith(".csv"):
        raw_df = pd.read_csv(uploaded_file)
    else:
        raw_df = pd.read_excel(uploaded_file)

    missing = REQUIRED_INVOICE_COLUMNS - set(raw_df.columns)

    if missing:
        raise ValueError(
            "Missing required columns: " + ", ".join(sorted(missing))
        )

    return normalize_invoices(raw_df)


# --------------------------------------------------
# 3. Data quality checks
# --------------------------------------------------

def find_data_quality_issues(df: pd.DataFrame) -> pd.DataFrame:
    """Return invoice records that require human review."""
    issues = []

    duplicate_mask = (
        df["invoice_id"].ne("")
        & df["invoice_id"].duplicated(keep=False)
    )

    for index, row in df.iterrows():
        record_issues = []

        if pd.isna(row["invoice_date"]):
            record_issues.append("Missing or invalid invoice date")

        if pd.isna(row["amount"]):
            record_issues.append("Missing or invalid amount")
        elif row["amount"] <= 0:
            record_issues.append("Non-positive invoice amount")

        if not row["customer_name"]:
            record_issues.append("Missing customer name")

        if not row["invoice_id"]:
            record_issues.append("Missing invoice ID")

        if not row["currency"]:
            record_issues.append("Missing currency")

        if row["payment_status"] not in {"paid", "unpaid", "overdue"}:
            record_issues.append("Invalid payment status")

        if (
            row["payment_status"] == "paid"
            and pd.isna(row["paid_date"])
        ):
            record_issues.append("Paid invoice has no payment date")

        if duplicate_mask.iloc[index]:
            record_issues.append("Duplicate invoice ID — verify before counting")

        if record_issues:
            issues.append({
                "invoice_id": row["invoice_id"],
                "invoice_date": row["invoice_date"],
                "customer_name": row["customer_name"],
                "amount": row["amount"],
                "issues": "; ".join(record_issues),
            })

    return pd.DataFrame(
        issues,
        columns=[
            "invoice_id",
            "invoice_date",
            "customer_name",
            "amount",
            "issues",
        ],
    )


# --------------------------------------------------
# 4. Bank reconciliation
# --------------------------------------------------

def reconcile_invoices(
    invoices: pd.DataFrame,
    transactions: pd.DataFrame,
) -> pd.DataFrame:
    """
    Match an invoice to one bank credit using reference,
    amount, and currency. Ambiguous cases need human review.
    """
    results = []

    duplicate_ids = set(
        invoices.loc[
            invoices["invoice_id"].ne("")
            & invoices["invoice_id"].duplicated(keep=False),
            "invoice_id",
        ]
    )

    for _, invoice in invoices.iterrows():
        invoice_id = invoice["invoice_id"]
        invoice_amount = invoice["amount"]

        def add_result(
            status: str,
            reason: str,
            transaction_id: str = "",
            bank_amount=None,
        ):
            results.append({
                "invoice_id": invoice_id,
                "invoice_amount": invoice_amount,
                "currency": invoice["currency"],
                "bank_transaction_id": transaction_id,
                "bank_amount": bank_amount,
                "match_status": status,
                "review_reason": reason,
            })

        if not invoice_id:
            add_result("Needs Review", "Missing invoice ID")
            continue

        if invoice_id in duplicate_ids:
            add_result(
                "Needs Review",
                "Duplicate invoice ID — resolve before reconciliation",
            )
            continue

        if pd.isna(invoice_amount) or invoice_amount <= 0:
            add_result("Needs Review", "Missing or non-positive invoice amount")
            continue

        if pd.isna(invoice["invoice_date"]):
            add_result("Needs Review", "Missing or invalid invoice date")
            continue

        if not invoice["currency"]:
            add_result("Needs Review", "Missing invoice currency")
            continue

        candidates = transactions[
            (transactions["reference"] == invoice_id)
            & (transactions["currency"] == invoice["currency"])
            & (transactions["transaction_type"] == "credit")
            & transactions["amount"].notna()
            & (transactions["amount"] > 0)
        ]

        if candidates.empty:
            add_result(
                "Unmatched",
                "No positive bank credit found with matching reference and currency",
            )
            continue

        exact_matches = candidates[
            (candidates["amount"] - invoice_amount).abs() < 0.01
        ]

        if len(exact_matches) == 1:
            transaction = exact_matches.iloc[0]
            add_result(
                "Matched",
                "",
                str(transaction["transaction_id"]),
                float(transaction["amount"]),
            )
        elif len(exact_matches) > 1:
            add_result(
                "Needs Review",
                "Multiple bank credits match this invoice",
            )
        else:
            add_result(
                "Needs Review",
                "Reference found, but bank amount differs from invoice amount",
            )

    return pd.DataFrame(results)


# --------------------------------------------------
# 5. Application title and invoice input
# --------------------------------------------------

st.title("Qawafel Financing Insights")
st.caption(
    "Prototype for reviewing synthetic SME invoice data "
    "and preparing a financing package."
)

if not INVOICE_FILE.exists():
    st.error("Invoice dataset not found. Run generate_data.py first.")
    st.stop()

try:
    df = normalize_invoices(pd.read_csv(INVOICE_FILE))
except Exception as exc:
    st.error(f"Could not load the default invoice dataset: {exc}")
    st.stop()

st.subheader("Upload Invoice Data")

uploaded_file = st.file_uploader(
    "Upload an invoice file (CSV or Excel)",
    type=["csv", "xlsx"],
    help=(
        "Required columns: invoice_id, invoice_date, customer_name, "
        "amount, currency, payment_status, paid_date."
    ),
)

if uploaded_file is not None:
    try:
        df = read_invoice_file(uploaded_file)
        st.success(
            f"Loaded {len(df)} invoice records from {uploaded_file.name}."
        )
    except Exception as exc:
        st.error(f"Could not process the uploaded file: {exc}")
        st.stop()


# --------------------------------------------------
# 6. Eligible records and financial summary
# --------------------------------------------------

valid_amount_mask = df["amount"].notna() & (df["amount"] > 0)
valid_date_mask = df["invoice_date"].notna()
has_invoice_id = df["invoice_id"].ne("")
duplicate_extra_mask = (
    has_invoice_id & df["invoice_id"].duplicated(keep="first")
)

# Exclude invalid dates, invalid amounts, and repeated copies
# from the summary. The quality report retains all source rows.
eligible_mask = (
    valid_amount_mask
    & valid_date_mask
    & ~duplicate_extra_mask
)

analysis_df = df.loc[eligible_mask].copy()
issues_df = find_data_quality_issues(df)

st.sidebar.header("Filters")

all_statuses = sorted(
    status for status in df["payment_status"].dropna().unique() if status
)

selected_statuses = st.sidebar.multiselect(
    "Payment status",
    options=all_statuses,
    default=all_statuses,
)

filtered_df = analysis_df[
    analysis_df["payment_status"].isin(selected_statuses)
].copy()

total_invoiced = filtered_df["amount"].sum()
paid_amount = filtered_df.loc[
    filtered_df["payment_status"] == "paid", "amount"
].sum()
unpaid_amount = filtered_df.loc[
    filtered_df["payment_status"] == "unpaid", "amount"
].sum()
overdue_amount = filtered_df.loc[
    filtered_df["payment_status"] == "overdue", "amount"
].sum()

st.subheader("Financial Summary")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Eligible Invoiced Value", f"SAR {total_invoiced:,.0f}")
col2.metric("Paid Invoice Value", f"SAR {paid_amount:,.0f}")
col3.metric("Unpaid Invoice Value", f"SAR {unpaid_amount:,.0f}")
col4.metric("Overdue Invoice Value", f"SAR {overdue_amount:,.0f}")

st.caption(
    "Values use the SAR label for this synthetic Saudi dataset. "
    "If you upload data in multiple currencies, convert currencies "
    "before combining their values."
)

st.subheader("Financial Performance Indicators")

eligible_count = len(filtered_df)
overdue_count = int(
    (filtered_df["payment_status"] == "overdue").sum()
)

paid_value_ratio = (
    paid_amount / total_invoiced * 100
    if total_invoiced > 0
    else 0
)

average_invoice_value = (
    total_invoiced / eligible_count
    if eligible_count > 0
    else 0
)

metric1, metric2, metric3 = st.columns(3)
metric1.metric(
    "Average Eligible Invoice Value",
    f"SAR {average_invoice_value:,.0f}",
)
metric2.metric("Overdue Invoice Count", f"{overdue_count:,}")
metric3.metric("Paid Value Ratio", f"{paid_value_ratio:.1f}%")

st.caption(
    "Paid Value Ratio is based on recorded invoice payment statuses. "
    "It is not a verified bank collection rate."
)


# --------------------------------------------------
# 7. Monthly chart and payment status chart
# --------------------------------------------------

st.subheader("Monthly Invoiced Value")

if not filtered_df.empty:
    monthly = (
        filtered_df.assign(
            month=filtered_df["invoice_date"].dt.to_period("M").astype(str)
        )
        .groupby("month", as_index=False)["amount"]
        .sum()
        .sort_values("month")
    )

    monthly_chart = px.bar(
        monthly,
        x="month",
        y="amount",
        labels={"month": "Month", "amount": "Invoiced Value (SAR)"},
        title="Eligible invoice value by month",
    )
    st.plotly_chart(monthly_chart, use_container_width=True)
else:
    st.info("No eligible invoices match the selected filters.")

st.subheader("Invoice Payment Status")

status_summary = (
    filtered_df.groupby("payment_status", as_index=False)
    .agg(
        invoice_count=("invoice_id", "count"),
        invoice_value=("amount", "sum"),
    )
)

if not status_summary.empty:
    status_chart = px.pie(
        status_summary,
        names="payment_status",
        values="invoice_value",
        title="Invoice value by recorded payment status",
    )
    st.plotly_chart(status_chart, use_container_width=True)
else:
    st.info("No payment status data is available for the selected filters.")


# --------------------------------------------------
# 8. Bank reconciliation dashboard
# --------------------------------------------------

st.header("Bank Reconciliation")

if not BANK_FILE.exists():
    st.warning(
        "Bank transaction data was not found. "
        "Run generate_bank_data.py first."
    )
else:
    try:
        raw_bank_df = pd.read_csv(BANK_FILE)
        missing_bank_columns = REQUIRED_BANK_COLUMNS - set(raw_bank_df.columns)

        if missing_bank_columns:
            st.error(
                "Bank data is missing required columns: "
                + ", ".join(sorted(missing_bank_columns))
            )
        else:
            bank_df = normalize_bank_transactions(raw_bank_df)
            reconciliation_df = reconcile_invoices(df, bank_df)

            matched_count = int(
                (reconciliation_df["match_status"] == "Matched").sum()
            )
            unmatched_count = int(
                (reconciliation_df["match_status"] == "Unmatched").sum()
            )
            review_count = int(
                (reconciliation_df["match_status"] == "Needs Review").sum()
            )

            bank_col1, bank_col2, bank_col3 = st.columns(3)
            bank_col1.metric("Matched Invoices", matched_count)
            bank_col2.metric("Unmatched Invoices", unmatched_count)
            bank_col3.metric("Needs Review", review_count)

            st.caption(
                "A match means one bank credit has the same reference, "
                "currency, and amount as an invoice. It does not prove "
                "the payment's authenticity. Partial payments and one "
                "payment covering multiple invoices are not supported yet."
            )

            status_options = ["Matched", "Unmatched", "Needs Review"]
            selected_match_statuses = st.multiselect(
                "Filter reconciliation status",
                options=status_options,
                default=status_options,
                key="reconciliation_status_filter",
            )

            visible_reconciliation = reconciliation_df[
                reconciliation_df["match_status"].isin(
                    selected_match_statuses
                )
            ]

            st.dataframe(
                visible_reconciliation,
                use_container_width=True,
                hide_index=True,
            )

            st.download_button(
                "Download Reconciliation Results",
                data=reconciliation_df.to_csv(index=False).encode("utf-8"),
                file_name="reconciliation_results.csv",
                mime="text/csv",
            )

    except Exception as exc:
        st.error(f"Could not process bank transaction data: {exc}")


# --------------------------------------------------
# 9. Data quality review
# --------------------------------------------------

st.header("Data Quality Review")

quality_col1, quality_col2 = st.columns(2)
quality_col1.metric("Records in Dataset", len(df))
quality_col2.metric(
    "Records Flagged for Review",
    issues_df["invoice_id"].nunique() if not issues_df.empty else 0,
)

if not issues_df.empty:
    st.dataframe(
        issues_df,
        use_container_width=True,
        hide_index=True,
    )

    st.download_button(
        "Download Data Quality Issues",
        data=issues_df.to_csv(index=False).encode("utf-8"),
        file_name="data_quality_issues.csv",
        mime="text/csv",
    )
else:
    st.success("No data quality issues were detected.")

st.subheader("Invoice Records")

st.dataframe(
    filtered_df[
        [
            "invoice_id",
            "invoice_date",
            "customer_name",
            "amount",
            "currency",
            "payment_status",
            "paid_date",
        ]
    ],
    use_container_width=True,
    hide_index=True,
)


# --------------------------------------------------
# 10. Financing readiness check
# --------------------------------------------------

st.header("Financing Readiness Check")

readiness_issues = []

if df["invoice_date"].isna().any():
    readiness_issues.append("Some invoices have missing or invalid dates.")

if df["amount"].isna().any() or (df["amount"] <= 0).any():
    readiness_issues.append(
        "Some invoices have missing or non-positive amounts."
    )

if df["customer_name"].eq("").any():
    readiness_issues.append("Some invoices have no customer name.")

if df["invoice_id"].eq("").any():
    readiness_issues.append("Some invoices have no invoice ID.")

if duplicate_extra_mask.any():
    readiness_issues.append("Duplicate invoice IDs require verification.")

if df["payment_status"].isin(["paid", "unpaid", "overdue"]).eq(False).any():
    readiness_issues.append("Some invoices have an invalid payment status.")

if readiness_issues:
    st.warning(
        "Needs Review — resolve or document the flagged issues "
        "before submitting the financing package."
    )
    for issue in readiness_issues:
        st.write(f"- {issue}")
else:
    st.success(
        "Invoice data checks passed. Required documents and bank "
        "reconciliation must still be verified before submission."
    )

st.caption(
    "This check evaluates data quality only. It does not determine "
    "creditworthiness, financing eligibility, or loan approval."
)


# --------------------------------------------------
# 11. Review notes and limitations
# --------------------------------------------------

st.header("Review Notes")

st.write(
    "- Missing dates, invalid amounts, and repeated invoice IDs are "
    "excluded from financial totals pending verification."
)
st.write(
    "- The original uploaded records remain available in the current "
    "session's review table; the app does not overwrite the source CSV."
)
st.write(
    "- Unpaid and overdue invoices are not automatically treated as bad debt."
)
st.write(
    "- Bank reconciliation currently matches reference, amount, and currency. "
    "Partial payments and grouped payments need further work."
)
st.write(
    "- This prototype uses synthetic data and does not submit financing "
    "applications to a bank or make approval decisions."
)