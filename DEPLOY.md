# Meridian Deployment Guide

## Overview

This guide covers deploying Meridian to production environments using:
- **AWS ECS Fargate** (recommended for production)
- **Docker Compose** (for self-hosted or local production)

## Prerequisites

- AWS CLI configured with appropriate credentials (ECS path only)
- Terraform >= 1.0 (ECS path only)
- Docker and Docker Compose
- GitHub repository with secrets configured

---

## Portfolio demo (Railway + Vercel) — recommended MVP path

For **recruiter demos and LinkedIn portfolio links**, deploy the smallest working stack before investing in AWS ECS.

| Component | Platform | Notes |
|-----------|----------|-------|
| Frontend (Vite/React) | **Vercel** | Connect GitHub repo, root `frontend/`, build `npm run build`, output `dist/` |
| API (FastAPI) | **Railway** | Dockerfile or Nixpacks from repo root; expose port `8000` |
| Neo4j | **Railway** or **Neo4j Aura Free** | Aura free tier fits demo graph size; set `NEO4J_URI` on API service |
| Env | Both | `VITE_API_URL` → Railway API URL; `NEO4J_*`, `JWT_SECRET_KEY` on API |

### Quick steps

1. **Railway:** New project → deploy API service → add Neo4j (plugin or Aura connection string).
2. **Seed data:** Run `make seed-all` against the remote Neo4j (or run seed scripts from a one-off Railway job / local with remote URI).
3. **Vercel:** Import repo → set root directory `frontend` → add `VITE_API_URL=https://your-api.up.railway.app`.
4. **Verify:** `/health` on API, map loads on Vercel preview URL, `make pipeline-refresh` optional for live GDELT.

See also `docs/DEMO.md` for the 5-minute local demo script. Record GIF to `docs/assets/meridian-demo.gif` after deploy.

**Cost:** Vercel hobby + Railway starter + Aura free ≈ **$0–20/mo** — suitable until open-source traction justifies ECS.

---

## Option 1: AWS ECS Fargate Deployment (production scale)

### Step 1: Configure AWS Credentials

```bash
aws configure
# Enter your AWS Access Key ID, Secret Access Key, and default region
```

### Step 2: Set Up GitHub Secrets

In your GitHub repository, add these secrets:

- `AWS_ACCESS_KEY_ID` - Your AWS access key
- `AWS_SECRET_ACCESS_KEY` - Your AWS secret key
- `NEO4J_PASSWORD` - Secure password for Neo4j database
- `JWT_SECRET_KEY` - Secure random string for JWT signing

### Step 3: Deploy Infrastructure

```bash
cd terraform

# Initialize Terraform
terraform init

# Plan deployment
terraform plan \
  -var="neo4j_password=your-secure-password" \
  -var="jwt_secret_key=your-jwt-secret"

# Apply deployment
terraform apply \
  -var="neo4j_password=your-secure-password" \
  -var="jwt_secret_key=your-jwt-secret"
```

### Step 4: Push to GitHub

```bash
git add .
git commit -m "Production deployment"
git push origin main
```

The CI/CD pipeline will automatically:
1. Run tests
2. Build Docker images
3. Push to Amazon ECR
4. Deploy to ECS

### Step 5: Verify Deployment

```bash
# Get the load balancer DNS
terraform output alb_dns_name

# Test the API
curl http://$(terraform output -raw alb_dns_name)/health
```

---

## Option 2: Docker Compose Deployment

### Step 1: Set Environment Variables

```bash
export NEO4J_PASSWORD=your-secure-password
export JWT_SECRET_KEY=your-jwt-secret
```

### Step 2: Start Services

```bash
docker-compose -f docker-compose.prod.yml up -d
```

### Step 3: Verify Services

```bash
# Check all services are running
docker-compose -f docker-compose.prod.yml ps

# View logs
docker-compose -f docker-compose.prod.yml logs -f api

# Test API
curl http://localhost:8000/health
```

