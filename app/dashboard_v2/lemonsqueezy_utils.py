import httpx
from typing import List, Dict, Any
import hashlib
import hmac
import json

class SimpleLemonSqueezy:
    def __init__(self, api_key: str, webhook_secret: str):
        self.api_key = api_key
        self.base_url = "https://api.lemonsqueezy.com/v1"
        self.webhook_secret = webhook_secret
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

    async def get_products(self) -> List[Dict[str, Any]]:
        """Fetch all products from Lemon Squeezy."""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.base_url}/products", headers=self.headers)
            response.raise_for_status()
            return response.json()['data']

    async def get_variants(self, product_id: int) -> List[Dict[str, Any]]:
        """Fetch all variants for a specific product."""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.base_url}/variants?filter[product_id]={product_id}", headers=self.headers)
            response.raise_for_status()
            return response.json()['data']

    async def create_checkout(self, user_email,user_id, store_id, variant_id: int, custom_price: int = None) -> Dict[str, Any]:
        """Create a checkout session for a variant."""
        payload = {
            "data": {
              "type": "checkouts",
              "attributes": {
                "checkout_data": {
                  "email": str(user_email),
                  "custom": {
                    "user_id": str(user_id)
                  }
                }
              },
              "relationships": {
                "store": {
                  "data": {
                    "type": "stores",
                    "id": str(store_id)
                  }
                },
                "variant": {
                  "data": {
                    "type": "variants",
                    "id": str(variant_id)
                  }
                }
              }
            }
        }
        if custom_price is not None:
            payload["data"]["attributes"]["custom_price"] = custom_price

        print(payload)

        async with httpx.AsyncClient() as client:
            response = await client.post(f"{self.base_url}/checkouts", json=payload, headers=self.headers)
            response.raise_for_status()
            return response.json()['data']

    def verify_webhook_signature(self, payload: bytes, signature: str) -> bool:
        """Verify the webhook signature from Lemon Squeezy."""
        computed_signature = hmac.new(
            self.webhook_secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(computed_signature, signature)

    async def process_webhook(self, payload: bytes, signature: str) -> Dict[str, Any]:
        """Process a webhook from Lemon Squeezy."""
        if not self.verify_webhook_signature(payload, signature):
            raise ValueError("Invalid webhook signature")

        event_data = json.loads(payload)
        event_name = event_data.get('meta', {}).get('event_name')

        if event_name == 'order_created':
            # Handle new order
            order_data = event_data.get('data', {}).get('attributes', {})
            # Process the order (e.g., update your database, send confirmation email, etc.)
            # You can add your own logic here
            print(f"New order received: {order_data.get('identifier')}")
        elif event_name == 'subscription_created':
            # Handle new subscription
            subscription_data = event_data.get('data', {}).get('attributes', {})
            # Process the subscription (e.g., update your database, provision access, etc.)
            # You can add your own logic here
            print(f"New subscription created: {subscription_data.get('id')}")
        # Add more event handlers as needed

        return event_data