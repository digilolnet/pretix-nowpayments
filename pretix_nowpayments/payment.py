import logging
from collections import OrderedDict

from nowpayments import NOWPayments
from nowpayments.sandbox import NOWPaymentsSandbox

from django import forms
from django.contrib import messages
from django.template.loader import get_template

from pretix.base.decimal import round_decimal
from pretix.base.models import Event, Order, OrderPayment, OrderRefund, Quota
from pretix.base.payment import BasePaymentProvider, PaymentException
from pretix.base.services.mail import SendMailException
from pretix.base.settings import SettingsSandbox
from pretix.multidomain.urlreverse import build_absolute_uri

logger = logging.getLogger('pretix.plugins.nowpayments')

SUPPORTED_CURRENCIES = ['EUR']
LOCAL_ONLY_CURRENCIES = ['EUR']

class NowPayments(BasePaymentProvider):
    identifier = 'nowpayments'
    verbose_name = 'NOWPayments'

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
                ('api_key', forms.CharField(label='API key'))
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
        nowp = self._init_api()
        try:
            api_status = nowp.get_api_status()
            if api_status['message'] != 'OK':
                messages.error("NOWPayments API is currently unavailable. Try again later.")
                return False

            currencies = nowp.get_available_currencies()
            if 'xmr' not in currencies['currencies']:
                messages.error("Monero is currently unavailable for payments.")
                return False

            logger.info("cart total: " + str(cart['total']))
            min_amount = nowp.get_minimum_payment_amount('xmr')

            # Retry this in case of 500, NOWPayments likes to throw that.
            est_amount = nowp.get_estimate_price(cart['total'], 'eur', 'xmr')
            logger.info("Min amount: " + str(min_amount['min_amount']) + ", est amount: " + str(est_amount['estimated_amount']))
            if min_amount['min_amount'] > float(est_amount['estimated_amount']):
                messages.error(request,
                    "Payment amount cannot be smaller than the minimum allowed amount")
                return False

            # set session vars and redirect to custom view here

        except Exception as e:
            messages.error(request,
                '{}: {}'.format("We had trouble communicating with NOWPayments.", e))
            return False
        return True

    def payment_is_valid_session(self, request):
        return True

    def checkout_confirm_render(self, request) -> str:
        # Displayed when the user selected this provider on the 'confirm order'
        # page.
        template = get_template('pretix_nowpayments/checkout_payment_confirm.html')
        ctx = {'request': request, 'event': self.event, 'settings': self.settings}
        return template.render(ctx)
