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

from django.http import HttpResponseRedirect
from django.core.exceptions import PermissionDenied
from django.contrib.admin import helpers
from django.contrib import messages
from django.db.models.loading import cache
from django.core.urlresolvers import reverse

from powerdns_manager.utils import generate_api_key


def reset_api_key(modeladmin, request, queryset):
    if not modeladmin.has_change_permission(request):
        raise PermissionDenied
    DynamicZone = cache.get_model('powerdns_manager', 'DynamicZone')
    n = queryset.count()
    for domain_obj in queryset:
        # Only one DynamicZone instance for each Domain
        try:
            dz = DynamicZone.objects.get(domain=domain_obj)
        except DynamicZone.DoesNotExist:
            messages.error(request, 'Zone is not dynamic: %s' % domain_obj.name)
            n = n - 1
        else:
            if dz.api_key:
                dz.api_key = generate_api_key()
                dz.save()
            else:
                messages.error(request, 'Zone is not dynamic: %s' % domain_obj.name)
                n = n - 1
    if n:
        messages.info(request, 'Successfully reset the API key of %d domains.' % n)
reset_api_key.short_description = "Reset API Key"


def set_domain_type_bulk(modeladmin, request, queryset):
    """Actions that sets the domain type on the selected Domain instances."""
    if not modeladmin.has_change_permission(request):
        raise PermissionDenied
    selected = request.POST.getlist(helpers.ACTION_CHECKBOX_NAME)
    return HttpResponseRedirect(reverse('zone_set_type', args=(','.join(selected),)))
set_domain_type_bulk.short_description = "Set domain type"


def set_ttl_bulk(modeladmin, request, queryset):
    """Action that resets TTL information on all resource records of the zone
    to the specified value.
    """
    if not modeladmin.has_change_permission(request):
        raise PermissionDenied
    selected = request.POST.getlist(helpers.ACTION_CHECKBOX_NAME)
    return HttpResponseRedirect(reverse('zone_set_ttl', args=(','.join(selected),)))
set_ttl_bulk.short_description = 'Set Resource Records TTL'


def force_serial_update(modeladmin, request, queryset):
    """Action that updates the serial resets TTL information on all resource
    records of the selected zones.
    """
    if not modeladmin.has_change_permission(request):
        raise PermissionDenied
    for domain in queryset:
        domain.update_serial()
    n = queryset.count()
    messages.info(request, 'Successfully updated %d zones.' % n)
force_serial_update.short_description = "Force serial update"


def clone_zone(modeladmin, request, queryset):
    """Actions that clones the selected zone.

    Accepts only one selected zone.

    """
    if not modeladmin.has_add_permission(request):
        raise PermissionDenied
    elif not modeladmin.has_change_permission(request):
        raise PermissionDenied
    n = queryset.count()
    if n != 1:
        messages.error(request, 'Only one zone may be selected for cloning.')
        return HttpResponseRedirect(reverse('admin:powerdns_manager_domain_changelist'))
    return HttpResponseRedirect(reverse('zone_clone', args=(queryset[0].id,)))
clone_zone.short_description = "Clone the selected zone"


def transfer_zone_to_user(modeladmin, request, queryset):
    """Action that transfers the zone to another user."""
    if not modeladmin.has_change_permission(request):
        raise PermissionDenied
    selected = request.POST.getlist(helpers.ACTION_CHECKBOX_NAME)
    return HttpResponseRedirect(reverse('zone_transfer', args=(','.join(selected),)))
transfer_zone_to_user.short_description = 'Transfer zone to another user'


def create_zone_from_template(modeladmin, request, queryset):
    """Action that creates a new zone using the selected template.
    
    Accepts only one selected template.
    
    """
    if not modeladmin.has_change_permission(request):
        raise PermissionDenied
    n = queryset.count()
    if n != 1:
        messages.error(request, 'Only one template may be selected.')
        return HttpResponseRedirect(reverse('admin:powerdns_manager_zonetemplate_changelist'))
    return HttpResponseRedirect(reverse('template_create_zone', args=(queryset[0].id,)))
create_zone_from_template.short_description = "Create zone from template"

