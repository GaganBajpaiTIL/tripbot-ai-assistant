# Deployment Guide

## Quick Deploy on Replit

1. **Set Environment Variables**
   - Go to Secrets tab in Replit
   - Add your API key:
     - `OPENAI_API_KEY` with your OpenAI key, OR
     - `GEMINI_API_KEY` with your Google Gemini key

2. **Run the Application**
   - Click the "Run" button
   - Application will start on port 5000
   - Access via the provided Replit URL

## Deploy on Other Platforms

### Heroku
```bash
# Install Heroku CLI and login
heroku create your-tripbot-app
heroku config:set OPENAI_API_KEY=your-key-here
git push heroku main
```

### Railway
```bash
# Install Railway CLI
railway login
railway new
railway add
railway up
```

### DigitalOcean App Platform
1. Connect your GitHub repository
2. Set environment variables in the dashboard
3. Deploy with one click

### Self-Hosted (Ubuntu/Linux)
```bash
# Install dependencies
sudo apt update
sudo apt install python3 python3-pip nginx

# Clone and setup
git clone your-repo
cd tripbot
pip3 install -r requirements.txt

# Create systemd service
sudo nano /etc/systemd/system/tripbot.service

# Add environment variables
export OPENAI_API_KEY=your-key

# Start service
sudo systemctl enable tripbot
sudo systemctl start tripbot

# Configure nginx reverse proxy
sudo nano /etc/nginx/sites-available/tripbot
```

## Database Options

### SQLite (Default)
- No additional setup required
- Perfect for development and small deployments

### PostgreSQL (Recommended for Production)
```bash
# Install PostgreSQL
sudo apt install postgresql postgresql-contrib

# Create database
sudo -u postgres createdb tripbot

# Set environment variable
export DATABASE_URL=postgresql://user:password@localhost/tripbot
```

### MySQL
```bash
# Install MySQL
sudo apt install mysql-server

# Create database
mysql -u root -p
CREATE DATABASE tripbot;

# Set environment variable
export DATABASE_URL=mysql://user:password@localhost/tripbot
```

## Security Checklist

- [ ] Set strong SESSION_SECRET
- [ ] Use HTTPS in production
- [ ] Secure API keys as environment variables
- [ ] Enable firewall rules
- [ ] Regular backups of database
- [ ] Monitor application logs
- [ ] Update dependencies regularly

## Performance Optimization

### Database
- Add indexes for frequently queried fields
- Use connection pooling
- Regular database maintenance

### Caching
- Add Redis for session storage
- Cache API responses
- Use CDN for static files

### Monitoring
- Set up application monitoring
- Log aggregation
- Error tracking
- Performance metrics

## Scaling Considerations

### Horizontal Scaling
- Use load balancer
- Multiple application instances
- Shared database
- Session storage in Redis

### Vertical Scaling
- Increase server resources
- Optimize database queries
- Profile application performance
