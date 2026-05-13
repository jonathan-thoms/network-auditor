#!/bin/bash
# =============================================================
# GSmart Audit Tool — Ubuntu Server Deployment Script
# Run this on your DigitalOcean droplet as root or with sudo
# =============================================================

set -e

APP_USER="deploy"
APP_DIR="/home/$APP_USER/audit"
REPO_URL="REPLACE_WITH_YOUR_GIT_REPO_URL"
DOMAIN="gsmarttool.com"

echo "============================================"
echo " 1. System Update & Dependencies"
echo "============================================"
apt update && apt upgrade -y
apt install -y python3 python3-venv python3-pip python3-dev \
    nginx git curl ufw

echo "============================================"
echo " 2. Firewall Setup"
echo "============================================"
ufw allow OpenSSH
ufw allow 'Nginx Full'
ufw --force enable

echo "============================================"
echo " 3. Create Deploy User"
echo "============================================"
if ! id "$APP_USER" &>/dev/null; then
    adduser --disabled-password --gecos "" $APP_USER
fi

echo "============================================"
echo " 4. Clone Repository"
echo "============================================"
if [ ! -d "$APP_DIR" ]; then
    sudo -u $APP_USER git clone $REPO_URL $APP_DIR
else
    cd $APP_DIR
    sudo -u $APP_USER git pull origin main
fi

echo "============================================"
echo " 5. Virtual Environment & Dependencies"
echo "============================================"
cd $APP_DIR
sudo -u $APP_USER python3 -m venv venv
sudo -u $APP_USER $APP_DIR/venv/bin/pip install --upgrade pip
sudo -u $APP_USER $APP_DIR/venv/bin/pip install -r requirements.txt

echo "============================================"
echo " 6. Environment File"
echo "============================================"
if [ ! -f "$APP_DIR/.env" ]; then
    sudo -u $APP_USER cp .env.example .env
    echo ""
    echo "⚠️  IMPORTANT: Edit $APP_DIR/.env with your actual secrets!"
    echo "   nano $APP_DIR/.env"
    echo ""
fi

echo "============================================"
echo " 7. Django Setup"
echo "============================================"
sudo -u $APP_USER $APP_DIR/venv/bin/python manage.py migrate
sudo -u $APP_USER $APP_DIR/venv/bin/python manage.py collectstatic --noinput

echo "============================================"
echo " 8. Create Gunicorn Log Directory"
echo "============================================"
mkdir -p /var/log/gunicorn
chown $APP_USER:$APP_USER /var/log/gunicorn

echo "============================================"
echo " 9. Setup Systemd Service"
echo "============================================"
cp $APP_DIR/deploy/gunicorn.service /etc/systemd/system/gunicorn.service
systemctl daemon-reload
systemctl enable gunicorn
systemctl restart gunicorn

echo "============================================"
echo " 10. Setup Nginx"
echo "============================================"
cp $APP_DIR/deploy/nginx.conf /etc/nginx/sites-available/$DOMAIN
ln -sf /etc/nginx/sites-available/$DOMAIN /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl restart nginx

echo "============================================"
echo " 11. Set Permissions"
echo "============================================"
chown -R $APP_USER:www-data $APP_DIR
chmod -R 755 $APP_DIR/static
mkdir -p $APP_DIR/media
chown -R $APP_USER:www-data $APP_DIR/media
chmod -R 775 $APP_DIR/media

echo ""
echo "============================================"
echo " ✅ Deployment Complete!"
echo "============================================"
echo ""
echo " Next steps:"
echo "   1. Edit secrets:     nano $APP_DIR/.env"
echo "   2. Restart gunicorn: sudo systemctl restart gunicorn"
echo "   3. Create superuser: cd $APP_DIR && sudo -u $APP_USER venv/bin/python manage.py createsuperuser"
echo "   4. Setup SSL:        sudo apt install certbot python3-certbot-nginx"
echo "                        sudo certbot --nginx -d $DOMAIN -d www.$DOMAIN"
echo "                        Then uncomment the HTTPS block in /etc/nginx/sites-available/$DOMAIN"
echo ""
