# FoodCompass — FastAPI backend

Same app, same frontend (templates, CSS, JS — copied over unmodified), the
backend engine swapped from Flask to FastAPI. Every feature behaves
identically; this README focuses on what changed underneath and how to run it.

## What's identical to the Flask version

- All HTML templates, `static/css/styles.css`, and every file in `static/js/` — **byte-for-byte unchanged**.
- Every URL path (`/`, `/donor`, `/api/donations`, `/admin/organizations`, etc.)
- The full donation lifecycle: post → claim → assign volunteer → pick up → confirm delivery → (or cancel)
- Organization verification gate + the demo admin approval panel
- The activity log / transparency trail per donation
- Demo accounts via `seed.py` (same emails, same `demo1234` password)

## What changed under the hood

| | Flask version | FastAPI version |
|---|---|---|
| ORM | Flask-SQLAlchemy | Plain SQLAlchemy 2.0 (declarative), with a `get_db()` dependency per request |
| Auth | Flask-Login (cookie session + `current_user`) | Hand-rolled signed-cookie session (`itsdangerous`) + a `get_current_user` dependency — see `auth_session.py` |
| Password hashing | Werkzeug's `generate_password_hash` | Self-contained PBKDF2 implementation in `werkzeug_security.py` (stdlib only, no Werkzeug dependency) |
| Request validation | Manual dict access (`request.get_json()`) | Pydantic models — every request body is now type-checked and validated automatically |
| Routing | Flask Blueprints | FastAPI `APIRouter`s (`routers/auth.py`, `routers/donations.py`, `routers/views.py`) |
| Templating | Flask's `render_template` + Flask's `url_for` | Starlette's `Jinja2Templates` + a compatibility shim (`templating.py`) that reproduces Flask's exact `url_for('blueprint.endpoint', ...)` calling convention, so **no template had to be edited** |
| Server | Flask dev server / gunicorn (WSGI) | Uvicorn (ASGI) / gunicorn with `UvicornWorker` |
| API docs | None | Free interactive docs at `/docs` (Swagger UI) and `/redoc` |

### Why the templates didn't need to change

The existing templates call Flask-style `url_for('views.index')`,
`url_for('auth.login_page', role='donor')`, and `url_for('static', filename='css/styles.css')`.
FastAPI's native `request.url_for(...)` uses a different convention (flat
route names, `path=` instead of `filename=`, and it can't take query-string
params like `role=` at all).

`templating.py` solves this with a small `url_for(name, **params)` Jinja
global that:
1. Maps the old dotted names (`"views.index"`, `"auth.login_page"`) to the
   FastAPI route names registered in `routers/*.py`.
2. Translates `filename=` to the `path=` FastAPI expects for static files.
3. Splits off query-string-style params (like `role`) and appends them as
   an actual `?role=...` query string, since Starlette's `url_for` only
   understands path params.

This is the one piece of real "glue code" the port needed — everything
else is a fairly mechanical translation.

### A genuine improvement from the move

Pydantic validates every request body automatically. For example, signup
now rejects malformed email addresses with a clear `422` before your code
ever runs — the Flask version had no such check and would have silently
created an account with a garbage email.

## Project structure

```
foodcompass-fastapi/
├── app.py                  # FastAPI app, static mount, router registration, startup (creates tables)
├── database.py              # SQLAlchemy engine/session + get_db() dependency
├── models.py                  # User, Donation, DonationLog (SQLAlchemy 2.0 declarative)
├── auth_session.py             # signed-cookie sessions, get_current_user, require_role()
├── werkzeug_security.py          # standalone PBKDF2 password hashing (no Flask/Werkzeug dependency)
├── templating.py                  # Jinja2Templates + Flask-compatible url_for shim
├── routers/
│   ├── auth.py                      # signup/login/logout pages + JSON API
│   ├── donations.py                  # full donation lifecycle API
│   └── views.py                       # dashboards, role redirects, admin verification panel
├── seed.py                              # demo accounts + sample donations
├── templates/                            # unchanged from the Flask version
├── static/                                # unchanged from the Flask version
├── requirements.txt
├── Procfile                                  # gunicorn + uvicorn worker, for Render/Heroku-style deploys
└── render.yaml                                # one-click Render config
```

## Running it locally

```bash
cd foodcompass-fastapi
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

# optional: populate demo accounts + sample donations
python3 seed.py

# development (auto-reload on file changes)
uvicorn app:app --reload --port 5000
```

Visit `http://127.0.0.1:5000`. Interactive API docs are at `http://127.0.0.1:5000/docs`.

### Demo accounts (after running `seed.py`)

Same as the Flask version — all passwords are `demo1234`.

| Role | Email | Notes |
|---|---|---|
| Donor | `donor@demo.com` | Has 3 sample donations posted |
| Organization | `org@demo.com` | Already **approved** — can claim immediately |
| Organization | `pendingorg@demo.com` | Still **pending** — shows the verification gate |
| Volunteer | `volunteer@demo.com` | No pickups yet — claim something as `org@demo.com` first |

The demo script from the Flask README applies unchanged — same steps, same accounts.

## Deploying to Render

1. Push this folder to a GitHub repo.
2. On Render: **New → Web Service**, connect the repo — it reads `render.yaml` automatically.
3. Same caveat as the Flask version: Render's **free tier disk is ephemeral**.
   SQLite resets on every restart/redeploy. Run `python3 seed.py` again via
   the Render shell after a deploy if you need data to survive a demo, or
   attach a free Render Postgres instance and set `DATABASE_URL` — the app
   already reads that env var, no code changes needed (see `database.py`).

## Where to extend

Same extension points as the Flask version still apply — they're now just in different files:
- **Real-time updates** instead of polling: `static/js/*.js` still poll every 15s; swapping to FastAPI's native WebSocket support (`@app.websocket(...)`) would make updates instant.
- **Maps/geolocation**: add lat/lng columns to `Donation` in `models.py`, geocode in `routers/donations.py`'s `create_donation`.
- **QR/OTP delivery confirmation**: swap the button in `organization.js` for a scan/OTP step that still calls `POST /api/donations/{id}/confirm-delivery` — no backend change needed.
- **Notifications**: `log_event()` in `routers/donations.py` fires at every state change — natural hook for an SMS/email call.
- **Admin security**: `/admin/organizations` still allows any logged-in user in, for demo convenience. Add an `is_admin` column to `User` and a `require_role("admin")` dependency before using this beyond a demo.
