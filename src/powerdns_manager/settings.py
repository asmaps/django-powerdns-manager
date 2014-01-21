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

from django.conf import settings


PDNS_DEFAULT_ZONE_TYPE = getattr(settings, 'PDNS_DEFAULT_ZONE_TYPE', 'NATIVE')

PDNS_DEFAULT_RR_TTL = getattr(settings, 'PDNS_DEFAULT_RR_TTL', 3600)

# Declares the server a SLAVE -- Will be used internally
PDNS_IS_SLAVE = getattr(settings, 'PDNS_IS_SLAVE', False)

_DEFAULT_PDNS_ENABLED_RR_TYPES = [
    'SOA',
    'NS',
    'MX',
    'A',
    'AAAA',
    'CNAME',
    'PTR',
    'TXT',
    'SPF',
    'SRV',
    'CERT',
    'DNSKEY',
    'DS',
    'KEY',
    'NSEC',
    'RRSIG',
    'HINFO',
    'LOC',
    'NAPTR',
    'RP',
    'AFSDB',
    'SSHFP',
]
PDNS_ENABLED_RR_TYPES = getattr(settings, 'PDNS_ENABLED_RR_TYPES', _DEFAULT_PDNS_ENABLED_RR_TYPES)

PDNS_ALLOW_WILDCARD_NAMES = getattr(settings, 'PDNS_ALLOW_WILDCARD_NAMES', True)

