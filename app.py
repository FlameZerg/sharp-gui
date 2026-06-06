from backend.app_factory import create_app
from backend.server import run_server

app = create_app()


if __name__ == "__main__":
    run_server(app)
