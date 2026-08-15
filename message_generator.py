import os
import logging
from typing import Optional
from openai import OpenAI

logger = logging.getLogger(__name__)


class MessageGenerator:
    """Generates personalized outreach messages for realtors using OpenAI API."""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the message generator with OpenAI API key.

        Args:
            api_key: OpenAI API key. If not provided, uses OPENAI_API_KEY env var.
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")

        self.client = OpenAI(api_key=self.api_key)
        self.model = "gpt-3.5-turbo"

    def generate_message(
        self,
        realtor_name: str,
        property_address: str,
        property_type: str,
        listing_url: str,
        photo_count: int,
        base_price: float,
        photographer_name: str = "Professional Photography",
        photographer_contact: str = None,
    ) -> dict:
        """
        Generate a personalized outreach message for a realtor.

        Args:
            realtor_name: Name of the realtor
            property_address: Full address of the listing
            property_type: Type of property (e.g., "Single Family Home", "Condo")
            listing_url: URL to the listing
            photo_count: Current number of photos on listing
            base_price: Base photography session price
            photographer_name: Name/brand of the photographer
            photographer_contact: Contact information or calendar link

        Returns:
            Dictionary containing:
                - subject: Email subject line
                - body: Email body
                - preview: Short preview text
                - estimated_price: Calculated price based on property type
        """
        try:
            estimated_price = self._calculate_price(property_type, base_price)

            prompt = self._build_prompt(
                realtor_name=realtor_name,
                property_address=property_address,
                property_type=property_type,
                photo_count=photo_count,
                estimated_price=estimated_price,
                photographer_name=photographer_name,
            )

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=300,
            )

            message_text = response.choices[0].message.content.strip()
            subject = self._extract_subject(message_text)
            body = self._extract_body(message_text, photographer_contact)

            return {
                "status": "success",
                "subject": subject,
                "body": body,
                "preview": body[:150] + "..." if len(body) > 150 else body,
                "estimated_price": estimated_price,
                "property_address": property_address,
                "realtor_name": realtor_name,
                "listing_url": listing_url,
            }

        except Exception as e:
            logger.error(f"Error generating message for {realtor_name}: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "realtor_name": realtor_name,
                "property_address": property_address,
            }

    def _build_prompt(
        self,
        realtor_name: str,
        property_address: str,
        property_type: str,
        photo_count: int,
        estimated_price: float,
        photographer_name: str,
    ) -> str:
        """Build the prompt for OpenAI to generate the outreach message."""
        prompt = f"""You are a professional real estate photographer outreach specialist. Generate a SHORT, compelling email to a realtor.

CONTEXT:
- Realtor Name: {realtor_name}
- Property Address: {property_address}
- Property Type: {property_type}
- Current Photos: {photo_count}
- Professional Photography Service: {photographer_name}
- Session Price: ${estimated_price}

REQUIREMENTS:
1. Email subject line (keep it catchy, max 60 chars)
2. Professional but friendly tone
3. Address the low photo count as an opportunity, not a criticism
4. Mention specific benefits: increased buyer interest, faster sales, better price
5. Include clear call-to-action (e.g., "Reply with your availability")
6. Max 200 words for email body
7. No generic greetings - personalize to them

FORMAT:
SUBJECT: [subject line here]
BODY: [email body here]

Generate the email now:"""
        return prompt

    def _extract_subject(self, message_text: str) -> str:
        """Extract subject line from the generated message."""
        lines = message_text.split("\n")
        for line in lines:
            if line.startswith("SUBJECT:"):
                return line.replace("SUBJECT:", "").strip()
        return "Professional Photography for Your Listing"

    def _extract_body(self, message_text: str, contact_info: Optional[str] = None) -> str:
        """Extract body from the generated message and append contact info."""
        lines = message_text.split("\n")
        in_body = False
        body_lines = []

        for line in lines:
            if line.startswith("BODY:"):
                in_body = True
                body_text = line.replace("BODY:", "").strip()
                if body_text:
                    body_lines.append(body_text)
                continue
            if in_body and line.strip():
                body_lines.append(line)

        body = "\n".join(body_lines).strip()

        if contact_info:
            body += f"\n\nBest regards,\n{contact_info}"

        return body

    def _calculate_price(self, property_type: str, base_price: float) -> float:
        """
        Calculate adjusted price based on property type.

        Args:
            property_type: Type of property
            base_price: Base photography session price

        Returns:
            Adjusted price
        """
        multipliers = {
            "single family home": 1.0,
            "condo": 0.9,
            "townhouse": 0.85,
            "apartment": 0.8,
            "commercial": 1.5,
            "land": 0.75,
        }

        property_type_lower = property_type.lower()
        multiplier = 1.0

        for key, value in multipliers.items():
            if key in property_type_lower:
                multiplier = value
                break

        return round(base_price * multiplier, 2)

    def generate_batch_messages(
        self,
        listings: list,
        base_price: float,
        photographer_name: str = "Professional Photography",
        photographer_contact: str = None,
    ) -> list:
        """
        Generate messages for multiple listings.

        Args:
            listings: List of listing dictionaries with keys:
                - realtor_name
                - property_address
                - property_type
                - listing_url
                - photo_count
            base_price: Base photography session price
            photographer_name: Name/brand of the photographer
            photographer_contact: Contact information

        Returns:
            List of generated message dictionaries
        """
        results = []
        for listing in listings:
            message = self.generate_message(
                realtor_name=listing.get("realtor_name"),
                property_address=listing.get("property_address"),
                property_type=listing.get("property_type", "Single Family Home"),
                listing_url=listing.get("listing_url"),
                photo_count=listing.get("photo_count", 0),
                base_price=base_price,
                photographer_name=photographer_name,
                photographer_contact=photographer_contact,
            )
            results.append(message)

        return results

    def validate_message(self, message: dict) -> dict:
        """
        Validate a generated message for quality and completeness.

        Args:
            message: Message dictionary to validate

        Returns:
            Dictionary with validation results
        """
        issues = []

        if message.get("status") == "error":
            return {"valid": False, "issues": [message.get("error", "Unknown error")]}

        subject = message.get("subject", "")
        body = message.get("body", "")

        if not subject or len(subject) < 10:
            issues.append("Subject line is too short or missing")

        if not body or len(body) < 50:
            issues.append("Message body is too short or missing")

        if len(subject) > 100:
            issues.append("Subject line is too long (max 100 chars)")

        if len(body) > 1000:
            issues.append("Message body is too long (max 1000 chars)")

        if "realtor_name" not in body and "[Realtor]" not in body:
            issues.append("Message should address the realtor by name")

        if "address" not in body.lower() and "property" not in body.lower():
            issues.append("Message should mention the property address")

        if "$" not in body:
            issues.append("Message should include pricing information")

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "quality_score": max(0, 100 - (len(issues) * 15)),
        }


def create_message_generator() -> MessageGenerator:
    """Factory function to create a MessageGenerator instance."""
    return MessageGenerator()