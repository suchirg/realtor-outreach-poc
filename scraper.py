import os
import logging
import time
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    StaleElementReferenceException,
)
from bs4 import BeautifulSoup
import requests
from models import db, Listing, RealtorContact
from config import Config
import re

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class ZillowScraper:
    """Scrapes Zillow listings for a given zip code."""
    
    def __init__(self):
        self.base_url = "https://www.zillow.com"
        self.driver = None
        self.wait = None
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def _init_driver(self) -> webdriver.Chrome:
        """Initialize Selenium WebDriver with Chrome options."""
        chrome_options = Options()
        
        if os.getenv('HEADLESS', 'true').lower() == 'true':
            chrome_options.add_argument('--headless')
        
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        driver = webdriver.Chrome(options=chrome_options)
        driver.set_page_load_timeout(30)
        return driver
    
    def _get_search_url(self, zip_code: str) -> str:
        """Construct Zillow search URL for zip code."""
        return f"{self.base_url}/homes/for_sale/{zip_code}_rb/"
    
    def _scroll_page(self, max_scrolls: int = 5) -> None:
        """Scroll page to load more listings dynamically."""
        try:
            for i in range(max_scrolls):
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
                logger.info(f"Scroll iteration {i+1}/{max_scrolls}")
        except Exception as e:
            logger.warning(f"Error during page scroll: {e}")
    
    def _parse_listing_card(self, card_element) -> Optional[Dict]:
        """Extract listing data from a single card element."""
        try:
            html = card_element.get_attribute('outerHTML')
            soup = BeautifulSoup(html, 'html.parser')
            
            listing_data = {}
            
            link_elem = soup.find('a', {'data-test': 'property-card-link'})
            if not link_elem or not link_elem.get('href'):
                return None
            
            listing_data['url'] = link_elem['href']
            listing_id_match = re.search(r'/(\d+)_zpid', listing_data['url'])
            if listing_id_match:
                listing_data['zillow_id'] = listing_id_match.group(1)
            else:
                return None
            
            address_elem = soup.find('span', {'data-test': 'property-card-addr'})
            listing_data['address'] = address_elem.text.strip() if address_elem else None
            if not listing_data['address']:
                return None
            
            price_elem = soup.find('span', {'data-test': 'property-card-price'})
            listing_data['price'] = price_elem.text.strip() if price_elem else None
            
            beds_elem = soup.find('span', {'data-test': 'property-card-beds'})
            baths_elem = soup.find('span', {'data-test': 'property-card-baths'})
            listing_data['beds'] = beds_elem.text.strip() if beds_elem else None
            listing_data['baths'] = baths_elem.text.strip() if baths_elem else None
            
            realtor_elem = soup.find('span', {'data-test': 'property-card-agent-name'})
            listing_data['realtor_name'] = realtor_elem.text.strip() if realtor_elem else None
            
            photo_count = self._estimate_photo_count(html)
            listing_data['photo_count'] = photo_count
            
            listing_data['scraped_at'] = datetime.utcnow()
            
            return listing_data
        
        except (AttributeError, IndexError, TypeError) as e:
            logger.warning(f"Error parsing listing card: {e}")
            return None
    
    def _estimate_photo_count(self, html: str) -> int:
        """Estimate number of photos from listing card HTML."""
        soup = BeautifulSoup(html, 'html.parser')
        
        photo_indicators = [
            soup.find('span', {'data-test': 'property-card-photo-count'}),
            soup.find('span', string=re.compile(r'\d+\s*photo', re.I)),
        ]
        
        for indicator in photo_indicators:
            if indicator:
                text = indicator.text.strip()
                match = re.search(r'(\d+)', text)
                if match:
                    return int(match.group(1))
        
        return 0
    
    def scrape_zip_code(self, zip_code: str, max_pages: int = 2) -> List[Dict]:
        """Scrape all listings from a zip code."""
        logger.info(f"Starting scrape for zip code: {zip_code}")
        listings = []
        
        try:
            self.driver = self._init_driver()
            search_url = self._get_search_url(zip_code)
            
            for page in range(1, max_pages + 1):
                page_url = f"{search_url}?p={page}" if page > 1 else search_url
                logger.info(f"Fetching page {page}: {page_url}")
                
                self.driver.get(page_url)
                time.sleep(3)
                
                self._scroll_page(max_scrolls=3)
                
                soup = BeautifulSoup(self.driver.page_source, 'html.parser')
                listing_cards = soup.find_all('div', {'data-test': 'property-card-container'})
                
                logger.info(f"Found {len(listing_cards)} listing cards on page {page}")
                
                for card in listing_cards:
                    try:
                        listing_data = self._parse_listing_card(card)
                        if listing_data:
                            listing_data['zip_code'] = zip_code
                            listings.append(listing_data)
                            logger.info(f"Parsed listing: {listing_data.get('address')}")
                    except Exception as e:
                        logger.warning(f"Error parsing individual card: {e}")
                        continue
                
                if page < max_pages:
                    time.sleep(2)
            
            logger.info(f"Scrape completed. Total listings: {len(listings)}")
            return listings
        
        except TimeoutException as e:
            logger.error(f"Timeout during scraping: {e}")
            return listings
        except Exception as e:
            logger.error(f"Error during scraping: {e}")
            return listings
        finally:
            if self.driver:
                self.driver.quit()
    
    def _extract_agent_info_from_zillow(self, listing_url: str) -> Optional[Dict]:
        """Extract detailed agent information from individual listing page."""
        try:
            response = self.session.get(listing_url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            agent_data = {}
            
            agent_name_elem = soup.find('span', {'data-test': 'agent-name'})
            agent_data['name'] = agent_name_elem.text.strip() if agent_name_elem else None
            
            agent_phone_elem = soup.find('a', {'data-test': 'agent-phone'})
            if agent_phone_elem:
                agent_data['phone'] = agent_phone_elem.text.strip()
            
            agent_email_elem = soup.find('a', {'data-test': 'agent-email'})
            if agent_email_elem:
                agent_data['email'] = agent_email_elem.text.strip()
            
            return agent_data if agent_data.get('name') else None
        
        except Exception as e:
            logger.warning(f"Error extracting agent info from {listing_url}: {e}")
            return None


class RealtorContactEnricher:
    """Enriches realtor contact information from multiple sources."""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def enrich_contact(self, realtor_name: str, address: str, zip_code: str) -> Optional[Dict]:
        """Enrich realtor contact info using name and property details."""
        contact = {
            'name': realtor_name,
            'email': None,
            'phone': None,
            'broker': None,
            'source': None
        }
        
        if realtor_name and '@' in realtor_name:
            email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', realtor_name)
            if email_match:
                contact['email'] = email_match.group(0)
                contact['source'] = 'zillow_listing'
                return contact
        
        phone_match = re.search(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', realtor_name or '')
        if phone_match:
            contact['phone'] = phone_match.group(0)
            contact['source'] = 'zillow_listing'
        
        mls_contact = self._lookup_mls_records(realtor_name, zip_code)
        if mls_contact:
            contact.update(mls_contact)
            contact['source'] = 'mls_records'
            return contact
        
        if realtor_name:
            contact['source'] = 'zillow_listing'
            return contact
        
        return None
    
    def _lookup_mls_records(self, realtor_name: str, zip_code: str) -> Optional[Dict]:
        """Attempt to lookup realtor in MLS records (placeholder for API integration)."""
        try:
            if not realtor_name or len(realtor_name.strip()) < 2:
                return None
            
            logger.info(f"Checking MLS records for: {realtor_name}")
            
            return None
        except Exception as e:
            logger.warning(f"Error looking up MLS records: {e}")
            return None


class ListingQualifier:
    """Qualifies listings as viable outreach opportunities."""
    
    PHOTO_THRESHOLD = 5
    MIN_PRICE = 100000
    MAX_PRICE = 5000000
    
    @staticmethod
    def should_outreach(listing: Dict) -> Tuple[bool, str]:
        """Determine if a listing qualifies for outreach."""
        reasons = []
        
        if not listing.get('photo_count') or listing['photo_count'] == 0:
            reasons.append("No photo count available")
        elif listing['photo_count'] < ListingQualifier.PHOTO_THRESHOLD:
            reasons.append(f"Low photo count: {listing['photo_count']}/{ListingQualifier.PHOTO_THRESHOLD}")
        else:
            return False, "Sufficient photos already"
        
        if not listing.get('realtor_name'):
            return False, "No realtor name found"
        
        if not listing.get('address'):
            return False, "No address found"
        
        price_str = listing.get('price', '').replace('$', '').replace(',', '')
        try:
            price = float(price_str) if price_str else None
            if price:
                if price < ListingQualifier.MIN_PRICE or price > ListingQualifier.MAX_PRICE:
                    return False, f"Price out of range: ${price}"
        except (ValueError, TypeError):
            pass
        
        return True, ", ".join(reasons) if reasons else "Qualifies for outreach"


def save_listings_to_db(listings: List[Dict]) -> int:
    """Save scraped listings to database."""
    saved_count = 0
    
    for listing_data in listings:
        try:
            existing = Listing.query.filter_by(
                zillow_id=listing_data.get('zillow_id')
            ).first()
            
            if existing:
                logger.info(f"Listing {listing_data.get('address')} already exists")
                continue
            
            qualifies, reason = ListingQualifier.should_outreach(listing_data)
            
            listing = Listing(
                zillow_id=listing_data.get('zillow_id'),
                address=listing_data.get('address'),
                zip_code=listing_data.get('zip_code'),
                price=listing_data.get('price'),
                beds=listing_data.get('beds'),
                baths=listing_data.get('baths'),
                photo_count=listing_data.get('photo_count', 0),
                url=listing_data.get('url'),
                realtor_name=listing_data.get('realtor_name'),
                qualifies_for_outreach=qualifies,
                qualification_reason=reason,
                scraped_at=listing_data.get('scraped_at')
            )
            
            db.session.add(listing)
            saved_count += 1
            
            if not existing and qualifies:
                enricher = RealtorContactEnricher()
                contact_info = enricher.enrich_contact(
                    listing_data.get('realtor_name'),
                    listing_data.get('address'),
                    listing_data.get('zip_code')
                )
                
                if contact_info:
                    realtor = RealtorContact(
                        name=contact_info.get('name'),
                        email=contact_info.get('email'),
                        phone=contact_info.get('phone'),
                        broker=contact_info.get('broker'),
                        source=contact_info.get('source'),
                        listing_id=listing.id
                    )
                    db.session.add(realtor)
        
        except Exception as e:
            logger.error(f"Error saving listing {listing_data.get('address')}: {e}")
            db.session.rollback()
            continue
    
    try:
        db.session.