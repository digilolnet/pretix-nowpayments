import json
import logging

from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django_scopes import scopes_disabled

from pretix.multidomain.urlreverse import build_absolute_uri

logger = logging.getLogger('pretix.plugins.nowpayments')

@csrf_exempt
@require_POST
@scopes_disabled()
def webhook(request, *args, **kwargs):
    event_body = request.body.decode('utf-8').strip()
    event_json = json.loads(event_body)
    logger.info("Got callback: " + event_body)
    logger.info("HMAC: " + request.headers['x-nowpayments-sig'])

def pay(request, *args, **kwargs):
    address = request.session.get('nowpayments_payment_address', '')
    amount = request.session.get('nowpayments_payment_amount', 0)
    if address == '' or amount == 0:
        messages.error(request, 'An error occured, please try again.')
    return render(request, 'pretix_nowpayments/pay.html', {
        'url': build_absolute_uri(request.event, 'plugins:pretix_nowpayments:pay'),
        'address': address,
        'amount': amount
    })
