@echo off
REM Transfer project files to Cloud VM
REM Usage: deploy-to-vm.bat YOUR_VM_IP path\to\ssh_key.pem

if "%1"=="" (
    echo Usage: deploy-to-vm.bat YOUR_VM_IP path\to\ssh_key.pem
    echo Example: deploy-to-vm.bat 132.145.1.23 C:\keys\ssh_key.pem
    pause
    exit /b 1
)

set VM_IP=%1
set SSH_KEY=%2

if "%SSH_KEY%"=="" (
    echo Error: SSH key path is required
    pause
    exit /b 1
)

echo ============================================
echo Transferring AI Employee to Cloud VM
echo ============================================
echo VM IP: %VM_IP%
echo SSH Key: %SSH_KEY%
echo.

echo Transferring files...
scp -i "%SSH_KEY%" -r ^
    docker-compose.yml ^
    platinum-docker-compose.yml ^
    Dockerfile.cloud-agent ^
    Dockerfile.health-monitor ^
    nginx.conf ^
    .env.example ^
    .gitignore ^
    *.py ^
    requirements.txt ^
    DEPLOYMENT.md ^
    ubuntu@%VM_IP%:~/ai-employee/

echo.
echo ============================================
echo Transfer Complete!
echo ============================================
echo.
echo Next steps:
echo 1. SSH into your VM:
echo    ssh -i "%SSH_KEY%" ubuntu@%VM_IP%
echo.
echo 2. Run the setup script:
echo    bash ~/ai-employee/deploy-vm.sh
echo.
echo 3. Edit .env with your credentials:
echo    nano ~/ai-employee/.env
echo.
echo 4. Deploy:
echo    cd ~/ai-employee
echo    docker compose -f platinum-docker-compose.yml up -d
echo.
pause
