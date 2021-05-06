import os
import re
import secrets
from pathlib import Path
from shutil import which
from subprocess import check_call, check_output, CalledProcessError
from textwrap import dedent

import pytest

REPO_NAME = "org/lfs-test"
LFS_PULL_URL = f"http://localhost:6428/{REPO_NAME}"
SSH_PORT = 6422
LFS_PUSH_URL = f"ssh://localhost:{SSH_PORT}/{REPO_NAME}"
ID_SSH_USER = Path(__file__).parent / ".." / "docker-compose" / "id_ssh-user"


@pytest.fixture
def origin_dir(tmpdir_factory):
    return Path(tmpdir_factory.mktemp("origin"))


@pytest.fixture
def clone_dir(tmpdir_factory):
    return Path(tmpdir_factory.mktemp("clone"))


@pytest.fixture
def new_clone_dir(tmpdir_factory):
    return Path(tmpdir_factory.mktemp("new-clone"))


@pytest.fixture(scope="session", autouse=True)
def check_setup():
    if not which("git-lfs"):
        raise Exception(
            "git-lfs command not found, these tests will not work without it"
        )

    if not ID_SSH_USER.is_file():
        raise Exception(
            f"{ID_SSH_USER} does not exist, run `make id_ssh-user` to create"
        )

    # The next bit is *required* on linux, but *breaks everything* on
    # docker-for-mac
    if os.uname().sysname == "Darwin":
        return

    test_storage_dir = (
        Path(__file__).parent / ".." / "docker-compose" / "lfs-test-storage"
    )
    test_storage_dir_stat = test_storage_dir.stat()
    if test_storage_dir_stat.st_gid != 60421 or test_storage_dir_stat.st_uid != 60421:
        raise Exception(
            f"{test_storage_dir} is not owned by 60421, run `make fix-perms` to correct"
        )


def create_git_lfs_repo(path, foo_contents="foo"):
    check_call(["git", "init"], cwd=path)
    check_call(["git", "config", "lfs.ssh.retries", "1"], cwd=path)
    check_call(["git", "config", "lfs.transfer.maxretries", "1"], cwd=path)

    check_call(["git", "lfs", "install"], cwd=path)
    (path / ".lfsconfig").write_text(
        dedent(
            f"""\
                [lfs]
                 url = {LFS_PULL_URL}
                 pushUrl = {LFS_PUSH_URL}
            """
        )
    )
    check_call(["git", "add", ".lfsconfig"], cwd=path)

    (path / "foo").write_text(foo_contents)
    check_call(["git", "lfs", "track", "foo"], cwd=path)
    check_call(["git", "add", "foo", ".gitattributes"], cwd=path)

    check_call(["git", "commit", "-m", "add foo"], cwd=path)


def env_with_git_ssh_user(username):
    env = dict(os.environ)
    env["GIT_SSH_COMMAND"] = re.sub(
        r"\s+",
        " ",
        f"""
        ssh
            -o StrictHostKeyChecking=no
            -o UserKnownHostsFile=/dev/null
            -o BatchMode=yes
            -p {SSH_PORT}
            -i {os.fspath(ID_SSH_USER)}
            -l {username}
        """,
    )
    return env


def create_and_push(clone_dir, origin_dir, username):
    assert clone_dir != origin_dir

    foo_contents = "big binary file " + secrets.token_hex(20)

    check_call(["git", "init", "--bare"], cwd=origin_dir)

    create_git_lfs_repo(clone_dir, foo_contents=foo_contents)

    check_call(["git", "remote", "add", "origin", origin_dir], cwd=clone_dir)
    check_call(["git", "push"], cwd=clone_dir, env=env_with_git_ssh_user(username))

    return foo_contents


def test_authorized_user_can_commit(clone_dir, origin_dir):
    foo_contents = create_and_push(clone_dir, origin_dir, "user")

    # The upstream repo should contain a pointer to the contents, not the
    # contents themselves.
    foo_blob = check_output(["git", "cat-file", "blob", "HEAD:foo"], cwd=origin_dir)

    assert foo_contents.encode("UTF-8") not in foo_blob
    assert b"version https://git-lfs.github.com/spec" in foo_blob


def test_anon_users_cannot_push(clone_dir, new_clone_dir, capfd):
    with pytest.raises(CalledProcessError, match="'git', 'push'"):
        create_and_push(clone_dir, new_clone_dir, "unauthorized")
    captured = capfd.readouterr()
    assert "Permission denied" in captured.err


def test_anon_users_can_pull(clone_dir, origin_dir, new_clone_dir):
    foo_contents = create_and_push(clone_dir, origin_dir, "user")

    check_call(
        ["git", "clone", "-c", "lfs.transfer.maxretries=1", origin_dir, "new"],
        cwd=new_clone_dir,
    )

    assert foo_contents in (new_clone_dir / "new" / "foo").read_text()
