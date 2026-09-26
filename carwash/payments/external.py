"""External gateway adapter base.

The business/payment models are intentionally not coupled to a single provider.
Add Yoco, Paystack, Peach, Ozow, Stitch, Stripe, etc. as separate adapters.
Keep secret keys in Django settings/environment variables, never in the database.
"""
from .base import BasePaymentGateway


class ExternalGatewayNotConfigured(RuntimeError):
    pass


class ConfigurableExternalGateway(BasePaymentGateway):
    code = None

    def initialize_payment(self, payment, request):
        raise ExternalGatewayNotConfigured(
            f'{self.code} adapter is registered but its API implementation has not been configured yet.'
        )

    def verify_payment(self, reference):
        raise ExternalGatewayNotConfigured(
            f'{self.code} verification has not been configured yet.'
        )
