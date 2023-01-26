import json
import logging
import hmac
import hashlib

from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django_scopes import scopes_disabled

from pretix.base.models import OrderPayment
from pretix.base.settings import GlobalSettingsObject
from pretix.multidomain.urlreverse import build_absolute_uri, eventreverse

logger = logging.getLogger('pretix.plugins.nowpayments')

@scopes_disabled()
@require_POST
@csrf_exempt
def webhook(request, *args, **kwargs):
    event_body = request.body.decode('utf-8').strip()
    header_sig = request.headers.get('x-nowpayments-sig')
    if header_sig == '':
        logger.error("x-nowpayments-sig header is missing in callback.")
        return HttpResponse(status=400)

    try:
        event_json = json.loads(event_body)
        sorted_str = json.dumps(event_json, sort_keys=True, separators=(',', ':'))
    except Exception as e:
        logger.error("Failed to load or dump callback JSON: {}".format(str(e)))
        return HttpResponse(status=400)

    try:
        ipn_secret = request.event.settings.payment_nowpayments_ipn
        signature = hmac.new(ipn_secret.encode('ASCII'), sorted_str.encode('ASCII'),
            hashlib.sha512).hexdigest()
    except Exception as e:
        logger.error("Failed to create HMAC: {}".format(str(e)))
        return HttpResponse(status=500)

    if signature != header_sig:
        logger.error("HMAC doesn't match callback signature header.")
        return HttpResponse(status=400)

    logger.info("Sig: " + signature + ", Header: " + header_sig)

    if event_json['payment_status'] != "finished":
        logger.info("Callback payment_status isn't finished, ignoring.")
        return HttpResponse(status=200)

    try:
        payment = OrderPayment.objects.get(id=event_json['order_id'])
    except OrderPayment.DoesNotExist:
        logger.info("Received callback but order_id doesn't match any.")
        return HttpResponse(status=500)

    # TODO: handle Quota.QuotaExceededException
    payment.confirm()

    return HttpResponse(status=200)

def pay(request, *args, **kwargs):
    order_id = request.session.get('order_id')

    try:
        payment = OrderPayment.objects.get(id=order_id)
    except OrderPayment.DoesNotExist:
        logger.info("Received callback but order_id doesn't match any.")
        return HttpResponse(status=500)

    if payment.state == OrderPayment.PAYMENT_STATE_CONFIRMED:
        return redirect(eventreverse(request.event, 'presale:event.order', kwargs={
            'order': payment.order.code,
            'secret': payment.order.secret
        }) + '?paid=yes')

    address = request.session.get('nowpayments_payment_address', '')
    amount = request.session.get('nowpayments_payment_amount', 0)
    currency = request.session.get('nowpayments_payment_currency', '')

    if address == '' or amount == 0 or currency == '':
        messages.error(request, 'An error occured, please try again.')

    return render(request, 'pretix_nowpayments/pay.html', {
        'url': build_absolute_uri(request.event, 'plugins:pretix_nowpayments:pay'),
        'address': address,
        'amount': amount,
        'currency': currency,
        'qr': ' '
    })
