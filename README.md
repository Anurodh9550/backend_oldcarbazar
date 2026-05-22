# Old Car Bazar — Django REST Framework Backend

Production-grade backend for the Old Car Bazar marketplace, built with:

| Layer | Tech |
|---|---|
| Framework | Django 5.1 + Django REST Framework 3.15 |
| Auth | JWT (djangorestframework-simplejwt) — separate user + admin tokens |
| Database | PostgreSQL (default) or SQLite (zero-config local) |
| Filters | django-filter + DRF SearchFilter/OrderingFilter |
| API docs | drf-spectacular (OpenAPI 3 + Swagger UI) |
| CORS | django-cors-headers |
| Env | django-environ |

---

## 1. Quick start (SQLite — zero config)

Open PowerShell **inside the `backend/` folder**:

```powershell
# 1. Create + activate venv
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2. Install dependencies
pip install -r requirements.txt

# 3. Env file (defaults are fine for SQLite)
copy .env.example .env

# 4. Migrations
python manage.py makemigrations users cities listings inquiries adminpanel
python manage.py migrate

# 5. Seed demo data (36 cities, 3 admins, 6 buyers, 18 cars, 10 inquiries)
python manage.py seed

# 6. Run the server
python manage.py runserver 8000
```

API base URL: `http://127.0.0.1:8000/api/v1/`
Swagger UI:    `http://127.0.0.1:8000/api/docs/`
Django admin:  `http://127.0.0.1:8000/admin/` (create a superuser with `python manage.py createsuperuser`)

---

## 2. Switching to PostgreSQL (Supabase / Neon / local)

In `backend/.env`, replace the `DATABASE_URL` line:

```env
# Supabase
DATABASE_URL=postgres://postgres:[PASSWORD]@db.[REF].supabase.co:5432/postgres

# Neon
DATABASE_URL=postgres://[USER]:[PASS]@[HOST]/neondb?sslmode=require

# Local Postgres
DATABASE_URL=postgres://postgres:postgres@localhost:5432/oldcarbazar
```

Then re-run:

```powershell
python manage.py migrate
python manage.py seed
```

---

## 3. Demo credentials (after running `seed`)

| Type | Email | Password |
|---|---|---|
| Super admin | `admin@oldcarbazar.com` | `admin@123` |
| Moderator | `moderator@oldcarbazar.com` | `mod@123` |
| Support | `support@oldcarbazar.com` | `support@123` |
| Buyer | `amit.kumar@gmail.com` | `password123` |
| Buyer | `priya.v@gmail.com` | `password123` |

(All 6 demo buyers share the password `password123`.)

---

## 4. API reference

All endpoints are versioned under `/api/v1/`.

### Auth (end users)

| Method | URL | Description |
|---|---|---|
| POST | `/auth/register/` | Create new buyer; returns access + refresh JWT |
| POST | `/auth/login/` | `{ identifier, password }` — phone or email; returns JWT pair + user |
| POST | `/auth/refresh/` | Refresh access token |
| GET, PATCH | `/auth/me/` | Get / update current user profile |
| POST | `/auth/otp/send/` | `{ target, purpose }` — sends OTP (console-only in dev) |
| POST | `/auth/otp/verify/` | `{ target, code, purpose }` |

### Listings (cars)

| Method | URL | Auth | Description |
|---|---|---|---|
| GET | `/listings/` | public | Approved + active listings. Query params: `city`, `brand`, `fuel`, `transmission`, `body_type`, `min_price`, `max_price`, `max_kms`, `ownership`, `featured`, `search`, `ordering` |
| GET | `/listings/<id>/` | public | Listing detail (auto-increments view count) |
| POST | `/listings/` | user | Create new listing (auto-promotes user to seller) |
| GET | `/listings/mine/` | user | Current user's listings |
| POST | `/listings/<id>/status/` | owner | Body: `{ status: active\|sold\|draft }` |
| DELETE | `/listings/<id>/` | owner / admin | Delete a listing |
| POST | `/listings/<id>/moderate/` | admin | Body: `{ status, reason? }` |
| POST | `/listings/<id>/feature/` | admin | Body: `{ featured: bool }` |
| POST | `/listings/<id>/flag/` | admin | Body: `{ reason }` |
| POST | `/listings/<id>/clear-flag/` | admin | Clear flag |

### Inquiries

| Method | URL | Auth | Description |
|---|---|---|---|
| POST | `/inquiries/` | public | Create inquiry on a listing |
| GET | `/inquiries/` | admin | List all inquiries (filter by status, channel, city) |
| GET | `/inquiries/mine/` | user | Buyer/seller's own inquiries |
| POST | `/inquiries/<id>/status/` | admin | Body: `{ status: new\|responded\|closed\|spam }` |

### Cities

| Method | URL | Description |
|---|---|---|
| GET | `/cities/` | Public list (filter `popular=true`) |

### Admin panel

