# lfs.altlab.dev

We’re running our own [git-lfs] server.

## Overview

There are a few different [LFS server implementations] but the only
maintained one that I found that seemed fairly suitable for our
purposes is [giftless], written in python.

[git-lfs]: https://www.google.com/search?client=safari&rls=en&q=git+lfs&ie=UTF-8&oe=UTF-8
[LFS server implementations]: https://github.com/git-lfs/git-lfs/wiki/Implementations
[giftless]: https://github.com/datopian/giftless

It supports anonymous read-only or anonymous read-write access out of the
box, but the authentication section of the README is just a big “TBD”, so I
put together a custom auth plugin.

This repo contains:

  - an ansible setup to deploy the lfs service to lfs.altlab.dev aka
    altlab-gw

  - an auth plugin for giftless that checks for a match between a token in
    an HTTP header and tokens in a sqlite database

  - a `git-lfs-authenticate` script that adds a token to a group-writeable
    sqlite database

  - a docker-compose + pytest setup for integration-testing the setup

What this repo *does not contain* but which is also important:

  - The nginx config for the virtual host. It is not (yet?) created by
    ansible here because of the extra work that would be required to
    integrate with certbot.

    Note that the `server{ }` block should contain a value for max body
    size, e.g., `client_max_body_size 1G;`, or you will get `413 – Request
    Entity Too Large` errors when trying to push large objects larger than
    the default of one mebibyte.

## Permissions

Assumptions:

  - Anyone in the world should be able to pull files from our server.

  - Nothing secret is stored in LFS itself, only files that would go into a
    public git repository if they weren’t too large to do that comfortably.

    <details>
    Since you get stuff from LFS by asking for it by SHA, in theory you may
    be able to store private objects for private repos in there—in order to
    read anything useful from LFS, you’d first need to have access to the
    private repo to get the object hash—but in the current configuration I
    am 90% sure that there is an API endpoint to enumerate all the objects
    in the LFS repo without knowing their hashes <i>a priori</i>.
    </details>

  - There is a server to which everyone who should be able to commit has
    SSH access.

  - All committers trust each other not to read or modify each other’s
    tokens. (This assumption could be relaxed on a dedicated SSH server
    that enforced that the only command that could be run was
    `git-lfs-authenticate`.)

## How it works

 1. The git repo contains an [`.lfsconfig`] file:

        [lfs]
         url = https://lfs.altlab.dev/foo/bar
         pushUrl = ssh://lfs.altlab.dev/foo/bar

 2. Anyone cloning the repo, who has git lfs installed via `git lfs
    install`, will get pointers to the objects from github, and the actual
    object contents anonymously from the `https://` server.

    If your checkout is showing tiny files like

        version https://git-lfs.github.com/spec/v1
        oid sha256:b37e50cedcd3e3f1ff64f4afc0422084ae694253cf399326868e07a35f4a45fb
        size 24828

    instead of the expected large file contents, then you can fix that with

        git lfs install --local
        git lfs fetch
        git lfs checkout

 3. For anyone *pushing*, as part of the [git-lfs protocol][protocol],
    `git` will ssh to host specified by the `pushUrl` and run
    `git-lfs-authenticate`.

 4. The `git-lfs-authenticate` script in this repo generates a token and
    saves it to a local database, then prints out some JSON telling `git`
    to talk to `https://lfs.altlab.dev` for the actual files, and to
    present the generated token when doing so.

        {
          "href": "https://lfs.altlab.app/foo/bar",
          "header": {
            "Authorization": "Git-LFS-Token secretblahblahblah"
          },
          "expires_at": "2021-02-11T22:16:40Z",
          "expires_in": 21599
        }

 5. The giftless server at the `https://` URL compares the presented token
    against the tokens in the same database as the ones from step 4,
    granting full permissions only if the token is valid.

    Otherwise the request gets read-only permissions only.

[`.lfsconfig`]: https://docs.github.com/en/enterprise-server@3.0/admin/user-management/configuring-git-large-file-storage-for-your-enterprise#configuring-git-large-file-storage-to-use-a-third-party-server
[protocol]: https://github.com/git-lfs/git-lfs/blob/main/docs/api/server-discovery.md
