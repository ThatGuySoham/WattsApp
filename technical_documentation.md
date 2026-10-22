# WattsApp: Technical Documentation & Run Guide

This document explains the technical architecture, dataset, and machine learning implementation behind WattsApp.

---

## 1. How to Run the Project

The project is split into a Python backend and a React (Next.js) frontend. You need two terminal windows to run them simultaneously.

### Start the Backend (Terminal 1)
1. Navigate to the backend directory:
   ```bash
   cd backend
   ```
2. Activate the virtual environment (Windows):
   ```bash
   .\.venv\Scripts\activate
   ```
3. Start the FastAPI server:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```
   *The API will be available at `http://localhost:8000`.*

### Start the Frontend (Terminal 2)
1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```
2. Start the Next.js development server:
   ```bash
   npm run dev
   ```
   *The web app will be available at `http://localhost:3000`.*

---

## 2. Technical Backend Overview

The backend is built with **FastAPI** (Python), designed for high performance and easy ML integration.

*   **Database:** A real **PostgreSQL** database hosted on Neon. We use `psycopg3` (with a connection pool) for fast, concurrent database access.
*   **API Layer:** FastAPI provides robust routing and automatic data validation using **Pydantic** models (found in `app/schemas.py`).
*   **Service Layer:** The `app/services/analytics.py` file acts as the brain. It orchestrates reading data from the database, passing it to the ML engine, and calculating the final electricity bill based on state-specific tariffs.
*   **ML Engine:** We use **scikit-learn** (`app/ml/regression.py`) to handle the model training and prediction entirely in memory using Pandas DataFrames and NumPy arrays.

---

## 3. Dataset Used, Location, and Parameters

### Where is the data?
There is no static `.csv` file. The data lives dynamically in the **PostgreSQL database** (in the `households`, `appliances`, and `daily_usage_logs` tables). 

### How is it generated?
The dataset is seeded by the `backend/scripts/seed.py` script. It generates a realistic, 90-day historical dataset for typical Indian households.

### The Parameters (Features)
For every single day of usage, the dataset logs the following parameters:
1.  **`hours_used`:** How long the appliance ran that day (incorporates weekend habits and seasonal trends).
2.  **`power_rating_watts`:** The standard wattage of the appliance (e.g., 50W for a fan, 1500W for an AC).
3.  **`age_years`:** The age of the appliance.
4.  **`is_smart`:** A boolean flag indicating if it's a modern inverter/smart appliance.
5.  **`energy_consumed_wh`:** The actual target variable (y). It is calculated using basic physics with an efficiency penalty for older appliances.

---

## 4. The Formula & How It Works

WattsApp uses **Multiple Linear Regression (MLR)** to predict energy consumption. 

### The Formula
```text
Predicted Energy (Wh) = Intercept (β0) 
                        + (β1 × hours_used) 
                        + (β2 × power_rating_watts) 
                        + (β3 × age_years)
```

### How it works:
1.  **Training:** When you view a household, the backend fetches the last 90 days of logs. `scikit-learn` finds the line of best fit through this multi-dimensional data, calculating the "weights" (Coefficients: β1, β2, β3) and the starting baseline (Intercept: β0).
2.  **Prediction:** To forecast the next 30 days, the system looks at your recent weekday habits (e.g., "The AC is usually on for 8 hours on Tuesdays"). It plugs those forecasted hours, along with the appliance's watts and age, back into the formula to predict the future Wh.
3.  **Standardized Importance:** On the Analytics tab, we multiply the coefficients by the standard deviation of each feature. This normalizes the weights so we can definitively say, for example, "Appliance wattage drives 60% of the variance in your bill."

---

## 5. Why Linear Regression? (The Rationale & Limitations)

### Why LR is a great use case here:
1.  **Explainability:** Neural networks are "black boxes." Linear Regression gives us explicit coefficients. We can show the user *exactly* how much 1 extra hour of usage or 1 extra year of appliance age costs them.
2.  **Speed & Efficiency:** Training an LR model on a few thousand rows takes milliseconds. We can retrain the model on-the-fly every time the user adds a new appliance.
3.  **Baseline Simplicity:** It prevents overfitting on small datasets (like a single household's 90-day history) and handles the linear trends of usage very well.

### The Physics Limitation (Important Context)
While LR is highly interpretable, electricity consumption is physically a **multiplicative** relationship:
`Energy = Power (Watts) × Time (Hours)`

Because MLR is an **additive** model (`y = a + b + c`), it tries to approximate a multiplication curve using addition. This is why the R² (accuracy) score hovers around 30-40%. 

**How to improve this in the future:** 
We could use "Feature Engineering". Instead of just feeding the model `hours` and `watts`, we could feed it a new column called `hours_times_watts`. The Linear Regression model would then achieve 99% accuracy because it's mapping a linear feature to a linear output! However, keeping them separate as requested allows the UI to show the isolated impact of *just* time or *just* power rating.
