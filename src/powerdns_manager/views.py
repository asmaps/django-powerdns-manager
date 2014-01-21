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
#  Copyright 2012-2014 George Notaras <gnot@g-loaded.eu>
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


from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.utils.translation import ugettext_lazy as _
from django.utils.encoding import force_unicode
from django.http import HttpResponse
from django.http import HttpResponseNotAllowed
from django.http import HttpResponseBadRequest
from django.http import HttpResponseNotFound
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.db.models.loading import cache
from django.utils.html import mark_safe
from django.core.validators import validate_ipv4_address
from django.core.validators import validate_ipv6_address
from django.core.exceptions import ValidationError
from django.contrib import messages
from django.contrib.contenttypes.models import ContentType
from django.contrib.admin.models import LogEntry, ADDITION, CHANGE, DELETION

from powerdns_manager.forms import ZoneImportForm
from powerdns_manager.forms import AxfrImportForm
from powerdns_manager.forms import DynamicIPUpdateForm
from powerdns_manager.forms import ZoneTransferForm
from powerdns_manager.forms import TemplateOriginForm
from powerdns_manager.forms import TtlSelectionForm
from powerdns_manager.forms import ZoneTypeSelectionForm
from powerdns_manager.forms import ClonedZoneDomainForm
from powerdns_manager.utils import process_zone_file
from powerdns_manager.utils import process_axfr_response
from powerdns_manager.utils import generate_zone_file
from powerdns_manager.utils import interchange_domain
from powerdns_manager.utils import generate_serial



@login_required
@csrf_protect
def import_zone_view(request):
    if request.method == 'POST': # If the form has been submitted...
        form = ZoneImportForm(request.POST) # A form bound to the POST data
        if form.is_valid(): # All validation rules pass
            # Process the data in form.cleaned_data
            origin = form.cleaned_data['origin']
            zonetext = form.cleaned_data['zonetext']
            overwrite = form.cleaned_data['overwrite']
            
            try:
                process_zone_file(origin, zonetext, request.user, overwrite)
            except Exception, e:
                info_dict = {
                    'strerror': mark_safe(str(e)),
                }
                return render_to_response('powerdns_manager/zone/import/error.html', info_dict)
            return render_to_response('powerdns_manager/zone/import/success.html', {})
            
    else:
        form = ZoneImportForm() # An unbound form

    info_dict = {
        'form': form,
    }
    return render_to_response(
        'powerdns_manager/zone/import/zonefile.html', info_dict, context_instance=RequestContext(request))



@login_required
@csrf_protect
def import_axfr_view(request):
    if request.method == 'POST':
        form = AxfrImportForm(request.POST)
        if form.is_valid():
            origin = form.cleaned_data['origin']
            nameserver = form.cleaned_data['nameserver']
            overwrite = form.cleaned_data['overwrite']
            
            try:
                process_axfr_response(origin, nameserver, request.user, overwrite)
            except Exception, e:
                info_dict = {
                    'strerror': mark_safe(str(e)),
                }
                return render_to_response('powerdns_manager/zone/import/error.html', {})
            info_dict = {'is_axfr': True}
            return render_to_response('powerdns_manager/zone/import/success.html', info_dict)
            
    else:
        form = AxfrImportForm() # An unbound form

    info_dict = {
        'form': form,
    }
    return render_to_response(
        'powerdns_manager/zone/import/axfr.html', info_dict, context_instance=RequestContext(request))




@login_required
def export_zone_view(request, origin):
    
    Domain = cache.get_model('powerdns_manager', 'Domain')
    
    obj = Domain.objects.get(name=origin)
    obj_display = force_unicode(obj)
            
    # Check zone ownership.
    if request.user != obj.created_by:
        messages.error(request, 'Permission denied for domain: %s' % obj_display)
        # Redirect to the Domain changelist.
        return render_to_response('powerdns_manager/zone/import/error.html', {})
        return HttpResponseRedirect(reverse('admin:powerdns_manager_domain_changelist'))
    else:
        info_dict = {
            'zone_text': generate_zone_file(origin),
            'origin': origin,
        }
        return render_to_response(
            'powerdns_manager/zone/export/zonefile.html', info_dict, context_instance=RequestContext(request))



