import secrets
from pathlib import Path
from shutil import which
from subprocess import check_call, check_output

import pytest


LFS_PULL_URL = "http://localhost:6428/foo/test2"
LFS_PUSH_URL = "ssh://localhost:6422/"


@pytest.fixture
def tmp_path2(tmpdir_factory):
    "For when you need more than one tmp_dir in a test"
    # see https://github.com/pytest-dev/pytest/issues/2703
    # “Multiple use of fixture in a single test”
    return tmpdir_factory.mktemp("tmp-path2")


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
    (path / ".lfsconfig").write_text(f"[lfs]\n url = {LFS_PULL_URL}")
    check_call(["git", "add", ".lfsconfig"], cwd=path)

    (path / "foo").write_text(foo_contents)
    check_call(["git", "add", "foo"], cwd=path)
    check_call(["git", "lfs", "track", "foo"], cwd=path)
    check_call(["git", "add", "foo", ".gitattributes"], cwd=path)

    check_call(["git", "commit", "-m", "add foo"], cwd=path)


def test_authorized_user_can_commit(tmp_path, tmp_path2):
    assert tmp_path != tmp_path2

    foo_contents = "big binary file " + secrets.token_hex(20)

    origin = tmp_path
    check_call(["git", "init", "--bare"], cwd=origin)

    clone = Path(tmp_path2)
    create_git_lfs_repo(clone, foo_contents=foo_contents)

    check_call(["git", "remote", "add", "origin", origin], cwd=clone)
    check_call(["git", "push"], cwd=clone)

    # The upstream repo should contain a pointer to the contents, not the
    # contents themselves.
    foo_blob = check_output(["git", "cat-file", "blob", "HEAD:foo"], cwd=origin)

    assert foo_contents.encode("UTF-8") not in foo_blob
    assert b"version https://git-lfs.github.com/spec" in foo_blob


@pytest.mark.skip()
def test_anon_users_cannot_push():
    pass


@pytest.mark.skip
def test_anon_users_can_pull():
    pass
