import importlib

from starlette.requests import Request


def make_request(main, path="/", cookies=None):
    headers = []
    if cookies:
        cookie_header = "; ".join(f"{key}={value}" for key, value in cookies.items())
        headers.append((b"cookie", cookie_header.encode()))

    scope = {
        "type": "http",
        "method": "GET",
        "path": path,
        "headers": headers,
        "app": main.app,
        "router": main.app.router,
        "server": ("testserver", 80),
        "scheme": "http",
    }
    return Request(scope)


def load_app(tmp_path, monkeypatch):
    import db_create

    test_db = tmp_path / "app.db"
    monkeypatch.setattr(db_create, "DATABASE_PATH", test_db)

    import main

    reloaded = importlib.reload(main)
    reloaded.create_database()
    return reloaded


def response_text(response):
    return response.body.decode()


def test_index_displays_seeded_messages(tmp_path, monkeypatch):
    main = load_app(tmp_path, monkeypatch)

    response = main.index(make_request(main))
    text = response_text(response)

    assert response.status_code == 200
    assert "Recent Messages" in text
    assert "FastAPI plus SQLite makes a very friendly lab stack." in text
    assert "grace" in text
    assert "44" in text
    assert "/static/style.css" in text
    assert "/static/message-board.png" in text


def test_all_get_routes_return_success_or_expected_redirect(tmp_path, monkeypatch):
    main = load_app(tmp_path, monkeypatch)

    assert main.index(make_request(main)).status_code == 200
    assert main.login_form(make_request(main, "/login")).status_code == 200
    assert main.logout(make_request(main, "/logout")).status_code == 200
    assert main.create_user_form(make_request(main, "/create_user")).status_code == 200

    response = main.create_message_form(make_request(main, "/create_message"), username=None)
    assert response.status_code == 303
    assert response.headers["location"] == "/login"


def test_create_user_login_and_create_message(tmp_path, monkeypatch):
    main = load_app(tmp_path, monkeypatch)
    request = make_request(main, "/create_user")

    create_user = main.create_user(request, username="katherine", age=32)
    assert create_user.status_code == 303
    assert create_user.headers["location"] == "/"

    duplicate_user = main.create_user(request, username="katherine", age=32)
    assert duplicate_user.status_code == 200
    assert "That username is already taken." in response_text(duplicate_user)

    create_message = main.create_message(
        make_request(main, "/create_message", cookies={"username": "katherine"}),
        text="A new test message.",
        username="katherine",
    )
    assert create_message.status_code == 303
    assert create_message.headers["location"] == "/"

    index = main.index(make_request(main))
    text = response_text(index)
    assert "A new test message." in text
    assert "katherine" in text
