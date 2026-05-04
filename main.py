import sqlite3
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Cookie, FastAPI, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from db_create import DATABASE_PATH, create_database, get_connection


BASE_DIR = Path(__file__).resolve().parent


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_database()
    yield


app = FastAPI(title="Message Board", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")


def get_current_user(username: str | None) -> sqlite3.Row | None:
    if not username:
        return None
    with get_connection() as connection:
        return connection.execute(
            "SELECT id, username, age FROM users WHERE username = ?",
            (username,),
        ).fetchone()


def render(request: Request, template_name: str, **context):
    return templates.TemplateResponse(
        request,
        template_name,
        {
            "current_username": request.cookies.get("username"),
            **context,
        },
    )


@app.get("/")
def index(request: Request):
    create_database()
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                messages.text AS text,
                messages.created_at AS created_at,
                users.username AS username,
                users.age AS age
            FROM messages
            JOIN users ON messages.user_id = users.id
            ORDER BY datetime(messages.created_at) DESC, messages.id DESC
            """
        ).fetchall()

    messages = [dict(row) for row in rows]
    return render(request, "index.html", messages=messages)


@app.get("/login")
def login_form(request: Request):
    return render(request, "login.html")


@app.post("/login")
def login(request: Request, username: str = Form(...)):
    username = username.strip()
    user = get_current_user(username)
    if not user:
        return render(
            request,
            "login.html",
            error="No user exists with that username. Create the user first.",
            username=username,
        )

    response = RedirectResponse(url="/", status_code=303)
    response.set_cookie(key="username", value=user["username"], httponly=True)
    return response


@app.get("/logout")
def logout(request: Request):
    response = render(request, "logout.html")
    response.delete_cookie("username")
    return response


@app.get("/create_user")
def create_user_form(request: Request):
    return render(request, "create_user.html")


@app.post("/create_user")
def create_user(
    request: Request,
    username: str = Form(...),
    age: int = Form(...),
):
    username = username.strip()
    if not username:
        return render(request, "create_user.html", error="Username is required.")
    if age < 0:
        return render(request, "create_user.html", error="Age must be zero or greater.")

    try:
        with get_connection() as connection:
            connection.execute(
                "INSERT INTO users (username, age) VALUES (?, ?)",
                (username, age),
            )
    except sqlite3.IntegrityError:
        return render(
            request,
            "create_user.html",
            error="That username is already taken.",
            username=username,
            age=age,
        )

    response = RedirectResponse(url="/", status_code=303)
    response.set_cookie(key="username", value=username, httponly=True)
    return response


@app.get("/create_message")
def create_message_form(request: Request, username: str | None = Cookie(default=None)):
    user = get_current_user(username)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    return render(request, "create_message.html")


@app.post("/create_message")
def create_message(
    request: Request,
    text: str = Form(...),
    username: str | None = Cookie(default=None),
):
    user = get_current_user(username)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    text = text.strip()
    if not text:
        return render(request, "create_message.html", error="Message text is required.")

    with get_connection() as connection:
        connection.execute(
            "INSERT INTO messages (user_id, text) VALUES (?, ?)",
            (user["id"], text),
        )

    return RedirectResponse(url="/", status_code=303)
