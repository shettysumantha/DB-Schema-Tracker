# Database Schema Documentation Portal

A professional web application to manage database connections, search tables, extract schema metadata, and generate documentation in Excel or Google Sheets format.

---

## Table of Contents

1. [Prerequisites & Tools Required](#prerequisites--tools-required)
2. [Project Structure](#project-structure)
3. [Setup Instructions](#setup-instructions)
4. [Google Sheets Setup](#google-sheets-setup)
5. [Running the Application](#running-the-application)
6. [API Endpoints](#api-endpoints)
7. [Features](#features)
8. [File Locations](#file-locations)

---

## Prerequisites & Tools Required

### Backend Requirements

- **Python 3.8+** — Download from https://www.python.org/downloads/
- **PostgreSQL** — Download from https://www.postgresql.org/download/
- **pip** (comes with Python)

### Frontend Requirements

- **Node.js 18+** — Download from https://nodejs.org/
- **npm** (comes with Node.js)

### Optional

- **Google Sheets API credentials** — For publishing to Google Sheets

### Verify Installation

```bash
# Check Python version
python --version

# Check pip
pip --version

# Check Node.js version
node -v

# Check npm version
npm -v
```

---

## Project Structure

```
c:\GMRS Table Structures\
├── backend.py                      # FastAPI backend server
├── config.py                       # Configuration (Google Sheet ID, paths)
├── database.py                     # PostgreSQL connection & schema extraction
├── connection_manager.py           # Database connection persistence
├── job_store.py                    # Job tracking & artifact storage
├── document_generator.py           # Excel workbook generation
├── schema_analyzer.py              # Schema analysis utilities
├── schema_comparator.py            # Schema change detection
├── google_sheets.py                # Google Sheets integration
├── local_writer.py                 # Local CSV output (fallback)
├── sync_cashcounter_schema.py      # Legacy Cash Counter sync script
├── sync_database_schema.py         # Generic database sync script
├── requirements.txt                # Python dependencies
├── config.py                       # Configuration
│
├── frontend/                       # React frontend
│   ├── src/
│   │   ├── App.tsx                # Main React component
│   │   ├── main.tsx               # Entry point
│   │   ├── styles.css             # Styling
│   │   └── services/
│   │       └── api.ts             # API service layer
│   ├── package.json               # Frontend dependencies
│   ├── tsconfig.json              # TypeScript config
│   ├── vite.config.ts             # Vite build config
│   └── index.html                 # HTML template
│
├── downloads/                      # Generated Excel files
├── local_docs/                     # Local CSV output (fallback)
├── connections.json               # Saved database connections
├── jobs.json                       # Job tracking
└── google_credentials.json        # Google Sheets credentials (DO NOT COMMIT)
```

---

## Setup Instructions

### Step 1: Install Python Dependencies

```bash
# Navigate to the project folder
cd c:\GMRS Table Structures

# Install required Python packages
pip install -r requirements.txt
```

**What gets installed:**

- `fastapi` — Web framework
- `uvicorn` — ASGI server
- `psycopg2-binary` — PostgreSQL driver
- `openpyxl` — Excel generation
- `gspread` — Google Sheets API
- `google-auth` — Google authentication
- `xlrd` — Read Excel files
- `python-multipart` — File upload support

### Step 2: Create Google Sheets Service Account (Optional but Recommended)

If you want to publish documentation to Google Sheets:

#### 2.1 Create a Google Cloud Project

1. Go to https://console.cloud.google.com/
2. Click **Create Project**
3. Enter project name: `Database Schema Documentation`
4. Click **Create**

#### 2.2 Enable Google Sheets API

1. In the Google Cloud Console, search for **Google Sheets API**
2. Click **Enable**

#### 2.3 Create a Service Account

1. Go to **APIs & Services** > **Credentials**
2. Click **Create Credentials** > **Service Account**
3. Enter service account name: `schema-doc-service`
4. Click **Create and Continue**
5. Grant role: **Editor** (or more restricted if preferred)
6. Click **Create**

#### 2.4 Create and Download JSON Key

1. In the **Service Accounts** list, click on your new service account
2. Go to the **Keys** tab
3. Click **Add Key** > **Create new key**
4. Select **JSON**
5. Click **Create**
6. The JSON file will download automatically

#### 2.5 Place the JSON File

1. Copy the downloaded JSON file
2. Paste it in the project root folder
3. Rename it to: **`google_credentials.json`**

```bash
# Location should be:
c:\GMRS Table Structures\google_credentials.json
```

#### 2.6 Create a Google Sheet

1. Go to https://docs.google.com/spreadsheets
2. Click **Create new spreadsheet**
3. Name it: `Database Schema Documentation`
4. Copy the spreadsheet ID from the URL:
   - URL: `https://docs.google.com/spreadsheets/d/1j1u_F3bwjTVEClpQWiRos8Tt6Ax8XuVxJUgMzkOGKBg/edit`
   - ID: `1j1u_F3bwjTVEClpQWiRos8Tt6Ax8XuVxJUgMzkOGKBg`

#### 2.7 Share Google Sheet with Service Account

1. Open your Google Sheet
2. Click **Share** (top right)
3. Copy the service account email from the JSON file (looks like: `schema-doc-service@PROJECT_ID.iam.gserviceaccount.com`)
4. Paste the email in the Share dialog
5. Give it **Editor** access
6. Click **Share**

#### 2.8 Update config.py

```python
# Open c:\GMRS Table Structures\config.py
# Update this line with your Google Sheet ID:
GOOGLE_SHEET_ID = "1j1u_F3bwjTVEClpQWiRos8Tt6Ax8XuVxJUgMzkOGKBg"
```

### Step 3: Install Frontend Dependencies

```bash
# Navigate to frontend folder
cd c:\GMRS Table Structures\frontend

# Install npm packages
npm install
```

This installs:
- `react` — UI framework
- `react-dom` — React rendering
- `vite` — Build tool
- `typescript` — Type checking

---

## Running the Application

### Terminal 1: Start the Backend API

```bash
cd c:\GMRS Table Structures

# Run the FastAPI server
uvicorn backend:app --reload --host 0.0.0.0 --port 8000
```

**Expected output:**
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete
```

**Backend API will be available at:**
- http://localhost:8000/api/
- http://localhost:8000/docs (interactive API documentation)

### Terminal 2: Start the Frontend Application

```bash
cd c:\GMRS Table Structures\frontend

# Start Vite development server
npm run dev
```

**Expected output:**
```
  VITE v5.4.0  ready in XXX ms

  ➜  Local:   http://localhost:5173/
```

### Terminal 3 (Optional): Run Database Sync Script

To synchronize database schema with Google Sheets:

```bash
cd c:\GMRS Table Structures

# Run generic sync script (uses first saved connection)
python sync_database_schema.py

# Or legacy Cash Counter sync
python sync_cashcounter_schema.py
```

---

## Using the Frontend

1. **Open your browser**
   - Navigate to: http://localhost:5173

2. **Add a Database Connection**
   - Click **+ Add Database**
   - Fill in connection details:
     - Name: `gas_malaysia`
     - Host: `10.0.1.32`
     - Port: `5432`
     - Database: `gas_malaysia`
     - Username: `gas_malaysia_user`
     - Password: `your_password`
     - Schema: `public`
   - Click **Test Connection**
   - Click **Save Database**

3. **Search and Document Tables**
   - Select database from dropdown
   - Search for table name (e.g., "receipts")
   - Click table to select it
   - Click **Submit**
   - Download documentation

4. **Bulk Documentation Upload**
   - Prepare CSV/XLSX file with table names
   - Upload file
   - System processes all tables
   - Download complete documentation
   - Optionally publish to Google Sheets

---

## API Endpoints

### Database Management

```bash
# List all connections
GET http://localhost:8000/api/databases

# Test connection
POST http://localhost:8000/api/databases/test
Body: { "name": "...", "host": "...", "port": 5432, "database": "...", "username": "...", "password": "...", "schema": "public" }

# Save connection
POST http://localhost:8000/api/databases
Body: { "name": "...", "host": "...", ... }

# Delete connection
DELETE http://localhost:8000/api/databases/{connection_id}
```

### Table Operations

```bash
# List tables in database
GET http://localhost:8000/api/tables?connection_id=xxx

# Search tables
GET http://localhost:8000/api/tables/search?connection_id=xxx&q=receipt

# Get table schema
GET http://localhost:8000/api/tables/{table_name}/schema?connection_id=xxx
```

### Documentation

```bash
# Document single table
POST http://localhost:8000/api/documentation/table
Body: { "connection_id": "...", "table_name": "..." }

# Upload bulk table list
POST http://localhost:8000/api/documentation/upload?connection_id=xxx
Body: multipart/form-data file upload

# Download documentation
GET http://localhost:8000/api/documentation/{job_id}/download

# Publish to Google Sheets
POST http://localhost:8000/api/documentation/{job_id}/google-sheet
```

---

## Features

### Backend Features
- ✅ Dynamic PostgreSQL connection management
- ✅ Table discovery and search with partial matching
- ✅ Complete schema extraction (columns, types, constraints, foreign keys)
- ✅ Single and bulk documentation generation
- ✅ Excel workbook generation with multiple sheets
- ✅ Google Sheets integration
- ✅ CSV and Excel file upload processing
- ✅ Job tracking and artifact storage

### Frontend Features
- ✅ Professional dashboard UI
- ✅ Database connection management
- ✅ Interactive table search with debouncing
- ✅ Single-table schema display
- ✅ Bulk file upload (CSV/XLSX/XLS)
- ✅ Processing summary with status tracking
- ✅ Excel download
- ✅ Google Sheets publishing
- ✅ Error handling and user-friendly messages

---

## File Locations

| File/Folder | Purpose |
|-------------|---------|
| `backend.py` | Main FastAPI application |
| `database.py` | PostgreSQL connection & queries |
| `connection_manager.py` | Save/load database connections |
| `document_generator.py` | Excel generation |
| `google_sheets.py` | Google Sheets API wrapper |
| `config.py` | Configuration (Google Sheet ID) |
| `frontend/src/App.tsx` | Main React component |
| `frontend/src/services/api.ts` | Frontend API calls |
| `connections.json` | Saved database connections (auto-generated) |
| `jobs.json` | Job tracking (auto-generated) |
| `downloads/` | Generated Excel files |
| `local_docs/` | CSV fallback output |
| `google_credentials.json` | Google Sheets credentials (DO NOT COMMIT) |

---

## Troubleshooting

### Backend won't start
- Check if port 8000 is in use: `netstat -ano | findstr :8000`
- Restart Uvicorn on a different port: `uvicorn backend:app --port 8001`

### Frontend won't start
- Make sure you're in the `frontend` folder: `cd frontend`
- Clear npm cache: `npm cache clean --force`
- Delete `node_modules`: `rm -r node_modules`
- Reinstall: `npm install`

### PostgreSQL connection fails
- Verify PostgreSQL is running
- Check host/port are correct
- Verify username/password

### Google Sheets API fails
- Verify `google_credentials.json` is in the correct location
- Check service account email has access to the Google Sheet
- Verify `GOOGLE_SHEET_ID` in `config.py` is correct

### npm installation fails in PowerShell
- Use Command Prompt (cmd.exe) instead
- Or run: `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`

---

## Security Notes

- **Never commit** `google_credentials.json` to version control
- **Never display** database passwords in logs or UI
- Use strong passwords for database connections
- Keep Google Sheets credentials private
- Restrict file uploads to authorized users only

---

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review API documentation at http://localhost:8000/docs
3. Check browser console for frontend errors
4. Check terminal output for backend errors

