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
        messages.info(request, 'Successfully updated %d domains.' % n)
reset_api_key.short_description = "Reset API Key"


def set_domain_type_bulk(modeladmin, request, queryset):
    """Actions that sets the domain type on the selected Domain instances.
    
    This action first displays a page which provides a dropdown box for the
    user to select the domain type and then sets the new domain type on the
    sele3cted objects.
    
    It checks if the user has change permission.
    
    Based on: https://github.com/django/django/blob/1.4.2/django/contrib/admin/actions.py
    
    Important
    ---------
    In order to work requires some special form fields (see the template).
    
    """
    opts = modeladmin.model._meta
    app_label = opts.app_label
    
    # Check that the user has change permission for the Domain model
    if not modeladmin.has_change_permission(request):
        raise PermissionDenied
    
    # The user has selected a new domain type through the
    # forms.ZoneTypeSelectionForm form. Make the changes to the selected
    # objects and return a None to display the change list view again.
    #if request.method == 'POST':
    if request.POST.get('post'):
        domain_type = request.POST.get('domaintype')
        n = queryset.count()
        
        if n and domain_type:
            for obj in queryset:
                obj.type = domain_type
                obj.update_serial()
                obj.save()
                obj_display = force_unicode(obj)
                modeladmin.log_change(request, obj, obj_display)
            messages.info(request, 'Successfully updated %d domains.' % n)
        # Return None to display the change list page again.
        return None
    
    info_dict = {
        'form': ZoneTypeSelectionForm(),
        'queryset': queryset,
        'opts': opts,
        'app_label': app_label,
        'action_checkbox_name': helpers.ACTION_CHECKBOX_NAME,
    }
    return render_to_response(
        'powerdns_manager/actions/set_domain_type.html', info_dict, context_instance=RequestContext(request))
set_domain_type_bulk.short_description = "Set domain type"



def set_ttl_bulk(modeladmin, request, queryset):
    """Actions that resets TTL information on all resource records of the zone
    to the specified value.
    
    This action first displays a page which provides an input box to enter
    the new TTL.
    
    It checks if the user has change permission.
    
    Based on: https://github.com/django/django/blob/1.4.2/django/contrib/admin/actions.py
    
    Important
    ---------
    In order to work requires some special form fields (see the template).
    
    """
    opts = modeladmin.model._meta
    app_label = opts.app_label
    
    Domain = cache.get_model('powerdns_manager', 'Domain')
    Record = cache.get_model('powerdns_manager', 'Record')
    
    perm_domain_change = '%s.%s' % (opts.app_label, opts.get_change_permission())
    perm_record_change = '%s.change_record' % opts.app_label
    
    if not request.user.has_perms([perm_domain_change, perm_record_change]):
        raise PermissionDenied
    
    # Check that the user has change permission for the Re model
    if not modeladmin.has_change_permission(request):
        raise PermissionDenied
    
    # The user has set a new TTL value through the forms.TtlSelectionForm form.
    # Make the changes to the selected objects and return a None to display the
    # change list view again.
    #if request.method == 'POST':
    if request.POST.get('post'):
        form = TtlSelectionForm(request.POST)
        if form.is_valid():
            new_ttl = form.cleaned_data['new_ttl']
            reset_zone_minimum = form.cleaned_data['reset_zone_minimum']
            
            n = queryset.count()
            record_count = 0
            
            if n and new_ttl:
                for domain_obj in queryset:
                    # Find all resource records of this domain (excludes empty non-terminals)
                    qs = Record.objects.filter(domain=domain_obj).exclude(type__isnull=True)
                    # Now set the new TTL
                    for rr in qs:
                        rr.ttl = int(new_ttl)
                        # If this is the SOA record and ``reset_zone_minimum`` has
                        # been checked, set the minimum TTL of the SOA record equal
                        # to the ``new_ttl`` value
                        #
                        # Important: We do not call ``models.Domain.set_minimum_ttl()``
                        # because we edit the SOA record here.
                        #
                        if reset_zone_minimum and rr.type == 'SOA':
                            bits = rr.content.split()
                            # SOA content:  primary hostmaster serial refresh retry expire default_ttl
                            bits[6] = str(new_ttl)
                            rr.content = ' '.join(bits)
                        # Save the resource record
                        rr.save()
                        rr_display = force_unicode(rr)
                        modeladmin.log_change(request, rr, rr_display)
                    
                    # Update the domain serial
                    domain_obj.update_serial()
                    
                    record_count += len(qs)
                messages.info(request, 'Successfully updated %d zones (%d total records).' % (n, record_count))
            # Return None to display the change list page again.
            return None
    else:
        form = TtlSelectionForm()
    
    info_dict = {
        'form': form,
        'queryset': queryset,
        'opts': opts,
        'app_label': app_label,
        'action_checkbox_name': helpers.ACTION_CHECKBOX_NAME,
    }
    return render_to_response(
        'powerdns_manager/actions/set_ttl.html', info_dict, context_instance=RequestContext(request))
