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

from django.contrib import admin
from django.db.models.loading import cache
from django.contrib import messages
from django.contrib.admin import SimpleListFilter
from django.utils.translation import ugettext_lazy as _
from django.utils.crypto import get_random_string
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse

from powerdns_manager import settings
from powerdns_manager.forms import DomainModelForm
from powerdns_manager.forms import SoaRecordModelForm
from powerdns_manager.forms import NsRecordModelForm
from powerdns_manager.forms import MxRecordModelForm
from powerdns_manager.forms import SrvRecordModelForm
from powerdns_manager.forms import ARecordModelForm
from powerdns_manager.forms import AaaaRecordModelForm
from powerdns_manager.forms import CnameRecordModelForm
from powerdns_manager.forms import PtrRecordModelForm
from powerdns_manager.forms import TxtRecordModelForm
from powerdns_manager.forms import DsRecordModelForm
from powerdns_manager.forms import CertRecordModelForm
from powerdns_manager.forms import HinfoRecordModelForm
from powerdns_manager.forms import LocRecordModelForm
from powerdns_manager.forms import SpfRecordModelForm
from powerdns_manager.forms import SshfpRecordModelForm
from powerdns_manager.forms import RpRecordModelForm
from powerdns_manager.forms import NaptrRecordModelForm
from powerdns_manager.forms import AfsdbRecordModelForm
from powerdns_manager.forms import DnskeyRecordModelForm
from powerdns_manager.forms import KeyRecordModelForm
from powerdns_manager.forms import NsecRecordModelForm
from powerdns_manager.forms import RrsigRecordModelForm
from powerdns_manager.signal_cb import zone_saved
from powerdns_manager.actions import set_domain_type_bulk
from powerdns_manager.actions import set_ttl_bulk
from powerdns_manager.actions import force_serial_update
from powerdns_manager.actions import reset_api_key
from powerdns_manager.actions import clone_zone
from powerdns_manager.actions import transfer_zone_to_user
from powerdns_manager.actions import create_zone_from_template
from powerdns_manager.utils import generate_api_key



class DynamicZoneInline(admin.StackedInline):
    model = cache.get_model('powerdns_manager', 'DynamicZone')
    fields = ('is_dynamic', 'api_key')
    readonly_fields = ('api_key', )
    search_fields = ('domain', )
    verbose_name = 'Dynamic Zone'
    verbose_name_plural = 'Dynamic Zone'    # Only one dynamic zone per domain
    can_delete = False
    # Show exactly one form
    extra = 1
    max_num = 1



class BaseTabularRecordInline(admin.TabularInline):
    RR_TYPE = '__OVERRIDE__'
    form = '__OVERRIDE__'
    model = cache.get_model('powerdns_manager', 'Record')
    extra = 0
    fields = ('name', 'ttl', 'content')
    
    def __init__(self, *args, **kwargs):
        self.verbose_name = '%s Resource Record' % self.RR_TYPE
        self.verbose_name_plural = '%s Resource Records' % self.RR_TYPE
        super(BaseTabularRecordInline, self).__init__(*args, **kwargs)
        
    def queryset(self, request):
        """Return only RR_TYPE records"""
        qs = super(BaseTabularRecordInline, self).queryset(request)
        return qs.filter(type=self.RR_TYPE)



class SoaRecordInline(admin.StackedInline):
    model = cache.get_model('powerdns_manager', 'Record')
    form = SoaRecordModelForm
    # Show exactly one form
    extra = 1
    max_num = 1
    verbose_name = 'SOA Resource Record'
    verbose_name_plural = 'SOA Resource Record' # Only one SOA RR per zone
    # The ``name`` field is not available for editing. It is always set to the
    # name of the domain in ``forms.SoaRecordModelForm.save()`` method.
    fields = ('ttl', 'primary', 'hostmaster', 'serial', 'refresh', 'retry', 'expire', 'default_ttl')
    can_delete = False
    
    def queryset(self, request):
        """Return only SOA records"""
        qs = super(SoaRecordInline, self).queryset(request)
        return qs.filter(type='SOA')


class NsRecordInline(BaseTabularRecordInline):
    RR_TYPE = 'NS'
    form = NsRecordModelForm

class MxRecordInline(BaseTabularRecordInline):
    RR_TYPE = 'MX'
    form = MxRecordModelForm
    fields = ('name', 'ttl', 'prio', 'content')
    
class SrvRecordInline(BaseTabularRecordInline):
    RR_TYPE = 'SRV'
    form = SrvRecordModelForm
    fields = ('name', 'ttl', 'prio', 'weight', 'port', 'target')

class ARecordInline(BaseTabularRecordInline):
    RR_TYPE = 'A'
    form = ARecordModelForm

class AaaaRecordInline(BaseTabularRecordInline):
    RR_TYPE = 'AAAA'
    form = AaaaRecordModelForm

