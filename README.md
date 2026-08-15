# Real Estate Photography Outreach Tool - POC

A system to help real estate photographers identify listing opportunities and automate outreach to realtors with low-quality or missing professional photography.

## Overview

This tool scrapes real estate listings from Zillow/Redfin, analyzes photo quality, enriches realtor contact information, generates personalized outreach messages, and provides a human-in-the-loop review dashboard before sending.

### Problem Solved
- **For Photographers:** Eliminates manual hunting for listing opportunities; fills booking pipeline efficiently
- **For Realtors:** Discovers affordable photography services for listings that need better visuals
- **Time Saved:** Automated discovery and messaging vs. manual email prospecting

## Features

### MVP (Current Implementation)
- ✅ Zillow/Redfin listing scraping for target zip codes (default: 60610)
- ✅ Photo quality analysis to flag listings needing professional photography
- ✅ Realtor contact information extraction
- ✅ AI-powered personalized outreach message generation
- ✅ Human review dashboard with approve/edit/reject workflow
- ✅ One-click email sending via SendGrid
- ✅ Conversion tracking (sent → response → booking)
- ✅ Analytics dashboard with funnel metrics

### Out of Scope (Future)
- Multi-region scaling
- Payment processing integration
- Advanced CRM features
- Automated follow-up sequences
- SMS/text outreach

## Prerequisites

- Python 3.9+
- PostgreSQL 12+
- Redis (for async task queue)
- Node.js 14+ (for frontend dashboard)
- Git

### API Keys Required
- OpenAI API key (for message generation)
- SendGrid API key (for email sending)
- Zillow API key or web scraping setup

## Installation

### 1. Clone Repository
```bash
git clone https://github.com/yourusername/real-estate-photography-outreach.git
cd real-estate-photography-outreach
```

### 2. Set Up Python Environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure Environment Variables
```bash
cp .env.example .env
```

Edit `.env` with your credentials:
```
FLASK_ENV=development
DATABASE_URL=postgresql://user:password@localhost:5432/real_estate_photo
OPENAI_API_KEY=your_openai_key
SENDGRID_API_KEY=your_sendgrid_key
ZILLOW_API_KEY=your_zillow_key
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=your_secret_key
TARGET_ZIP_CODE=60610
```

### 4. Initialize Database
```bash
flask db init
flask db migrate -m "Initial migration"
flask db upgrade
```

### 5. Start Redis Server
```bash
redis-server
```

### 6. Run Application
```bash
# Terminal 1: Start Flask backend
python app.py

# Terminal 2: Start Celery worker for async tasks
celery -A app.celery worker --loglevel=info

# Terminal 3 (optional): Start Celery beat for scheduled scraping
celery -A app.celery beat --loglevel=info
```

Application will be available at `http://localhost:5000`

## Project Structure

```
real-estate-photography-outreach/
├── README.md
├── requirements.txt
├── .env.example
├── .gitignore
├── config.py                 # Configuration management
├── app.py                    # Flask application entry point
├── scraper.py               # Zillow/Redfin scraping logic
├── message_generator.py     # LLM-powered message generation
├── models.py                # SQLAlchemy database models
├── dashboard.html           # Frontend review dashboard
├── static/
│   ├── css/
│   │   └── style.css
│   └── js/
│       └── dashboard.js
├── templates/
│   ├── base.html
│   ├── queue.html
│   ├── analytics.html
│   └── settings.html
├── migrations/              # Database migrations
├── logs/                    # Application logs
└── tests/
    ├── test_scraper.py
    ├── test_message_generator.py
    └── test_models.py
```

## Usage

### Dashboard Workflow

1. **Access Dashboard:** Navigate to `http://localhost:5000/dashboard`
2. **Review Queue:** View flagged listings with extracted realtor data and auto-generated messages
3. **Approve/Edit:** Customize message if needed before approval
4. **Send:** One-click send to realtor email address
5. **Track:** Monitor responses and conversions in analytics tab

### Running Manual Scrape

```bash
from scraper import ListingScraper
from config import Config

scraper = ListingScraper(
    zip_code=Config.TARGET_ZIP_CODE,
    max_listings=50
)
listings = scraper.run()
```

### Generating Outreach Message

```bash
from message_generator import MessageGenerator

generator = MessageGenerator()
message = generator.generate(
    realtor_name="John Smith",
    property_address="123 N Michigan Ave, Chicago, IL 60610",
    property_type="Condo",
    listing_price=450000,
    photo_count=2
)
```

### API Endpoints

#### GET `/api/queue`
Returns flagged listings pending review
```json
{
  "listings": [
    {
      "id": 1,
      "address": "123 N Michigan Ave",
      "realtor_name": "John Smith",
      "realtor_email": "john@realestate.com",
      "photo_count": 2,
      "message_draft": "Hi John, I noticed...",
      "status": "pending_review"
    }
  ]
}
```

#### POST `/api/queue/approve`
Approve and send outreach message
```json
{
  "listing_id": 1,
  "message": "Customized message text",
  "send_immediately": true
}
```

#### GET `/api/analytics`
Return conversion funnel metrics
```json
{
  "total_outreach_sent": 45,
  "responses_received": 6,
  "response_rate": 0.133,
  "bookings_closed": 2,
  "conversion_rate": 0.033,
  "avg_days_to_response": 3.2
}
```

## Database Schema

### Listings
- `id` (Primary Key)
- `address` (String)
- `zip_code` (String)
- `listing_id` (String, external ID)
- `mls_number` (String)
- `property_type` (String)
- `price` (Decimal)
- `photo_count` (Integer)
- `photo_quality_score` (Float, 0-100)
- `realtor_id` (Foreign Key)
- `flagged_at` (DateTime)
- `created_at` (DateTime)

