 1. Copy an existing nginx sites-available file to `lfs.altlab.dev`

        server {
            listen 443 ssl;
            server_name lfs.altlab.dev;
            access_log /var/log/nginx/lfs.dev.access.log;

            location / {
                uwsgi_pass localhost:6421;
                include uwsgi_params;
            }
        }

        server {
            listen 80;
            server_name lfs.altlab.dev;
            return 301 https://lfs.altlab.dev$request_uri;
        }

 2. Enable the server

        cd ../sites-enabled/
        sudo ln -s ../sites-available/lfs.altlab.dev .
        sudo nginx -t && sudo sudo systemctl reload nginx
        sudo certbot
        # choose the new domain name
        # choose “No redirect” because we already have one in the file

 3. Create the lfs user

        sudo mkdir /data/lfs
        sudo groupadd --gid 60421 lfs
        sudo useradd --system --uid 60421 --gid 60421 --home /data/lfs lfs
        sudo chown -R lfs:lfs /data/lfs
        sudo -u lfs mkdir -p /data/lfs/docker-compose/lfs
        sudo ln -s /data/lfs/docker-compose/lfs /etc/docker-compose/lfs