@csrf_exempt
def tools_getip_view(request):
    return HttpResponse(request.META.get('REMOTE_ADDR'), content_type='text/plain')


@csrf_exempt
def dynamic_ip_update_view(request):
    """
    
    TODO: explain dynamic IP update options and logic
    
    if hostname is missing, the ips of all A and AAAA records of the zone are changed
    otherwise only the specific record with the name=hostname and provided that the
    correct ip (v4, v6) has been provided for the type of the record (A, AAAA)
    
    If no ipv4 or ipv6 address is provided, then the client IP address is used
    to update A records (if the client IP is IPv4) or AAAA records (if client IP is IPv6).
    
    curl -k \
        -F "api_key=UBSE1RJ0J175MRAMJC31JFUH" \
        -F "hostname=ns1.centos.example.org" \
        -F "ipv4=10.1.2.3" \
        -F "ipv6=3ffe:1900:4545:3:200:f8ff:fe21:67cf" \
        https://centos.example.org/powerdns/update/

    """
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])
    form = DynamicIPUpdateForm(request.POST)
    
    if not form.is_valid():
        return HttpResponseBadRequest(repr(form.errors))
    
    # Determine protocol or REMOTE_ADDR
    remote_ipv4 = None
    remote_ipv6 = None
    try:
        validate_ipv4_address(request.META['REMOTE_ADDR'])
    except ValidationError:
        try:
            validate_ipv6_address(request.META['REMOTE_ADDR'])
        except ValidationError:
            return HttpResponseBadRequest('Cannot determine protocol of remote IP address')
        else:
            remote_ipv6 = request.META['REMOTE_ADDR']
    else:
        remote_ipv4 = request.META['REMOTE_ADDR']
    
    # Gather required information
    
    # API key
    
    api_key = form.cleaned_data['api_key']
    
    # Hostname
    
    hostname = form.cleaned_data['hostname']
    
    # If the hostname is missing, the IP addresses of all A and AAAA records
    # of the zone are updated.
    update_all_hosts_in_zone = False
    if not hostname:
        update_all_hosts_in_zone = True
    
    # IP addresses
    
    ipv4 = form.cleaned_data['ipv4']
    ipv6 = form.cleaned_data['ipv6']

    # If IP information is missing, the remote client's IP address will be used.
    if not ipv4 and not ipv6:
        if remote_ipv4:
            ipv4 = remote_ipv4
        if remote_ipv6:
            ipv6 = remote_ipv6
    
    # All required data is good. Process the request.
    
    DynamicZone = cache.get_model('powerdns_manager', 'DynamicZone')
    Record = cache.get_model('powerdns_manager', 'Record')
    
    # Get the relevant dynamic zone instance
    dyn_zone = DynamicZone.objects.get(api_key__exact=api_key)
    
    # Get A and AAAA records
    dyn_rrs = Record.objects.filter(domain=dyn_zone.domain, type__in=('A', 'AAAA'))
    if not dyn_rrs:
        return HttpResponseNotFound('A or AAAA resource records not found')
    
    # Check existence of hostname
    if hostname:
        hostname_exists = False
        for rr in dyn_rrs:
            if rr.name == hostname:
                hostname_exists = True
                break
        if not hostname_exists:
            return HttpResponseNotFound('error:Hostname not found: %s' % hostname)
    
    # Update the IPs
    
    rr_has_changed = False
    
    if update_all_hosts_in_zone:    # No hostname supplied
        for rr in dyn_rrs:
            
            # Try to update A records
            if rr.type == 'A' and ipv4:
                rr.content = ipv4
                rr_has_changed = True
            
            # Try to update AAAA records
            elif rr.type == 'AAAA' and ipv6:
                rr.content = ipv6
                rr_has_changed = True
            
            rr.save()
        
    else:    # A hostname is supplied
        for rr in dyn_rrs:
            if rr.name == hostname:
                
                # Try to update A records
                if rr.type == 'A' and ipv4:
                    rr.content = ipv4
                    rr_has_changed = True
            
                # Try to update AAAA records
                elif rr.type == 'AAAA' and ipv6:
                    rr.content = ipv6
                    rr_has_changed = True
                
                rr.save()
    
    if rr_has_changed:
        return HttpResponse('Success')
    else:
        return HttpResponseNotFound('error:No suitable resource record found')



