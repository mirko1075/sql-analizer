#!/bin/bash
# MySQL Lab Database Connection Troubleshooting
# Run this on your local machine to diagnose the connection issue

echo "==================================================================="
echo "MySQL Lab Database - Connection Troubleshooting"
echo "==================================================================="
echo ""

# Step 1: Check container status
echo "Step 1: Container Status"
echo "-------------------------------------------------------------------"
docker ps --filter name=mysql-lab-slowquery
echo ""

# Step 2: Check logs for initialization status
echo "Step 2: Checking if MySQL is ready (last 30 lines of logs)"
echo "-------------------------------------------------------------------"
docker logs mysql-lab-slowquery 2>&1 | tail -30
echo ""
echo "Look for: 'ready for connections' - should appear TWICE"
echo "First time = MySQL started"
echo "Second time = Initialization scripts completed"
echo ""

# Step 3: Test connection from INSIDE the container
echo "Step 3: Testing connection from INSIDE container"
echo "-------------------------------------------------------------------"
docker exec mysql-lab-slowquery mysql -uroot -proot -e "SELECT 'MySQL is accessible from inside' as status;"
if [ $? -eq 0 ]; then
    echo "✓ MySQL works from inside the container"
else
    echo "✗ MySQL not ready yet - still initializing"
fi
echo ""

# Step 4: Check if database exists
echo "Step 4: Checking if ecommerce_lab database exists"
echo "-------------------------------------------------------------------"
docker exec mysql-lab-slowquery mysql -uroot -proot -e "SHOW DATABASES LIKE 'ecommerce_lab';" 2>/dev/null
echo ""

# Step 5: Check bind address
echo "Step 5: Checking MySQL bind address"
echo "-------------------------------------------------------------------"
docker exec mysql-lab-slowquery mysql -uroot -proot -e "SHOW VARIABLES LIKE 'bind_address';" 2>/dev/null
echo "Should be: 0.0.0.0 or * (not 127.0.0.1)"
echo ""

# Step 6: Check port binding
echo "Step 6: Checking port binding from host"
echo "-------------------------------------------------------------------"
netstat -tuln | grep 3307 || ss -tuln | grep 3307
echo ""

# Step 7: Try connection from host
echo "Step 7: Testing connection from HOST"
echo "-------------------------------------------------------------------"
echo "Attempting: mysql -h 127.0.0.1 -P 3307 -u root -proot"
mysql -h 127.0.0.1 -P 3307 -u root -proot -e "SELECT 'Connection from host works!' as status;" 2>&1
echo ""

# Step 8: Check if data is loaded
echo "Step 8: Checking if data is loaded"
echo "-------------------------------------------------------------------"
docker exec mysql-lab-slowquery mysql -uroot -proot ecommerce_lab -e "SELECT COUNT(*) as user_count FROM users;" 2>/dev/null
echo ""

echo "==================================================================="
echo "Diagnostics Complete"
echo "==================================================================="
echo ""
echo "Common Issues and Solutions:"
echo ""
echo "1. If MySQL is not ready:"
echo "   - Wait 1-2 minutes for initialization"
echo "   - Check logs: docker logs mysql-lab-slowquery"
echo ""
echo "2. If bind_address is 127.0.0.1:"
echo "   - Stop container: docker compose down"
echo "   - Restart: docker compose up -d"
echo ""
echo "3. If port 3307 is not listening:"
echo "   - Check if another service is using port 3307"
echo "   - Try: lsof -i :3307"
echo ""
echo "4. If connection works from inside but not outside:"
echo "   - This is a Docker networking issue"
echo "   - Try: docker inspect mysql-lab-slowquery"
echo "   - Check firewall: sudo ufw status"
echo ""