class CnameRecordInline(BaseTabularRecordInline):
    RR_TYPE = 'CNAME'
    form = CnameRecordModelForm

class PtrRecordInline(BaseTabularRecordInline):
    RR_TYPE = 'PTR'
    form = PtrRecordModelForm

class TxtRecordInline(BaseTabularRecordInline):
    RR_TYPE = 'TXT'
    form = TxtRecordModelForm

class DsRecordInline(BaseTabularRecordInline):
    RR_TYPE = 'DS'
    form = DsRecordModelForm

class CertRecordInline(BaseTabularRecordInline):
    RR_TYPE = 'CERT'
    form = CertRecordModelForm

class HinfoRecordInline(BaseTabularRecordInline):
    RR_TYPE = 'HINFO'
    form = HinfoRecordModelForm

class LocRecordInline(BaseTabularRecordInline):
    RR_TYPE = 'LOC'
    form = LocRecordModelForm

class SpfRecordInline(BaseTabularRecordInline):
    RR_TYPE = 'SPF'
    form = SpfRecordModelForm

class SshfpRecordInline(BaseTabularRecordInline):
    RR_TYPE = 'SSHFP'
    form = SshfpRecordModelForm

class RpRecordInline(BaseTabularRecordInline):
    RR_TYPE = 'RP'
    form = RpRecordModelForm

class NaptrRecordInline(BaseTabularRecordInline):
    RR_TYPE = 'NAPTR'
    form = NaptrRecordModelForm

class AfsdbRecordInline(BaseTabularRecordInline):
    RR_TYPE = 'AFSDB'
    form = AfsdbRecordModelForm

class DnskeyRecordInline(BaseTabularRecordInline):
    RR_TYPE = 'DNSKEY'
    form = DnskeyRecordModelForm

class KeyRecordInline(BaseTabularRecordInline):
    RR_TYPE = 'KEY'
    form = KeyRecordModelForm

class NsecRecordInline(BaseTabularRecordInline):
    RR_TYPE = 'NSEC'
    form = NsecRecordModelForm

class RrsigRecordInline(BaseTabularRecordInline):
    RR_TYPE = 'RRSIG'
    form = RrsigRecordModelForm

class EmptyNonTerminalRecordInline(admin.TabularInline):
    """Special inline for empty non-terminals supported by PowerDNS 3.2.
    
    See: http://doc.powerdns.com/dnssec-modes.html#dnssec-direct-database
    
    """
    model = cache.get_model('powerdns_manager', 'Record')
    extra = 0
    verbose_name = 'Empty Non-Terminal Resource Record'
    verbose_name_plural = 'Empty Non-Terminal Resource Record' # Only one SOA RR per zone
    fields = ('name', 'type', 'content', 'ttl', 'prio', 'auth', 'ordername', 'change_date')
    readonly_fields = ('name', 'type', 'content', 'ttl', 'prio', 'auth', 'ordername', 'change_date')
    can_delete = False
    
    def queryset(self, request):
        """Return only Empty Non-Terminal records"""
        qs = super(EmptyNonTerminalRecordInline, self).queryset(request)
        return qs.filter(type__isnull=True)


class DomainMetadataInline(admin.TabularInline):
    model = cache.get_model('powerdns_manager', 'DomainMetadata')
    fields = ('kind', 'content', )
    extra = 0
    verbose_name_plural = 'Domain Metadata'

    
class CryptoKeyInline(admin.TabularInline):
    model = cache.get_model('powerdns_manager', 'CryptoKey')
    fields = ('flags', 'active', 'content')
    extra = 0
    verbose_name_plural = 'Crypto Keys'




