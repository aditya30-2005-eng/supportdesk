# SupportDesk

SupportDesk is a helpdesk ticketing system I built with Django REST Framework and React.
Customers raise support tickets, an admin assigns them to agents, agents work on them, and everyone gets an email at each important step through Celery and Redis.

## Features

**Customer**
- Register and log in
- Raise a ticket with a title, description, category and priority
- See only their own tickets, with filters, search and pagination
- Comment on their own tickets
- Edit the title, description, category or priority while the ticket is still open
- Get an email whenever the status of their ticket changes

**Agent**
- See only the tickets assigned to them
- Change the status (open, in progress, resolved, closed)
- Comment on assigned tickets
- Get an email when a ticket is assigned to them

**Admin**
- See every ticket and filter unassigned ones
- Assign tickets to agents and delete tickets
- Add categories, change user roles and deactivate users
- Dashboard with counts by status and priority, average resolution time and agent workload
- Get an email for every new ticket

**Under the hood**
- JWT login with short-lived access tokens, refresh token rotation and logout (blacklist)
- Every role rule is checked on the server with DRF permission classes and queryset filtering
- Emails are sent by a Celery worker, triggered by Django signals, only after the database commit
- An email is sent only when the status or assignee really changes
- Swagger docs generated from the code
- 58 backend tests

## Tech stack

| Layer | Tools |
| --- | --- |
| Backend | Python 3.13, Django 6.1, Django REST Framework, SimpleJWT, django-filter, django-cors-headers, drf-spectacular |
| Database | PostgreSQL 17 with `psycopg` 3 |
| Async | Django signals, Celery 5, Redis 7 |
| Email | Django email backends (console in development, SMTP for Mailtrap or Gmail) |
| Frontend | React 19, Vite, React Router, Axios, plain CSS |
| Testing | Django test runner with DRF `APITestCase` |
| Tooling | Docker Compose, black, ruff, oxlint, Prettier, GitHub Actions, Render blueprint |

## Architecture

```mermaid
flowchart LR
    Browser["React app<br/>(Vite)"] -- "REST + JWT" --> API["Django REST Framework"]
    API -- "Django ORM" --> DB[("PostgreSQL")]
    API -- "post_save signal<br/>task.delay()" --> Redis[("Redis broker")]
    Redis --> Worker["Celery worker"]
    Worker -- "Django ORM" --> DB
    Worker -- "send_mail" --> Mail["Email<br/>console / Mailtrap / Gmail"]
```

The React app only talks to the API. The API saves tickets in PostgreSQL. When a ticket is created or changed, a signal in the `notifications` app puts a task on the Redis queue after the transaction commits. A separate Celery worker picks up the task, loads the ticket and sends the email. This keeps the API response fast even if the mail server is slow.

## Screenshots

| Login | Ticket list (admin) |
| --- | --- |
| ![Login page](docs/screenshots/login.png) | ![Ticket list](docs/screenshots/ticket-list.png) |

| Create ticket (customer) | Ticket details (admin) |
| --- | --- |
| ![Create ticket form](docs/screenshots/create-ticket.png) | ![Ticket details](docs/screenshots/ticket-details.png) |

| Admin dashboard | Swagger docs |
| --- | --- |
| ![Admin dashboard](docs/screenshots/admin-dashboard.png) | ![Swagger docs](docs/screenshots/swagger-docs.png) |

## Running the project

You need Python 3.11 or newer, Node.js 20 or newer, and either Docker or your own PostgreSQL and Redis.

### With Docker (recommended)

Docker runs PostgreSQL and Redis. Django, Celery and React run on your machine.

```bash
# 1. Start PostgreSQL (host port 5433) and Redis (port 6379)
docker compose up -d

# 2. Backend
cd backend
python -m venv venv
# Windows PowerShell:  venv\Scripts\Activate.ps1
# macOS / Linux:       source venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env          # Windows PowerShell: Copy-Item .env.example .env
```

Open `backend/.env` and set `DJANGO_SECRET_KEY` to a random value. You can make one with:

```bash
python -c "import secrets; print(secrets.token_urlsafe(50))"
```

Then create the tables and the demo data, and start the API:

```bash
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```

In a **second terminal**, start the Celery worker from the `backend` folder (with the virtual environment active):

```bash
# macOS / Linux
celery -A config worker -l info

# Windows: the default pool does not work on Windows, so use the solo pool
celery -A config worker -l info --pool=solo
```

In a **third terminal**, start the frontend:

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 and log in with one of the demo accounts below.
The emails are printed in the Celery worker terminal.

