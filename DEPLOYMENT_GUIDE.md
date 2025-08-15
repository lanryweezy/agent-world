# Autonomous AI Ecosystem - Deployment Guide

## 🚀 Production Deployment Guide

This guide provides step-by-step instructions for deploying the Autonomous AI Ecosystem in production environments.

## 📋 Prerequisites

### System Requirements
- **OS**: Linux (Ubuntu 20.04+ recommended), macOS, or Windows 10+
- **Python**: 3.8 or higher
- **Memory**: Minimum 4GB RAM (8GB+ recommended for production)
- **Storage**: 10GB+ available disk space
- **Network**: Stable internet connection for LLM API access

### Dependencies
```bash
# Core dependencies
pip install asyncio aiohttp sqlite3 psutil pytest

# Web interface dependencies
pip install flask websockets

# Optional: LLM integration
pip install openai anthropic

# Optional: Advanced features
pip install selenium beautifulsoup4 numpy pandas matplotlib
```

## 🔧 Installation Steps

### 1. Clone and Setup
```bash
# Clone the repository
git clone <repository-url>
cd autonomous-ai-ecosystem

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration
```bash
# Copy configuration template
cp config.json.example config.json

# Edit configuration
nano config.json
```

### Sample Production Configuration
```json
{
  "ecosystem_id": "production_ecosystem",
  "data_directory": "/var/lib/ai_ecosystem",
  "log_level": "INFO",
  "max_agents": 50,
  
  "enable_web_browsing": true,
  "enable_virtual_world": true,
  "enable_economy": true,
  "enable_reproduction": true,
  "enable_distributed_mode": false,
  "enable_human_oversight": true,
  "enable_safety_systems": true,
  
  "health_check_interval": 30,
  "cleanup_interval": 300,
  
  "api_keys": {
    "openai": "your-openai-api-key",
    "anthropic": "your-anthropic-api-key"
  },
  
  "network": {
    "host": "0.0.0.0",
    "port": 8080,
    "max_connections": 100
  },
  
  "security": {
    "enable_authentication": true,
    "admin_password": "secure-admin-password",
    "rate_limiting": true
  },
  
  "monitoring": {
    "enable_metrics": true,
    "metrics_port": 9090,
    "log_file": "/var/log/ai_ecosystem.log"
  }
}
```

### 3. Database Setup
```bash
# Create data directory
sudo mkdir -p /var/lib/ai_ecosystem
sudo chown $USER:$USER /var/lib/ai_ecosystem

# Initialize database
python -c "from autonomous_ai_ecosystem.core.config import initialize_database; initialize_database()"
```

### 4. Security Setup
```bash
# Create log directory
sudo mkdir -p /var/log/ai_ecosystem
sudo chown $USER:$USER /var/log/ai_ecosystem

# Set appropriate permissions
chmod 750 /var/lib/ai_ecosystem
chmod 640 config.json
```

## 🐳 Docker Deployment

### Dockerfile
```dockerfile
FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN useradd -m -u 1000 aiuser && chown -R aiuser:aiuser /app
USER aiuser

# Expose ports
EXPOSE 8080 9090

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:8080/health')"

# Start application
CMD ["python", "main.py"]
```

### Docker Compose
```yaml
version: '3.8'

services:
  ai-ecosystem:
    build: .
    ports:
      - "8080:8080"
      - "9090:9090"
    volumes:
      - ./data:/var/lib/ai_ecosystem
      - ./logs:/var/log/ai_ecosystem
      - ./config.json:/app/config.json:ro
    environment:
      - PYTHONPATH=/app
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "python", "-c", "import requests; requests.get('http://localhost:8080/health')"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  monitoring:
    image: prom/prometheus:latest
    ports:
      - "9091:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml:ro
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/etc/prometheus/console_libraries'
      - '--web.console.templates=/etc/prometheus/consoles'
    restart: unless-stopped

volumes:
  data:
  logs:
