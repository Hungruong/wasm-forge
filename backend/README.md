# Backend Setup Instructions

## Prerequisites
- Python 3.11+ installed
- Access to Akamai Managed PostgreSQL database

## Step 1: Create a Virtual Environment
Navigate to the backend directory and create a virtual environment:

```bash
cd /home/ubuntu/wasm-ai-platform/backend
python3 -m venv venv
```

## Step 2: Activate the Virtual Environment

```bash
source venv/bin/activate
```

## Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

## Step 4: Configure Environment
Copy the example environment file and fill in your database credentials:

```bash
cp env.example .env
```

Edit `.env` and set your database password:
```
DB_PASS=your_actual_password_here
```

## Step 5: Add SSL Certificate
Download the CA certificate from the Akamai dashboard and save it to:

```
backend/certs/ca-certificate.crt
```

## Step 6: Test Database Connection
Verify that the backend can connect to PostgreSQL:

```bash
python test_db.py
```

Expected output:
```
============================================================
  WASM AI Platform — Database Connection Test
============================================================

[1/3] Testing connection...
  ✓ Connected: PostgreSQL 15.16 on x86_64-pc-linux-gnu, ...

[2/3] Creating tables (drop + recreate)...
  ✓ Tables created

[3/3] Testing CRUD...
  ✓ Insert OK
  ✓ Query OK: name=__test_plugin__, size=64B
  ✓ Delete OK (test data cleaned up)

============================================================
  ✓ Database is fully operational!
============================================================
```

## Step 7: Run the Application

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## Step 8: Access the Application
Open your web browser and navigate to:

```
http://172.234.27.110:8000/docs
```

You should now see the API documentation.

### Health Check Endpoints
- `GET /health` — API liveness check
- `GET /health/db` — PostgreSQL connection check
- `GET /health/ollama` — Ollama AI server check

## Notes
- Ensure that your firewall settings allow traffic on port 8000.
- Never commit `.env` or `certs/` to git — they contain secrets.
- To deactivate the virtual environment, simply run:

```bash
deactivate
```