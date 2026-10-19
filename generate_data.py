
from pathlib import Path

import pandas as pd


OUTPUT_DIR = Path(__file__).parent / "data"
OUTPUT_FILE = OUTPUT_DIR / "invoices.csv"


def generate_invoices() -> pd.DataFrame:
    """Generate synthetic invoice records for a fictional Saudi wholesaler."""

    customers = [
        "Riyadh Retail Co.",
        "Jeddah Market Supplies",
        "Eastern Trading Group",
        "Najd Supermarkets",
        "Red Sea Distribution",
        "Al Waha Stores",
        "Desert Star Trading",
        "Palm Grove Markets",
    ]

    monthly_invoice_counts = [
        18, 20, 19, 22, 21, 24,
        23, 25, 24, 27, 26, 30,
    ]

    records = []
    invoice_number = 1

    for month_index, invoice_count in enumerate(
        monthly_invoice_counts
    ):
        month_start = pd.Timestamp("2025-01-01") + pd.DateOffset(
            months=month_index
        )

        for item_index in range(invoice_count):
            invoice_date = month_start + pd.Timedelta(
                days=(item_index * 3) % 27
            )

            # Simulate gradual business growth with realistic variation.
            base_amount = 3500 + (month_index * 180)
            variation = ((item_index * 137) % 6500) + 500
            amount = round(base_amount + variation, 2)

            status_pattern = (invoice_number * 7) % 10

            if status_pattern < 6:
                payment_status = "paid"
                days_to_pay = 10 + ((invoice_number * 3) % 35)
                paid_date = invoice_date + pd.Timedelta(
                    days=days_to_pay
                )
            elif status_pattern < 8:
                payment_status = "unpaid"
                paid_date = pd.NaT
            else:
                payment_status = "overdue"
                paid_date = pd.NaT

            records.append(
                {
                    "invoice_id": f"INV-{invoice_number:04d}",
                    "invoice_date": invoice_date.date().isoformat(),
                    "customer_name": customers[
                        invoice_number % len(customers)
                    ],
                    "amount": amount,
                    "currency": "SAR",
                    "payment_status": payment_status,
                    "paid_date": (
                        paid_date.date().isoformat()
                        if pd.notna(paid_date)
                        else ""
                    ),
                }
            )

            invoice_number += 1

    df = pd.DataFrame(records)

    # Introduce controlled data-quality issues for testing.
    df.loc[4, "invoice_date"] = ""
    df.loc[11, "customer_name"] = ""
    df.loc[19, "amount"] = -2500.00

    # Add a duplicate record to test duplicate detection.
    duplicate = df.iloc[[7]].copy()
    df = pd.concat([df, duplicate], ignore_index=True)

    return df


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    invoices = generate_invoices()
    invoices.to_csv(OUTPUT_FILE, index=False)

    print(f"Generated {len(invoices)} synthetic invoice records.")
    print(f"Saved dataset to: {OUTPUT_FILE}")
    print("\nPayment status counts:")
    print(invoices["payment_status"].value_counts())
    print("\nFirst five records:")
    print(invoices.head().to_string(index=False))


if __name__ == "__main__":
    main()