### Without Docker

1. Install PostgreSQL and create a database and user, for example:
   ```sql
   CREATE USER supportdesk WITH PASSWORD 'supportdesk';
   CREATE DATABASE supportdesk OWNER supportdesk;
   ```
2. In `backend/.env`, point `DATABASE_URL` at it, for example
   `postgres://supportdesk:supportdesk@localhost:5432/supportdesk`.
3. Redis:
   - If you have Redis running, keep `CELERY_BROKER_URL=redis://localhost:6379/0` and start the worker as shown above (`--pool=solo` on Windows).
   - If you do not have Redis, set `CELERY_TASK_ALWAYS_EAGER=True`. Tasks then run inside the Django process and the emails are printed in the `runserver` terminal. No worker is needed.
4. Follow the same backend and frontend steps as above, skipping `docker compose up -d`.

### Sending real emails

The console backend is the default. To use Mailtrap or Gmail, set these in `backend/.env`:

```env
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=sandbox.smtp.mailtrap.io   # or smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-username
EMAIL_HOST_PASSWORD=your-password     # for Gmail, use an app password
EMAIL_USE_TLS=True
```

Restart the Celery worker after changing `.env`.

## Environment variables

Backend (`backend/.env`):

| Variable | Default | What it does |
| --- | --- | --- |
| `DJANGO_SECRET_KEY` | none (required) | Django secret key. The app refuses to start without it. |
| `DJANGO_DEBUG` | `False` | Turns on debug mode. Use `True` only in development. |
| `DJANGO_ALLOWED_HOSTS` | `localhost,127.0.0.1` | Comma-separated host names the API answers to. |
| `DATABASE_URL` | `postgres://supportdesk:supportdesk@localhost:5433/supportdesk` | PostgreSQL connection string. |
| `CELERY_BROKER_URL` | `redis://localhost:6379/0` | Redis URL used by Celery. |
| `CELERY_TASK_ALWAYS_EAGER` | `False` | Run tasks inline, without Redis or a worker. |
| `CORS_ALLOWED_ORIGINS` | `http://localhost:5173` | Frontend origins allowed to call the API. |
| `CSRF_TRUSTED_ORIGINS` | `http://localhost:5173` | Trusted origins for CSRF checks. |
| `FRONTEND_URL` | `http://localhost:5173` | Used to build ticket links inside emails. |
| `EMAIL_BACKEND` | console backend | Django email backend class. |
| `EMAIL_HOST`, `EMAIL_PORT` | empty, `587` | SMTP server. |
| `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` | empty | SMTP login. |
| `EMAIL_USE_TLS` | `True` | Use STARTTLS for SMTP. |
| `DEFAULT_FROM_EMAIL` | `SupportDesk <no-reply@supportdesk.local>` | Sender address. |
| `DJANGO_SECURE_SSL_REDIRECT` | `True` (when debug is off) | Redirect HTTP to HTTPS in production. |

Frontend (`frontend/.env`, optional):

| Variable | Default | What it does |
| --- | --- | --- |
| `VITE_API_URL` | `http://localhost:8000/api` | Base URL of the API. |

## Demo accounts

`python manage.py seed_demo` creates these **test-only** accounts. All of them use the password `Demo@12345`.

| Role | Username | Name |
| --- | --- | --- |
| Admin | `admin` | Asha Verma |
| Agent | `agent1` | Rahul Mehta |
| Agent | `agent2` | Priya Nair |
| Customer | `customer1` | Karan Shah |
| Customer | `customer2` | Neha Iyer |

It also creates 4 categories and 20 tickets with a mix of statuses, priorities and comments. The command can be run again; it resets the demo customers' tickets. It does not send any emails.
The `admin` account can also log in to the Django admin at http://localhost:8000/admin/.

## API

Interactive docs (Swagger UI): http://localhost:8000/api/docs/
OpenAPI schema: http://localhost:8000/api/schema/

All endpoints are under `/api/`. Everything except register, login and refresh needs an `Authorization: Bearer <access token>` header.

