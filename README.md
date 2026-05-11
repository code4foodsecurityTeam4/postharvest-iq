# PostHarvest IQ

A USSD-powered sell-or-store decision intelligence service
for smallholder maize farmers in Northern Ghana.

Built for the WFP Code4FoodSecurity Fellowship 2026 — Blossom Academy.

## Setup

### 1. Clone the repo
git clone https://github.com/your-org/postharvest-iq.git
cd postharvest-iq

### 2. Create virtual environment
python -m venv venv
source venv/bin/activate        # Mac/Linux
venv\Scripts\activate           # Windows

### 3. Install dependencies
pip install -r requirements.txt

### 4. Set up environment variables
cp .env.example .env
# Open .env and fill in your MySQL credentials

### 5. Create MySQL database
mysql -u root -p
CREATE DATABASE postharvest_iq;
EXIT;

### 6. Run the API
uvicorn app.main:app --reload

### 7. Open API docs
http://localhost:8000/docs

## Team

| Role | Name |
|------|------|
| Backend Lead | [Your name] |
| ML Lead | |
| Data Lead | |
| USSD Developer | |
| Dashboard Developer | |
| Integration Lead | |
| Presentation Lead | |

## Project Structure

app/           FastAPI backend
app/ml/        ML models and training scripts
data/          Datasets (raw/ is gitignored)
dashboard/     Streamlit officer dashboard
notebooks/     Jupyter notebooks for ML work
tests/         Automated tests