```

## ☸️ Kubernetes Deployment

### Namespace
```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: ai-ecosystem
```

### ConfigMap
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: ai-ecosystem-config
  namespace: ai-ecosystem
data:
  config.json: |
    {
      "ecosystem_id": "k8s_ecosystem",
      "data_directory": "/data",
      "log_level": "INFO",
      "max_agents": 100,
      "enable_distributed_mode": true,
      "network": {
        "host": "0.0.0.0",
        "port": 8080
      }
    }
```

### Deployment
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ai-ecosystem
  namespace: ai-ecosystem
spec:
  replicas: 3
  selector:
    matchLabels:
      app: ai-ecosystem
  template:
    metadata:
      labels:
        app: ai-ecosystem
    spec:
      containers:
      - name: ai-ecosystem
        image: ai-ecosystem:latest
        ports:
        - containerPort: 8080
        - containerPort: 9090
        volumeMounts:
        - name: config
          mountPath: /app/config.json
          subPath: config.json
        - name: data
          mountPath: /data
        resources:
          requests:
            memory: "2Gi"
            cpu: "500m"
          limits:
            memory: "4Gi"
            cpu: "2000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /ready
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 10
      volumes:
      - name: config
        configMap:
          name: ai-ecosystem-config
      - name: data
        persistentVolumeClaim:
          claimName: ai-ecosystem-data
```

### Service
```yaml
apiVersion: v1
kind: Service
metadata:
  name: ai-ecosystem-service
  namespace: ai-ecosystem
spec:
  selector:
    app: ai-ecosystem
  ports:
  - name: web
    port: 80
    targetPort: 8080
  - name: metrics
    port: 9090
    targetPort: 9090
  type: LoadBalancer
```

## 🔍 Monitoring Setup

### Prometheus Configuration
```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'ai-ecosystem'
    static_configs:
      - targets: ['localhost:9090']
    metrics_path: /metrics
    scrape_interval: 30s
```

### Grafana Dashboard
```json
{
  "dashboard": {
    "title": "AI Ecosystem Monitoring",
    "panels": [
      {
        "title": "Active Agents",
        "type": "stat",
        "targets": [
          {
            "expr": "ai_ecosystem_active_agents"
          }
        ]
      },
      {
        "title": "System Health",
        "type": "stat",
        "targets": [
          {
            "expr": "ai_ecosystem_system_health"
          }
        ]
      },
      {
        "title": "Memory Usage",
        "type": "graph",
        "targets": [
          {
            "expr": "ai_ecosystem_memory_usage_bytes"
          }
        ]
      }
    ]
  }
}
```

## 🔒 Security Hardening

### 1. Network Security
```bash
# Configure firewall
sudo ufw allow 8080/tcp
sudo ufw allow 9090/tcp
sudo ufw enable

# Use reverse proxy (nginx)
sudo apt install nginx
```

### Nginx Configuration
```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req zone=api burst=20 nodelay;
}
```

### 2. SSL/TLS Setup
```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx

# Get SSL certificate
sudo certbot --nginx -d your-domain.com

# Auto-renewal
sudo crontab -e
# Add: 0 12 * * * /usr/bin/certbot renew --quiet
```

### 3. Application Security
```python
# In config.json
{
  "security": {
    "enable_authentication": true,
    "jwt_secret": "your-secure-jwt-secret",
    "session_timeout": 3600,
    "max_login_attempts": 5,
    "enable_2fa": true
  }
}
```

## 📊 Performance Tuning

### 1. System Optimization
```bash
# Increase file descriptor limits
echo "* soft nofile 65536" >> /etc/security/limits.conf
echo "* hard nofile 65536" >> /etc/security/limits.conf

# Optimize network settings
echo "net.core.somaxconn = 65536" >> /etc/sysctl.conf
echo "net.ipv4.tcp_max_syn_backlog = 65536" >> /etc/sysctl.conf
sysctl -p
```

### 2. Application Tuning
```python
# In config.json
{
  "performance": {
    "worker_threads": 8,
    "connection_pool_size": 100,
    "cache_size_mb": 512,
    "batch_size": 50,
    "async_timeout": 30
  }
}
```

### 3. Database Optimization
```sql
-- SQLite optimizations
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA cache_size = 10000;
PRAGMA temp_store = memory;
```

## 🔄 Backup and Recovery

### 1. Automated Backup Script
```bash
#!/bin/bash
# backup.sh

