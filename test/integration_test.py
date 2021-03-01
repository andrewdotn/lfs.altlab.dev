import secrets
import tempfile
from pathlib import Path
from subprocess import check_call, check_output
from shutil import which

if not which("git-lfs"):
    raise Exception("git-lfs command not found, these tests will not work")

test_storage_dir = Path('../docker-compose/lfs-test-storage')
test_storage_dir_stat = test_storage_dir.stat()
if test_storage_dir_stat.st_gid != 60421 or test_storage_dir_stat.st_uid != 60421:
    raise Exception(f"{test_storage_dir} is not owned by 60421, run `make fix-perms` to correct")

LFS_PULL_URL = "http://localhost:6428/foo/test1"
LFS_PUSH_URL = "ssh://localhost:6422/"


def test_can_commit():
    lfs_file_contents = "big binary file " + secrets.token_hex(20)

    with tempfile.TemporaryDirectory(prefix="lfs.altlab.dev") as origin:
        check_call(["git", "init", "--bare"], cwd=origin)

        with tempfile.TemporaryDirectory(prefix="lfs.altlab.dev") as clone:
            tmpdir = Path(clone)
            check_call(["git", "init"], cwd=clone)

            check_call(["git", "lfs", "install"], cwd=clone)
            (tmpdir / ".lfsconfig").write_text(f"[lfs]\n url = {LFS_PULL_URL}")
            check_call(["git", "add", ".lfsconfig"], cwd=clone)

            (tmpdir / "foo").write_text(lfs_file_contents)
            check_call(["git", "add", "foo"], cwd=clone)
            check_call(["git", "lfs", "track", "foo"], cwd=clone)
            check_call(["git", "add", "foo", ".gitattributes"], cwd=clone)

            check_call(["git", "commit", "-m", "add foo"], cwd=clone)
            check_call(["git", "remote", "add", "origin", origin], cwd=clone)
            check_call(["git", "push"], cwd=clone)

        # The upstream repo should contain a pointer to the contents, not the
        # contents themselves.
        foo_blob =               check_output(
                   ["git", "cat-file", "blob", "HEAD:foo"], cwd=origin
               )
        assert lfs_file_contents.encode('UTF-8') not in foo_blob
        assert b'version https://git-lfs.github.com/spec' in foo_blob

