# lfs.altlab.dev

We’re running our own git-lfs server.

## Overview

There are a few different [LFS server implementations] but the only
maintained one that I found that seemed fairly suitable for our
purposes is [giftless], written in python.

[LFS server implementations]: https://github.com/git-lfs/git-lfs/wiki/Implementations
[giftless]: https://github.com/datopian/giftless

It supports anonymous read-only access out of the box, but the
authentication section is just a big “TBD”, so we would have to fill in
some of the details ourselves.

How I think this setup would work for developers:

 1. We could reuse `altlab-gw` for this, or ask Michael Ward to create a
    new VM specifically for this.

 2. In the `cree-intelligent-dictionary` repo, we’d add a new
    [`.lfsconfig`] file:

        [lfs]
                url = ssh://lfs.altlab.dev/

 3. On git operations like `clone` or `commit`, as part of the [git-lfs
    protocol][protocol], `git` would automatically ssh to that host and run
    `git-lfs-authenticate`. This would be a wrapper script I’d write, that
    would let anyone with an SSH account on that server insert a token into
    a group-writable SQLite database file.

 4. The `git-lfs-authenticate` script would print out some JSON telling
    `git` to talk to `https://lfs.altlab.dev` for the actual files.

    The JSON would look like

        {
          "href": "https://lfs.altlab.app/UAlbertaALTLab/cree-intelligent-dictionary",
          "header": {
            "Authorization": "Git-LFS-Token secretblahblahblah"
          },
          "expires_at": "2021-02-11T22:16:40Z",
          "expires_in": 21599
        }

 5. When the developer’s `git` instance talked to `https://lfs.altlab.app`,
    it would send the token in the authorization header to `giftless`.
    `giftless` would have a custom auth plugin that would check the very
    same SQLite database file from step 3 for token existence, allowing
    writes.

 5. Our README would tell people who don’t have a shell account on
    `altlab.dev` to change the `.lfsconfig` setting to point to to
    `https://lfs.altlab.dev` for anonymous read-only access.

    There may be a user-specific-config thing that could be set up
    / documented here to make this part easier / automatic.

[`.lfsconfig`]: https://docs.github.com/en/enterprise-server@3.0/admin/user-management/configuring-git-large-file-storage-for-your-enterprise#configuring-git-large-file-storage-to-use-a-third-party-server
[protocol]: https://github.com/git-lfs/git-lfs/blob/main/docs/api/server-discovery.md

