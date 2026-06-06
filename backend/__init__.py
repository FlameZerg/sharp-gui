"""Sharp GUI backend package."""


def create_app(*args, **kwargs):
    from backend.app_factory import create_app as _create_app

    return _create_app(*args, **kwargs)


__all__ = ["create_app"]
