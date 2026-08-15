import os
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Index, CheckConstraint
from sqlalchemy.dialects.postgresql import JSONB, ENUM
import enum

db = SQLAlchemy()


class ListingStatus(enum.Enum):
    FLAGGED = "flagged"
    APPROVED = "approved"
    SENT = "sent"
    RESPONDED = "responded"
    BOOKED = "booked"
    REJECTED = "rejected"
    ARCHIVED = "archived"


class OutreachStatus(enum.Enum):
    DRAFT = "draft"
    APPROVED = "approved"
    SENT = "sent"
    OPENED = "opened"
    CLICKED = "clicked"
    REPLIED = "replied"
    FAILED = "failed"


class Listing(db.Model):
    __tablename__ = 'listings'
    
    id = db.Column(db.Integer, primary_key=True)
    listing_id = db.Column(db.String(100), unique=True, nullable=False, index=True)
    address = db.Column(db.String(255), nullable=False)
    city = db.Column(db.String(100), nullable=False)
    state = db.Column(db.String(2), nullable=False)
    zip_code = db.Column(db.String(10), nullable=False, index=True)
    property_type = db.Column(db.String(50), nullable=True)
    bedrooms = db.Column(db.Integer, nullable=True)
    bathrooms = db.Column(db.Float, nullable=True)
    square_feet = db.Column(db.Integer, nullable=True)
    price = db.Column(db.Integer, nullable=True)
    
    photo_count = db.Column(db.Integer, nullable=False, default=0)
    photo_quality_score = db.Column(db.Float, nullable=True)
    photo_urls = db.Column(JSONB, nullable=True, default=list)
    
    realtor_name = db.Column(db.String(255), nullable=False)
    realtor_phone = db.Column(db.String(20), nullable=True)
    realtor_email = db.Column(db.String(255), nullable=True, index=True)
    realtor_brokerage = db.Column(db.String(255), nullable=True)
    
    listing_url = db.Column(db.Text, nullable=False)
    source = db.Column(db.String(50), nullable=False)
    mls_number = db.Column(db.String(50), nullable=True)
    
    status = db.Column(db.Enum(ListingStatus), nullable=False, default=ListingStatus.FLAGGED, index=True)
    
    flag_reason = db.Column(db.String(255), nullable=True)
    rejection_reason = db.Column(db.String(255), nullable=True)
    internal_notes = db.Column(db.Text, nullable=True)
    
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    scraped_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    outreaches = db.relationship('Outreach', backref='listing', lazy=True, cascade='all, delete-orphan')
    
    __table_args__ = (
        Index('idx_zip_status', 'zip_code', 'status'),
        Index('idx_realtor_email', 'realtor_email'),
        Index('idx_created_status', 'created_at', 'status'),
    )
    
    def __repr__(self):
        return f'<Listing {self.listing_id} - {self.address}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'listing_id': self.listing_id,
            'address': self.address,
            'city': self.city,
            'state': self.state,
            'zip_code': self.zip_code,
            'property_type': self.property_type,
            'bedrooms': self.bedrooms,
            'bathrooms': self.bathrooms,
            'square_feet': self.square_feet,
            'price': self.price,
            'photo_count': self.photo_count,
            'photo_quality_score': self.photo_quality_score,
            'realtor_name': self.realtor_name,
            'realtor_email': self.realtor_email,
            'realtor_phone': self.realtor_phone,
            'realtor_brokerage': self.realtor_brokerage,
            'listing_url': self.listing_url,
            'source': self.source,
            'mls_number': self.mls_number,
            'status': self.status.value,
            'flag_reason': self.flag_reason,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
        }


class Outreach(db.Model):
    __tablename__ = 'outreaches'
    
    id = db.Column(db.Integer, primary_key=True)
    listing_id = db.Column(db.Integer, db.ForeignKey('listings.id'), nullable=False, index=True)
    
    recipient_email = db.Column(db.String(255), nullable=False, index=True)
    recipient_name = db.Column(db.String(255), nullable=False)
    recipient_phone = db.Column(db.String(20), nullable=True)
    
    message_subject = db.Column(db.String(255), nullable=False)
    message_body = db.Column(db.Text, nullable=False)
    message_draft = db.Column(db.Text, nullable=True)
    
    status = db.Column(db.Enum(OutreachStatus), nullable=False, default=OutreachStatus.DRAFT, index=True)
    
    approved_at = db.Column(db.DateTime, nullable=True)
    approved_by = db.Column(db.String(255), nullable=True)
    
    sent_at = db.Column(db.DateTime, nullable=True)
    opened_at = db.Column(db.DateTime, nullable=True)
    clicked_at = db.Column(db.DateTime, nullable=True)
    replied_at = db.Column(db.DateTime, nullable=True)
    
    reply_message = db.Column(db.Text, nullable=True)
    reply_sentiment = db.Column(db.String(50), nullable=True)
    
    email_provider = db.Column(db.String(50), nullable=True)
    email_message_id = db.Column(db.String(255), nullable=True)
    send_error = db.Column(db.Text, nullable=True)
    
    tracking_url = db.Column(db.Text, nullable=True)
    
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    booking = db.relationship('Booking', backref='outreach', uselist=False, cascade='all, delete-orphan')
    
    __table_args__ = (
        Index('idx_listing_status', 'listing_id', 'status'),
        Index('idx_email_status', 'recipient_email', 'status'),
        Index('idx_sent_at', 'sent_at'),
    )
    
    def __repr__(self):
        return f'<Outreach {self.id} - {self.recipient_email}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'listing_id': self.listing_id,
            'recipient_email': self.recipient_email,
            'recipient_name': self.recipient_name,
            'message_subject': self.message_subject,
            'status': self.status.value,
            'sent_at': self.sent_at.isoformat() if self.sent_at else None,
            'opened_at': self.opened_at.isoformat() if self.opened_at else None,
            'replied_at': self.replied_at.isoformat() if self.replied_at else None,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
        }


