from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from dotenv import load_dotenv
import os
import logging
from datetime import datetime
import json
from functools import wraps
import hashlib
import hmac

load_dotenv()

app = Flask(__name__)
CORS(app)

app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'postgresql://localhost/real_estate_photography')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['SESSION_TYPE'] = 'filesystem'

db = SQLAlchemy(app)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from models import Listing, Realtor, Outreach, Booking
from message_generator import generate_outreach_message
from scraper import scrape_listings_by_zip


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'photographer_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'timestamp': datetime.utcnow().isoformat()}), 200


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            return jsonify({'error': 'Email and password required'}), 400
        
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        photographer_email = os.getenv('PHOTOGRAPHER_EMAIL')
        photographer_password_hash = os.getenv('PHOTOGRAPHER_PASSWORD_HASH')
        
        if email == photographer_email and password_hash == photographer_password_hash:
            session['photographer_id'] = email
            return jsonify({'success': True, 'redirect': url_for('dashboard')}), 200
        else:
            return jsonify({'error': 'Invalid credentials'}), 401
    
    return render_template('login.html'), 200


@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route('/dashboard', methods=['GET'])
@login_required
def dashboard():
    return render_template('dashboard.html'), 200


@app.route('/api/listings', methods=['GET'])
@login_required
def get_listings():
    try:
        status = request.args.get('status', 'pending')
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        query = Listing.query
        if status != 'all':
            query = query.filter_by(status=status)
        
        listings = query.order_by(Listing.created_at.desc()).paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )
        
        listings_data = []
        for listing in listings.items:
            realtor = Realtor.query.get(listing.realtor_id)
            outreach = Outreach.query.filter_by(listing_id=listing.id).first()
            
            listings_data.append({
                'id': listing.id,
                'address': listing.address,
                'city': listing.city,
                'state': listing.state,
                'zip_code': listing.zip_code,
                'property_type': listing.property_type,
                'price': listing.price,
                'photo_count': listing.photo_count,
                'photo_quality_score': listing.photo_quality_score,
                'mls_id': listing.mls_id,
                'listing_url': listing.listing_url,
                'status': listing.status,
                'realtor': {
                    'id': realtor.id,
                    'name': realtor.name,
                    'email': realtor.email,
                    'phone': realtor.phone,
                    'brokerage': realtor.brokerage
                } if realtor else None,
                'outreach': {
                    'id': outreach.id,
                    'message': outreach.message,
                    'status': outreach.status,
                    'sent_at': outreach.sent_at.isoformat() if outreach.sent_at else None,
                    'response_received': outreach.response_received,
                    'response_received_at': outreach.response_received_at.isoformat() if outreach.response_received_at else None
                } if outreach else None,
                'created_at': listing.created_at.isoformat(),
                'updated_at': listing.updated_at.isoformat()
            })
        
        return jsonify({
            'listings': listings_data,
            'total': listings.total,
            'pages': listings.pages,
            'current_page': page
        }), 200
    
    except Exception as e:
        logger.error(f"Error fetching listings: {str(e)}")
        return jsonify({'error': 'Failed to fetch listings'}), 500


@app.route('/api/listings/<int:listing_id>', methods=['GET'])
@login_required
def get_listing(listing_id):
    try:
        listing = Listing.query.get(listing_id)
        if not listing:
            return jsonify({'error': 'Listing not found'}), 404
        
        realtor = Realtor.query.get(listing.realtor_id)
        outreach = Outreach.query.filter_by(listing_id=listing.id).first()
        
        listing_data = {
            'id': listing.id,
            'address': listing.address,
            'city': listing.city,
            'state': listing.state,
            'zip_code': listing.zip_code,
            'property_type': listing.property_type,
            'price': listing.price,
            'sqft': listing.sqft,
            'bedrooms': listing.bedrooms,
            'bathrooms': listing.bathrooms,
            'photo_count': listing.photo_count,
            'photo_quality_score': listing.photo_quality_score,
            'photo_urls': listing.photo_urls,
            'mls_id': listing.mls_id,
            'listing_url': listing.listing_url,
            'status': listing.status,
            'notes': listing.notes,
            'realtor': {
                'id': realtor.id,
                'name': realtor.name,
                'email': realtor.email,
                'phone': realtor.phone,
                'brokerage': realtor.brokerage
            } if realtor else None,
            'outreach': {
                'id': outreach.id,
                'message': outreach.message,
                'status': outreach.status,
                'sent_at': outreach.sent_at.isoformat() if outreach.sent_at else None,
                'response_received': outreach.response_received,
                'response_received_at': outreach.response_received_at.isoformat() if outreach.response_received_at else None
            } if outreach else None,
            'created_at': listing.created_at.isoformat(),
            'updated_at': listing.updated_at.isoformat()
        }
        
        return jsonify(listing_data), 200
    
    except Exception as e:
        logger.error(f"Error fetching listing {listing_id}: {str(e)}")
        return jsonify({'error': 'Failed to fetch listing'}), 500


