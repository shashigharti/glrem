
# Deploy GLREM Space Server

The deployment uses Gunicorn with Uvicorn workers to handle the server, and Nginx is used as a reverse proxy.

## Prerequisites

- A server (Ubuntu 24.04).
- Python 3.12 installed.
- `pip` and `virtualenv` installed.

## 1. Install Required Dependencies

Install dependencies:

```bash
pip install -r requirements.txt
```

## 3. Run Gunicorn with Uvicorn Worker

Run the the server using Gunicorn with Uvicorn workers:

```bash
gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app --bind 0.0.0.0:8000
```

Explanation:
- `-w 4`: Run 4 worker processes.
- `-k uvicorn.workers.UvicornWorker`: Use Uvicorn as the worker.
- `main:app`: The server app in `app.py`.
- `--bind 0.0.0.0:8000`: Bind to all interfaces on port 8000.

## 4. Install Nginx

Install Nginx on your server:

```bash
sudo apt update
sudo apt install nginx
```

## 5. Configure Nginx to Proxy Requests to Gunicorn

Create or modify the Nginx configuration file for your app:

```bash
sudo vi /etc/nginx/sites-available/glrem-server
```

Add the following configuration:

```nginx
server {
    listen 80;
    server_name your_domain_or_ip;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Enable the Nginx Configuration

Create a symbolic link to enable the configuration:

```bash
sudo ln -s /etc/nginx/sites-available/glrem-server.conf /etc/nginx/sites-enabled
```

### Restart Nginx

Restart Nginx to apply the changes:

```bash
sudo systemctl restart nginx
```

## 6. Set Up Gunicorn as a Systemd Service

To ensure Gunicorn starts automatically, create a systemd service file for the server:

```bash
sudo vi /etc/systemd/system/glrem-server.service
```

Add the following content:

```ini
[Unit]
Description=GLREM Server
After=network.target

[Service]
User=ubuntu
Group=ubuntu
WorkingDirectory=/path/to/your/app/server
ExecStart=/path/to/your/venv/bin/gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app --bind 127.0.0.1:8000

[Install]
WantedBy=multi-user.target
```

Replace `/path/to/your/app` with the directory of your FastAPI application and `/path/to/your/venv/bin/gunicorn` with the path to your Gunicorn executable in your virtual environment.

### Enable and Start Gunicorn

Reload the systemd daemon and start the Gunicorn service:

```bash
sudo systemctl daemon-reload
sudo systemctl start glrem-server
sudo systemctl enable glrem-server
```

## 7. Test the Application

Visit your server's IP address or domain name in a web browser:

```bash
http://your_domain_or_ip
```

## 8. Troubleshooting

- **Check Gunicorn Logs**: Check the status of your Gunicorn service:
  ```bash
  sudo systemctl status your_app
  ```

  You can view Gunicorn logs with:
  ```bash
  journalctl -u your_app
  ```

- **Check Nginx Logs**: If you encounter issues with Nginx, check its logs:
  ```bash
  sudo tail -f /var/log/nginx/error.log
  ```

- **Firewall**: Ensure that ports 80 (HTTP) and 8000 (for Gunicorn) are open in your server's firewall.
