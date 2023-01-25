from django.conf.urls import re_path
from django.urls import include

from pretix.multidomain import event_url

from .views import webhook, pay

event_patterns = [
    re_path(r'^nowpayments/', include([
        event_url(r'^webhook/$', webhook, name='webhook', require_live=False),
        re_path(r'^pay/$', pay, name='pay')
    ]))
]
