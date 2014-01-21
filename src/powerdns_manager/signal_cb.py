# -*- coding: utf-8 -*-
#
#  This file is part of django-powerdns-manager.
#
#  django-powerdns-manager is a web based PowerDNS administration panel.
#
#  Development Web Site:
#    - http://www.codetrax.org/projects/django-powerdns-manager
#  Public Source Code Repository:
#    - https://source.codetrax.org/hgroot/django-powerdns-manager
#
#  Copyright 2012-2014 George Notaras <gnot [at] g-loaded.eu>
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#

import django.dispatch

from powerdns_manager.utils import rectify_zone



# ``zone_saved`` signal.
# Sent by admin.DomainAdmin.save_related() after the Domain instance and all
# the associated Record instances have been saved.
zone_saved = django.dispatch.Signal(providing_args=['instance'])


def rectify_zone_cb(sender, **kwargs):
    instance = kwargs['instance']   # powerdns_manager.Domain instance
    rectify_zone(instance.name)

def update_zone_serial_cb(sender, **kwargs):
    instance = kwargs['instance']   # powerdns_manager.Domain instance
    instance.update_serial()

