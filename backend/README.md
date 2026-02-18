# Backend Setup Instructions

## Prerequisites
Ensure you have Python installed on your system.

## Step 1: Create a Virtual Environment
Navigate to the backend directory and create a virtual environment:

```bash
cd /home/ubuntu/wasm-ai-platform/backend
python3 -m venv venv
```

## Step 2: Activate the Virtual Environment
Activate the virtual environment using the following command:

```bash
source venv/bin/activate
```

## Step 3: Install Dependencies
Make sure to install the required dependencies. You can do this by running:

```bash
pip install -r requirements.txt
```

## Step 4: Run the Application
Start the application using Uvicorn:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## Step 5: Access the Application
Open your web browser and navigate to:

```
http://172.234.27.110:8000/docs
```

You should now see the API documentation.

## Notes
- Ensure that your firewall settings allow traffic on port 8000.
- To deactivate the virtual environment, simply run:

```bash
deactivate
```