class DomainAdmin(admin.ModelAdmin):
    form = DomainModelForm
    fields = ('date_modified', 'name', 'type', 'master', 'created_by')
    readonly_fields = ('date_modified', 'created_by')
    list_display = ('name', 'export_zone_html_link', 'type', 'master', 'date_modified', 'created_by')
    list_filter = ['type', 'created_by']
    search_fields = ['name', 'master', 'created_by']
    verbose_name = 'zone'
    verbose_name_plural = 'zones'
    save_on_top = True
    actions = [reset_api_key, set_domain_type_bulk, set_ttl_bulk, force_serial_update, clone_zone, transfer_zone_to_user]
    change_list_template = 'powerdns_manager/domain_changelist.html'
    change_form_template = 'powerdns_manager/domain_changeform.html'
    
    #
    # Build the ``inlines`` list. Only inlines for enabled RR types are included.
    # 
    inlines = [DynamicZoneInline]
    
    # Resource Record type to Resource Record Inline Map
    RR_INLINE_MAP = {
        'A':        ARecordInline,
        'AAAA':     AaaaRecordInline,
        'AFSDB':    AfsdbRecordInline,
        'CERT':     CertRecordInline,
        'CNAME':    CnameRecordInline,
        'DNSKEY':   DnskeyRecordInline,
        'DS':       DsRecordInline,
        'HINFO':    HinfoRecordInline,
        'KEY':      KeyRecordInline,
        'LOC':      LocRecordInline,
        'MX':       MxRecordInline,
        'NAPTR':    NaptrRecordInline,
        'NS':       NsRecordInline,
        'NSEC':     NsecRecordInline,
        'PTR':      PtrRecordInline,
        'RP':       RpRecordInline,
        'RRSIG':    RrsigRecordInline,
        'SOA':      SoaRecordInline,
        'SPF':      SpfRecordInline,
        'SSHFP':    SshfpRecordInline,
        'SRV':      SrvRecordInline,
        'TXT':      TxtRecordInline,
    }
    
    # Add RR inlines
    for RR_TYPE in settings.PDNS_ENABLED_RR_TYPES:
        inlines.append(RR_INLINE_MAP[RR_TYPE])
    
    # Add other inlines
    #inlines.append(EmptyNonTerminalRecordInline)
    inlines.append(DomainMetadataInline)
    inlines.append(CryptoKeyInline)
    
    def queryset(self, request):
        qs = super(DomainAdmin, self).queryset(request)
        if not request.user.is_superuser:
            # Non-superusers see the domains they have created
            qs = qs.filter(created_by=request.user)
        return qs
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        obj.save()
        # The zone serial is updated after all RRs have been saved.
        # This is accomplished by sending the ``zone_saved`` signal in ``save_related()``
    
    def save_related(self, request, form, formsets, change):
        """Calls the signal that rectifies the zone.
        
        In ModelAdmin.add_view() and ModelAdmin.change_view() the method
        save_model() is normally called before save_related().
        
        Using a post_save signal on the Domain or Record models is not
        efficient. In case of the Domain model, rectify_zone() would not process
        any new data in the associated records. In case of the Record model,
        rectify_zone() would be called multiple times and only the last call
        would be the effective one.
        
        rectify_zone() must be called after all the records and the domain have
        been saved to the database.
        
        Here we execute the parent save_related() and then we call rectify zone
        through a custom signal.
        
        """
        super(DomainAdmin, self).save_related(request, form, formsets, change)
        # Send the zone_saved signal
        zone_saved.send(sender=self.model, instance=form.instance)
    
    def response_change(self, request, obj):
        """Determines the HttpResponse for the change_view stage.
        
        Extends admin.ModelAdmin's ``response_change()`` method to support
        the domain tools.
        
        """

        # See template ``powerdns_manager/domain_change_form.html``
        
        if "_transfer" in request.POST:
            return HttpResponseRedirect(reverse('zone_transfer', args=(obj.id,)))
        elif "_clone" in request.POST:
            return HttpResponseRedirect(reverse('zone_clone', args=(obj.id,)))

        return super(DomainAdmin, self).response_change(request, obj)

admin.site.register(cache.get_model('powerdns_manager', 'Domain'), DomainAdmin)



class TsigKeyAdmin(admin.ModelAdmin):
    fields = ('name', 'algorithm', 'secret', 'date_modified')
    readonly_fields = ('date_modified', )
    list_display = ('name', 'algorithm', 'date_modified')
    list_filter = ('algorithm', )
    search_fields = ('name', )
    verbose_name = 'TSIG Key'
    verbose_name_plural = 'TSIG Keys'
    
    def queryset(self, request):
        qs = super(TsigKeyAdmin, self).queryset(request)
        if not request.user.is_superuser:
            # Non-superusers see the records they have created
            qs = qs.filter(created_by=request.user)
        return qs
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        obj.save()
    
admin.site.register(cache.get_model('powerdns_manager', 'TsigKey'), TsigKeyAdmin)



class SuperMasterAdmin(admin.ModelAdmin):
    fields = ('ip', 'nameserver', 'account', 'date_modified')
    readonly_fields = ('date_modified', )
    list_display = ('ip', 'nameserver', 'account', 'date_modified')
    search_fields = ('nameserver', 'account')
    verbose_name = 'SuperMaster'
    verbose_name_plural = 'SuperMasters'
    
admin.site.register(cache.get_model('powerdns_manager', 'SuperMaster'), SuperMasterAdmin)



class ZoneTemplateAdmin(admin.ModelAdmin):
    fields = ('name', 'content', 'notes', 'date_modified')
    readonly_fields = ('date_modified', )
    list_display = ('name', 'date_modified')
    search_fields = ('name', )
    verbose_name = _('template')
    verbose_name_plural = _('templates')
    actions = [create_zone_from_template, ]
    
    def queryset(self, request):
        qs = super(ZoneTemplateAdmin, self).queryset(request)
        if not request.user.is_superuser:
            # Non-superusers see the templates they have created
            qs = qs.filter(created_by=request.user)
        return qs
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        obj.save()
    
admin.site.register(cache.get_model('powerdns_manager', 'ZoneTemplate'), ZoneTemplateAdmin)