set_ttl_bulk.short_description = "Set Resource Records TTL"



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
    
    Clones:
    
      - Resource Records
      - Dynamic setting
      - Domain Metadata
    
    This action first displays a page which provides an input box to enter
    the origin of the new zone.
    
    It checks if the user has add & change permissions.
    
    It checks if a zone with the name that has been entered as new exists in
    the database.
    
    Based on: https://github.com/django/django/blob/1.4.2/django/contrib/admin/actions.py
    
    Important
    ---------
    In order to work requires some special form fields (see the template).
    
    """
    opts = modeladmin.model._meta
    app_label = opts.app_label
    
    Domain = cache.get_model('powerdns_manager', 'Domain')
    Record = cache.get_model('powerdns_manager', 'Record')
    DynamicZone = cache.get_model('powerdns_manager', 'DynamicZone')
    DomainMetadata = cache.get_model('powerdns_manager', 'DomainMetadata')
    
    # Check the number of selected zones. This action can work on a single zone.
    
    n = queryset.count()
    if n != 1:
        messages.error(request, 'Only one zone may be selected for cloning.')
        return None
    
    # Check permissions
        
    perm_domain_add = '%s.%s' % (opts.app_label, opts.get_add_permission())
    perm_domain_change = '%s.%s' % (opts.app_label, opts.get_change_permission())
    perm_record_add = '%s.add_record' % opts.app_label
    perm_record_change = '%s.change_record' % opts.app_label
    
    if not request.user.has_perms(
            [perm_domain_add, perm_domain_change, perm_record_add, perm_record_change]):
        raise PermissionDenied
    
    # Check that the user has change permission for the add and change modeladmin forms
    if not modeladmin.has_add_permission(request):
        raise PermissionDenied
    if not modeladmin.has_change_permission(request):
        raise PermissionDenied
    
    # The user has set a domain name for the clone through the forms.ClonedZoneDomainForm form.
    #if request.method == 'POST':
    if request.POST.get('post'):
        form = ClonedZoneDomainForm(request.POST)
        if form.is_valid():
            
            # Store Data from the form
            
            # Store the new domain name for the clone.
            clone_domain_name = form.cleaned_data['clone_domain_name']
            
            if not clone_domain_name:
                return None # Should never happen

            option_clone_dynamic = form.cleaned_data['option_clone_dynamic']
            option_clone_metadata = form.cleaned_data['option_clone_metadata']
            
            # Clone base zone
            
            # At this point queryset contain exactly one object. Checked above.
            domain_obj = queryset[0]
            
            # Create the clone (Check for uniqueness takes place in forms.ClonedZoneDomainForm 
            clone_obj = Domain.objects.create(
                name = clone_domain_name,
                master = domain_obj.master,
                #last_check = domain_obj.last_check,
                type = domain_obj.type,
                #notified_serial = domain_obj.notified_serial,
                account = domain_obj.account,
                created_by = request.user   # We deliberately do not use the domain_obj.created_by
            )
            modeladmin.log_addition(request, clone_obj)
            
            # Clone Resource Records
            
            # Find all resource records of this domain (also clones empty non-terminals)
            domain_rr_qs = Record.objects.filter(domain=domain_obj)
            
            # Create the clone's RRs
            for rr in domain_rr_qs:
                
                # Construct RR name with interchanged domain
                clone_rr_name = interchange_domain(rr.name, domain_obj.name, clone_domain_name)
                
                # Special treatment to the content of SOA and SRV RRs
                if rr.type == 'SOA':
                    content_parts = rr.content.split()
                    # primary
                    content_parts[0] = interchange_domain(content_parts[0], domain_obj.name, clone_domain_name)
                    # hostmaster
                    content_parts[1] = interchange_domain(content_parts[1], domain_obj.name, clone_domain_name)
                    # Serial. Set new serial
                    content_parts[2] = generate_serial()
                    clone_rr_content = ' '.join(content_parts)
                elif rr.type == 'SRV':
                    content_parts = rr.content.split()
                    # target
                    content_parts[2] = interchange_domain(content_parts[2], domain_obj.name, clone_domain_name)
                    clone_rr_content = ' '.join(content_parts)
                else:
                    clone_rr_content = interchange_domain(rr.content, domain_obj.name, clone_domain_name)
                
                # Create and save the cloned record.
                clone_rr = Record(
                    domain = clone_obj,
                    name = clone_rr_name,
                    type = rr.type,
                    content = clone_rr_content,
                    ttl = rr.ttl,
                    prio = rr.prio,
                    auth = rr.auth,
                    ordername = rr.ordername
                )
                clone_rr.save()
                #modeladmin.log_addition(request, clone_rr)
            
            # Clone Dynamic Zone setting
            
            if option_clone_dynamic:
                
                # Get the base domain's dynamic zone.
                # There is only one Dynamic Zone object for each zone.
                try:
                    domain_dynzone_obj = DynamicZone.objects.get(domain=domain_obj)
                except DynamicZone.DoesNotExist:
                    pass
                else:
                    # Create and save the dynamic zone object for the clone.
                    clone_dynzone_obj = DynamicZone(
                        domain = clone_obj,
                        is_dynamic = domain_dynzone_obj.is_dynamic
                        )
                    clone_dynzone_obj.save()
            
            # Clone the zone's metadata
            
            if option_clone_metadata:
                
                # Get the base domain's metadata object.
                # There is only one metadata object for each zone.
                try:
                    domain_metadata_obj = DomainMetadata.objects.get(domain=domain_obj)
                except DomainMetadata.DoesNotExist:
                    pass
                else:
                    # Create and save the metadata object for the clone.
                    clone_metadata_obj = DomainMetadata(
                        domain = clone_obj,
                        kind = domain_metadata_obj.kind,
                        content = domain_metadata_obj.content
                        )
                    clone_metadata_obj.save()
            
            messages.info(request, 'Successfully cloned %s zone to %s' % \
                (domain_obj.name, clone_domain_name))
            
            # Redirect to the new zone's change form.
            return HttpResponseRedirect(reverse('admin:%s_domain_change' % app_label, args=(clone_obj.id,)))
    
    else:
        form = ClonedZoneDomainForm()
    
    info_dict = {
        'form': form,
        'queryset': queryset,
        'opts': opts,
        'app_label': app_label,
        'action_checkbox_name': helpers.ACTION_CHECKBOX_NAME,
    }
    return render_to_response(
        'powerdns_manager/actions/clone_zone.html', info_dict, context_instance=RequestContext(request))
clone_zone.short_description = "Clone the selected zone"



def transfer_zone_to_user(modeladmin, request, queryset):
    """Action that transfers the zone to another user."""
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
        'powerdns_manager/actions/zone_from_template.html', info_dict, context_instance=RequestContext(request))
create_zone_from_template.short_description = "Create zone from template"

