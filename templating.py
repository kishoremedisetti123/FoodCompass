"""
Templates setup — wires up Jinja2 the way the existing templates expect.

The existing templates (carried over unmodified from the Flask app) call
`url_for('blueprint.endpoint', **params)` and `url_for('static', filename=...)`,
which is Flask's calling convention. FastAPI's own `request.url_for(name, **params)`
uses a flat route-name registry and a `path=` kwarg for static files, not `filename=`.

Rather than edit any template, this module builds a small ROUTES table mapping
the old Flask-style dotted names to FastAPI route names + the param-name FastAPI
expects, and exposes a `url_for(name, **params)` Jinja global that translates
between the two conventions transparently.
"""
from fastapi import Request
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="templates")


class AnonymousUser:
    """Mirrors Flask-Login's AnonymousUserMixin so `current_user.is_authenticated`
    works in templates even when nobody is logged in."""
    is_authenticated = False
    name = None
    role = None


ANONYMOUS_USER = AnonymousUser()

# Flask dotted endpoint name -> FastAPI route `name=` it maps to
_ROUTE_NAME_MAP = {
    "views.index": "index",
    "views.donor_dashboard": "donor_dashboard",
    "views.volunteer_dashboard": "volunteer_dashboard",
    "views.organization_dashboard": "organization_dashboard",
    "views.role_redirect": "role_redirect",
    "views.admin_organizations": "admin_organizations",
    "auth.signup_page": "signup_page",
    "auth.login_page": "login_page",
}


def _make_url_for(request: Request):
    def url_for(name, **params):
        if name == "static":
            # Flask: url_for('static', filename='css/styles.css')
            filename = params.get("filename", "")
            return request.url_for("static", path=filename)

        route_name = _ROUTE_NAME_MAP.get(name, name)

        # Our routes (signup_page, login_page, etc.) take role as a query
        # param, not a path param — Starlette's url_for only understands
        # path params, so split query-style kwargs off and append them as
        # a real query string instead.
        query_params = {}
        if "role" in params:
            query_params["role"] = params.pop("role")

        url = str(request.url_for(route_name, **params))
        if query_params:
            qs = "&".join(f"{k}={v}" for k, v in query_params.items())
            url = f"{url}?{qs}"
        return url

    return url_for


def render(request: Request, template_name: str, db_user_context: dict | None = None, **extra):
    """
    Renders a template the same way Flask's render_template(...) did, but also
    injects a Flask-compatible `url_for` and `current_user` into the context.
    `db_user_context` should be {"current_user": <User|AnonymousUser>}.
    """
    context = {"request": request, "url_for": _make_url_for(request)}
    if db_user_context:
        context.update(db_user_context)
    context.update(extra)
    return templates.TemplateResponse(template_name, context)