| Method | Endpoint | Who can use it | Notes |
| --- | --- | --- | --- |
| POST | `auth/register/` | Anyone | Always creates a customer |
| POST | `auth/login/` | Anyone | Returns `access`, `refresh` and the user |
| POST | `auth/refresh/` | Anyone with a refresh token | Returns a new access and refresh token |
| POST | `auth/logout/` | Logged in | Blacklists the refresh token |
| GET | `auth/me/` | Logged in | Current user |
| GET | `tickets/` | Logged in | Customers: own tickets. Agents: assigned tickets. Admins: all |
| POST | `tickets/` | Customer | Creates a ticket |
| GET | `tickets/<id>/` | Owner, assigned agent, admin | Includes comments |
| PATCH | `tickets/<id>/` | Owner, assigned agent, admin | Customer: text fields while open. Agent: status. Admin: status, priority, category |
| DELETE | `tickets/<id>/` | Admin | |
| POST | `tickets/<id>/assign/` | Admin | Body: `{"agent": <user id>}` |
| GET, POST | `tickets/<id>/comments/` | Owner, assigned agent, admin | |
| GET | `categories/` | Logged in | Not paginated |
| POST, PATCH, DELETE | `categories/`, `categories/<id>/` | Admin | |
| GET | `users/` | Admin | Filter with `?role=agent` |
| PATCH | `users/<id>/` | Admin | Change `role` or `is_active` (not your own) |
| GET | `dashboard/stats/` | Admin | Counts, average resolution time, agent workload |

Ticket list query parameters:

| Parameter | Example | Meaning |
| --- | --- | --- |
| `status` | `?status=open` | Filter by status |
| `priority` | `?priority=urgent` | Filter by priority |
| `category` | `?category=2` | Filter by category id |
| `assigned_to` | `?assigned_to=3` | Filter by agent id |
| `unassigned` | `?unassigned=true` | Only tickets with no agent |
| `created_after`, `created_before` | `?created_after=2026-10-01` | Date range |
| `search` | `?search=refund` | Search in title and description |
| `ordering` | `?ordering=-priority_rank` | `created_at`, `updated_at`, `priority_rank`, `status` (prefix `-` for descending) |
| `page`, `page_size` | `?page=2&page_size=20` | Pagination (10 per page by default, 100 at most) |

## Tests

The tests use the real PostgreSQL database (Django creates a separate test database), run Celery tasks eagerly and store emails in Django's in-memory outbox.

```bash
cd backend
python manage.py test
```

Last run: **58 tests, all passing.**

They cover registration and login, token rotation and logout, the permission rules for each role, ticket create/update/delete, the assign endpoint, comments, filters, search, ordering and pagination, the dashboard numbers, a query-count check against N+1 queries, and the signal and Celery email behaviour.

Code style checks:

```bash
cd backend && ruff check . && black --check .
cd frontend && npm run lint && npm run build
```

GitHub Actions runs the same checks and the tests on every push (`.github/workflows/ci.yml`).

## Project structure

```
supportdesk/
├── backend/
│   ├── config/            # settings, URLs, Celery app, pagination
│   ├── accounts/          # custom User model, auth API, user admin API, permissions
│   ├── tickets/           # Category, Ticket, Comment models, serializers, views, filters,
│   │   │                  # dashboard stats, seed_demo command
│   │   └── tests/         # ticket, filter and dashboard tests
│   ├── notifications/     # signals, Celery tasks and email content
│   ├── manage.py
│   ├── requirements.txt
│   ├── requirements-dev.txt
│   └── .env.example
├── frontend/
│   └── src/
│       ├── api/           # Axios client with token refresh, endpoint functions
│       ├── auth/          # auth context and hook
│       ├── components/    # layout, route guard, badges, pagination, state messages
│       ├── pages/         # login, register, tickets, ticket details, dashboard, manage
│       └── utils/         # labels, formatting, useFetch hook
├── docs/
│   ├── PROJECT_REPORT.md
│   └── screenshots/
├── .github/workflows/ci.yml
├── docker-compose.yml
├── render.yaml
├── LICENSE
└── README.md
```

## Deployment (optional)

`render.yaml` is a Render Blueprint that describes the API, the Celery worker, Redis (Key Value), PostgreSQL and the static React site. I have not deployed it yet, so the service URLs inside it are the default names and may need to be changed after the first deploy. Background workers are a paid feature on Render.

## Future improvements

- File attachments on tickets and comments (for screenshots)
- Real-time updates with WebSockets (Django Channels) instead of reloading
- Email replies that turn into comments
- SLA timers and automatic escalation of old urgent tickets with Celery beat
- Internal notes that customers cannot see
- Move the refresh token into an httpOnly cookie
- Frontend tests with Vitest and React Testing Library

## Project report

A detailed report on the design, database, API, security and testing is in [docs/PROJECT_REPORT.md](docs/PROJECT_REPORT.md).

## License

MIT. See [LICENSE](LICENSE).
