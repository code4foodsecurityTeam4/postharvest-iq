# PostHarvest IQ

A USSD-powered sell-or-store decision intelligence service for 
smallholder maize farmers in Northern Ghana.

Built for the WFP Code4FoodSecurity Fellowship 2026 — Blossom Academy.

---

## What It Does

A farmer dials `*384#` on any basic phone, selects their crop and 
district, and receives a **STORE / SELL NOW / SELL PARTIAL** 
recommendation with the net financial gain in Ghana cedis and the 
nearest verified storage location. Available in English, Dagbani, 
and Hausa.

Powered by an LSTM price forecasting model trained on WFP VAM data 
and an XGBoost decision classifier.

---

## Setup

```bash
# Clone
git clone https://github.com/code4foodsecurityTeam4/postharvest-iq.git
cd postharvest-iq

# Environment
conda create -n postharvest python=3.11
conda activate postharvest
pip install -r requirements.txt
pip install cryptography

# Configure
cp .env.example .env
# Fill in your MySQL credentials in .env

# Database
mysql -u root -p
CREATE DATABASE IF NOT EXISTS postharvest_iq;
EXIT;

# Notebook output stripping (required — prevents local paths and stale outputs being committed)
nbstripout --install

# Run
uvicorn app.main:app --reload --host localhost
```

API docs: `http://localhost:8000/docs`

---

## Stack

FastAPI · MySQL · LSTM · XGBoost · Africa's Talking USSD · Streamlit

---

## Rules

- Never push directly to `main`
- Always create a branch: `git checkout -b feature/your-task`
- Open a Pull Request and get one approval before merging

---

