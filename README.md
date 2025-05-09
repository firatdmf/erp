# Nejum ERP

**A lightweight, modular ERP system for production environments without modern software infrastructure.**

---

## Why Nejum ERP?

Nejum ERP is a lightweight, modular web-based ERP system designed to help production facilities get up and running fast — even if they currently have no ERP in place.

This project lives under the `nejum-org` GitHub organization and is part of a broader mission to build the simplest open-source industrial automation system.

## ✨ Core Values

> **"We build small systems that give people big control over their work."**

## Tech Stack

- **Backend:** Django
- **Database:** PostgreSQL
- **Frontend:** Next.js (or custom depending on client)
- **API:** RESTful (planned)
- **Deployment:** Docker (planned)

## ✅ Current Modules

| Module       | Status         | Description                                               |
|--------------|----------------|-----------------------------------------------------------|
| Accounting   | ✅ Complete    | Basic accounting functionality (products, SKUs)           |
| Marketing    | 🛠️ In Progress | CRM, Product editor, tagging, automation groundwork       |
| Operations   | 🛠️ In Progress | Basic CRM features to manage customer data                |

---

## 🔜 Upcoming Features

- Product Variant UX improvements
- Cold email/newsletter system using product data
- Inventory alerts and automation
- Operational modules (tasks, machines, schedules)
- Open API layer for frontend integration
- Role-based permissions and team access

---
## License

[![AGPL v3](https://img.shields.io/badge/license-AGPLv3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0.html)

This project is licensed under the GNU Affero General Public License v3.0.

## 🤝 Community

We are preparing to open this project to the community. Stay tuned for:

- Public roadmap
- Contribution guide
- Discussions
- Discord or forum space

---

## 🚀 Getting Started

To clone and run the project locally:

```bash
git clone https://github.com/nejum-org/erp.git
cd erp
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver

