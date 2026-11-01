from decimal import Decimal, InvalidOperation
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Sum, F, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST, require_GET
from hiring.models import BusinessProfile, Conversation, Message, MessageRecipient
from .models import Retailer, Product, Offer, PriceHistory, MerchantAccount, Inventory, StockMovement, MarketplaceOrder, MerchantLedgerEntry, ProductChatLink, DeliveryBooking


def merchant_for(user):
    profile = BusinessProfile.objects.filter(user=user).first()
    if not profile: return None
    merchant = MerchantAccount.objects.filter(business_profile=profile).first()
    if merchant: return merchant
    # Avoid stealing an existing retailer merely because the name matches.
    # Never auto-claim a pre-existing retailer by its display name.
    # Staff must explicitly link legacy retailers after verifying ownership.
    retailer = Retailer.objects.filter(name=profile.company_name).first()
    if retailer is not None:
        return None
    retailer = Retailer.objects.create(name=profile.company_name, active=True)
    return MerchantAccount.objects.create(retailer=retailer,owner=user,business_profile=profile)

@login_required
@require_POST
def save_product(request):
    name=request.POST.get('name','').strip()[:255]; sku=request.POST.get('sku','').strip()[:120]
    if not name or not sku: return JsonResponse({'error':'Name and SKU required'},status=400)
    try:
        price=Decimal(request.POST.get('price','')); cost=Decimal(request.POST.get('cost','0'))
        stock=int(request.POST.get('stock','0'))
        if not price.is_finite() or price<=0 or not cost.is_finite() or cost<0 or stock<0: raise ValueError()
    except (ValueError,InvalidOperation): return JsonResponse({'error':'Invalid price, cost or stock'},status=400)
    with transaction.atomic():
        merchant=merchant_for(request.user)
        if not merchant: return JsonResponse({'error':'Business profile or merchant ownership conflict'},status=403)
        product=Product.objects.filter(barcode=request.POST.get('barcode','').strip()).first() if request.POST.get('barcode','').strip() else None
        if not product: product=Product.objects.create(name=name,brand=request.POST.get('brand','')[:120],barcode=request.POST.get('barcode','')[:80],sku=sku,category=request.POST.get('category','Other')[:80])
        offer,created=Offer.objects.update_or_create(retailer=merchant.retailer,retailer_sku=sku,branch='',defaults={'product':product,'price':price,'currency':'ZAR','source':'merchant','available':True})
        inv,_=Inventory.objects.select_for_update().get_or_create(offer=offer)
        delta=stock-inv.on_hand
        if stock<inv.reserved: return JsonResponse({'error':'Cannot reduce stock below reserved units'},status=409)
        inv.on_hand=stock; inv.cost_per_unit=cost; inv.save()
        if delta: StockMovement.objects.create(inventory=inv,actor=request.user,delta=delta,reason='Merchant stock update')
        PriceHistory.objects.create(offer=offer,price=price)
    return JsonResponse({'success':True,'offer_id':offer.pk,'available':inv.available})

@login_required
@require_GET
def dashboard(request):
    merchant=MerchantAccount.objects.filter(owner=request.user).first()
    if not merchant:
        merchant=merchant_for(request.user)
    if not merchant: return render(request,'pricecheck/dashboard.html',{'merchant':None})
    inventory=Inventory.objects.filter(offer__retailer=merchant.retailer).select_related('offer__product')
    stock_value=sum((x.on_hand*x.cost_per_unit for x in inventory),Decimal('0'))
    sales=MerchantLedgerEntry.objects.filter(merchant=merchant).aggregate(total=Sum('amount'))['total'] or Decimal('0')
    return render(request,'pricecheck/dashboard.html',{'merchant':merchant,'inventory':inventory,'stock_value':stock_value,'ledger_balance':sales,'orders':MarketplaceOrder.objects.filter(merchant=merchant).order_by('-created_at')[:30]})

@login_required
@require_POST
def contact_seller(request,offer_id):
    offer=get_object_or_404(Offer.objects.select_related('retailer'),pk=offer_id)
    merchant=get_object_or_404(MerchantAccount,retailer=offer.retailer)
    if merchant.owner_id==request.user.pk: return JsonResponse({'error':'Cannot message yourself'},status=400)
    body=request.POST.get('message','').strip()[:3000]
    if not body: return JsonResponse({'error':'Message required'},status=400)
    with transaction.atomic():
        link=ProductChatLink.objects.select_for_update().filter(offer=offer,buyer=request.user).first()
        if not link:
            conversation=Conversation.objects.create()
            conversation.participants.add(request.user,merchant.owner)
            link=ProductChatLink.objects.create(offer=offer,buyer=request.user,conversation=conversation)
        msg=Message.objects.create(conversation=link.conversation,sender=request.user,content=f'[Product: {offer.product.name} / Offer #{offer.pk}]\n{body}')
        MessageRecipient.objects.create(message=msg,recipient=merchant.owner)
        link.conversation.save(update_fields=['updated_at'])
    return JsonResponse({'success':True,'conversation_id':str(link.conversation_id)})

@login_required
@require_POST
def start_checkout(request,offer_id):
    try: quantity=int(request.POST.get('quantity','1'))
    except ValueError: return JsonResponse({'error':'Invalid quantity'},status=400)
    if quantity<1 or quantity>1000: return JsonResponse({'error':'Invalid quantity'},status=400)
    method=request.POST.get('delivery_method','collection')
    if method not in ('collection','seller','courier'): return JsonResponse({'error':'Invalid delivery method'},status=400)
    with transaction.atomic():
        offer=get_object_or_404(Offer.objects.select_related('retailer'),pk=offer_id,available=True,retailer__active=True)
        merchant=get_object_or_404(MerchantAccount,retailer=offer.retailer)
        if merchant.owner_id==request.user.pk: return JsonResponse({'error':'Cannot buy own product'},status=400)
        inv=get_object_or_404(Inventory.objects.select_for_update(),offer=offer)
        if inv.available<quantity: return JsonResponse({'error':'Insufficient stock'},status=409)
        if method=='courier': return JsonResponse({'error':'Courier quoting and booking not yet enabled; select collection'},status=409)
        if method=='seller' and offer.delivery_fee is None: return JsonResponse({'error':'Seller delivery not offered'},status=409)
        if offer.currency != 'ZAR': return JsonResponse({'error':'Only ZAR checkout is currently supported'},status=409)
        fee=offer.delivery_fee if method=='seller' else Decimal('0')
        if method!='collection' and not request.POST.get('delivery_address','').strip(): return JsonResponse({'error':'Delivery address required'},status=400)
        order=MarketplaceOrder.objects.create(buyer=request.user,merchant=merchant,offer=offer,quantity=quantity,unit_price=offer.price,delivery_fee=fee,total=offer.price*quantity+fee,delivery_method=method,delivery_address=request.POST.get('delivery_address','').strip()[:1000])
        inv.reserved+=quantity; inv.save(update_fields=['reserved','updated_at'])
    try:
        from carwash.payments.registry import get_gateway
        gateway=get_gateway('yoco')
        success=request.build_absolute_uri(reverse('pricecheck:order',args=[order.pk]))
        cancel=request.build_absolute_uri(reverse('pricecheck:order',args=[order.pk]))
        result=gateway.create_checkout(amount=order.total,reference=f'PRICECHECK-{order.pk}',success_url=success,cancel_url=cancel,metadata={'pricecheck_order_id':str(order.pk)},currency='ZAR',idempotency_key=f'pricecheck-{order.pk}')
        if not result.get('success',True): raise RuntimeError(result.get('error','Checkout failed'))
        redirect_url=result.get('redirect_url')
        if not redirect_url: raise RuntimeError('Gateway returned no redirect URL')
        order.checkout_reference=str(result.get('checkout_id','')); order.save(update_fields=['checkout_reference'])
        return JsonResponse({'success':True,'redirect_url':redirect_url,'order_id':order.pk})
    except Exception:
        # No payment was verified. Release reservation, never create ledger earnings.
        with transaction.atomic():
            locked=MarketplaceOrder.objects.select_for_update().get(pk=order.pk)
            if locked.status=='pending_payment':
                inv=Inventory.objects.select_for_update().get(offer=locked.offer)
                inv.reserved=max(0,inv.reserved-locked.quantity); inv.save(update_fields=['reserved','updated_at'])
                locked.status='cancelled'; locked.save(update_fields=['status'])
        return JsonResponse({'error':'Checkout unavailable. No payment was confirmed; please retry later.'},status=503)

@login_required
@require_GET
def order_detail(request,pk):
    order=get_object_or_404(MarketplaceOrder.objects.select_related('offer__product','merchant'),pk=pk)
    if request.user.pk not in (order.buyer_id,order.merchant.owner_id) and not request.user.is_staff:
        return JsonResponse({'error':'Forbidden'},status=403)
    return render(request,'pricecheck/order.html',{'order':order})

@login_required
@require_POST
def request_delivery(request,order_id):
    order=get_object_or_404(MarketplaceOrder,pk=order_id,merchant__owner=request.user)
    if order.status not in ('paid','preparing','ready'): return JsonResponse({'error':'Order not eligible for delivery'},status=409)
    if order.delivery_method=='collection': return JsonResponse({'error':'Collection order'},status=409)
    booking,created=DeliveryBooking.objects.get_or_create(order=order,defaults={'pickup_address':order.merchant.business_profile.address,'dropoff_address':order.delivery_address})
    return JsonResponse({'success':True,'booking_id':booking.pk,'status':booking.status,'note':'Booking request recorded; courier dispatch integration pending.'})


@login_required
@require_GET
def dashboard_api(request):
    merchant = MerchantAccount.objects.filter(owner=request.user).first()
    if not merchant:
        merchant = merchant_for(request.user)
    if not merchant:
        return JsonResponse({'error': 'Create a business profile first, or ask support to verify your existing retailer ownership.'}, status=403)
    inventory = Inventory.objects.filter(offer__retailer=merchant.retailer).select_related('offer__product').order_by('offer__product__name')[:200]
    stock_value = sum((x.on_hand * x.cost_per_unit for x in inventory), Decimal('0'))
    ledger = MerchantLedgerEntry.objects.filter(merchant=merchant).aggregate(total=Sum('amount'))['total'] or Decimal('0')
    return JsonResponse({'business': merchant.retailer.name, 'stock_value': str(stock_value), 'ledger_balance': str(ledger),
      'inventory': [{'product': x.offer.product.name, 'sku': x.offer.retailer_sku, 'price': str(x.offer.price), 'on_hand': x.on_hand, 'reserved': x.reserved} for x in inventory]})


@login_required
@require_GET
def orders_api(request):
    records = MarketplaceOrder.objects.filter(Q(buyer=request.user) | Q(merchant__owner=request.user)).select_related('offer__product').distinct().order_by('-created_at')[:100]
    return JsonResponse({'orders': [{'id': x.pk, 'product': x.offer.product.name, 'quantity': x.quantity, 'unit_price': str(x.unit_price), 'total': str(x.total), 'status': x.status, 'delivery_method': x.delivery_method} for x in records]})
