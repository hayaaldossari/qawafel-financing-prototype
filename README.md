# Qawafel Financing Insights

A prototype for reviewing SME invoice data, identifying data-quality issues, analyzing invoice payment patterns, and reconciling invoices against synthetic bank transactions before preparing a financing package.

## Problem Statement

Small and medium-sized businesses may need to submit invoices and bank statements when applying for financing. Reviewing these documents manually can be time-consuming and may lead to missing information, duplicate records, or inconsistencies between invoiced amounts and recorded bank transactions.

This prototype demonstrates an initial workflow for organizing invoice data, surfacing data-quality issues, and supporting human review.

## Features

- **Invoice upload:** Load invoice records from CSV or Excel files.
- **Financial overview:** Review eligible invoiced value, recorded paid value, unpaid value, and overdue value.
- **Performance indicators:** View average eligible invoice value, overdue invoice count, and paid invoice value ratio.
- **Monthly analysis:** Explore invoice values by month.
- **Data-quality checks:** Flag missing fields, invalid amounts, invalid dates, and duplicate invoice IDs.
- **Bank reconciliation:** Compare invoice references, amounts, and currencies against bank credits.
- **Review workflow:** Separate matched, unmatched, and ambiguous records for further investigation.
- **Exportable reports:** Download data-quality issues and reconciliation results as CSV files.
- **Readiness check:** Highlight invoice-data issues before a financing package is prepared.

## Technology Stack

- Python
- Streamlit
- Pandas
- Plotly
- OpenPyXL

## Project Structure

```text
qawafel-financing-prototype/
├── app.py
├── generate_data.py
├── generate_bank_data.py
├── requirements.txt
├── .gitignore
└── data/
    ├── invoices.csv
    └── bank_transactions.csv
```

## Getting Started

### 1. Create and activate a virtual environment

Python 3.11 or a compatible supported version is recommended.

On Windows PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, run the environment's Python executable directly as shown below.

### 2. Install dependencies

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### 3. Generate the synthetic datasets

```powershell
.\.venv\Scripts\python.exe generate_data.py
.\.venv\Scripts\python.exe generate_bank_data.py
```

The scripts create the following files in the `data/` directory:

- `invoices.csv`
- `bank_transactions.csv`

### 4. Run the application

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Open the local URL displayed in the terminal.

## Sample Data

All sample records are synthetic and intended for demonstration only.

The invoice dataset covers 12 months of invoice activity and includes deliberately introduced data-quality cases, such as missing fields, a non-positive amount, and a duplicate invoice ID.

The bank transaction dataset contains synthetic credits and debits, including transactions linked to selected invoices and unrelated transactions used to test reconciliation behavior.

The sample data is located in the `data/` directory. Running the generation scripts recreates the datasets.

## Key Assumptions

- Invoice payment statuses are provided by the source data and are not independently verified.
- Financial totals exclude records with invalid or missing invoice dates, non-positive or invalid amounts, and additional occurrences of duplicate invoice IDs.
- Duplicate records remain available for review rather than being deleted from the source dataset.
- The prototype assumes SAR for its sample financial overview. Mixed-currency datasets require currency-aware aggregation or conversion before totals can be combined.
- A bank match requires one credit with the same reference, currency, and amount as the invoice.
- Ambiguous or unmatched records require further investigation.

## Limitations and Next Steps

- Bank-statement PDF extraction is not implemented.
- Reconciliation does not yet support partial payments or a single payment covering multiple invoices.
- Matching reference, amount, and currency does not independently prove payment authenticity.
- Uploaded files are processed in the current application session and are not persisted as a managed customer-document workflow.
- The prototype does not integrate with a bank API, transmit financing applications, or determine creditworthiness or financing approval.
- Production use would require authentication, authorization, secure document storage, audit logging, stronger validation, automated tests, and a safe bank-integration workflow.

## AI Tools Used

AI assistance was used to help plan the prototype, draft and refine parts of the implementation, troubleshoot code issues, and structure the project documentation. The generated code and design decisions should be reviewed and tested before production use.

## Disclaimer

This project is a demonstration prototype using synthetic data. It is not a lending decision system and must not be used to make real financing decisions.
