# Platinum Tier: Deploy to Oracle Cloud Free VM
# Step-by-step deployment guide

## Prerequisites
- Oracle Cloud Free Tier account: https://www.oracle.com/cloud/free/
- SSH client installed
- Docker Desktop installed locally

---

## STEP 1: Create Free Cloud VM

1. Go to https://www.oracle.com/cloud/free/
2. Sign up / Sign in
3. Navigate to **Compute → Instances**
4. Click **Create Instance**
5. Configure:
   - **Name:** `ai-employee-cloud`
   - **Compartment:** Root compartment
   - **Availability Domain:** Any (AD-1)
   - **Image:** Ubuntu 22.04 or 24.04
   - **Shape:** VM.Standard.A1.Flex (ARM) — **FREE**
     - OCPUs: 4
     - Memory: 24 GB
   - **SSH Keys:** Generate a new key pair or upload your public key
     - Download the private key (`ssh_key.pem`)
   - **Networking:** Create a new VCN (default settings)
   - **Boot Volume:** Keep default (50GB)

6. Click **Create**
7. Note the **Public IP Address** (e.g., `132.x.x.x`)

---

## STEP 2: Configure Firewall Rules

1. In Oracle Cloud Console, go to **Networking → Virtual Cloud Networks**
2. Click your VCN → **Security Lists** → Default Security List
3. Add Ingress Rules:
   - **Port 80** (HTTP) — Source: `0.0.0.0/0`
   - **Port 443** (HTTPS) — Source: `0.0.0.0/0`
   - **Port 22** (SSH) — Source: `0.0.0.0/0`
   - **Port 8069** (Odoo) — Source: `0.0.0.0/0` (or restrict to your IP)

---

## STEP 3: SSH Into Your VM

```bash
# Set permissions on your SSH key
chmod 400 /path/to/ssh_key.pem

# SSH into the VM
ssh -i /path/to/ssh_key.pem ubuntu@YOUR_PUBLIC_IP
```

---

## STEP 4: Install Docker on the VM

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add your user to docker group
sudo usermod -aG docker $USER

# Install Docker Compose
sudo apt install docker-compose-plugin -y

# Verify installation
docker --version
docker compose version

# Start Docker on boot
sudo systemctl enable docker
sudo systemctl start docker
```

---

## STEP 5: Transfer Project Files to VM

**From your LOCAL machine** (new terminal):

```bash
# Navigate to your project folder
cd C:\Users\Dell\Documents\GitHub\personal-AI-Employe-FTEs\personal-AI-Employe-FTEs

# Copy files to VM using SCP
scp -i /path/to/ssh_key.pem -r ./* ubuntu@YOUR_PUBLIC_IP:~/ai-employee/
```

**Or use Git** (from the VM):

```bash
# On the VM
mkdir ~/ai-employee
cd ~/ai-employee
git clone https://github.com/YOUR_USERNAME/personal-AI-Employe-FTEs.git .
```

---

## STEP 6: Configure Environment Variables

**On the VM:**

```bash
cd ~/ai-employee

# Copy the example env file
cp .env.example .env

# Edit with your actual credentials
nano .env
```

Update these values in `.env`:
```
ODOO_DB_PASSWORD=<strong-password>
ODOO_ADMIN_EMAIL=ramshashafiq85@gmail.com
ODOO_ADMIN_PASSWORD=<your-odoo-password>

# Add your API keys for social media
GMAIL_CLIENT_ID=...
FB_PAGE_ID=...
TWITTER_API_KEY=...
```

**IMPORTANT:** Never commit `.env` to Git!

---

## STEP 7: Deploy with Docker Compose

```bash
cd ~/ai-employee

# Start all services
docker compose -f platinum-docker-compose.yml up -d

# Check status
docker compose ps

# View logs
docker compose logs -f cloud-agent
```

Services will start:
- **PostgreSQL** (port 5432)
- **Odoo** (port 8069)
- **Cloud Agent** (24/7 email/social processing)
- **Nginx** (ports 80, 443)
- **Redis** (port 6379)
- **Health Monitor** (continuous monitoring)

---

## STEP 8: Set Up HTTPS (Let's Encrypt)

```bash
# Install Certbot
sudo apt install certbot -y

# Get SSL certificate (replace with your domain)
sudo certbot certonly --standalone -d your-domain.com

# Configure Nginx for HTTPS
# (Edit nginx.conf to use the certificate paths)
sudo nano /etc/nginx/nginx.conf
```

---

## STEP 9: Set Up Automatic Backups

```bash
# Create backup script
cat > ~/backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR=~/backups/$(date +%Y%m%d)
mkdir -p $BACKUP_DIR

# Backup Odoo database
docker exec platinum-odoo-db pg_dump -U odoo postgres > $BACKUP_DIR/db_backup.sql

# Backup Odoo filestore
docker cp platinum-odoo:/var/lib/odoo $BACKUP_DIR/odoo-filestore

# Backup vault
cp -r ~/ai-employee/cloud-vault $BACKUP_DIR/vault

# Compress
tar -czf $BACKUP_DIR.tar.gz $BACKUP_DIR
rm -rf $BACKUP_DIR

# Keep only last 7 days
find ~/backups -name "*.tar.gz" -mtime +7 -delete

echo "Backup complete: $BACKUP_DIR.tar.gz"
EOF

chmod +x ~/backup.sh

# Add to crontab (daily at 2 AM)
(crontab -l 2>/dev/null; echo "0 2 * * * ~/backup.sh") | crontab -
```

---

## STEP 10: Verify Deployment

```bash
# Check all services are running
docker compose -f platinum-docker-compose.yml ps

# Test Odoo
curl http://YOUR_PUBLIC_IP:8069

# Test Cloud Agent health
docker logs platinum-cloud-agent

# Check Health Monitor
docker logs platinum-health-monitor
```

---

## STEP 11: Connect Local Agent to Cloud

**On your LOCAL machine:**

```bash
# Update your local .env with Cloud VM IP
echo "CLOUD_VM_IP=YOUR_PUBLIC_IP" >> .env

# Test connection
ssh -i /path/to/ssh_key.pem ubuntu@YOUR_PUBLIC_IP "docker ps"
```

---

## Troubleshooting

### Container won't start
```bash
docker compose logs <service-name>
```

### Can't access Odoo
- Check firewall rules in Oracle Cloud Console
- Verify port 8069 is open: `sudo ufw status`

### Out of memory
```bash
# Check memory usage
free -h

# Restart heavy services
docker restart platinum-odoo
```

### SSL certificate issues
```bash
sudo certbot renew
sudo systemctl reload nginx
```

---

## Cost Breakdown (Oracle Free Tier)

| Resource | Cost |
|----------|------|
| VM (4 OCPUs, 24GB RAM) | **FREE** |
| 50GB Boot Volume | **FREE** |
| 10TB/month Bandwidth | **FREE** |
| **Total** | **$0/month** |

---

## Next Steps

1. **Configure your domain** (optional — use Oracle's public IP)
2. **Set up monitoring alerts** (Slack/Discord webhook)
3. **Add Gmail/WhatsApp watchers** to Cloud Agent
4. **Test the full Cloud → Local flow** with real emails
