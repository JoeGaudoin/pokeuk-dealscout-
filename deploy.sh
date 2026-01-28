#!/bin/bash

# PokeUK DealScout - Deployment Script
# Run: chmod +x deploy.sh && ./deploy.sh

set -e

echo "========================================"
echo "  PokeUK DealScout - Deployment"
echo "========================================"
echo ""

# Check for required tools
check_command() {
    if ! command -v $1 &> /dev/null; then
        echo "Installing $1..."
        npm install -g $2 || npm install $2 --save-dev
    fi
}

# Step 1: Railway Backend Deployment
echo "STEP 1: Deploy Backend to Railway"
echo "=================================="
echo ""

# Check if logged in to Railway
if ! npx railway whoami &> /dev/null; then
    echo "Please login to Railway (opens browser)..."
    npx railway login
fi

echo ""
echo "Creating Railway project..."
npx railway init --name pokeuk-dealscout

echo ""
echo "Adding PostgreSQL database..."
npx railway add --database postgres

echo ""
echo "Adding Redis..."
npx railway add --database redis

echo ""
echo "Setting environment variables..."
echo "Please enter your eBay API credentials (press Enter to skip):"
read -p "EBAY_APP_ID: " EBAY_APP_ID
read -p "EBAY_CERT_ID: " EBAY_CERT_ID
read -p "EBAY_OAUTH_TOKEN: " EBAY_OAUTH_TOKEN

if [ ! -z "$EBAY_APP_ID" ]; then
    npx railway variables set EBAY_APP_ID="$EBAY_APP_ID"
fi
if [ ! -z "$EBAY_CERT_ID" ]; then
    npx railway variables set EBAY_CERT_ID="$EBAY_CERT_ID"
fi
if [ ! -z "$EBAY_OAUTH_TOKEN" ]; then
    npx railway variables set EBAY_OAUTH_TOKEN="$EBAY_OAUTH_TOKEN"
fi

echo ""
echo "Deploying backend..."
cd backend
npx railway up --detach
cd ..

echo ""
echo "Getting backend URL..."
BACKEND_URL=$(npx railway domain)
echo "Backend deployed at: $BACKEND_URL"

# Step 2: Vercel Frontend Deployment
echo ""
echo "STEP 2: Deploy Frontend to Vercel"
echo "=================================="
echo ""

cd frontend

# Check if logged in to Vercel
if ! npx vercel whoami &> /dev/null; then
    echo "Please login to Vercel (opens browser)..."
    npx vercel login
fi

echo ""
echo "Deploying frontend..."
npx vercel --prod --yes -e NEXT_PUBLIC_API_URL="https://$BACKEND_URL"

cd ..

echo ""
echo "========================================"
echo "  DEPLOYMENT COMPLETE!"
echo "========================================"
echo ""
echo "Backend API: https://$BACKEND_URL"
echo "Frontend: Check Vercel dashboard for URL"
echo ""
echo "Next steps:"
echo "1. Run database migrations:"
echo "   cd backend && npx railway run alembic upgrade head"
echo ""
echo "2. Sync Pokemon card data:"
echo "   npx railway run python -m scrapers.sync_cards --popular"
echo ""
echo "3. Start scrapers (optional):"
echo "   npx railway run python -m scrapers.run_once"
echo ""
