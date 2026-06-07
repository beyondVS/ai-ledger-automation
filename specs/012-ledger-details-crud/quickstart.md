# Developer Quickstart Guide: Ledger Detail Edit & Delete Modal (CRUD)

This guide walks you through the local setup and verification process for testing the manual ledger entry modifications and deletions.

## 1. Local Database Migrations

Apply the database schema changes (addition of the `category` column to the `Ledger` table):

```bash
# 1. Generate new migration files based on model updates
uv run python backend/src/manage.py makemigrations ledgers

# 2. Apply migrations to RDBMS
uv run python backend/src/manage.py migrate
```

## 2. Launch Local Servers

Start the Backend API Server and Frontend Vite Dev Server:

```bash
# In Backend terminal (port 8080)
uv run python backend/src/manage.py runserver 0.0.0.0:8080

# In Frontend terminal
cd frontend
npm run dev
```

Open your browser at `http://localhost:5173`, log in, and test the edit/delete buttons on the ledger items in the dashboard list.

## 3. Run Quality Gates & Tests

### Backend Unit Tests (DRF Views & Serializers)
Verify user isolation, PATCH validators, and CASCADE deletes:

```bash
cd backend
uv run pytest tests/ledgers/
```

### Frontend Component Tests (Vue/Vitest)
Verify modal rendering, validation states, and deletion warning flows:

```bash
cd frontend
npm run test -- --run
```
