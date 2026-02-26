# Nejum ERP - Project Context

## Project Overview
Nejum ERP (**Nejum ERP - Proje Dokümantasyonu**) is a lightweight, modular, and high-performance ERP system designed for production environments. It is built to provide production facilities with simple but powerful control over their operations, starting from no existing software infrastructure.

**Mission:** "We build small systems that give people big control over their work." To create the simplest open-source industrial automation system.

## Tech Stack
- **Backend:** Django 4.2 (Python 3.x)
- **Database:** PostgreSQL (Production), SQLite (Local/Testing)
- **Frontend:**
  - Django Templates with **HTMX** for dynamic interactions.
  - **Crispy Forms** with **Bootstrap 5** for UI components.
  - **jQuery** and **Alpine.js** for client-side logic.
- **Asynchronous Tasks:** Celery + Redis (for image uploads and email automation).
- **Storage/CDN:** Cloudinary (Current), Bunny CDN (Transitioning).
- **External Integrations:** Gmail API (OAuth2), Google Calendar, Google Drive.

## Core Modules & Status
| Module | Status | Description |
| :--- | :--- | :--- |
| **Accounting** | ✅ Complete | Product & SKU management, basic inventory. |
| **CRM / Marketing** | 🛠️ In Progress | Lead management, automated email sequences, product editing. |
| **Operations** | 🛠️ In Progress | Order processing and task tracking. |
| **Email Automation** | 🛠️ In Progress | 6-email follow-up sequences using Gmail OAuth2. |

## Building and Running
1. **Setup Environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Or venv\Scripts\activate on Windows
   pip install -r requirements.txt
   ```
2. **Configuration:**
   - Create a `.env` file based on `settings.py` requirements (SECRET_KEY, DB credentials, Cloudinary, etc.).
3. **Database:**
   ```bash
   python manage.py migrate
   ```
4. **Execution:**
   ```bash
   python manage.py runserver
   ```
5. **Testing:**
   ```bash
   python manage.py test
   ```

## Development Conventions & Best Practices
- **UI Responsiveness:** Prefer **HTMX** for partial page updates to avoid full reloads.
- **Performance:** For long-running operations (like image uploads or external API calls), use asynchronous background tasks (Celery).
- **Forms:** Always use `django-crispy-forms` with the Bootstrap 5 template pack.
- **Coding Style:** Follow standard Django patterns. Modularize logic into `services.py` or `utils.py` where appropriate to keep views clean.
- **API:** When building for the frontend (Next.js), use Django Rest Framework (DRF).

## Key Documentation Files
- `README.md`: High-level project intro.
- `EMAIL_AUTOMATION_PLAN.md`: Roadmap for the Gmail sequence system.
- `PERFORMANCE_OPTIMIZATION_PLAN.md`: Current focus on speeding up product updates and uploads.
- `PROJE_DOKUMANTASYONU.md`: General project documentation (in Turkish).
- `GMAIL_API_SETUP.md`: Instructions for setting up Google OAuth credentials.

## Directory Structure Notes
- **`/` (Repository Root):** Contains project documentation (`.md` files), root configuration, and the main `erp/` application directory.
- **`/erp/` (Project Root):** The core Django project directory containing `manage.py`, environment files (`.env`), and all functional apps.
- **`/erp/erp/`:** The main configuration package (settings, global URLs, templates).
- **`/erp/accounting/`, `/erp/crm/`, etc.:** Modular Django apps implementing specific ERP features.
- **`/playground/`:** Scratchpad for testing scripts, data processing, and independent code exploration.
