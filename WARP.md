# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Project Overview

**Nejum ERP** is a lightweight, modular web-based ERP system designed for production facilities. It helps businesses manage accounting, marketing, CRM, and operations through a Django-based application.

- **Tech Stack**: Django 4.2.4 + PostgreSQL + HTMX
- **License**: AGPL v3.0
- **Organization**: nejum-org on GitHub

## Development Commands

### Environment Setup

```bash
# Install dependencies (from erp/ directory)
pip install -r erp/requirements.txt

# Set up environment variables
# Create erp/.env file with:
# - SECRET_KEY
# - DEBUG (True/False)
# - DB_ENGINE (e.g., django.db.backends.postgresql)
# - DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT
# - Cloudinary credentials for media storage
```

### Database Operations

```bash
# Run migrations
python erp/manage.py migrate

# Create migrations after model changes
python erp/manage.py makemigrations

# Create superuser for admin access
python erp/manage.py createsuperuser

# Access Django shell
python erp/manage.py shell
```

### Running the Application

```bash
# Development server (from project root)
python erp/manage.py runserver

# Run on specific port
python erp/manage.py runserver 8080

# Run on specific host (for local network testing)
python erp/manage.py runserver 0.0.0.0:8000
```

### Testing

```bash
# Run all tests
python erp/manage.py test

# Run tests for specific app
python erp/manage.py test accounting
python erp/manage.py test crm
python erp/manage.py test marketing
python erp/manage.py test operating

# Run with verbosity
python erp/manage.py test --verbosity=2
```

### Static Files

```bash
# Collect static files for production (uses whitenoise)
python erp/manage.py collectstatic
```

## Architecture Overview

### Project Structure

The Django project follows a modular app-based architecture:

```
erp/                    # Main Django project directory
├── erp/                # Core project settings and configuration
│   ├── settings.py     # Django settings (DB, apps, middleware)
│   ├── urls.py         # Root URL routing
│   └── context_processors.py  # Global template context
├── accounting/         # Financial tracking and transactions
├── crm/               # Customer Relationship Management
├── marketing/         # Product catalog and collections
├── operating/         # Operations and work-in-progress tracking
├── authentication/    # User authentication
├── todo/              # Task management
├── static/            # Static assets (CSS, JS, images)
├── templates/         # Shared HTML templates
└── media/             # User-uploaded files (served via Cloudinary)
```

### Core Applications

#### Accounting Module
- **Purpose**: Double-entry accounting system with multi-currency support
- **Key Models**:
  - `Book`: Separate accounting entities (business divisions/projects)
  - `AssetCash`: Cash accounts per book/currency
  - `CurrencyExchangeRate`: Exchange rates for multi-currency transactions
  - `StakeholderBook`: Links members to books with ownership shares
  - `TransactionEntry`/`CashTransactionEntry`: Generic transaction system using ContentTypes
  - Raw material and finished goods receipts with inventory tracking
- **Architecture Pattern**: Uses Django's ContentType framework for polymorphic relationships between transactions and various accounting entities

#### CRM Module
- **Purpose**: Manage customers, contacts, suppliers, and relationships
- **Key Models**:
  - `Company`: Customer companies with status tracking (prospect/qualified)
  - `Contact`: Individual contacts linked to companies
  - `Supplier`: Vendor management
  - `ClientGroup`: Categorization system
  - `Note`: Notes linked to companies or contacts
- **Pattern**: Flexible relationship modeling with optional company linkage for contacts

#### Marketing Module
- **Purpose**: Product catalog management with variant support
- **Key Models**:
  - `Product`: Base product with SKU, pricing, variants
  - `ProductVariant`: Product variations with separate SKUs
  - `ProductCollection`: Curated product groupings
  - `ProductCategory`: Hierarchical product taxonomy
  - File attachments for products (images, videos) stored on Cloudinary
- **Media Handling**: Custom file validators (size, type) with Cloudinary CDN integration
- **Features**: PostgreSQL ArrayField for tags, HTMX for dynamic UX

#### Operating Module
- **Purpose**: Manufacturing and operations management
- **Key Models**:
  - `RawMaterialGood`: Raw material inventory tracking
  - `RawMaterialGoodReceipt`: Purchase receipts from suppliers
  - `RawMaterialGoodItem`: Line items for receipts
  - `WorkInProgressGood`: WIP tracking linked to orders