### Realtors
- `id` (Primary Key)
- `name` (String)
- `email` (String)
- `phone` (String)
- `broker` (String)
- `mls_provider` (String)
- `created_at` (DateTime)

### Outreach
- `id` (Primary Key)
- `listing_id` (Foreign Key)
- `message_draft` (Text)
- `message_sent` (Text)
- `status` (String: pending_review, approved, sent, bounced)
- `sent_at` (DateTime)
- `response_received_at` (DateTime)
- `booking_id` (Foreign Key, nullable)
- `created_at` (DateTime)

### Bookings
- `id` (Primary Key)
- `outreach_id` (Foreign Key)
- `realtor_id` (Foreign Key)
- `listing_id` (Foreign Key)
- `pricing` (Decimal)
- `shoot_date` (DateTime)
- `status` (String: pending, confirmed, completed, cancelled)
- `created_at` (DateTime)

## Configuration

Edit `config.py` to customize:
- Target zip codes for scraping
- Photo quality threshold for flagging
- Default pricing for photography services
- Message tone and templates
- Scraping frequency and limits
- Email sending preferences

## Logging

Logs are written to `logs/app.log` with rotating file handler. Adjust verbosity in `config.py`:
```python
LOG_LEVEL = 'INFO'  # DEBUG, INFO, WARNING, ERROR
```

## Testing

Run test suite:
```bash
pytest tests/ -v
```

Test coverage:
```bash
pytest tests/ --cov=. --cov-report=html
```

## Success Metrics (POC Target)

- ✅ Identify ≥20 viable listings in 60610 within 1 week
- ✅ Generate outreach messages with ≥80% accuracy
- ✅ Achieve ≥10% response rate from sent outreach
- ✅ Close ≥2-3 photography sessions
- ✅ Validate realtor pain point through conversations

## Troubleshooting

### Scraper Timeouts
- Increase `SCRAPER_TIMEOUT` in `.env` (default: 30 seconds)
- Verify Zillow/Redfin not blocking requests; rotate user agents
- Check Redis connection if using async scraping

### Message Generation Delays
- Verify OpenAI API key and rate limits
- Check `logs/app.log` for API errors
- Increase timeout in `message_generator.py`

### Database Connection Issues
```bash
# Test PostgreSQL connection
psql postgresql://user:password@localhost:5432/real_estate_photo

# Reset database (development only)
flask db downgrade
flask db upgrade
```

### Email Not Sending
- Verify SendGrid API key in `.env`
- Check SendGrid sender verification
- Review bounce/spam reports in SendGrid dashboard
- Check `logs/app.log` for delivery errors

## Performance Considerations

- **Scraping:** Runs async via Celery; typical 50 listings = 2-5 minutes
- **Message Generation:** ~1-2 seconds per message via OpenAI API
- **Dashboard Load:** Optimized for 100+ listings; pagination built-in
- **Email Sending:** Batched via SendGrid; 100 emails ~30 seconds

## Security

- ✅ Environment variables for sensitive credentials (no hardcoding)
- ✅ SQL injection prevention via SQLAlchemy ORM
- ✅ CSRF protection on forms
- ✅ Rate limiting on API endpoints (optional)
- ✅ Input validation on all user submissions
- ✅ Encrypted password storage (if user accounts added)

**Important:** Never commit `.env` file; use `.env.example` template only.

## Deployment

### Heroku
```bash
heroku create real-estate-photo-outreach
heroku addons:create heroku-postgresql:standard-0
heroku addons:create heroku-redis:premium-0
git push heroku main
heroku run flask db upgrade
```

### Railway
Connect GitHub repository; Railway auto-deploys on push. Set environment variables in Railway dashboard.

### GitHub Actions (Daily Scrape)
Create `.github/workflows/daily-scrape.yml`:
```yaml
name: Daily Listing Scrape
on:
  schedule:
    - cron: '0 2 * * *'
jobs:
  scrape:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - run: pip install -r requirements.txt
      - run: python -c "from scraper import ListingScraper; ListingScraper().run()"
```

## Contributing

1. Fork repository
2. Create feature branch (`git checkout -b feature/improvement`)
3. Commit changes (`git commit -am 'Add feature'`)
4. Push branch (`git push origin feature/improvement`)
5. Open Pull Request

## License

MIT License - See LICENSE file for details

## Support

For issues, questions, or feature requests:
1. Check existing GitHub Issues
2. Review troubleshooting section above
3. Open new Issue with detailed reproduction steps
4. Contact: support@realtorphoto.local

## Roadmap (Post-POC)

- [ ] Multi-zip code support with region management
- [ ] Payment processing integration (Stripe)
- [ ] Advanced CRM features (follow-up sequences, tags)
- [ ] SMS/text outreach channel
- [ ] Competitor integration (Redfin, Trulia)
- [ ] Mobile app for photographers
- [ ] Analytics dashboard with custom reporting
- [ ] A/B testing on message variations
- [ ] Integration with photographer scheduling tools
- [ ] White-label option for agencies

## Changelog

### v0.1.0 (Initial POC)
- Zillow scraping for single zip code
- Realtor contact enrichment
- AI message generation
- Review dashboard
- Email sending integration
- Basic analytics
- PostgreSQL persistence
- Async task processing

---

**Last Updated:** 2024
**Maintained By:** Real Estate Photography Team
**POC Status:** Active Development