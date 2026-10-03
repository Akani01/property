from decimal import Decimal, ROUND_HALF_UP
from math import radians, sin, cos, sqrt, atan2

from django.db import transaction
from django.utils import timezone

from .models import (
    CarWashLedgerEntry,
    CarWashPayment,
    CarWashStatusHistory,
    CarWashWallet,
)


TWOPLACES = Decimal('0.01')


def money(value):
    return Decimal(value).quantize(TWOPLACES, rounding=ROUND_HALF_UP)


def haversine_km(lat1, lon1, lat2, lon2):
    radius = 6371.0
    lat1, lon1, lat2, lon2 = map(lambda x: radians(float(x)), [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return radius * c


def calculate_quote(business, price_row, fulfilment_mode, route_distance_km=Decimal('0.00')):
    service_price = money(price_row.price)
    travel_fee = Decimal('0.00')

    if fulfilment_mode == 'mobile':
        distance = max(Decimal(route_distance_km or 0), Decimal('0.00'))
        chargeable = max(distance - business.free_travel_km, Decimal('0.00'))
        travel_fee = money(chargeable * business.travel_fee_per_km)

    discount = Decimal('0.00')
    total = money(service_price + travel_fee - discount)
    commission_rate = money(business.commission_rate)
    platform_commission = money(total * commission_rate / Decimal('100.00'))
    provider_amount = money(total - platform_commission)

    return {
        'service_price': service_price,
        'travel_fee': travel_fee,
        'discount': discount,
        'total': total,
        'commission_rate': commission_rate,
        'platform_commission': platform_commission,
        'provider_amount': provider_amount,
    }


def record_status(wash_request, status, changed_by=None, note='', latitude=None, longitude=None):
    CarWashStatusHistory.objects.create(
        wash_request=wash_request,
        status=status,
        changed_by=changed_by,
        note=note,
        latitude=latitude,
        longitude=longitude,
    )


@transaction.atomic
def settle_completed_payment(payment: CarWashPayment):
    """Create ledger entries once a wash is completed/paid.

    Card/digital: provider earns provider_amount.
    Cash: provider physically collected gross; platform commission becomes debt.
    Tips are 100% provider-owned.
    """
    business = payment.wash_request.business
    wallet, _ = CarWashWallet.objects.select_for_update().get_or_create(business=business)

    if payment.payment_method == 'cash':
        if not CarWashLedgerEntry.objects.filter(payment=payment, entry_type='cash_debt').exists():
            CarWashLedgerEntry.objects.create(
                business=business,
                wash_request=payment.wash_request,
                payment=payment,
                entry_type='cash_debt',
                amount=payment.platform_commission,
                description='Platform commission due from cash wash',
            )
            wallet.commission_due = money(wallet.commission_due + payment.platform_commission)
    else:
        if not CarWashLedgerEntry.objects.filter(payment=payment, entry_type='earning').exists():
            CarWashLedgerEntry.objects.create(
                business=business,
                wash_request=payment.wash_request,
                payment=payment,
                entry_type='earning',
                amount=payment.provider_amount,
                description='Provider earnings from digital wash payment',
            )
            wallet.available_balance = money(wallet.available_balance + payment.provider_amount)

        if not CarWashLedgerEntry.objects.filter(payment=payment, entry_type='commission').exists():
            CarWashLedgerEntry.objects.create(
                business=business,
                wash_request=payment.wash_request,
                payment=payment,
                entry_type='commission',
                amount=payment.platform_commission,
                description='OppoGlobe platform commission',
            )

    if payment.tip_amount > 0 and not CarWashLedgerEntry.objects.filter(payment=payment, entry_type='tip').exists():
        CarWashLedgerEntry.objects.create(
            business=business,
            wash_request=payment.wash_request,
            payment=payment,
            entry_type='tip',
            amount=payment.tip_amount,
            description='Customer tip - 100% provider-owned',
        )
        if payment.payment_method != 'cash':
            wallet.available_balance = money(wallet.available_balance + payment.tip_amount)

    wallet.save(update_fields=['available_balance', 'commission_due', 'updated_at'])
    return wallet
