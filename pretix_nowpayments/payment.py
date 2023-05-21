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

import logging
from time import sleep
from collections import OrderedDict

from nowpayments import NOWPayments
from nowpayments.sandbox import NOWPaymentsSandbox

from django import forms
from django.contrib import messages
from django.template.loader import get_template

from pretix.helpers.urls import build_absolute_uri as build_global_uri
from pretix.base.decimal import round_decimal
from pretix.base.models import Event, Order, OrderPayment, OrderRefund, Quota
from pretix.base.payment import BasePaymentProvider, PaymentException
from pretix.base.services.mail import SendMailException
from pretix.base.settings import SettingsSandbox
from pretix.multidomain.urlreverse import build_absolute_uri

logger = logging.getLogger('pretix.plugins.nowpayments')

class NowPayments(BasePaymentProvider):
    identifier = 'nowpayments'
    verbose_name = 'NOWPayments'
    is_meta = True
    payment_form_fields = OrderedDict(
        [
            ('currency', forms.ChoiceField(
                label='Currency',
                initial='Monero',
                choices=(
                    ('xmr', 'Monero'),
                    ('btc', 'Bitcoin'))))
        ])

    def __init__(self, event: Event):
        super().__init__(event)
        self.settings = SettingsSandbox('payment', 'nowpayments', event)

    @property
    def settings_form_fields(self):
        d = OrderedDict(list(super().settings_form_fields.items()) +
            [
                ('endpoint', forms.ChoiceField(
                    label='Endpoint',
                    initial='live',
                    choices=(
                        ('live', 'Use production API to accept money'),
                        ('sandbox', 'Use sandbox API to test')))),
                ('api_key', forms.CharField(label='API key')),
                ('ipn', forms.CharField(label='IPN secret key')),
                ('email', forms.EmailField(label='Contact e-mail'))
            ])
        return d

    def _init_api(self):
        if self.settings.get('endpoint') == 'sandbox':
            payment = NOWPaymentsSandbox(self.settings.get('api_key'))
            return payment
        else:
            payment = NOWPayments(self.settings.get('api_key'))
            return payment

    def checkout_prepare(self, request, cart):
        form = self.payment_form(request)
        if form.is_valid():
            currency = form.cleaned_data['currency']
            request.session['nowpayments_payment_currency'] = currency
            logger.info("Selected: " + currency)

        nowp = self._init_api()

        try:
            api_status = nowp.get_api_status()
        except Exception as e:
            messages.error(request,
                '{}: {}'.format("Failed to get NOWPayments API status.", e))
            return False
        if api_status['message'] != 'OK':
            messages.error("NOWPayments API is currently unavailable. Try again later.")
            return False

        # Some NOWPayments API endpoints can be unstable, retrying works.
        for _ in range(5):
            try:
                currencies = nowp.get_available_currencies()
            except Exception as e:
                err = e
                sleep(0.5)
                continue
            else:
                break
        else:
            # All attempts failed.
            messages.error(request,
                '{}: {}'.format("Try again. Failed to get available currencies from NOWPayments.", err))
            return False

        if currency not in currencies['currencies']:
            messages.error("The selected currency is currently unavailable on NOWPayments.")
            return False

        for _ in range(5):
            try:
                min_amount = nowp.get_minimum_payment_amount(currency)
            except Exception as e:
                err = e
                sleep(0.5)
                continue
            else:
                break
        else:
            messages.error(request,
                '{}: {}'.format("Try again. Failed to get minimum payment amount from NOWPayments.", err))
            return False

        for _ in range(5):
            try:
                est_amount = nowp.get_estimate_price(cart['total'], self.event.currency.lower(), currency)
            except Exception as e:
                err = e
                sleep(0.5)
                continue
            else:
                break
        else:
            messages.error(request,
                '{}: {}'.format("Try again. Failed to get price estimate from NOWPayments.", err))
            return False

        if min_amount['min_amount'] > float(est_amount['estimated_amount']):
            messages.error(request,
                "Payment amount cannot be smaller than the minimum allowed amount.")
            return False
        return True

    def payment_is_valid_session(self, request):
        return True

    def checkout_confirm_render(self, request):
        template = get_template('pretix_nowpayments/checkout_payment_confirm.html')
        ctx = {'request': request, 'event': self.event, 'settings': self.settings}
        return template.render(ctx)

    def execute_payment(self, request, order_payment):
        currency = request.session['nowpayments_payment_currency']
        callback_url = build_absolute_uri(request.event, 'plugins:pretix_nowpayments:webhook')
        order_desc = 'Order #{} for {}'.format(order_payment.order.code, request.event.name) 
        nowp = self._init_api()

        for _ in range(5):
            try:
                created_payment = nowp.create_payment(order_payment.amount, self.event.currency.lower(), currency,
                    ipn_callback_url = callback_url, order_id = order_payment.order.code,
                    order_description = order_desc)
            except Exception as e:
                err = e
                sleep(0.5)
                continue
            else:
                break
        else:
            raise PaymentException(
                '{}: {}'.format("Failed to create payment on NOWPayments.", err))

        request.session['nowpayments_payment_amount'] = created_payment['pay_amount']
        request.session['nowpayments_payment_address'] = created_payment['pay_address']
        request.session['order_id'] = order_payment.id
        request.session['order_code'] = order_payment.order.code

        return build_absolute_uri(request.event, 'plugins:pretix_nowpayments:pay')
