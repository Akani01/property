from abc import ABC, abstractmethod


class BasePaymentGateway(ABC):
    code = None

    @abstractmethod
    def initialize_payment(self, payment, request):
        raise NotImplementedError

    @abstractmethod
    def verify_payment(self, reference):
        raise NotImplementedError

    def refund(self, payment, amount=None):
        raise NotImplementedError('Refunds are not implemented for this gateway.')

    def create_provider_account(self, business):
        raise NotImplementedError('Provider account onboarding is not implemented for this gateway.')

    def payout_provider(self, business, amount):
        raise NotImplementedError('Provider payouts are not implemented for this gateway.')