@login_required
@csrf_protect
def zone_set_type_view(request, id_list):
    """sets the domain type on the selected zones.
    
    Accepts a comma-delimited list of Domain object IDs.
    
    An intermediate page asking for the new zone type is used.
    
    """
    # Create a list from the provided comma-delimited list of IDs.
    id_list = id_list.split(',')
    
    # Permission check on models.
    if not request.user.has_perms([
            'powerdns_manager.change_domain',
        ]):
        messages.error(request, 'Insufficient permissions for this action.')
        return HttpResponseRedirect(reverse('admin:powerdns_manager_domain_changelist'))
    
    if request.method == 'POST':
        domain_type = request.POST.get('domaintype')
        
        Domain = cache.get_model('powerdns_manager', 'Domain')
        
        for n, zone_id in enumerate(id_list):
            obj = Domain.objects.get(id=zone_id)
            obj_display = force_unicode(obj)
            
            # Check zone ownership.
            if request.user != obj.created_by:
                messages.error(request, 'Permission denied for domain: %s' % obj_display)
            else:
                obj.type = domain_type
                obj.update_serial()
                obj.save()
                
        n += 1
        if n == 1:
            messages.info(request, "Successfully set the type of '%s' to '%s'" % (obj_display, domain_type))
        elif n > 1:
            messages.info(request, "Successfully set the type of %s zones to '%s'" % (n, domain_type))
            
        # Redirect to the Domain changelist.
        return HttpResponseRedirect(reverse('admin:powerdns_manager_domain_changelist'))
    
    else:
        form = ZoneTypeSelectionForm()
        
    info_dict = {
        'form': form,
        'id_list': id_list,
    }
    return render_to_response(
        'powerdns_manager/zone/set_type.html', info_dict, context_instance=RequestContext(request))



@login_required
@csrf_protect
def zone_set_ttl_view(request, id_list):
    """Resets TTL information on all resource records of the zone.
    
    Accepts a comma-delimited list of Domain object IDs.
    
    An intermediate page asking for the new TTL is used.
    
    """
    # Create a list from the provided comma-delimited list of IDs.
    id_list = id_list.split(',')
    
    # Permission check on models.
    if not request.user.has_perms([
            'powerdns_manager.change_domain',
            'powerdns_manager.change_record',
        ]):
        messages.error(request, 'Insufficient permissions for this action.')
        return HttpResponseRedirect(reverse('admin:powerdns_manager_domain_changelist'))
    
    if request.method == 'POST':
        form = TtlSelectionForm(request.POST)
        if form.is_valid():
            new_ttl = form.cleaned_data['new_ttl']
            reset_zone_minimum = form.cleaned_data['reset_zone_minimum']
            
            Domain = cache.get_model('powerdns_manager', 'Domain')
            Record = cache.get_model('powerdns_manager', 'Record')
            
            record_count = 0
            
            for n, zone_id in enumerate(id_list):
                obj = Domain.objects.get(id=zone_id)
                obj_display = force_unicode(obj)
                
                # Check zone ownership.
                if request.user != obj.created_by:
                    messages.error(request, 'Permission denied for domain: %s' % obj_display)
                else:
                    # Find all resource records of this domain (excludes empty non-terminals)
                    qs = Record.objects.filter(domain=obj).exclude(type__isnull=True)
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
                    
                    # Update the domain serial
                    obj.update_serial()
                    
                    record_count += len(qs)
            
            n += 1
            if n == 1:
                messages.info(request, "Successfully updated %s resource records of '%s'" % (record_count, obj_display))
            elif n > 1:
                messages.info(request, 'Successfully updated %s zones (%s total resource records).' % (n, record_count))
                
            # Redirect to the Domain changelist.
            return HttpResponseRedirect(reverse('admin:powerdns_manager_domain_changelist'))
        
    else:
        form = TtlSelectionForm()
        
    info_dict = {
        'form': form,
        'id_list': id_list,
    }
    return render_to_response(
        'powerdns_manager/zone/set_ttl.html', info_dict, context_instance=RequestContext(request))



