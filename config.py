import os
from dotenv import load_dotenv
from datetime import timedelta

load_dotenv()

class Config:
    """Base configuration"""
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JSON_SORT_KEYS = False
    
    # Database
    SQLALCHEMY_DATABASE_URI = os.getenv(
        'DATABASE_URL',
        'postgresql://user:password@localhost:5432/re_photography_poc'
    )
    
    # Flask
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    DEBUG = os.getenv('DEBUG', 'False') == 'True'
    TESTING = False
    
    # Scraping
    TARGET_ZIP_CODES = os.getenv('TARGET_ZIP_CODES', '60610').split(',')
    ZILLOW_BASE_URL = 'https://www.zillow.com'
    REDFIN_BASE_URL = 'https://www.redfin.com'
    SCRAPER_TIMEOUT = int(os.getenv('SCRAPER_TIMEOUT', '30'))
    SCRAPER_MAX_RETRIES = int(os.getenv('SCRAPER_MAX_RETRIES', '3'))
    PHOTO_QUALITY_THRESHOLD = int(os.getenv('PHOTO_QUALITY_THRESHOLD', '5'))
    
    # Scraping delays (in seconds) to avoid detection
    SCRAPER_MIN_DELAY = float(os.getenv('SCRAPER_MIN_DELAY', '2'))
    SCRAPER_MAX_DELAY = float(os.getenv('SCRAPER_MAX_DELAY', '8'))
    
    # User agent for web scraping
    USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    
    # OpenAI API
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
    OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo')
    
    # Email Service (SendGrid/Mailgun)
    EMAIL_SERVICE = os.getenv('EMAIL_SERVICE', 'sendgrid')  # 'sendgrid' or 'mailgun'
    SENDGRID_API_KEY = os.getenv('SENDGRID_API_KEY', '')
    MAILGUN_API_KEY = os.getenv('MAILGUN_API_KEY', '')
    MAILGUN_DOMAIN = os.getenv('MAILGUN_DOMAIN', '')
    FROM_EMAIL = os.getenv('FROM_EMAIL', 'noreply@photography-outreach.com')
    FROM_NAME = os.getenv('FROM_NAME', 'Photography Outreach')
    
    # Pricing
    DEFAULT_PHOTOGRAPHY_RATE = float(os.getenv('DEFAULT_PHOTOGRAPHY_RATE', '250'))
    
    # Outreach
    OUTREACH_MESSAGE_TEMPLATE = os.getenv(
        'OUTREACH_MESSAGE_TEMPLATE',
        "Hi {realtor_name},\n\nI noticed your listing at {property_address} could really stand out with professional photography. Professional photos increase buyer engagement by up to 80%.\n\nI specialize in real estate photography and offer competitive rates starting at ${rate} for {property_type} properties.\n\nWould you be interested in learning more?\n\nBest regards"
    )
    
    # Redis (for Celery)
    REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    
    # Celery
    CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', REDIS_URL)
    CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', REDIS_URL)
    CELERY_TASK_SERIALIZER = 'json'
    CELERY_RESULT_SERIALIZER = 'json'
    CELERY_ACCEPT_CONTENT = ['json']
    CELERY_TIMEZONE = 'UTC'
    CELERY_ENABLE_UTC = True
    
    # Scheduling
    SCRAPER_SCHEDULE_HOUR = int(os.getenv('SCRAPER_SCHEDULE_HOUR', '2'))  # 2 AM
    SCRAPER_SCHEDULE_MINUTE = int(os.getenv('SCRAPER_SCHEDULE_MINUTE', '0'))
    
    # Pagination
    ITEMS_PER_PAGE = int(os.getenv('ITEMS_PER_PAGE', '20'))
    
    # Session
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    SESSION_COOKIE_SECURE = os.getenv('SESSION_COOKIE_SECURE', 'True') == 'True'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # CORS
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', 'http://localhost:3000,http://localhost:5000').split(',')
    
    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', 'logs/app.log')
    
    # MLS Data
    MLS_LOOKUP_API = os.getenv('MLS_LOOKUP_API', '')  # Optional MLS API endpoint
    
    # Feature Flags
    ENABLE_ZILLOW_SCRAPING = os.getenv('ENABLE_ZILLOW_SCRAPING', 'True') == 'True'
    ENABLE_REDFIN_SCRAPING = os.getenv('ENABLE_REDFIN_SCRAPING', 'False') == 'True'
    ENABLE_EMAIL_SENDING = os.getenv('ENABLE_EMAIL_SENDING', 'False') == 'True'
    ENABLE_MESSAGE_GENERATION = os.getenv('ENABLE_MESSAGE_GENERATION', 'True') == 'True'
    
    # Listing Analysis
    MIN_PHOTOS_FOR_QUALITY = int(os.getenv('MIN_PHOTOS_FOR_QUALITY', '5'))
    DAYS_TO_CONSIDER_FRESH = int(os.getenv('DAYS_TO_CONSIDER_FRESH', '30'))
    
    # Contact Information
    SUPPORT_EMAIL = os.getenv('SUPPORT_EMAIL', 'support@photography-outreach.com')
    SUPPORT_PHONE = os.getenv('SUPPORT_PHONE', '+1-555-0000')


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    TESTING = False
    SESSION_COOKIE_SECURE = False
    ENABLE_EMAIL_SENDING = False
    ENABLE_ZILLOW_SCRAPING = True


class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = 'postgresql://user:password@localhost:5432/re_photography_test'
    ENABLE_EMAIL_SENDING = False
    ENABLE_MESSAGE_GENERATION = False
    REDIS_URL = 'redis://localhost:6379/1'
    CELERY_BROKER_URL = 'redis://localhost:6379/1'
    CELERY_RESULT_BACKEND = 'redis://localhost:6379/1'


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    TESTING = False
    SESSION_COOKIE_SECURE = True
    
    # Ensure critical environment variables are set
    @staticmethod
    def validate():
        required_vars = [
            'DATABASE_URL',
            'SECRET_KEY',
            'OPENAI_API_KEY',
            'FROM_EMAIL'
        ]
        missing = [var for var in required_vars if not os.getenv(var)]
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")


def get_config(env=None):
    """Get configuration object based on environment"""
    if env is None:
        env = os.getenv('FLASK_ENV', 'development')
    
    config_map = {
        'development': DevelopmentConfig,
        'testing': TestingConfig,
        'production': ProductionConfig,
    }
    
    config_class = config_map.get(env, DevelopmentConfig)
    
    if env == 'production':
        config_class.validate()
    
    return config_class