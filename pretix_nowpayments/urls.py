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
