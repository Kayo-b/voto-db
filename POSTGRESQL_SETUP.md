# PostgreSQL Deployment Guide for VotoDB

## Understanding the Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│    Frontend     │    │    Backend      │    │   PostgreSQL    │
│   (React)       │───▶│   (FastAPI)     │───▶│   (Database)    │
│   Port 3000     │    │   Port 8001     │    │   Port 5432     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

**PostgreSQL is a separate service** - it doesn't run "inside" your backend. Your FastAPI backend **connects to** PostgreSQL as a client.

## Deployment Options

### 🐳 **Option 1: Docker (Recommended for Development)**

#### **Quick Start:**
```bash
# Start PostgreSQL
./postgres.sh start

# Start your app (detects and uses PostgreSQL automatically)
./start_simple.sh
```

#### **Manual Docker:**
```bash
# Run PostgreSQL container
docker run -d \
  --name votodb-postgres \
  -e POSTGRES_DB=votodb \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -p 5432:5432 \
  postgres:15

# Initialize database
cd backend && python setup_database.py init

# Start backend with database
python -m uvicorn main_db:app --port 8001
```

### 💻 **Option 2: Local PostgreSQL Installation**

#### **Ubuntu/Debian:**
```bash
# Install PostgreSQL
sudo apt update
sudo apt install postgresql postgresql-contrib

# Start service
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Create database
sudo -u postgres createdb votodb
sudo -u postgres psql -c "ALTER USER postgres PASSWORD 'postgres';"

# Set environment
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/votodb"
```

#### **macOS:**
```bash
# Install with Homebrew
brew install postgresql
brew services start postgresql

# Create database
createdb votodb

# Set environment
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/votodb"
```

#### **Windows:**
```bash
# Download PostgreSQL installer from postgresql.org
# Or use WSL with Ubuntu instructions
```

### ☁️ **Option 3: Cloud PostgreSQL (Production)**

#### **Railway (Free tier available):**
```bash
# 1. Create Railway account
# 2. Create PostgreSQL service
# 3. Copy connection URL
export DATABASE_URL="postgresql://user:pass@host:port/database"
```

#### **Supabase (Free tier available):**
```bash
# 1. Create Supabase project
# 2. Go to Settings → Database
# 3. Copy connection string
export DATABASE_URL="postgresql://user:pass@host:port/database"
```

#### **AWS RDS, Google Cloud SQL, etc.:**
```bash
# Follow cloud provider setup
# Get connection URL from console
export DATABASE_URL="postgresql://user:pass@host:port/database"
```

## Updated Start Scripts

### **Simple Start (Recommended)**
```bash
./start_simple.sh
# Automatically detects and starts PostgreSQL if available
# Falls back to file cache if not
```

### **Advanced Start (Full Control)**
```bash
./start.sh
# Enhanced script with detailed PostgreSQL management
```

### **PostgreSQL Management**
```bash
./postgres.sh start    # Start database
./postgres.sh stop     # Stop database  
./postgres.sh status   # Check status
./postgres.sh shell    # Connect to database
./postgres.sh init     # Initialize schema
./postgres.sh stats    # Show statistics
```

## Environment Variables

### **Required for PostgreSQL:**
```bash
# Option A: Full connection URL
export DATABASE_URL="postgresql://user:password@host:port/database"

# Option B: Individual components  
export DB_HOST=localhost
export DB_PORT=5432
export DB_USER=postgres
export DB_PASSWORD=postgres
export DB_NAME=votodb
```

### **Optional Configuration:**
```bash
export USE_DATABASE=true          # Enable/disable database mode
export DB_ECHO=false             # Enable SQL query logging
export REDIS_URL=redis://localhost:6379  # Redis for API caching
```

## How the System Chooses Backend

Your enhanced start script now **automatically selects** the best backend:

```bash
1. Check if PostgreSQL is available
   ├─ Available → Use main_db.py (Enhanced with PostgreSQL)
   └─ Not available → Use main_v2.py (Legacy file cache)

2. Try to start PostgreSQL if not running
   ├─ Docker available → Start container
   ├─ Local PostgreSQL → Use existing
   └─ None available → Fallback mode

3. Initialize database schema if needed
4. Start appropriate backend version
```

## Production Deployment

### **With Docker Compose:**
```yaml
# docker-compose.yml
version: '3.8'
services:
  database:
    image: postgres:15
    environment:
      POSTGRES_DB: votodb
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
  
  backend:
    build: ./backend
    environment:
      DATABASE_URL: postgresql://postgres:${DB_PASSWORD}@database:5432/votodb
    depends_on:
      - database
    ports:
      - "8001:8001"
  
  frontend:
    build: ./frontend
    ports:
      - "3000:3000"

volumes:
  postgres_data:
```

### **With Cloud Deployment:**
```bash
# 1. Deploy PostgreSQL to cloud (Railway, Supabase, etc.)
# 2. Set DATABASE_URL environment variable
# 3. Deploy backend with main_db.py
# 4. Deploy frontend
```

## Troubleshooting

### **PostgreSQL Won't Start:**
```bash
# Check if port is in use
lsof -i :5432

# Check Docker containers
docker ps -a | grep postgres

# Check logs
./postgres.sh logs
```

### **Connection Issues:**
```bash
# Test connection
psql "postgresql://postgres:postgres@localhost:5432/votodb" -c "SELECT 1;"

# Check environment variables
echo $DATABASE_URL

# Verify backend is using database mode
curl http://localhost:8001/health
```

### **Data Migration:**
```bash
# Re-run setup to import existing cache
python setup_database.py init

# Check what data was imported
python setup_database.py stats
```

## Summary

**The database (PostgreSQL) runs separately** from your backend. Your start script now:

1. **Automatically detects** if PostgreSQL is available
2. **Starts PostgreSQL** with Docker if needed  
3. **Chooses appropriate backend** (database vs file cache)
4. **Initializes database** if using PostgreSQL
5. **Falls back gracefully** if database unavailable

**Just run `./start_simple.sh` and it handles everything automatically!**