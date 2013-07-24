from functools import wraps
from flask import g, request, redirect, url_for


class HTTPException(RuntimeError):
    """HTTPError does not take keyword arguments, so we are defining a custom exception class."""
    def __init__(self, message, status_code):
        self.message = message
        self.status_code = status_code
        super(HTTPException, self).__init__()


def get_remote_address(req):
    if not req.headers.getlist('X-Forwarded-For'):
        return req.remote_addr
    else:
        return req.headers.getlist('X-Forwarded-For')[0]