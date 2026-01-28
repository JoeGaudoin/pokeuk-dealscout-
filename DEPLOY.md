# Deployment Guide - PokeUK DealScout

## Quick Deploy Options

### Option 1: Vercel + Railway (Recommended)

**Frontend (Vercel):**
```bash
cd frontend
npm install -g vercel
vercel
# Follow prompts, set NEXT_PUBLIC_API_URL to your Railway backend URL
```

**Backend (Railway):**
```bash
# Install Railway CLI
npm install -g @railway/cli
railway login
railway init
railway up
# Add PostgreSQL and Redis from Railway dashboard
# Set environment variables in Railway dashboard
```

### Option 2: Render (All-in-One)

```bash
# Push to GitHub first
git remote add origin https://github.com/YOUR_USERNAME/pokeuk-dealscout.git
git push -u origin main

# Then in Render dashboard:
# 1. New > Blueprint
# 2. Connect your GitHub repo
# 3. Render will read render.yaml and create all services
```

### Option 3: Fly.io

```bash
# Install Fly CLI
curl -L https://fly.io/install.sh | sh
fly auth login

# Deploy backend
fly launch --config fly.toml
fly secrets set DATABASE_URL=your_db_url REDIS_URL=your_redis_url

# Deploy frontend to Vercel or Fly
```

### Option 4: Docker Compose (Self-hosted / VPS)

```bash
# On your server
git clone https://github.com/YOUR_USERNAME/pokeuk-dealscout.git
cd pokeuk-dealscout

# Create .env file
cat > .env << EOF
POSTGRES_PASSWORD=your_secure_password
EBAY_APP_ID=your_ebay_app_id
EBAY_CERT_ID=your_ebay_cert_id
EBAY_OAUTH_TOKEN=your_token
EOF

# Deploy
docker compose -f docker-compose.prod.yml up -d

# Run migrations
docker compose exec api alembic upgrade head
```

---

## Environment Variables Required

### Backend (Required)
```
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/db
REDIS_URL=redis://host:6379/0
```

### Backend (Optional - for scrapers)
```
EBAY_APP_ID=your_ebay_app_id
EBAY_CERT_ID=your_ebay_cert_id
EBAY_OAUTH_TOKEN=your_oauth_token
POKEMON_TCG_API_KEY=your_api_key
PROXY_ENABLED=false
PROXY_SERVICE_URL=
```

### Frontend
```
NEXT_PUBLIC_API_URL=https://your-api-domain.com
```

---

## Database Setup

### Railway PostgreSQL
1. Add PostgreSQL from Railway dashboard
2. Copy connection string to `DATABASE_URL`

### Supabase (Free tier available)
1. Create project at supabase.com
2. Go to Settings > Database
3. Copy connection string (use "Connection pooling" URL)

### Neon (Free tier available)
1. Create project at neon.tech
2. Copy connection string from dashboard

---

## Redis Setup

### Railway Redis
1. Add Redis from Railway dashboard
2. Copy connection string to `REDIS_URL`

### Upstash (Free tier, serverless)
1. Create database at upstash.com
2. Copy Redis URL

---

## Running Migrations

After deploying, run database migrations:

```bash
# Railway
railway run alembic upgrade head

# Render
# Migrations run automatically via render.yaml

# Docker
docker compose exec api alembic upgrade head

# Fly
fly ssh console -C "alembic upgrade head"
```

---

## Monitoring & Logs

### Railway
```bash
railway logs
```

### Render
View logs in Render dashboard

### Fly.io
```bash
fly logs
```

### Docker
```bash
docker compose logs -f api
docker compose logs -f scraper
```

---

## Scraper Deployment

The scraper worker runs separately and can be deployed as:

1. **Background worker** (Railway/Render) - Runs continuously
2. **Cron job** - Run on schedule (e.g., every 5 minutes)
3. **Serverless function** - Triggered by scheduler

For serverless/cron, modify `run_once.py` to exit after one run.

---

## SSL/HTTPS

- **Vercel**: Automatic SSL
- **Railway**: Automatic SSL
- **Render**: Automatic SSL
- **Fly.io**: Automatic SSL
- **Self-hosted**: Use Caddy or nginx with Let's Encrypt

---

## Scaling

### Horizontal Scaling
- Backend: Increase replicas in Railway/Render/Fly
- Frontend: Vercel scales automatically
- Database: Upgrade to larger plan

### Caching
- Redis caches active deals (5 min TTL)
- React Query caches on frontend (60s stale time)

---

## Costs (Estimated Monthly)

| Service | Free Tier | Production |
|---------|-----------|------------|
| Vercel (Frontend) | Free | $0-20 |
| Railway (Backend) | $5 credit | $10-30 |
| Railway (Postgres) | Included | $5-20 |
| Railway (Redis) | Included | $5-10 |
| **Total** | ~$5 | ~$30-80 |

---

## Troubleshooting

### API not responding
1. Check logs: `railway logs` or Render dashboard
2. Verify DATABASE_URL and REDIS_URL are set
3. Check health endpoint: `curl https://your-api/health`

### Scrapers not working
1. eBay requires valid API credentials
2. Playwright scrapers need more memory (upgrade plan)
3. Check proxy configuration if getting blocked

### Frontend not connecting
1. Verify NEXT_PUBLIC_API_URL is correct
2. Check CORS settings in backend
3. Ensure API is publicly accessible

---

## Security Checklist

- [ ] Use strong POSTGRES_PASSWORD
- [ ] Keep API keys in environment variables (not code)
- [ ] Enable HTTPS everywhere
- [ ] Set up rate limiting on API
- [ ] Monitor for unusual activity
- [ ] Regular backups of PostgreSQL