BACKUP_DIR="/backup/ai_ecosystem"
DATA_DIR="/var/lib/ai_ecosystem"
DATE=$(date +%Y%m%d_%H%M%S)

# Create backup directory
mkdir -p $BACKUP_DIR

# Backup database and configuration
tar -czf $BACKUP_DIR/ecosystem_backup_$DATE.tar.gz \
    $DATA_DIR \
    /app/config.json \
    /var/log/ai_ecosystem

# Keep only last 7 days of backups
find $BACKUP_DIR -name "ecosystem_backup_*.tar.gz" -mtime +7 -delete

echo "Backup completed: ecosystem_backup_$DATE.tar.gz"
```

### 2. Recovery Procedure
```bash
#!/bin/bash
# restore.sh

BACKUP_FILE=$1
RESTORE_DIR="/var/lib/ai_ecosystem"

if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: $0 <backup_file>"
    exit 1
fi

# Stop services
systemctl stop ai-ecosystem

# Restore data
tar -xzf $BACKUP_FILE -C /

# Restart services
systemctl start ai-ecosystem

echo "Recovery completed from $BACKUP_FILE"
```

## 📈 Scaling Strategies

### Horizontal Scaling
```yaml
# HorizontalPodAutoscaler
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: ai-ecosystem-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: ai-ecosystem
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

### Load Balancing
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: ai-ecosystem-ingress
  annotations:
    nginx.ingress.kubernetes.io/load-balance: "round_robin"
    nginx.ingress.kubernetes.io/upstream-hash-by: "$remote_addr"
spec:
  rules:
  - host: ai-ecosystem.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: ai-ecosystem-service
            port:
              number: 80
```

## 🚨 Troubleshooting

### Common Issues

1. **High Memory Usage**
   ```bash
   # Check memory usage
   ps aux | grep python
   
   # Adjust configuration
   # Reduce max_agents in config.json
   ```

2. **Connection Timeouts**
   ```bash
   # Check network connectivity
   netstat -tulpn | grep 8080
   
   # Increase timeout values in config
   ```

3. **Database Locks**
   ```bash
   # Check for database locks
   lsof /var/lib/ai_ecosystem/ecosystem.db
   
   # Restart if necessary
   systemctl restart ai-ecosystem
   ```

### Log Analysis
```bash
# View real-time logs
tail -f /var/log/ai_ecosystem/ecosystem.log

# Search for errors
grep -i error /var/log/ai_ecosystem/ecosystem.log

# Analyze performance
grep -i "slow" /var/log/ai_ecosystem/ecosystem.log
```

## ✅ Health Checks

### Application Health Endpoint
```python
# Health check endpoint returns:
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00Z",
  "version": "1.0.0",
  "agents": {
    "active": 25,
    "total": 30
  },
  "systems": {
    "safety": "running",
    "communication": "running",
    "database": "running"
  },
  "metrics": {
    "uptime_seconds": 86400,
    "memory_usage_mb": 1024,
    "cpu_usage_percent": 45.2
  }
}
```

### Monitoring Alerts
```yaml
# Prometheus alerts
groups:
- name: ai-ecosystem
  rules:
  - alert: HighMemoryUsage
    expr: ai_ecosystem_memory_usage_bytes > 2e9
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "High memory usage detected"
      
  - alert: SystemDown
    expr: up{job="ai-ecosystem"} == 0
    for: 1m
    labels:
      severity: critical
    annotations:
      summary: "AI Ecosystem is down"
```

## 🎯 Production Checklist

- [ ] Configuration reviewed and secured
- [ ] SSL/TLS certificates installed
- [ ] Firewall rules configured
- [ ] Monitoring and alerting setup
- [ ] Backup procedures tested
- [ ] Load testing completed
- [ ] Security audit performed
- [ ] Documentation updated
- [ ] Team training completed
- [ ] Rollback plan prepared

---

This deployment guide provides comprehensive instructions for production deployment of the Autonomous AI Ecosystem. Follow the steps carefully and adapt configurations to your specific environment and requirements.