| Method | URL | Description |
|---|---|---|
| POST | `/admin-panel/login/` | `{ email, password }` → admin JWT pair |
| GET | `/admin-panel/me/` | Current admin operator |
| GET | `/admin-panel/dashboard/` | Aggregated stats (listings, users, inquiries, breakdowns) |
| GET, PATCH | `/admin-panel/settings/` | Singleton platform settings |
| GET | `/admin-panel/activity/` | Admin activity feed |
| GET | `/admin-panel/users/` | All registered users (search, filter `role`, `status`) |
| GET | `/admin-panel/users/<id>/` | User detail |
| POST | `/admin-panel/users/<id>/block/` | Body: `{ blocked: bool }` |
| POST | `/admin-panel/users/<id>/note/` | Body: `{ note }` |
| GET | `/admin-panel/users/counts/` | User totals by role + status |

---

## 5. Example requests

### Buyer login

```bash
curl -X POST http://127.0.0.1:8000/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"identifier": "amit.kumar@gmail.com", "password": "password123"}'
```

Response:
```json
{
  "access": "eyJhbGc…",
  "refresh": "eyJhbGc…",
  "user": { "id": "…", "name": "Amit Kumar", "role": "buyer", … }
}
```

### Post a listing

```bash
curl -X POST http://127.0.0.1:8000/api/v1/listings/ \
  -H "Authorization: Bearer <access-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "brand": "Honda", "model": "City", "year": 2021,
    "fuel": "Petrol", "transmission": "Automatic", "kms": 25000,
    "owners": "1st Owner", "price": "9.5", "city": "Delhi",
    "seller_name": "Amit Kumar", "phone": "9876512345"
  }'
```

### Admin login + dashboard

```bash
curl -X POST http://127.0.0.1:8000/api/v1/admin-panel/login/ \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@oldcarbazar.com", "password": "admin@123"}'

curl http://127.0.0.1:8000/api/v1/admin-panel/dashboard/ \
  -H "Authorization: Bearer <admin-access-token>"
```

---

## 6. Project structure

```
backend/
├── manage.py
├── requirements.txt
├── .env / .env.example
├── config/                     # Django project
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
└── apps/
    ├── users/                  # buyer/seller accounts + OTP
    │   ├── models.py           # User (UUID, role, status), OtpCode
    │   ├── serializers.py
    │   ├── views.py
    │   ├── urls.py
    │   ├── permissions.py
    │   └── managers.py
    ├── cities/                 # Indian cities catalog
    ├── listings/               # Car listings + photos
    │   ├── models.py           # Listing, ListingPhoto
    │   ├── serializers.py      # read + write + moderation
    │   ├── filters.py          # django-filter FilterSet
    │   ├── permissions.py
    │   └── views.py            # ListingViewSet with custom actions
    ├── inquiries/              # buyer ↔ seller messages
    ├── adminpanel/             # admin operators, activity, settings
    │   ├── models.py           # Admin, ActivityLog, AppSettings
    │   ├── authentication.py   # OcbJWTAuthentication (dual user/admin)
    │   ├── permissions.py      # IsAdminOperator
    │   ├── serializers.py
    │   └── views.py
    └── core/                   # Shared utils + management commands
        └── management/commands/seed.py
```

---

## 7. Architecture decisions

- **Custom User model with UUID PK** — matches the frontend's user shape, plus admin can reference users by UUID safely.
- **Separate `Admin` model** — operator accounts are distinct from end users (different password store, different roles, no marketplace activity).
- **Two JWT shapes** — user tokens (default `user_id` claim) and admin tokens (`is_admin: true` + `admin_id`). A single `OcbJWTAuthentication` class handles both.
- **All-PUBLIC reads, AUTH writes** — listings + inquiries can be created publicly (matching the existing UX), but moderation and user management are admin-only.
- **Idempotent seed** — `python manage.py seed` is safe to run multiple times; only inserts what's missing. Use `--reset` to wipe seed data and reinsert.
- **`AppSettings.singleton()`** — single-row platform config (matches the frontend's settings page).

---

## 8. Frontend integration

The existing Next.js app under `/src` can talk to this backend over HTTP.
In any client component:

```ts
const res = await fetch("http://127.0.0.1:8000/api/v1/auth/login/", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ identifier: email, password }),
});
const { access, refresh, user } = await res.json();
localStorage.setItem("ocb_access", access);
```

Update `next.config.ts` to allow images from your image host (Cloudinary/Supabase Storage when you switch from data URLs).

---

## 9. Production deployment

```powershell
$Env:DEBUG = "False"
python manage.py collectstatic --noinput
python manage.py migrate
gunicorn config.wsgi:application --bind 0.0.0.0:8000
```

Recommended stack:
- **App**: Railway / Render / Fly.io (single container)
- **DB**: Supabase Postgres / Neon
- **Static + media**: WhiteNoise (already configured) or S3
- **Reverse proxy**: Nginx in front of gunicorn
- **TLS**: Let's Encrypt / managed by host

---

## 10. Useful commands

```powershell
python manage.py makemigrations
python manage.py migrate
python manage.py seed              # demo data
python manage.py seed --reset      # wipe + reseed
python manage.py createsuperuser   # Django admin login
python manage.py shell             # interactive REPL
python manage.py runserver         # dev server
```

---

API docs auto-generated at: **http://127.0.0.1:8000/api/docs/**