### Step 4: Build and Deploy Frontend (Optional)

```bash
cd frontend
npm install
npm run build

# Serve with nginx or copy to static hosting
```

---

## Infrastructure Components

### AWS Resources Created

| Resource | Purpose |
|----------|---------|
| ECS Cluster | Container orchestration |
| ECR Repositories | Docker image storage (API + Frontend) |
| Application Load Balancer | Traffic distribution |
| VPC + Subnets | Network isolation |
| Security Groups | Firewall rules |
| CloudWatch Logs | Logging |
| Secrets Manager | Secure credential storage |

### Services Deployed

| Service | Container | Port | Description |
|---------|-----------|------|-------------|
| API | meridian-api | 8000 | FastAPI backend |
| Neo4j | neo4j:5.14 | 7687 | Graph database |
| Kafka | confluentinc/cp-kafka | 9092 | Message broker |
| Zookeeper | confluentinc/cp-zookeeper | 2181 | Kafka coordination |

---

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `NEO4J_URI` | Yes | - | Neo4j connection string |
| `NEO4J_USER` | Yes | neo4j | Neo4j username |
| `NEO4J_PASSWORD` | Yes | - | Neo4j password |
| `KAFKA_BOOTSTRAP_SERVERS` | Yes | - | Kafka brokers |
| `JWT_SECRET_KEY` | Yes | - | JWT signing key |
| `SLACK_WEBHOOK_URL` | No | - | Slack alerting |
| `ENVIRONMENT` | No | dev | Environment name |

---

## Scaling

### AWS ECS Auto-scaling

Edit `terraform/main.tf` to adjust:

```hcl
resource "aws_ecs_service" "api" {
  desired_count = 4  # Increase for more instances
  # ...
}
```

Or use auto-scaling:

```bash
aws application-autoscaling register-scalable-target \
  --service-namespace ecs \
  --resource-id service/meridian-dev/meridian-api-dev \
  --scalable-dimension ecs:service:DesiredCount \
  --min-capacity 2 \
  --max-capacity 10
```

---

## Monitoring

### CloudWatch

View logs in AWS Console:
- CloudWatch > Log Groups > `/ecs/meridian-api-dev`

### Health Checks

```bash
# API health
curl https://your-domain.com/health

# Neo4j health
curl https://your-domain.com/health/neo4j
```

---

## Troubleshooting

### Container Won't Start

```bash
# Check logs
docker-compose -f docker-compose.prod.yml logs api

# Verify environment variables
docker-compose -f docker-compose.prod.yml config
```

### Database Connection Issues

```bash
# Test Neo4j connection
docker-compose -f docker-compose.prod.yml exec neo4j cypher-shell -u neo4j -p $NEO4J_PASSWORD

# Reset Neo4j (WARNING: Deletes data)
docker-compose -f docker-compose.prod.yml down -v
docker-compose -f docker-compose.prod.yml up -d
```

### ECS Deployment Failed

```bash
# Check service events
aws ecs describe-services \
  --cluster meridian-dev \
  --services meridian-api-dev \
  --query 'services[0].events' \
  --output table
```

---

## Security Checklist

- [ ] Change default passwords (Neo4j, JWT)
- [ ] Enable HTTPS/SSL certificates
- [ ] Restrict security group access
- [ ] Enable CloudTrail logging
- [ ] Rotate AWS credentials regularly
- [ ] Enable MFA for AWS console
- [ ] Review IAM permissions

---

## Cost Optimization

### AWS Free Tier Eligible
- ECS (with Fargate)
- ECR (500MB storage)
- CloudWatch (logs)

### Cost-Saving Tips
1. Use Fargate Spot for non-critical workloads
2. Set CloudWatch log retention to 7 days
3. Use smaller task sizes (512 CPU / 1GB memory)
4. Shut down dev environment when not needed

---

## Support

For deployment issues:
1. Check GitHub Issues
2. Review CloudWatch logs
3. Verify Terraform plan output
4. Test locally with Docker Compose first