class Booking(db.Model):
    __tablename__ = 'bookings'
    
    id = db.Column(db.Integer, primary_key=True)
    outreach_id = db.Column(db.Integer, db.ForeignKey('outreaches.id'), nullable=False, index=True)
    
    booking_date = db.Column(db.DateTime, nullable=False)
    session_duration_minutes = db.Column(db.Integer, nullable=False, default=120)
    
    photography_rate = db.Column(db.Float, nullable=False)
    base_rate = db.Column(db.Float, nullable=False)
    adjustments = db.Column(db.Float, nullable=False, default=0)
    total_amount = db.Column(db.Float, nullable=False)
    
    status = db.Column(db.String(50), nullable=False, default='confirmed')
    payment_status = db.Column(db.String(50), nullable=False, default='pending')
    
    notes = db.Column(db.Text, nullable=True)
    realtor_notes = db.Column(db.Text, nullable=True)
    
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)
    
    __table_args__ = (
        Index('idx_booking_date', 'booking_date'),
        Index('idx_status', 'status'),
    )
    
    def __repr__(self):
        return f'<Booking {self.id} - {self.booking_date}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'outreach_id': self.outreach_id,
            'booking_date': self.booking_date.isoformat(),
            'total_amount': self.total_amount,
            'status': self.status,
            'payment_status': self.payment_status,
            'created_at': self.created_at.isoformat(),
        }


class OutreachTemplate(db.Model):
    __tablename__ = 'outreach_templates'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False, unique=True)
    description = db.Column(db.Text, nullable=True)
    
    subject_template = db.Column(db.String(500), nullable=False)
    body_template = db.Column(db.Text, nullable=False)
    
    variables = db.Column(JSONB, nullable=False, default=list)
    
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<OutreachTemplate {self.name}>'


class PricingTier(db.Model):
    __tablename__ = 'pricing_tiers'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text, nullable=True)
    
    min_bedrooms = db.Column(db.Integer, nullable=True)
    max_bedrooms = db.Column(db.Integer, nullable=True)
    min_square_feet = db.Column(db.Integer, nullable=True)
    max_square_feet = db.Column(db.Integer, nullable=True)
    
    base_rate = db.Column(db.Float, nullable=False)
    per_photo_rate = db.Column(db.Float, nullable=True)
    
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<PricingTier {self.name}>'


class ScraperLog(db.Model):
    __tablename__ = 'scraper_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    zip_code = db.Column(db.String(10), nullable=False, index=True)
    source = db.Column(db.String(50), nullable=False)
    
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=True)
    
    total_listings_found = db.Column(db.Integer, nullable=False, default=0)
    flagged_listings = db.Column(db.Integer, nullable=False, default=0)
    errors_encountered = db.Column(db.Integer, nullable=False, default=0)
    
    status = db.Column(db.String(50), nullable=False, default='running')
    error_message = db.Column(db.Text, nullable=True)
    
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_zip_time', 'zip_code', 'start_time'),
    )
    
    def __repr__(self):
        return f'<ScraperLog {self.zip_code} - {self.start_time}>'


class Analytics(db.Model):
    __tablename__ = 'analytics'
    
    id = db.Column(db.Integer, primary_key=True)
    metric_date = db.Column(db.Date, nullable=False, index=True)
    metric_type = db.Column(db.String(100), nullable=False)
    
    listings_flagged = db.Column(db.Integer, nullable=False, default=0)
    listings_approved = db.Column(db.Integer, nullable=False, default=0)
    outreaches_sent = db.Column(db.Integer, nullable=False, default=0)
    outreaches_opened = db.Column(db.Integer, nullable=False, default=0)
    outreaches_replied = db.Column(db.Integer, nullable=False, default=0)
    bookings_created = db.Column(db.Integer, nullable=False, default=0)
    revenue_generated = db.Column(db.Float, nullable=False, default=0)
    
    response_rate_percent = db.Column(db.Float, nullable=True)
    booking_rate_percent = db.Column(db.Float, nullable=True)
    average_booking_value = db.Column(db.Float, nullable=True)
    
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at =