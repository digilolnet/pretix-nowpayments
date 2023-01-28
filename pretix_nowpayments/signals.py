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
