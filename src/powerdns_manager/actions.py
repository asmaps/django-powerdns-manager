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

from django.contrib.contenttypes.models import ContentType
from django.http import HttpResponseRedirect
from django import template
from django.core.exceptions import PermissionDenied
from django.contrib.admin import helpers
from django.contrib.admin.util import get_deleted_objects, model_ngettext
from django.db import router
from django.shortcuts import render_to_response
from django.utils.encoding import force_unicode
from django.utils.translation import ugettext_lazy, ugettext as _
from django.contrib import messages
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.db.models.loading import cache
from django.core.urlresolvers import reverse
from django.contrib.auth import get_user_model

from powerdns_manager.forms import ZoneTypeSelectionForm
from powerdns_manager.forms import TtlSelectionForm
from powerdns_manager.forms import ClonedZoneDomainForm
from powerdns_manager.forms import ZoneTransferForm
from powerdns_manager.forms import TemplateOriginForm
from powerdns_manager.utils import generate_serial
from powerdns_manager.utils import generate_api_key
from powerdns_manager.utils import interchange_domain
from powerdns_manager.utils import process_zone_file



# Action for
# - set change date
# - set serial (?)
# - set TTL to 300, 3600, 86400
#
#def test_action(modeladmin, request, queryset):
#    messages.add_message(request, messages.INFO, 'The test action was successful.')
#test_action.short_description = "Test Action"


def reset_api_key(modeladmin, request, queryset):
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
    # Check that the user has change permission for the change modeladmin form.
    if not modeladmin.has_change_permission(request):
        raise PermissionDenied
    selected = request.POST.getlist(helpers.ACTION_CHECKBOX_NAME)
    return HttpResponseRedirect(reverse('zone_set_type', args=(','.join(selected),)))
set_domain_type_bulk.short_description = "Set domain type"



def set_ttl_bulk(modeladmin, request, queryset):
    """Action that resets TTL information on all resource records of the zone
    to the specified value.
    """
    # Check that the user has change permission for the change modeladmin form.
    if not modeladmin.has_change_permission(request):
        raise PermissionDenied
    selected = request.POST.getlist(helpers.ACTION_CHECKBOX_NAME)
    return HttpResponseRedirect(reverse('zone_set_ttl', args=(','.join(selected),)))
set_ttl_bulk.short_description = 'Set Resource Records TTL'



def force_serial_update(modeladmin, request, queryset):
    """Action that updates the serial resets TTL information on all resource
    records of the selected zones.
    """
    for domain in queryset:
        domain.update_serial()
    n = queryset.count()
    messages.info(request, 'Successfully updated %d zones.' % n)
force_serial_update.short_description = "Force serial update"



def clone_zone(modeladmin, request, queryset):
    """Actions that clones the selected zone.
    
    Accepts only one selected zone.
    
    """
    n = queryset.count()
    if n != 1:
        messages.error(request, 'Only one zone may be selected for cloning.')
        return HttpResponseRedirect(reverse('admin:powerdns_manager_domain_changelist'))
    
    # Check that the user has change permission for the add and change modeladmin forms
    if not modeladmin.has_add_permission(request):
        raise PermissionDenied
    if not modeladmin.has_change_permission(request):
        raise PermissionDenied
    
    return HttpResponseRedirect(reverse('zone_clone', args=(queryset[0].id,)))
clone_zone.short_description = "Clone the selected zone"



def transfer_zone_to_user(modeladmin, request, queryset):
    """Action that transfers the zone to another user."""
    # Check that the user has change permission for the change modeladmin form.
    if not modeladmin.has_change_permission(request):
        raise PermissionDenied
    selected = request.POST.getlist(helpers.ACTION_CHECKBOX_NAME)
    return HttpResponseRedirect(reverse('zone_transfer', args=(','.join(selected),)))
transfer_zone_to_user.short_description = 'Transfer zone to another user'



def create_zone_from_template(modeladmin, request, queryset):
    """Action that creates a new zone using the selected template.
    
    This action first displays a page which provides a text box where the user
    can enter the origin of the new zone.
    
    It checks if the user has change permission.
    
    Based on: https://github.com/django/django/blob/1.4.2/django/contrib/admin/actions.py
    
    Important
    ---------
    In order to work requires some special form fields (see the template).
    
    """
    opts = modeladmin.model._meta
    app_label = opts.app_label
    
    # Check the number of selected templates. This action can work on a single template.
    
    n = queryset.count()
    if n != 1:
        messages.error(request, 'Only one template may be selected for this action.')
        return None
    
    # Check that the user has change permission
    if not modeladmin.has_change_permission(request):
        raise PermissionDenied
    
    # The user has entered an origin through the forms.TemplateOriginForm form.
    # Make the changes to the selected
    # objects and return a None to display the change list view again.
    #if request.method == 'POST':
    if request.POST.get('post'):
        origin = request.POST.get('origin')
        
        if origin:
            
            # The queryset contains exactly one object. Checked above.
            template_obj = queryset[0]
            
            # Replace placeholder with origin in the template content.
            zonetext = template_obj.content.replace('#origin#', origin)
            
            process_zone_file(origin, zonetext, request.user)
            
            #obj_display = force_unicode(obj)
            #modeladmin.log_change(request, obj, obj_display)
            messages.info(request, "Successfully created zone '%s' from template '%s'." % (origin, template_obj.name))
            
        # Return None to display the change list page again.
        #return None
        # Redirect to the new zone's change form.
        Domain = cache.get_model('powerdns_manager', 'Domain')
        domain_obj = Domain.objects.get(name=origin)
        return HttpResponseRedirect(reverse('admin:%s_domain_change' % app_label, args=(domain_obj.id,)))
    
    info_dict = {
        'form': TemplateOriginForm(),
        'queryset': queryset,
        'opts': opts,
        'app_label': app_label,
        'action_checkbox_name': helpers.ACTION_CHECKBOX_NAME,
    }
    return render_to_response(
        'powerdns_manager/template/create_zone.html', info_dict, context_instance=RequestContext(request))
create_zone_from_template.short_description = "Create zone from template"

