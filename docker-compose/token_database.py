import hmac
import logging
import re
import sqlite3
import time
from threading import local

from .identity import DefaultIdentity, Permission


log = logging.getLogger(__name__)

saved_connections = local()


def get_connection():
    # runs on python 3.7, too old for @functools.cache, and need thread-local
    # anyway or sqlite complains
    if hasattr(saved_connections, "conn"):
        return saved_connections.conn

    conn = sqlite3.connect("/var/lib/git-lfs-authenticate/tokens.sqlite3")
    conn.row_factory = sqlite3.Row
    saved_connections.conn = conn
    return saved_connections.conn


TOKEN_HEADER = re.compile(
    r"""
    ^
    \s*
    Git-LFS-Token
    \s+
    ([a-fA-Z0-9]{80}) # hex token
    \s*
    $
    """,
    re.VERBOSE,
)


def allow_write_if_presenting_token(request):
    header = request.headers.get("Authorization")
    if header is None:
        return None

    match = TOKEN_HEADER.match(header)
    if match is None:
        return None
    supplied_token = match.group(1)

    conn = get_connection()
    valid_tokens = conn.execute(
        """
    SELECT user, token, created_at, expires_at FROM tokens
    WHERE expires_at >= ? - 1
    """,
        (time.time(),),
    )
    for token in valid_tokens.fetchall():
        if hmac.compare_digest(token["token"], supplied_token):
            log.info(
                f"Accepting token for ‘{token['user']}’ created {token['created_at']} expires {token['expires_at']}"
            )
            user = DefaultIdentity(name=token["user"])
            user.allow(permissions=Permission.all())
            return user

    return None
