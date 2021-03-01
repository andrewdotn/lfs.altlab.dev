# For testing the lfs setup: an ssh server that only accepts logins from a
# single user

FROM python:3.9-slim
RUN apt update && apt install -y openssh-server && rm -rf /var/cache/apt
RUN mkdir /run/sshd \
    && useradd --create-home user \
    && mkdir -p /home/user/.ssh \
    && chown user /home/user/.ssh \
    `# due to docker stuff, root sshd in container may need world-read here` \
    && chmod 0755 /home/user/.ssh
EXPOSE 22
CMD cp /home/user/id_ssh-user.pub /home/user/.ssh/authorized_keys \
    && chown user /home/user/.ssh/authorized_keys \
    && chmod 0644 /home/user/.ssh/authorized_keys \
    `# add -d for debug output; note ssh will then exit after 1 connection` \
    && exec /usr/sbin/sshd -D
