keyfile:
	ssh-keygen -t ed25519 -N '' -f id_ssh-user

clean::
	rm -f id_ssh-user{,.pub}

fix-perms:
	sudo chown 60421:60421 lfs-storage
