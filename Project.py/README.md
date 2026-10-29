# Smart AgroConnect Rwanda

Smart AgroConnect is a Django web application that connects farmers, buyers, and transporters. It implements the first usable scope from the project notes and uses SQLite by default so it runs locally without a separate database server.

## Run locally on Windows

From the repository root:

```powershell
py -m pip install -r requirements.txt
py Project.py\manage.py migrate
py Project.py\Wajp.py
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000). Stop the development server with `Ctrl+C`.

Create an administrator account when needed:

```powershell
py Project.py\manage.py createsuperuser
```

The admin dashboard is at `/admin/`. Django's built-in authentication handles password hashing, sessions, and CSRF protection.

## Languages

The interface supports English and Kinyarwanda. Use the `EN` and `RW` buttons in the header to change languages. The Kinyarwanda catalog is in `locale/rw/LC_MESSAGES/django.po`; regenerate the compiled `django.mo` file after editing translations with Django's `compilemessages` command.

The Kinyarwanda wording is a draft and should be reviewed by a fluent speaker before production use.

## Implemented workflows

- Role-based sign-up and login for farmers, buyers, and transporters.
- Farmer farm and crop records, with a transparent planting-date-plus-duration harvest estimate.
- Produce listings and future buyer demands.
- Potential matching by crop name, unit, quantity, district, availability date, and a negotiable price ceiling.
- Buyer order requests, farmer acceptance/rejection, agreed prices, collection status, and delivery status.
- Transport requests that transporters with a registered vehicle type and capacity can claim and update.
- In-app updates as orders are accepted, agreed, collected, and delivered.
- Post-harvest storage records and user-configured inspection/storage reminders.
- Expense tracking and a simple delivered-order revenue/profit calculation.
- In-app order notifications and actual-record administrator counts.

## Important limits

Harvest estimates need reliable crop and variety guidance supplied by the user; a date estimate does not confirm harvest readiness. Buyer matches are not guaranteed sales. Storage reminders are user-configured reminders, not food-safety assessments. The weather page explicitly indicates that no forecast provider is connected. SMS/USSD, offline synchronization, voice assistance, sensors, uploaded product photos, payments, and cooperative/agricultural-officer workflows remain future work.

## Database options

SQLite is used by default. To use MySQL, install a compatible `mysqlclient` package, set `DB_ENGINE=mysql`, and provide `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST` (and optionally `DB_PORT`) as environment variables before running migrations. Do not put database passwords or production secrets in source code.

For deployment, set `DJANGO_DEBUG=false`, set a unique `DJANGO_SECRET_KEY`, configure `DJANGO_ALLOWED_HOSTS`, use HTTPS, and follow Django's deployment checklist. The built-in development server is for local development only.