@login_required
@csrf_protect
def zone_clone_view(request, zone_id):
    """Clones zone.
    
    Accepts a single Domain object ID.
    
    An intermediate page asking for the origin of the new zone.

    Clones:
    
      - Resource Records
      - Dynamic setting
      - Domain Metadata
      
    """
    # Permission check on models.
    if not request.user.has_perms([
            'powerdns_manager.add_domain',
            'powerdns_manager.change_domain',
            'powerdns_manager.add_record',
            'powerdns_manager.change_record',
            'powerdns_manager.add_domainmetadata',
            'powerdns_manager.change_domainmetadata',
            'powerdns_manager.add_dynamiczone',
            'powerdns_manager.change_dynamiczone',
        ]):
        messages.error(request, 'Insufficient permissions for this action.')
        return HttpResponseRedirect(reverse('admin:powerdns_manager_domain_changelist'))
    
    if request.method == 'POST':
        form = ClonedZoneDomainForm(request.POST)
        if form.is_valid():
            
            # Store Data from the form
            
            # Store the new domain name for the clone.
            clone_domain_name = form.cleaned_data['clone_domain_name']
            
            option_clone_dynamic = form.cleaned_data['option_clone_dynamic']
            option_clone_metadata = form.cleaned_data['option_clone_metadata']
            
            # Get the models
            Domain = cache.get_model('powerdns_manager', 'Domain')
            Record = cache.get_model('powerdns_manager', 'Record')
            DynamicZone = cache.get_model('powerdns_manager', 'DynamicZone')
            DomainMetadata = cache.get_model('powerdns_manager', 'DomainMetadata')
            
            # Clone base zone
            
            # Get the Domain object which will be cloned.
            domain_obj = Domain.objects.get(id=zone_id)
            
            # Check zone ownership.
            if request.user != domain_obj.created_by:
                messages.error(request, "Insufficient permissions to clone domain '%s'" % force_unicode(domain_obj))
                return HttpResponseRedirect(reverse('admin:powerdns_manager_domain_changelist'))
            
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
            #modeladmin.log_addition(request, clone_obj)
            
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
            return HttpResponseRedirect(reverse('admin:powerdns_manager_domain_change', args=(clone_obj.id,)))

    else:
        form = ClonedZoneDomainForm()
    
    info_dict = {
        'form': form,
        'zone_id': zone_id,
    }
    return render_to_response(
        'powerdns_manager/zone/clone.html', info_dict, context_instance=RequestContext(request))
    
    

