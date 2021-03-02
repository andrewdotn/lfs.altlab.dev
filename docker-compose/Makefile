SHELL = /bin/bash -eu
.DELETE_ON_ERROR:

.PHONY: prep
prep::

test-db/tokens.sqlite3:
	mkdir -p test-db
	sqlite3 $@ < /dev/null

prep:: test-db/tokens.sqlite3

id_ssh-user id_ssh-user.pub:
	ssh-keygen -t ed25519 -N '' -f id_ssh-user

prep:: id_ssh-user

clean::
	rm -f id_ssh-user{,.pub}

lfs-test-storage:
	mkdir $@

prep:: lfs-test-storage

.PHONY: fix-perms
fix-perms:
	if [ "$$(uname)" != "Darwin" ]; then \
		sudo chown 60421:60421 lfs-test-storage; \
		sudo chown -R 60421:60421 test-db; \
		sudo chmod -R g+w test-db; \
	fi

prep:: fix-perms

