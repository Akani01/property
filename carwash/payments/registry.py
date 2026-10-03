from .cash import CashGateway
from .paystack import PaystackGateway
from .yoco import YocoGateway


_GATEWAYS = {
    'cash': CashGateway,
    'yoco': YocoGateway,
    'paystack': PaystackGateway,
}


def register_gateway(code, gateway_class):
    _GATEWAYS[code] = gateway_class


def get_gateway(code):
    gateway_class = _GATEWAYS.get(code)
    if not gateway_class:
        raise ValueError(f'Unknown payment gateway: {code}')
    return gateway_class()
