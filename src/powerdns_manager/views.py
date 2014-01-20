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
from powerdns_manager.utils import process_zone_file
from powerdns_manager.utils import process_axfr_response
from powerdns_manager.utils import generate_zone_file



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
                return render_to_response('powerdns_manager/import/error.html', info_dict)
            return render_to_response('powerdns_manager/import/success.html', {})
            
    else:
        form = ZoneImportForm() # An unbound form

    info_dict = {
        'form': form,
    }
    return render_to_response(
        'powerdns_manager/import/zone.html', info_dict, context_instance=RequestContext(request))



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
                return render_to_response('powerdns_manager/import/error.html', {})
            info_dict = {'is_axfr': True}
            return render_to_response('powerdns_manager/import/success.html', info_dict)
            
    else:
        form = AxfrImportForm() # An unbound form

    info_dict = {
        'form': form,
    }
    return render_to_response(
        'powerdns_manager/import/axfr.html', info_dict, context_instance=RequestContext(request))




@login_required
def export_zone_view(request, origin):
    info_dict = {
        'zone_text': generate_zone_file(origin),
        'origin': origin,
    }
    return render_to_response(
        'powerdns_manager/export/zone.html', info_dict, context_instance=RequestContext(request))



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
def zone_transfer_view(request, id_list):
    """Transfer zones to another user.
    
    Accepts a comma-delimited list of Domain object IDs.
    
    An intermediate page asking for the username of the target owner is used.
    
    """
    # Create a list from the provided comma-delimited list of IDs.
    id_list = id_list.split(',')
    
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
                
                # Check change permission
                if request.user.has_perm('powerdns_manager.change_zone', obj):
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
                else:
                    messages.error(request, 'Permission denied for domain: %s' % obj_display)
            
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
    
    