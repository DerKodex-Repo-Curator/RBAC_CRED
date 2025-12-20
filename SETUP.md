# 🚀 RBAC Policy Engine - Setup Guide

This guide will help you set up and run the RBAC Policy Engine on your local machine.

---

## 📋 Prerequisites

Before you begin, ensure you have the following installed:

| Tool | Version | Download Link |
|------|---------|---------------|
| Python | 3.10+ | [python.org](https://www.python.org/downloads/) |
| Git | Latest | [git-scm.com](https://git-scm.com/downloads) |
| Docker (Optional) | Latest | [docker.com](https://www.docker.com/products/docker-desktop/) |

---

## 🔧 Method 1: Local Setup (Recommended for Development)

### Step 1: Clone the Repository

```bash
git clone <repository-url>
cd RBAC_CRED
```

### Step 2: Create Virtual Environment

**Windows (PowerShell):**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**Windows (Command Prompt):**
```cmd
python -m venv venv
venv\Scripts\activate.bat
```

**Linux/macOS:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 4: Configure Environment Variables

Create a `.env` file in the project root:

```bash
# Copy the example file
cp .env.example .env
```

Edit `.env` and add your Anthropic API key:

```env
# Anthropic Claude API Key (Required)
ANTHROPIC_API_KEY=your-api-key-here

# Server Configuration
API_HOST=0.0.0.0
API_PORT=8000
UI_PORT=8501

# Environment
ENVIRONMENT=development
DEBUG=true
```

> ⚠️ **Important:** Never commit your `.env` file to version control!

### Step 5: Run the Application

You need to run **two terminals** - one for the API server and one for the UI.

**Terminal 1 - Start API Server:**
```bash
# Make sure venv is activated
python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
```

**Terminal 2 - Start Streamlit UI:**
```bash
# Make sure venv is activated
streamlit run src/ui/app.py --server.port 8501
```

### Step 6: Access the Application

| Service | URL |
|---------|-----|
| 🎨 **Chat UI** | http://localhost:8501 |
| 📚 **API Docs** | http://localhost:8000/docs |
| 🔄 **API (Swagger)** | http://localhost:8000/redoc |
| ❤️ **Health Check** | http://localhost:8000/health |

---

## 🐳 Method 2: Docker Setup (Recommended for Production)

### Option A: Using Docker Compose (Easiest)

#### Step 1: Ensure Docker is Running

Make sure Docker Desktop is running on your machine.

#### Step 2: Configure Environment

Create a `.env` file with your API key:

```env
ANTHROPIC_API_KEY=your-api-key-here
```

#### Step 3: Build and Run

```bash
# Build and start all services
docker-compose up --build

# Or run in detached mode (background)
docker-compose up --build -d
```

#### Step 4: Access the Application

- **Chat UI:** http://localhost:8501
- **API Docs:** http://localhost:8000/docs

#### Step 5: Stop the Application

```bash
# Stop all services
docker-compose down

# Stop and remove volumes (clean slate)
docker-compose down -v
```

---

### Option B: Using Docker Manually

#### Step 1: Build the Docker Image

```bash
docker build -t rbac-policy-engine .
```

#### Step 2: Run the Container

```bash
docker run -d \
  --name rbac-engine \
  -p 8000:8000 \
  -p 8501:8501 \
  -e ANTHROPIC_API_KEY=your-api-key-here \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/output:/app/output \
  rbac-policy-engine
```

#### Step 3: View Logs

```bash
docker logs -f rbac-engine
```

#### Step 4: Stop the Container

```bash
docker stop rbac-engine
docker rm rbac-engine
```

---

## 🧪 Running Tests

### Run All Tests

```bash
# Activate virtual environment first
pytest tests/ -v
```

### Run Specific Test File

```bash
pytest tests/test_policy_builder.py -v
pytest tests/test_decision_engine.py -v
pytest tests/test_mock_apis.py -v
pytest tests/test_api.py -v
```

### Run with Coverage

```bash
pip install pytest-cov
pytest tests/ -v --cov=src --cov-report=html
```

---

## 📁 Project Structure

```
RBAC_CRED/
├── src/
│   ├── api/            # FastAPI backend
│   │   └── main.py     # API endpoints
│   ├── agent/          # Conversation agent
│   │   ├── conversation_agent.py
│   │   └── session_manager.py
│   ├── core/           # Policy engine core
│   │   ├── policy_builder.py
│   │   ├── decision_engine.py
│   │   └── schema_cache.py
│   ├── mock_apis/      # Discovery APIs
│   │   ├── roles_api.py
│   │   ├── resource_api.py
│   │   ├── context_api.py
│   │   └── validator_api.py
│   ├── models/         # Pydantic models
│   │   ├── policy.py
│   │   ├── role.py
│   │   ├── resource.py
│   │   └── context.py
│   └── ui/             # Streamlit UI
│       └── app.py
├── tests/              # Unit tests
├── data/               # Session storage
├── output/             # Exported policies
├── .streamlit/         # Streamlit config
├── docker-compose.yml  # Docker compose config
├── Dockerfile          # Docker build file
├── requirements.txt    # Python dependencies
├── .env.example        # Environment template
├── README.md           # Project overview
├── DESIGN.md           # Architecture docs
└── SETUP.md            # This file
```

---

## 🔧 Troubleshooting

### Issue: "Cannot connect to API server"

**Solution:** Make sure the API server is running on port 8000:
```bash
python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000
```

### Issue: "ANTHROPIC_API_KEY not found"

**Solution:** Ensure your `.env` file exists and contains a valid API key:
```bash
cat .env  # Check if file exists
echo "ANTHROPIC_API_KEY=sk-ant-..." > .env  # Create/update
```

### Issue: Port already in use

**Solution:** Kill the process using the port:

**Windows:**
```powershell
# Find process using port 8000
netstat -ano | findstr :8000
# Kill process (replace PID with actual process ID)
taskkill /PID <PID> /F
```

**Linux/macOS:**
```bash
# Kill process on port 8000
kill $(lsof -t -i:8000)
```

### Issue: Docker build fails

**Solution:** Clear Docker cache and rebuild:
```bash
docker system prune -a
docker-compose build --no-cache
```

### Issue: Streamlit shows dark theme

**Solution:** The light theme should be automatically applied. If not:
1. Click the **⋮** menu (top right corner)
2. Go to **Settings**
3. Under **Theme**, select **Light**

---

## 🔑 API Key Setup

### Getting an Anthropic API Key

1. Go to [console.anthropic.com](https://console.anthropic.com/)
2. Sign up or log in
3. Navigate to **API Keys**
4. Create a new API key
5. Copy the key and add it to your `.env` file

---

## 💡 Quick Start Commands

### Using Make (if available)

```bash
make setup      # Create venv and install deps
make run-api    # Start API server
make run-ui     # Start Streamlit UI
make run        # Start both (requires tmux)
make test       # Run tests
make clean      # Clean up
```

### Manual Commands Summary

```bash
# Setup
python -m venv venv
source venv/bin/activate  # or .\venv\Scripts\Activate.ps1 on Windows
pip install -r requirements.txt

# Run API
python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload

# Run UI (new terminal)
streamlit run src/ui/app.py

# Run Tests
pytest tests/ -v

# Docker
docker-compose up --build
```

---

## 📞 Support

If you encounter any issues:

1. Check the **Troubleshooting** section above
2. Review the logs for error messages
3. Ensure all prerequisites are installed
4. Verify your API key is valid

---

**Happy Policy Building! 🔐**
