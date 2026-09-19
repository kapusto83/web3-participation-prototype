# Web3 Participation Prototype

## Setup

Create and activate the virtual environment:

```powershell
python -m venv .venv
.venv\Scripts\activate
```

Install dependencies:

```powershell
pip install streamlit pandas web3
```

## Run the application

From the project root:

```powershell
streamlit run src/app.py
```

## Run the dashboard

In a separate terminal:

```powershell
streamlit run src/dashboard.py
```

## Generate synthetic data

```powershell
python src/seed_synthetic.py
```

The script adds synthetic data to the local SQLite database. It does not wipe existing data.
