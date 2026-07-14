#!/bin/bash
# Quick-Start Deployment Script for Oracle Cloud Free VM
# Run this AFTER SSH-ing into your VM

set -e

echo "============================================"
echo "AI Employee Platinum Tier - VM Setup"
echo "============================================"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Step 1: Update system
echo -e "\n${YELLOW}[1/7] Updating system...${NC}"
sudo apt update && sudo apt upgrade -y

# Step 2: Install Docker
echo -e "\n${YELLOW}[2/7] Installing Docker...${NC}"
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    echo "Docker installed!"
else
    echo "Docker already installed."
fi

# Step 3: Install Docker Compose
echo -e "\n${YELLOW}[3/7] Installing Docker Compose...${NC}"
sudo apt install docker-compose-plugin -y

# Step 4: Install Git
echo -e "\n${YELLOW}[4/7] Installing Git...${NC}"
sudo apt install git -y

# Step 5: Clone repository (or use existing files)
echo -e "\n${YELLOW}[5/7] Setting up project...${NC}"
if [ ! -d "ai-employee" ]; then
    mkdir -p ~/ai-employee
    echo "Created project directory."
    echo "Now copy your project files to ~/ai-employee/"
    echo "Or run: git clone <your-repo-url> ~/ai-employee"
else
    echo "Project directory already exists."
fi

# Step 6: Create necessary directories
echo -e "\n${YELLOW}[6/7] Creating directories...${NC}"
cd ~/ai-employee
mkdir -p cloud-vault/{Needs_Action/cloud,Plans/cloud,Pending_Approval/cloud,Approved,Rejected,Done/cloud,Logs,Updates,Signals/{cloud,local},Briefings,Inbox,DropFolder}
mkdir -p ssl logs odoo-addons

# Step 7: Generate self-signed SSL cert (for testing)
echo -e "\n${YELLOW}[7/7] Generating SSL certificate (self-signed for testing)...${NC}"
if [ ! -f "ssl/fullchain.pem" ]; then
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout ssl/privkey.pem \
        -out ssl/fullchain.pem \
        -subj "/C=US/ST=State/L=City/O=AI Employee/CN=localhost"
    echo "Self-signed SSL certificate generated."
else
    echo "SSL certificate already exists."
fi

# Final status
echo -e "\n${GREEN}============================================${NC}"
echo -e "${GREEN}Setup Complete!${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""
echo "Next steps:"
echo "1. Edit .env file with your credentials:"
echo "   nano ~/ai-employee/.env"
echo ""
echo "2. Deploy with Docker Compose:"
echo "   cd ~/ai-employee"
echo "   docker compose -f platinum-docker-compose.yml up -d"
echo ""
echo "3. Check status:"
echo "   docker compose ps"
echo ""
echo "4. View logs:"
echo "   docker compose logs -f"
echo ""
echo "Access Odoo at: http://YOUR_PUBLIC_IP:8069"
echo ""
