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
#  Copyright 2012 George Notaras <gnot [at] g-loaded.eu>
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

from django.conf.urls import patterns, include, url

urlpatterns = patterns('powerdns_manager.views',
    url(r'^import/zonefile/$', 'import_zone_view', name='import_zone'),
    url(r'^import/axfr/$', 'import_axfr_view', name='import_axfr'),
    url(r'^export/(?P<origin>[/.\-_\w]+)/$', 'export_zone_view', name='export_zone'),
    url(r'^update/$', 'dynamic_ip_update_view', name='dynamic_ip_update'),
    url(r'^zone/set-ttl/(?P<id_list>[0-9,]+)/$', 'zone_set_ttl_view', name='zone_set_ttl'),
    url(r'^zone/clone/(?P<zone_id>[0-9]+)/$', 'zone_clone_view', name='zone_clone'),
    url(r'^zone/transfer/(?P<id_list>[0-9,]+)/$', 'zone_transfer_view', name='zone_transfer'),
)
