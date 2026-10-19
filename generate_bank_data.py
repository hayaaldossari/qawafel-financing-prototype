
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_FILE = DATA_DIR / "bank_transactions.csv"


def generate_bank_transactions() -> pd.DataFrame:
    invoices_file = DATA_DIR / "invoices.csv"
    invoices = pd.read_csv(invoices_file)

    invoices["invoice_date"] = pd.to_datetime(
        invoices["invoice_date"], errors="coerce"
    )
    invoices["amount"] = pd.to_numeric(
        invoices["amount"], errors="coerce"
    )

    transactions = []
    transaction_number = 1

    # Generate synthetic bank transactions for selected paid invoices.
    paid_invoices = invoices[
        (invoices["payment_status"] == "paid")
        & invoices["invoice_date"].notna()
        & invoices["amount"].notna()
        & (invoices["amount"] > 0)
    ].drop_duplicates(subset=["invoice_id"])

    for _, invoice in paid_invoices.iterrows():
        # Some payments are intentionally omitted to simulate
        # invoices that still need reconciliation.
        if transaction_number % 5 == 0:
            transaction_number += 1
            continue

        payment_date = invoice["invoice_date"] + pd.Timedelta(
            days=10 + (transaction_number % 25)
        )

        transactions.append(
            {
                "transaction_id": f"TXN-{transaction_number:04d}",
                "transaction_date": payment_date.date().isoformat(),
                "description": (
                    f"Payment for invoice {invoice['invoice_id']}"
                ),
                "reference": invoice["invoice_id"],
                "amount": round(float(invoice["amount"]), 2),
                "currency": invoice.get("currency", "SAR"),
                "transaction_type": "credit",
            }
        )

        transaction_number += 1

    # Add a synthetic unrelated credit and a debit to test
    # reconciliation filters.
    transactions.extend(
        [
            {
                "transaction_id": "TXN-EXTRA-001",
                "transaction_date": "2025-08-15",
                "description": "Unrelated customer deposit",
                "reference": "OTHER-REF-001",
                "amount": 7200.00,
                "currency": "SAR",
                "transaction_type": "credit",
            },
            {
                "transaction_id": "TXN-EXTRA-002",
                "transaction_date": "2025-09-10",
                "description": "Office rent payment",
                "reference": "RENT-SEP",
                "amount": -4500.00,
                "currency": "SAR",
                "transaction_type": "debit",
            },
        ]
    )

    return pd.DataFrame(transactions)


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    transactions = generate_bank_transactions()
    transactions.to_csv(OUTPUT_FILE, index=False)

    print(f"Generated {len(transactions)} synthetic bank transactions.")
    print(f"Saved dataset to: {OUTPUT_FILE}")
    print(transactions.head().to_string(index=False))


if __name__ == "__main__":
    main()
