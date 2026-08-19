# Data Lineage Tracker

A tool to trace and visualize data flow through your pipeline architecture.

## Data Flow Architecture

```
ADLS (Data Lake)
    ↓
Azure Data Factory (Raw Layer)
    ↓
Snowflake (Raw Layer)
    ↓
DBT Staging Layer
    ↓
DBT Star Layer
```

## Features

✅ **Table Configuration** - CSV-based mapping of tables to systems  
✅ **ADLS Integration** - Check file existence in Azure Data Lake  
✅ **ADF Pipeline Monitoring** - Get latest pipeline run status  
✅ **DBT Job Tracking** - Monitor DBT staging and star layer jobs  
✅ **Lineage Visualization** - Interactive UI showing data flow  
✅ **Local Testing** - Works with mock data without real credentials  

## Project Structure

```
data-lineage-tracker/
├── backend/
│   ├── app/
│   │   ├── services/
│   │   │   ├── config_service.py      # Configuration loader
│   │   │   ├── adls_service.py        # ADLS operations
│   │   │   ├── adf_service.py         # ADF pipeline operations
│   │   │   └── dbt_service.py         # DBT job operations
│   │   ├── routes/
│   │   │   └── lineage.py             # API endpoints
│   │   ├── config.py                  # Settings
│   │   ├── models.py                  # Data models
│   │   └── main.py                    # FastAPI app
│   └── run.py                         # Server entry point
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── TableSearch.jsx        # Table selection
│   │   │   ├── LineageViewer.jsx      # Lineage display
│   │   │   └── LineageFlow.jsx        # Flow diagram
│   │   ├── App.jsx                    # Root component
│   │   ├── index.jsx                  # Entry point
│   │   └── index.css                  # Global styles
│   ├── index.html
│   ├── vite.config.js
│   └── package.json
├── .env                               # Environment variables
├── .env.example                       # Environment template
├── requirements.txt                   # Python dependencies
├── ConfigurationFile.csv              # Table mappings
└── README.md
```

## Setup Instructions

### Prerequisites

- Python 3.8+
- Node.js 16+
- npm or yarn

### Backend Setup

1. Create and activate virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: .\venv\Scripts\activate
```

2. Install dependencies from root directory:
```bash
pip install -r requirements.txt
```

3. Configure environment variables (if needed):
```bash
# .env file is already at the root level
# Edit .env with your credentials (optional for local testing)
```

4. Run the backend server:
```bash
cd backend
python run.py
```

Server will start at `http://localhost:8000`

### Frontend Setup

1. Navigate to frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. Start development server:
```bash
npm run dev
```

Frontend will be available at `http://localhost:3000`

## Configuration

### ConfigurationFile.csv

Maps tables to their respective systems. Format:

```csv
TableName,ADLS2,DataFactory,DbtStage,DbtStar
table_name,adls_path,pipeline_name,staging_job_name,star_job_name
```

Example:
```csv
TableName,ADLS2,DataFactory,DbtStage,DbtStar
customers,/raw/customers/,CustomersPipeline,stg_customers,customers_star
orders,/raw/orders/,OrdersPipeline,stg_orders,orders_star
```

### Environment Variables (.env)

```
# Azure Data Factory
ADF_TENANT_ID=your_tenant_id
ADF_CLIENT_ID=your_client_id
ADF_CLIENT_SECRET=your_client_secret
ADF_SUBSCRIPTION_ID=your_subscription_id
ADF_RESOURCE_GROUP=your_resource_group

# DBT Cloud
DBT_SECRET=your_dbt_api_token
DBT_ENVIRONMENT_ID=21843
DBT_ACCESS_URL=https://mt384.us1.dbt.com/

# ADLS Storage
ADLS_ACCOUNT_NAME=your_account_name
ADLS_ACCOUNT_KEY=your_account_key

# Server
SERVER_PORT=8000
CONFIG_FILE_PATH=../ConfigurationFile.csv
```

## API Endpoints

### Health Check
```
GET /api/health
```

### Get All Tables
```
GET /api/tables
```

Returns list of configured tables.

### Get Table Lineage
```
GET /api/lineage/{table_name}
```

Returns complete lineage data including:
- ADLS file information
- ADF pipeline status
- DBT staging layer status
- DBT star layer status

## Using the Application

1. Open `http://localhost:3000` in your browser
2. Search for a table by name
3. Click on a table to view its lineage
4. See detailed information for each layer:
   - **ADLS**: Data lake file path and status
   - **ADF**: Azure Data Factory pipeline runs
   - **DBT STG**: Staging layer transformation jobs
   - **DBT STAR**: Star layer analytics jobs

## Testing Without Credentials

The application includes mock data support. It will work with:
- Mock ADLS responses
- Mock ADF pipeline runs
- Mock DBT job runs

This allows testing the UI and API without real Azure/DBT credentials.

## Testing with Real Credentials

1. Update `.env` with your actual credentials
2. Restart the backend server
3. The application will fetch real data from your systems

## API Testing

Using curl:

```bash
# Health check
curl http://localhost:8000/api/health

# Get all tables
curl http://localhost:8000/api/tables

# Get lineage for specific table
curl http://localhost:8000/api/lineage/customers
```

## Troubleshooting

### Backend won't start
- Check if port 8000 is available
- Verify Python version: `python --version`
- Check dependencies: `pip list`

### Frontend won't start
- Check if port 3000 is available
- Verify Node version: `node --version`
- Clear npm cache: `npm cache clean --force`

### API returns errors
- Check `.env` file exists
- Verify config file path is correct
- Check ConfigurationFile.csv is in project root

### CORS errors
- Backend has CORS enabled for all origins
- Check both servers are running
- Verify proxy config in vite.config.js

## Future Enhancements

- Real-time pipeline monitoring
- Historical lineage tracking
- Data quality metrics integration
- Custom lineage rules
- Deployment to cloud platforms

## License

MIT

## Support

For issues or questions, please check the backend/frontend logs or enable debug mode in development.
