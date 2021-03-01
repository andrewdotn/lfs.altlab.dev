import secrets
from pathlib import Path
from shutil import which
from subprocess import check_call, check_output
from textwrap import dedent

import pytest


LFS_PULL_URL = "http://localhost:6428/foo/test2"
LFS_PUSH_URL = "ssh://localhost:6422/"


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
    check_call(["git", "add", "foo"], cwd=path)
    check_call(["git", "lfs", "track", "foo"], cwd=path)
    check_call(["git", "add", "foo", ".gitattributes"], cwd=path)

    check_call(["git", "commit", "-m", "add foo"], cwd=path)


def create_and_push(clone_dir, origin_dir):
    assert clone_dir != origin_dir

    foo_contents = "big binary file " + secrets.token_hex(20)

    check_call(["git", "init", "--bare"], cwd=origin_dir)

    create_git_lfs_repo(clone_dir, foo_contents=foo_contents)

    check_call(["git", "remote", "add", "origin", origin_dir], cwd=clone_dir)
    check_call(["git", "push"], cwd=clone_dir)

    return foo_contents


def test_authorized_user_can_commit(clone_dir, origin_dir):
    foo_contents = create_and_push(clone_dir, origin_dir)

    # The upstream repo should contain a pointer to the contents, not the
    # contents themselves.
    foo_blob = check_output(["git", "cat-file", "blob", "HEAD:foo"], cwd=origin_dir)

    assert foo_contents.encode("UTF-8") not in foo_blob
    assert b"version https://git-lfs.github.com/spec" in foo_blob


def test_anon_users_cannot_push(clone_dir, new_clone_dir):
    with pytest.raises(Exception, match="unauthorized"):
        create_and_push(clone_dir, new_clone_dir)


def test_anon_users_can_pull(clone_dir, origin_dir, new_clone_dir):
    foo_contents = create_and_push(clone_dir, origin_dir)

    check_call(["git", "clone", origin_dir, "new"], cwd=new_clone_dir)

    assert foo_contents in (new_clone_dir / "new" / "foo").read_text()
