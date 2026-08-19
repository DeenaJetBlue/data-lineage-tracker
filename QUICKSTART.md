# Quick Start Guide

Get up and running in 5 minutes!

## Prerequisites

- Python 3.8+ installed
- Node.js 16+ and npm installed
- Git (optional)

## Step 1: Clone/Setup Project

```bash
# If you downloaded as ZIP, extract it
# If using git:
git clone <repository-url>
cd data-lineage-tracker
```

## Step 2: Setup Backend

### Windows:
```bash
cd backend
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python run.py
```

### macOS/Linux:
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python run.py
```

✅ Backend will start at: `http://localhost:8000`

Open another terminal for frontend setup...

## Step 3: Setup Frontend

```bash
cd frontend
npm install
npm run dev
```

✅ Frontend will start at: `http://localhost:3000`

## Step 4: Test the Application

1. Open your browser to `http://localhost:3000`
2. You'll see a search form with sample tables:
   - customers
   - orders
   - products
3. Click on any table to see its lineage
4. The UI will show:
   - ADLS (Data Lake)
   - Azure Data Factory
   - DBT Staging Layer
   - DBT Star Layer

## Step 5: Add Your Own Tables

Edit `ConfigurationFile.csv`:

```csv
TableName,ADLS2,DataFactory,DbtStage,DbtStar
my_table,/raw/my_table/,MyPipeline,stg_my_table,my_table_star
```

Then refresh your browser - new table will appear!

## API Documentation

Access Swagger docs at: `http://localhost:8000/docs`

### Test API Endpoints:

```bash
# Get all tables
curl http://localhost:8000/api/tables

# Get lineage for a table
curl http://localhost:8000/api/lineage/customers

# Health check
curl http://localhost:8000/api/health
```

## Configure Real Credentials (Optional)

Edit `backend/.env`:

```
ADF_TENANT_ID=your_tenant_id
ADF_CLIENT_ID=your_client_id
ADF_CLIENT_SECRET=your_client_secret
ADF_SUBSCRIPTION_ID=your_subscription_id
ADF_RESOURCE_GROUP=your_resource_group
DBT_SECRET=your_dbt_secret
ADLS_ACCOUNT_NAME=your_account_name
ADLS_ACCOUNT_KEY=your_account_key
```

Then restart the backend:
```bash
python run.py
```

## Common Commands

### Stop Backend
```bash
# In backend terminal: Ctrl+C
```

### Stop Frontend
```bash
# In frontend terminal: Ctrl+C
```

### Deactivate Python Virtual Environment
```bash
deactivate
```

### Install New Python Package
```bash
pip install <package-name>
pip freeze > requirements.txt
```

### Install New npm Package
```bash
npm install <package-name>
```

## Troubleshooting

### "Port already in use"
- Change port in `vite.config.js` (frontend) or `run.py` (backend)

### "Module not found"
- Backend: `pip install -r requirements.txt`
- Frontend: `npm install`

### "ConfigurationFile.csv not found"
- Make sure it's in the project root directory

### API returns 404
- Check table name in ConfigurationFile.csv
- Verify ConfigurationFile.csv path in `.env`

### "Failed to fetch tables"
- Backend server not running?
- Check `http://localhost:8000/api/health`

## Project Structure Overview

```
data-lineage-tracker/
├── backend/          ← Python FastAPI server
├── frontend/         ← React Vite app
├── ConfigurationFile.csv  ← Your table mappings
├── README.md         ← Full documentation
└── QUICKSTART.md     ← This file
```

## Next Steps

1. ✅ Run the application locally
2. Add your own tables to ConfigurationFile.csv
3. Configure real Azure/DBT credentials
4. Deploy to production

## Getting Help

1. Check backend logs: Terminal window running `python run.py`
2. Check frontend logs: Browser console (F12)
3. Verify all services are running
4. Check that ports 3000 and 8000 are available

## Performance Tips

- Keep ConfigurationFile.csv limited to ~100 tables for best performance
- Use shorter ADLS paths when possible
- Cache DBT API responses if making frequent calls

Enjoy tracking your data lineage! 🚀
