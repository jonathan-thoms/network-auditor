# GSmart Audit Tool

Django-based telecom network audit and reporting platform.

## Local Development

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Run development server
python manage.py runserver
```

## Project Structure

```
audit/              ← Django project config (settings, urls, wsgi)
auditor/            ← Core audit app (models, views, audit scripts)
  audit/            ← Audit logic modules (LTE, NR, USID, reports)
users/              ← User management (auth, profiles, SMTP config)
common_func/        ← Shared utilities (DCGK parsing, logging, helpers)
static/             ← Static assets (CSS, JS, images)
deploy/             ← Deployment configs (Nginx, Gunicorn, setup script)
```

## Deployment to DigitalOcean (Ubuntu)

### Quick Deploy

1. Push this repo to GitHub
2. SSH into your droplet
3. Edit `deploy/setup.sh` and set your `REPO_URL`
4. Run:

```bash
chmod +x deploy/setup.sh
sudo ./deploy/setup.sh
```

5. Edit your secrets: `nano /home/deploy/audit/.env`
6. Restart: `sudo systemctl restart gunicorn`
7. Create admin: `cd /home/deploy/audit && sudo -u deploy venv/bin/python manage.py createsuperuser`

### SSL Setup (Let's Encrypt)

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d gsmarttool.com -d www.gsmarttool.com
```

Then uncomment the HTTPS server block in `/etc/nginx/sites-available/gsmarttool.com`.

### Useful Commands

```bash
# Check app status
sudo systemctl status gunicorn

# View logs
sudo journalctl -u gunicorn -f
tail -f /var/log/gunicorn/error.log

# Restart after code changes
cd /home/deploy/audit
sudo -u deploy git pull origin main
sudo -u deploy venv/bin/pip install -r requirements.txt
sudo -u deploy venv/bin/python manage.py migrate
sudo -u deploy venv/bin/python manage.py collectstatic --noinput
sudo systemctl restart gunicorn
```

## Environment Variables

| Variable | Description | Default |
|---|---|---|
| `DJANGO_SECRET_KEY` | Django secret key | *(dev fallback)* |
| `DJANGO_DEBUG` | Enable debug mode | `False` |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated hosts | `gsmarttool.com,...` |
| `EMAIL_HOST` | SMTP server | — |
| `EMAIL_PORT` | SMTP port | `587` |
| `EMAIL_HOST_USER` | SMTP username | — |
| `EMAIL_HOST_PASSWORD` | SMTP app password | — |
