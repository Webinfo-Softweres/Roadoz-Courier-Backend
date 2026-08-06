import razorpay
import hmac
import hashlib
from app.core.config import settings

class PaymentService:
    def __init__(self):
        self.client = razorpay.Client(
            auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_SECRET_KEY)
        )

    def create_order(self, amount: float, currency: str = "INR", receipt: str = None) -> dict:
        """
        Create a razorpay order for the given amount.
        amount is passed in rupees, so we multiply by 100 for paise.
        """
        data = {
            "amount": int(amount * 100),
            "currency": currency,
            "receipt": receipt,
        }
        # returns a dict like {'id': 'order_...', 'amount': ..., ...}
        return self.client.order.create(data=data)

    def verify_payment_signature(self, razorpay_order_id: str, razorpay_payment_id: str, razorpay_signature: str) -> bool:
        """
        Verify the signature of the razorpay payment.
        """
        msg = f"{razorpay_order_id}|{razorpay_payment_id}"
        secret = settings.RAZORPAY_SECRET_KEY
        
        generated_signature = hmac.new(
            secret.encode('utf-8'),
            msg.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

        
        return hmac.compare_digest(generated_signature, razorpay_signature)

payment_service = PaymentService()