@app.route('/api/listings/<int:listing_id>/update-status', methods=['PATCH'])
@login_required
def update_listing_status(listing_id):
    try:
        listing = Listing.query.get(listing_id)
        if not listing:
            return jsonify({'error': 'Listing not found'}), 404
        
        data = request.get_json()
        new_status = data.get('status')
        
        valid_statuses = ['pending', 'flagged', 'contacted', 'rejected', 'booked']
        if new_status not in valid_statuses:
            return jsonify({'error': f'Invalid status. Must be one of: {", ".join(valid_statuses)}'}), 400
        
        listing.status = new_status
        listing.updated_at = datetime.utcnow()
        db.session.commit()
        
        logger.info(f"Updated listing {listing_id} status to {new_status}")
        
        return jsonify({
            'success': True,
            'listing_id': listing.id,
            'status': listing.status
        }), 200
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating listing {listing_id} status: {str(e)}")
        return jsonify({'error': 'Failed to update listing status'}), 500


@app.route('/api/outreach/<int:listing_id>/preview', methods=['GET'])
@login_required
def preview_outreach(listing_id):
    try:
        listing = Listing.query.get(listing_id)
        if not listing:
            return jsonify({'error': 'Listing not found'}), 404
        
        realtor = Realtor.query.get(listing.realtor_id)
        if not realtor:
            return jsonify({'error': 'Realtor not found'}), 404
        
        pricing = request.args.get('pricing', os.getenv('DEFAULT_PHOTOGRAPHY_PRICE', '300'))
        
        message = generate_outreach_message(
            realtor_name=realtor.name,
            property_address=listing.address,
            property_type=listing.property_type,
            price=pricing
        )
        
        return jsonify({
            'message': message,
            'realtor_email': realtor.email,
            'realtor_phone': realtor.phone,
            'listing_address': listing.address
        }), 200
    
    except Exception as e:
        logger.error(f"Error previewing outreach for listing {listing_id}: {str(e)}")
        return jsonify({'error': 'Failed to generate outreach preview'}), 500


@app.route('/api/outreach/<int:listing_id>/send', methods=['POST'])
@login_required
def send_outreach(listing_id):
    try:
        listing = Listing.query.get(listing_id)
        if not listing:
            return jsonify({'error': 'Listing not found'}), 404
        
        realtor = Realtor.query.get(listing.realtor_id)
        if not realtor:
            return jsonify({'error': 'Realtor not found'}), 404
        
        data = request.get_json()
        message = data.get('message')
        contact_method = data.get('contact_method', 'email')
        
        if not message:
            return jsonify({'error': 'Message required'}), 400
        
        existing_outreach = Outreach.query.filter_by(listing_id=listing_id).first()
        if existing_outreach:
            return jsonify({'error': 'Outreach already sent for this listing'}), 400
        
        outreach = Outreach(
            listing_id=listing_id,
            realtor_id=realtor.id,
            message=message,
            contact_method=contact_method,
            status='sent',
            sent_at=datetime.utcnow()
        )
        
        db.session.add(outreach)
        listing.status = 'contacted'
        listing.updated_at = datetime.utcnow()
        db.session.commit()
        
        logger.info(f"Sent outreach {outreach.id} to realtor {realtor.id} for listing {listing_id}")
        
        if contact_method == 'email' and realtor.email:
            try:
                send_email_outreach(realtor.email, realtor.name, message, listing)
            except Exception as e:
                logger.error(f"Failed to send email: {str(e)}")
        
        return jsonify({
            'success': True,
            'outreach_id': outreach.id,
            'status': outreach.status,
            'sent_at': outreach.sent_at.isoformat()
        }), 201
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error sending outreach for listing {listing_id}: {str(e)}")
        return jsonify({'error': 'Failed to send outreach'}), 500


@app.route('/api/outreach/<int:outreach_id>/response', methods=['POST'])
@login_required
def log_outreach_response(outreach_id):
    try:
        outreach = Outreach.query.get(outreach_id)
        if not outreach:
            return jsonify({'error': 'Outreach not found'}), 404
        
        data = request.get_json()
        response_type = data.get('response_type', 'positive')
        notes = data.get('notes', '')
        
        outreach.response_received = True
        outreach.response_received_at = datetime.utcnow()
        outreach.response_type = response_type
        outreach.response_notes = notes
        outreach.status = 'responded'
        
        listing = Listing.query.get(outreach.listing_id)
        if response_type == 'positive':
            listing.status = 'booked'
        elif response_type == 'interested':
            listing.status = 'contacted'
        
        db.session.commit()
        
        logger.info(f"Logged response for outreach {outreach_id}: {response_type}")
        
        return jsonify({
            'success': True,
            'outreach_id': outreach.id,
            'status': outreach.status,
            'response_received_at': outreach.response_received_at.isoformat()
        }), 200
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error logging response for outreach {outreach_id}: {str(e)}")
        return jsonify({'error': 'Failed to log response'}), 500


@app.route('/api/scrape', methods=['POST'])
@login_required
def start_scrape():
    try:
        data = request.get_json()
        zip_code = data.get('zip_code', '60610')
        
        if not zip_code or not zip_code.isdigit() or len(zip_code) != 5:
            return jsonify({'error': 'Invalid zip code format'}), 400
        
        logger.info(f"Starting scrape for zip code {zip_code}")
        
        listings_data = scrape_listings_by_zip(zip_code)
        
        created_count = 0
        for listing_data in listings_data:
            existing = Listing.query.filter_by(mls_id=listing_data['mls_id']).first()
            if existing:
                continue
            
            realtor_data = listing_data.get('realtor', {})
            realtor = Realtor.query.filter_by(email=realtor_data.get('email')).first()
            
            if not realtor and realtor_data.get('email'):
                realtor = Realtor