# NOWPayments plugin for Pretix.
# Copyright (C) 2023 İrem Kuyucu <irem@digilol.net>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import json
import logging
import hmac
import hashlib
import base64
from io import BytesIO

import qrcode

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

    logger.info("Received and verified callback: {}".format(event_body))

    try:
        payment = OrderPayment.objects.get(order__code=event_json['order_id'])
    except OrderPayment.DoesNotExist:
        logger.info("Received callback but order code doesn't match any: {}".format(event_json['order_id']))
        return HttpResponse(status=500)
    except OrderPayment.MultipleObjectsReturned:
        payment = OrderPayment.objects.filter(order__code=event_json['order_id']).last()

    if payment.info is not None:
        info_json = json.loads(payment.info)
        info_json['callback'] = event_json
        payment.info = json.dumps(info_json)
        payment.save()

    if event_json['payment_status'] != "finished":
        return HttpResponse(status=200)

    try:
        payment.confirm()
    except Quota.QuotaExceededException as e:
        info_json = json.loads(payment.info)
        info_json['QuotaExceeded'] = True
        payment.info = json.dumps(info_json)
        payment.save()
        logger.error("Payment was received but there are no ticket(s) left for "
                     "order_code: {}".format(payment.order.code))

    return HttpResponse(status=200)

def pay(request, *args, **kwargs):
    order_id = request.session.get('order_id')

    try:
        payment = OrderPayment.objects.get(id=order_id)
    except OrderPayment.DoesNotExist:
        logger.info("Order with this ID doesn't exist.")
        return HttpResponse(status=500)
    except OrderPayment.MultipleObjectsReturned:
        payment = OrderPayment.objects.filter(id=order_id).last()

    if payment.info is not None:
        try:
            payment_info = json.loads(payment.info)
            if payment_info.get('QuotaExceeded', False) == True:
                return render(request, 'pretix_nowpayments/failed.html', {
                    'url': build_absolute_uri(request.event, 'plugins:pretix_nowpayments:pay'),
                    'email': request.event.settings.payment_nowpayments_email,
                    'order_code': payment.order.code
                })
            payment_status = payment_info.get('callback', {}).get('payment_status', 'waiting')
        except Exception as e:
            logger.error("Exception occured while checking payment info: {}".format(str(e)))

    if payment.state == OrderPayment.PAYMENT_STATE_CONFIRMED:
        return redirect(eventreverse(request.event, 'presale:event.order', kwargs={
            'order': payment.order.code,
            'secret': payment.order.secret
        }) + '?paid=yes')

    address = request.session.get('nowpayments_payment_address', '')
    amount = request.session.get('nowpayments_payment_amount', 0)
    currency = request.session.get('nowpayments_payment_currency', '')

    if address == '' or amount == 0 or currency == '':
        messages.error(request, "An error occured, please try again.")

    if currency == "xmr":
        uri = "monero:{}?tx_amount={}".format(address, amount)
    elif currency == "btc":
        uri = "bitcoin:{}?amount={}".format(address, amount)

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(uri)
    qr.make()
    qr_img = qr.make_image()
    stream = BytesIO()
    qr_img.save(stream)
    qr_str = base64.b64encode(stream.getvalue()).decode('utf-8')

    return render(request, 'pretix_nowpayments/pay.html', {
        'url': build_absolute_uri(request.event, 'plugins:pretix_nowpayments:pay'),
        'address': address,
        'amount': amount,
        'currency': currency.upper(),
        'qr': qr_str,
        'status': payment_status
    })
