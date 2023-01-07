# Register your receivers here
from django.dispatch import receiver

from pretix.base.signals import logentry_display, register_payment_providers

from .payment import NowPayments

@receiver(register_payment_providers, dispatch_uid="payment_nowpayments")
def register_payment_provider(sender, **kwargs):
    return NowPayments


@receiver(signal=logentry_display, dispatch_uid="nowpayments_logentry_display")
def pretixcontrol_logentry_display(sender, logentry, **kwargs):
    if logentry.action_type != 'pretix.plugins.nowpayments.event':
        return

    data = json.loads(logentry.data)
    event_type = data.get('event_type')
    text = None
    plains = {
        'PAYMENT.SALE.COMPLETED': _('Payment completed.'),
        'PAYMENT.SALE.DENIED': _('Payment denied.'),
        'PAYMENT.SALE.REFUNDED': _('Payment refunded.'),
        'PAYMENT.SALE.REVERSED': _('Payment reversed.'),
        'PAYMENT.SALE.PENDING': _('Payment pending.'),
        'CHECKOUT.ORDER.APPROVED': _('Order approved.'),
    }

    if event_type in plains:
        text = plains[event_type]
    else:
        text = event_type

    if text:
        return _('NOWPayments reported an event: {}').format(text)
