# AI SYSTEM DIRECTIVE
You are an expert full-stack developer and architect. Do not write any code until you have read this entire document. Follow these requirements exactly. If a requirement is ambiguous, STOP and ask for clarification.

# 1. PROJECT OVERVIEW
* **Name:** WattsApp (Indian Household Power Management)
* **Core Purpose:** A web-based power management dashboard tailored for Indian households. It uses linear regression to analyze appliance-level data, predict future energy consumption, estimate monthly bills based on local tariffs, and recommend energy-saving actions in a vibrant, light-themed UI.
* **Target User:** General Indian households, homeowners, and tenants looking to monitor, predict, and optimize their electricity bills.

# 2. TECH STACK & ARCHITECTURE
(CRITICAL: Do not install or use any libraries outside this list without explicit permission.)
* **Frontend:** React (Next.js App Router), HTML/JS
* **Styling:** Tailwind CSS, shadcn/ui (configured for a light, vibrant, high-contrast color palette; avoiding dark purple/neon AI tropes).
* **Backend:** Python / FastAPI (Required for robust implementation of scikit-learn linear regression).
* **Database:** PostgreSQL (via Supabase for ease of setup and real-time capabilities).
* **Machine Learning:** `scikit-learn` (for Linear Regression models), `pandas`, `numpy`.
* **Key Dependencies:** `Chart.js` or `Recharts` (for data visualization), `axios` or `fetch` API, `dotenv`.

# 3. DATABASE SCHEMA & DATA SHAPES
(Use exact field names and types. Do not invent new tables.)

**Table:** `households`
* `id`: UUID - Primary Key
* `name`: String - Household name (e.g., "Sharma Residence")
* `state`: String - State for tariff calculation (e.g., "Tamil Nadu")
* `created_at`: Timestamp

**Table:** `appliances`
* `id`: UUID - Primary Key
* `household_id`: UUID - Foreign Key to `households.id`
* `appliance_name`: String - (e.g., "500W Mixer Grinder", "BLDC Fan", "1.5 Ton AC")
* `category`: String - (e.g., "Kitchen", "Cooling", "Entertainment")
* `power_rating_watts`: Int - Standard wattage of the appliance
* `age_years`: Int - Age of the appliance (impacts efficiency)
* `is_smart`: Boolean - Flag if it's a smart/inverter appliance

**Table:** `daily_usage_logs`
* `id`: UUID - Primary Key
* `appliance_id`: UUID - Foreign Key to `appliances.id`
* `date`: Date - Date of usage
* `hours_used`: Float - Total hours the appliance was active that day
* `energy_consumed_wh`: Float - (power_rating_watts * hours_used) * efficiency_factor

**Table:** `regression_models` (Stores parameters for the household's unique model)
* `id`: UUID - Primary Key
* `household_id`: UUID - Foreign Key to `households.id`
* `coefficient_hours`: Float - Derived beta value for usage hours
* `coefficient_age`: Float - Derived beta value for appliance age
* `intercept`: Float - y-intercept of the model
* `r_squared`: Float - Model accuracy metric
* `last_trained`: Timestamp

# 4. CORE FEATURES & LOGIC FLOWS
Implement these sequentially. Do not move to Step 2 until Step 1 is fully functional and error-free.

### Step 1: Layout Skeleton, Routing & Vibrant UI Setup
* **Action:** User navigates to the web application.
* **Expected Result:** The system renders the main layout. It must include a sidebar navigation with two main tabs: "Household Dashboard" (standard power management view) and "AI Analytics & Predictions" (the linear regression specific tab). 
* **UI/UX Notes:** Strictly enforce a light, vibrant color scheme (e.g., warm oranges, clean teals, bright whites, and soft grays). Do not use dark mode or cyberpunk/neon aesthetics. Typography should be clean (sans-serif) and use ample padding.

### Step 2: Database Connection & Appliance Management
* **Action:** User navigates to the "Household Dashboard" and views/adds appliances.
* **Expected Result:** Frontend fetches data from the `appliances` and `daily_usage_logs` tables in PostgreSQL via the FastAPI backend. Displays a list/grid of appliances with their typical Indian wattages (e.g., 50W Normal Fan vs 28W BLDC Fan, 500W Mixer Grinder).
* **UI/UX Notes:** Render a simple, responsive list or card grid. Ensure the API calls are wrapped in try/catch blocks with visible loading states.

### Step 3: Linear Regression Backend Engine
* **Action:** Backend periodically (or on-demand) processes the `daily_usage_logs` for a household.
* **Expected Result:** FastAPI reads the historical usage data. It uses `scikit-learn` to run a Multiple Linear Regression: 
    * *Independent Variables (X):* `hours_used`, `age_years`, `power_rating_watts`.
    * *Dependent Variable (y):* `energy_consumed_wh`.
    * The backend calculates the coefficients, intercept, and R-squared value, updating the `regression_models` table. It exposes an endpoint `/predict` that accepts current usage patterns and returns a 30-day forecast.

### Step 4: AI Analytics & Predictions Tab (The Math & Charts)
* **Action:** User clicks on the "AI Analytics & Predictions" tab.
* **Expected Result:** 
    1. System fetches the linear regression data from the backend.
    2. Displays a clear, human-readable explanation of the Linear Regression formula being used: `Predicted Consumption = Intercept + (Beta1 * Hours) + (Beta2 * Age) + ...`
    3. Renders a scatter plot (using Recharts/Chart.js) showing *Actual vs. Predicted* energy consumption to visualize the model's accuracy.
    4. Shows the calculated coefficients, highlighting which factor (e.g., age vs. hours) is driving the most power consumption.
* **UI/UX Notes:** This tab should look distinct from the operational dashboard—more like an interactive report or educational breakdown. Use vibrant chart colors (e.g., coral and teal) against a white background.

### Step 5: Dashboard Visualization & Tariff Output
* **Action:** User views the main "Household Dashboard".
* **Expected Result:** 
    1. The system calls the `/predict` endpoint to get the estimated total power consumption (in kWh/Units) for the current billing cycle.
    2. **Goal State Output:** It applies standard Indian tariff logic (e.g., Tamil Nadu bi-monthly slabs: 0-200 units free, ₹4.70 for 201-400, etc.) to the predicted units to display an Estimated Bill Amount in INR (₹).
    3. It highlights "Energy Guzzlers" (appliances causing the highest predicted spike based on the regression weights).

# 5. STRICT AI CONSTRAINTS (NON-NEGOTIABLE)
1. **No Mock Data in Production:** The application must read from the actual PostgreSQL database containing realistic Indian household appliance data (wattages, hours).
2. **File Structure:** Keep React components modular. The FastAPI backend must separate routing, database operations, and machine learning logic into different files.
3. **Error Handling:** Never swallow errors silently. All API calls must have `try/catch` blocks that render a visible error state (toast notification or inline error text) in the UI.
4. **Environment Variables:** Never hardcode API keys or database URLs. Always use `.env` files for Supabase and backend config.
5. **Styling Rules:** The UI must be bright, clean, and vibrant. Rely on padding, typography, and subtle drop shadows rather than heavy borders. **Absolutely no dark purple, neon green, or typical "hacker" AI styling.**