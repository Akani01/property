from .base import BasePaymentGateway


class CashGateway(BasePaymentGateway):
    code = 'cash'

    def initialize_payment(self, payment, request):
        return {
            'success': True,
            'gateway': 'cash',
            'checkout': None,
            'message': 'Cash selected. Pay the washer after the service is completed.',
        }

    def verify_payment(self, reference):
        return {'success': True, 'status': 'manual'}