- **Pattern**: Receipt-based inventory system that links to accounting module

### Important Design Patterns

1. **Multi-Currency Architecture**
   - Base currency defined in settings (defaults to USD)
   - `CurrencyExchangeRate` model tracks conversion rates
   - All monetary transactions store both local and base currency values
   - Function `get_base_currency()` provides centralized currency access

2. **Book-Based Multi-Entity Accounting**
   - Each business division/project has its own `Book`
   - Stakeholders have shares in books via `StakeholderBook`
   - All transactions are scoped to a specific book
   - Enables separate P&L and balance sheets per entity

3. **Generic Relations for Transactions**
   - Uses Django's ContentType framework for polymorphic relationships
   - Transactions can link to various models (invoices, expenses, transfers)
   - `allowed_equity_models()` function defines permitted transaction types

4. **Product Variant System**
   - Products can have multiple variants (size, color, etc.)
   - Variants have separate SKUs, pricing, and inventory
   - Product files can be associated with specific variants

5. **Media Management**
   - Cloudinary integration for all user-uploaded media
   - Custom validators for file size (10MB max) and type
   - Files organized by product SKU in folder structure

### Configuration Notes

- **Database**: PostgreSQL required (uses ArrayField and specific features)
- **Middleware**: WhiteNoise for static files, HTMX middleware enabled
- **Authentication**: Custom authentication app (django-allauth code commented out)
- **Static Files**: Served via WhiteNoise in production
- **Media Files**: Served via Cloudinary CDN
- **CSRF**: Configured for deployment on vercel.app, demfirat.com, nejum.com domains

### URL Routing Structure

Root URLs in `erp/urls.py`:
- `/` - Landing page
- `/dashboard/` - Main dashboard
- `/accounting/` - Accounting module URLs
- `/crm/` - CRM module URLs
- `/marketing/` - Marketing module URLs
- `/operating/` - Operations module URLs
- `/todo/` - Task management
- `/authentication/` - Login/logout
- `/admin/` - Django admin
- `/reports/` - Reporting views

### Database Migration Approach

The project has extensive migrations (39+ in accounting alone), indicating active development. When making model changes:
- Always create migrations via `makemigrations`
- Test migrations with `migrate`
- Be aware of existing constraints and relationships
- Consider data migration needs for production

### Dependencies of Note

- `django-htmx`: HTMX integration for dynamic UI
- `cloudinary`: CDN for media files
- `whitenoise`: Static file serving
- `psycopg2`: PostgreSQL adapter
- `python-decouple`: Environment variable management
- `forex-python`/`CurrencyConverter`: Exchange rate handling
- `openpyxl`, `pandas`: Data import/export
- `reportlab`: PDF generation

## Development Guidelines

### Adding New Features

1. **New Models**: Add to appropriate app's `models.py`, then run `makemigrations` and `migrate`
2. **New Views**: Class-based views are used throughout (see `views.py` in each app)
3. **URL Routing**: Add to app's `urls.py`, include in root `erp/urls.py` if needed
4. **Templates**: Place in app's `templates/` directory or shared `templates/`
5. **Static Assets**: Add to `static/` directory

### Working with Accounting

- All monetary transactions should go through the transaction entry system
- Always specify a `Book` for accounting entries
- Use `get_base_currency()` for currency operations
- Exchange rates are fetched and stored automatically
- Consider both local and base currency when querying balances

### Working with Products

- Products can be standalone or have variants
- If a product has variants, SKU/price should be on the variant, not the product
- All product media goes through Cloudinary
- Use `validate_file_size` and `validate_file_type` for uploads
- Tags are stored in PostgreSQL ArrayField

### Environment Variables Required

Essential `.env` variables in `erp/` directory:
- `SECRET_KEY`: Django secret key
- `DEBUG`: Boolean for debug mode
- `DB_ENGINE`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`: Database config
- Cloudinary credentials (check settings.py for exact names)

### Common Patterns

- **Generic Foreign Keys**: Used for flexible model relationships (see accounting transactions)
- **Related Names**: Consistently used for reverse relations (e.g., `related_name='products'`)
- **Auto Timestamps**: Most models use `auto_now_add` for `created_at`
- **String Representations**: All models implement `__str__()` for admin display
- **Custom Validation**: Models use `clean()` method for business logic validation
