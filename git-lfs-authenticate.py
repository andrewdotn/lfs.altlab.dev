#!/usr/bin/env python3.8

import datetime
import json
import os
import pwd
import re
import secrets
import sqlite3
import sys
from argparse import ArgumentParser
from configparser import ConfigParser
from math import floor
from pathlib import Path
from socket import gethostname

# called as:
#
#     git-lfs-authenticate [path] 'upload'
#
# where path is the part after the hostname in the ssh://host URL.

ALLOWED_PATHS = re.compile(
    """
    ^
    [^/]+
    /
    [^/]+
    $
    """,
    re.VERBOSE,
)

TOKEN_EXPIRY_TIME = datetime.timedelta(hours=4)


def main():
    config_file = Path("/etc/git-lfs-authenticate.ini")
    if not config_file.exists():
        raise FileNotFoundError(f"Config file {config_file} not found")

    config = ConfigParser()
    config.read("/etc/git-lfs-authenticate.ini")
    if "git-lfs-authenticate" not in config:
        raise Exception(
            f"{config_file} found, but [git-lfs-authenticate] section missing"
        )
    lfs_config = config["git-lfs-authenticate"]

    for key in ["webserver_url", "database_path"]:
        if key not in lfs_config:
            raise Exception(f"key {key} not found in {config_file}")

    parser = ArgumentParser()
    parser.add_argument("path", nargs="?")
    parser.add_argument("command", choices=["upload"])
    args = parser.parse_args()

    if not args.path:
        return parser.error(
            "this script requires a path, even though git-lfs may not always supply one"
        )
    if not ALLOWED_PATHS.match(args.path):
        return parser.error("path must be of the form foo/bar")

    # This doesn’t seem to get shown to clients, but could be helpful for
    # debugging by running `ssh $host git-lfs-authenticate` directly
    print(f"Hello from git-lfs-authenticate on {gethostname()}", file=sys.stderr)

    conn = None
    try:
        conn = sqlite3.connect(lfs_config["database_path"])
    except sqlite3.OperationalError as e:
        raise Exception(f"unable to open {lfs_config['database_path']}") from e

    with conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tokens
            (user TEXT, token TEXT, created_at FLOAT, expires_at FLOAT)
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS tokens_by_user_and_expires_at
            ON tokens
            (user, expires_at)
            """
        )

        user = pwd.getpwuid(os.getuid())
        token = secrets.token_hex(40)
        now = datetime.datetime.now(tz=datetime.timezone.utc)
        expiry = now + TOKEN_EXPIRY_TIME

        conn.execute(
            """
            INSERT INTO tokens (user, token, created_at, expires_at)
            VALUES (?, ?, ?, ?)
            """,
            (
                user.pw_name,
                token,
                now.timestamp(),
                expiry.timestamp(),
            ),
        )
        conn.commit()

    print(
        json.dumps(
            {
                "href": f"{lfs_config['webserver_url']}/{args.path}",
                "header": {
                    "Authorization": f"Git-LFS-Token {token}",
                },
                "expires_at": expiry.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "expires_in": floor(TOKEN_EXPIRY_TIME.total_seconds()),
            }
        )
    )


if __name__ == "__main__":
    main()