@login_required
@csrf_protect
def zone_transfer_view(request, id_list):
    """Transfer zones to another user.
    
    Accepts a comma-delimited list of Domain object IDs.
    
    An intermediate page asking for the username of the target owner is used.
    
    """
    # Create a list from the provided comma-delimited list of IDs.
    id_list = id_list.split(',')
    
    # Permission check on models.
    if not request.user.has_perms([
            'powerdns_manager.change_domain',
        ]):
        messages.error(request, 'Insufficient permissions for this action.')
        return HttpResponseRedirect(reverse('admin:powerdns_manager_domain_changelist'))
    
    if request.method == 'POST':
        form = ZoneTransferForm(request.POST)
        if form.is_valid():
            transfer_to_username = request.POST.get('transfer_to_username')
            
            # Get the user object of the new owner.
            # We always have a valid user object as validation has taken place
            # in the ZoneTransferForm.
            User = get_user_model()
            owner = User.objects.get(username=transfer_to_username)
            owner_display = force_unicode(owner)
            
            Domain = cache.get_model('powerdns_manager', 'Domain')
            
            for n, zone_id in enumerate(id_list):
                obj = Domain.objects.get(id=zone_id)
                obj_display = force_unicode(obj)
                
                # Check zone ownership.
                if request.user != obj.created_by:
                    messages.error(request, 'Permission denied for domain: %s' % obj_display)
                else:
                    obj.created_by = owner
                    obj.update_serial()
                    obj.save()
                    
                    # Create log entry
#                     LogEntry.objects.log_action(
#                         user_id         = request.user.pk, 
#                         content_type_id = ContentType.objects.get_for_model(obj).pk,
#                         object_id       = obj.pk,
#                         object_repr     = obj_display, 
#                         action_flag     = CHANGE
#                     )
            
            n += 1
            if n == 1:
                messages.info(request, "Successfully transfered domain '%s' to '%s'" % (obj_display, owner_display))
            elif n > 1:
                messages.info(request, 'Successfully transfered %d domains.' % n)
                
            # Redirect to the Domain changelist.
            return HttpResponseRedirect(reverse('admin:powerdns_manager_domain_changelist'))
        
    else:
        form = ZoneTransferForm()
        
    info_dict = {
        'form': form,
        'id_list': id_list,
    }
    return render_to_response(
        'powerdns_manager/zone/transfer.html', info_dict, context_instance=RequestContext(request))
    




@login_required
@csrf_protect
def template_create_zone_view(request, template_id):
    """Create zone from template.
    
    Accepts a template ID.
    
    An intermediate page asking for the origin of the new zone is used.
    
    """
    # Permission check on models.
    if not request.user.has_perms([
            'powerdns_manager.add_domain',
        ]):
        messages.error(request, 'Insufficient permissions for this action.')
        return HttpResponseRedirect(reverse('admin:powerdns_manager_zonetemplate_changelist'))
    
    if request.method == 'POST':
        origin = request.POST.get('origin')
        
        # Get the models
        ZoneTemplate = cache.get_model('powerdns_manager', 'ZoneTemplate')
        Domain = cache.get_model('powerdns_manager', 'Domain')
        
        template_obj = ZoneTemplate.objects.get(id=template_id)
        template_obj_display = force_unicode(template_obj)
        
        # Check template ownership.
        if request.user != template_obj.created_by:
            messages.error(request, 'Permission denied for template: %s' % template_obj_display)
            return HttpResponseRedirect(reverse('admin:powerdns_manager_zonetemplate_changelist'))
        else:
            # Replace placeholder with origin in the template content.
            zonetext = template_obj.content.replace('#origin#', origin)
            
            process_zone_file(origin, zonetext, request.user)
            
            messages.info(request, "Successfully created zone '%s' from template '%s'." % (origin, template_obj.name))
            
            # Redirect to the new zone's change form.
            domain_obj = Domain.objects.get(name=origin)
            return HttpResponseRedirect(reverse('admin:powerdns_manager_domain_change', args=(domain_obj.id,)))
                    
                    # Create log entry
#                     LogEntry.objects.log_action(
#                         user_id         = request.user.pk, 
#                         content_type_id = ContentType.objects.get_for_model(obj).pk,
#                         object_id       = obj.pk,
#                         object_repr     = obj_display, 
#                         action_flag     = CHANGE
#                     )

    else:
        form = TemplateOriginForm()
        
    info_dict = {
        'form': form,
        'template_id': template_id,
    }
    return render_to_response(
        'powerdns_manager/template/create_zone.html', info_dict, context_instance=RequestContext(request))
    
