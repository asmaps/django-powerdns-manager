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

from django.db import models
from django.db.models import signals
from django.utils.translation import ugettext_lazy as _
from django.db.models.loading import cache
from django.core.urlresolvers import reverse
from django.conf import settings as django_settings

from powerdns_manager import settings
from powerdns_manager import signal_cb
from powerdns_manager.utils import generate_serial
from powerdns_manager.utils import generate_serial_timestamp
from powerdns_manager.utils import generate_api_key



"""
http://doc.powerdns.com/generic-mypgsql-backends.html#idp9002432
http://wiki.powerdns.com/trac/wiki/fields
"""


# Django 1.5 introduced the AUTH_USER_MODEL
# https://docs.djangoproject.com/en/dev/ref/settings/#std:setting-AUTH_USER_MODEL
# Supporting custom user models requires this setting.
# For backwards compatibility here we check whether ``django_settings`` contains
# this setting and use it, otherwise use ``auth.User`` as a fallback.
if hasattr(django_settings, 'AUTH_USER_MODEL'):
    AUTH_USER_MODEL = django_settings.AUTH_USER_MODEL
else:
    AUTH_USER_MODEL = 'auth.User'



class Domain(models.Model):
    """Model for PowerDNS domain."""
    
    DOMAIN_TYPE_CHOICES = (
        ('NATIVE', 'Native'),
        ('MASTER', 'Master'),
        ('SLAVE', 'Slave'),
        #('SUPERSLAVE', 'Superslave'),
    )
    name = models.CharField(max_length=255, unique=True, db_index=True, verbose_name=_('name'), help_text="""This field is the actual domainname. This is the field that powerDNS matches to when it gets a request. The domainname should be in the format of: domainname.TLD (no trailing dot)""")
    master = models.CharField(max_length=128, blank=True, null=True, verbose_name=_('master'), help_text="""Enter a comma delimited list of nameservers that are master for this domain. This setting applies only to slave zones.""")
    last_check = models.PositiveIntegerField(max_length=11, null=True, verbose_name=_('last check'), help_text="""Last time this domain was checked for freshness.""")
    type = models.CharField(max_length=6, choices=DOMAIN_TYPE_CHOICES, default=settings.PDNS_DEFAULT_ZONE_TYPE, verbose_name=_('type'), help_text="""Select the zone type. Native refers to native SQL replication. Master/Slave refers to DNS server based zone transfers.""")
    notified_serial = models.PositiveIntegerField(max_length=11, null=True, verbose_name=_('notified serial'), help_text="""The last notified serial of a master domain. This is updated from the SOA record of the domain.""")
    account = models.CharField(max_length=40, blank=True, null=True, verbose_name=_('account'), help_text="""Determine if a certain host is a supermaster for a certain domain name. (???)""")

    # PowerDNS Manager internal fields
    #date_created = models.DateTimeField(auto_now_add=True, verbose_name=_('Created on'))
    date_modified = models.DateTimeField(auto_now=True, verbose_name=_('Last Modified'))
    created_by = models.ForeignKey(AUTH_USER_MODEL, related_name='%(app_label)s_%(class)s_created_by', null=True, verbose_name=_('owner username'), help_text="""The Django user this zone belongs to.""")
    
    class Meta:
        db_table = 'domains'
        verbose_name = _('zone')
        verbose_name_plural = _('zones')
        get_latest_by = 'date_modified'
        ordering = ['name']

    def __unicode__(self):
        return self.name
    
#    def save(self, *args, **kwargs):
#        """Saves the instance to the database.
#        
#        The serial of the zone is updated.
#        
#        """
#        self.update_serial()
#        return super(Domain, self).save(*args, **kwargs)
    
    def get_minimum_ttl(self):
        """Returns the minimum TTL.
        
        The SOA record of the zone is retrieved and the minimum TTL is extracted
        from the ``content`` field.
        
        If a SOA record does not exist for this zone, PDNS_DEFAULT_RR_TTL
        is returned from the settings..
        
        """
        Record = cache.get_model('powerdns_manager', 'Record')
        try:
            soa_rr = Record.objects.get(domain=self, type='SOA')
        except Record.DoesNotExist:
            return settings.PDNS_DEFAULT_RR_TTL
        else:
            return soa_rr.content.split()[-1]
    
    def set_minimum_ttl(self, new_minimum_ttl):
        """Sets the minimum TTL.
        
        Accepts ``new_minimum_ttl`` (integer)
        
        SOA content:  primary hostmaster serial refresh retry expire default_ttl
        
        Important
        ---------
        Make sure this is not called while the SOA record object is modified.
        
        TODO: Investigate whether it is needed to perform any checks against settings.PDNS_DEFAULT_RR_TTL
        
        """
        Record = cache.get_model('powerdns_manager', 'Record')
        try:
            soa_rr = Record.objects.get(domain=self, type='SOA')
        except Record.DoesNotExist:
            raise Exception('SOA Resource Record does not exist.')
        else:
            bits = soa_rr.content.split()
            bits[6] = new_minimum_ttl
            soa_rr.content = ' '.join(bits)
            soa_rr.save()
    
    def update_serial(self):
        """Updates the serial of the zone (SOA record).
        
        SOA content:  primary hostmaster serial refresh retry expire default_ttl
        
        """
        Record = cache.get_model('powerdns_manager', 'Record')
        try:
            soa_rr = Record.objects.get(domain=self, type='SOA')
        except Record.DoesNotExist:
            raise Exception('SOA Resource Record does not exist.')
        else:
            bits = soa_rr.content.split()
            bits[2] = str(generate_serial(serial_old=bits[2]))
            soa_rr.content = ' '.join(bits)
            soa_rr.save()
    
    def export_zone_html_link(self):
        html_link = '<a href="%s"><strong>export zone</strong></a>' % reverse('export_zone', kwargs={'origin': self.name})
        return html_link
    export_zone_html_link.allow_tags = True
    export_zone_html_link.short_description = 'Export zone file'

signal_cb.zone_saved.connect(signal_cb.rectify_zone_cb, sender=Domain)
signal_cb.zone_saved.connect(signal_cb.update_zone_serial_cb, sender=Domain)


class Record(models.Model):
    """Model for PowerDNS resource record.
    
    Supported record types:
    
        http://doc.powerdns.com/types.html
    
    Rules for filling in AUTH and ORDERNAME fields:
        
        http://doc.powerdns.com/dnssec-modes.html#dnssec-direct-database
    
    """
    # Build resource record choices list
    RECORD_TYPE_CHOICES = []
    for enabled_rr_type in settings.PDNS_ENABLED_RR_TYPES:
        RECORD_TYPE_CHOICES.append( (enabled_rr_type, enabled_rr_type) )

    # domain -> specs state 'default null'. Consider adding: null=True
    domain = models.ForeignKey('powerdns_manager.Domain', related_name='%(app_label)s_%(class)s_domain', verbose_name=_('domain'), help_text=_("""Select the domain this record belongs to."""))
    name = models.CharField(max_length=255, null=True, db_index=True, verbose_name=_('name'), help_text="""Actual name of a record. Must not end in a '.' and be fully qualified - it is not relative to the name of the domain!  For example: www.test.com (no trailing dot)""")
    # See section 8.5 about why the type field allows NULL. (PowerDNS 3.2 and above)
    # Has db_index=True, without specs specifying so.
    type = models.CharField(max_length=10, null=True, db_index=True, choices=RECORD_TYPE_CHOICES, verbose_name=_('type'), help_text="""Select the type of the resource record.""")
    content = models.CharField(max_length=64000, null=True, verbose_name=_('content'), help_text="""This is the 'right hand side' of a DNS record. For an A record, this is the IP address for example.""")
    ttl = models.PositiveIntegerField(max_length=11, blank=True, null=True, verbose_name=_('TTL'), help_text="""How long the DNS-client are allowed to remember this record. Also known as Time To Live(TTL) This value is in seconds.""")
    prio = models.PositiveIntegerField(max_length=11, null=True, verbose_name=_('priority'), help_text="""For MX records, this should be the priority of the mail exchanger specified.""")
    # Extra fields for DNSSEC (http://doc.powerdns.com/dnssec-modes.html#dnssec-direct-database)
    auth = models.NullBooleanField(verbose_name=_('authoritative'), help_text="""The 'auth' field should be set to '1' for data for which the zone itself is authoritative, which includes the SOA record and its own NS records. The 'auth' field should be 0 however for NS records which are used for delegation, and also for any glue (A, AAAA) records present for this purpose. Do note that the DS record for a secure delegation should be authoritative!""")
    # 'ordername' allows NULL to facilitate late calculation
    ordername = models.CharField(max_length=255, null=True, db_index=True, verbose_name=_('ordername'), help_text="""http://doc.powerdns.com/dnssec-modes.html#dnssec-direct-database""")
    
    # This is set to the current timestamp on every save
    change_date = models.PositiveIntegerField(max_length=11, null=True, verbose_name=_('change date'), help_text="""Timestamp for the last update. This is used by PowerDNS internally.""")

    # PowerDNS Manager internal fields
    date_modified = models.DateTimeField(auto_now=True, verbose_name=_('Last Modified'))

    class Meta:
        db_table = 'records'
        verbose_name = _('record')
        verbose_name_plural = _('records')
        get_latest_by = 'date_modified'
        ordering = ['name', 'type']
        index_together = [
            ['name', 'type'],
            ['domain', 'ordername'],
        ]
        # The following index is created by a MySQL statement in ``sql/record.mysql.sql``
        #     CREATE INDEX nametype_index ON records(name,type);
        # SEE: http://stackoverflow.com/questions/1578195/django-create-index-non-unique-multiple-column
        
    def __unicode__(self):
        #return '%s %s' % (self.type, self.name)
        return self.name
    
    def save(self, *args, **kwargs):
        """Saves the instance to the database.
        
        The following actions are performed:
        
        1) Sets the current timestamp to the ``change_date`` field. This is
        used by PowerDNS. (Empty non-terminals are excluded)
        
        2) Sets the TTL of the resource record(s), if missing. Since
        ``get_minimum_ttl()`` retrieves the minimum TTL from the SOA record,
        if a SOA record has not been saved yet, then PDNS_DEFAULT_RR_TTL will
        be used instead.
        
        3) Set the ``auth`` field. Needed by PowerDNS internals.
        
        4) Set the ``ordername`` field. Needed by PowerDNS internals.
        
        """
        if self.type is not None:   # Exclude empty non-terminals
            
            self.change_date = generate_serial_timestamp()
        
            if not self.ttl:
                self.ttl = self.domain.get_minimum_ttl()
        
        # auth and ordername fields are set automatically after the zone and
        # all records have been saved. See: admin.DomainAdmin.save_related()
        
        return super(Record, self).save(*args, **kwargs)



class SuperMaster(models.Model):
    """Model for PowerDNS supermasters.
    
    More on supermasters: http://doc.powerdns.com/slave.html#supermaster
    
    PDNS can recognize so called 'supermasters'. A supermaster is a host which
    is master for domains and for which we are to be a slave. When a master
    (re)loads a domain, it sends out a notification to its slaves. Normally,
    such a notification is only accepted if PDNS already knows that it is a
    slave for a domain.
    
    SuperMaster records should be added on the secondary DNS servers (slaves).
    This table contains known and trusted master servers.
    
    A supermaster is a host which is master for domains and for which we are to be a slave.  ref  ref2
    This table is an authorization table for the IP/nameserver. 

    """
    # TODO: added ``unique=True`` to ``ip`` because it is set as primary key
    ip = models.GenericIPAddressField(unique=True, verbose_name=_('IP address'), help_text="""IP address for supermaster (IPv4 or IPv6).""")
    # TODO: added ``unique=True`` to ``nameserver`` because it is set as primary key
    nameserver = models.CharField(max_length=255, unique=True, verbose_name=_('nameserver'), help_text="""Hostname of the supermaster.""")
    account = models.CharField(max_length=40, blank=True, null=True, verbose_name=_('account'), help_text="""Account name (???)""")

    # PowerDNS Manager internal fields
    date_modified = models.DateTimeField(auto_now=True, verbose_name=_('Last Modified'))

    class Meta:
        db_table = 'supermasters'
        verbose_name = _('supermaster')
        verbose_name_plural = _('supermasters')
        get_latest_by = 'date_modified'
        ordering = ['nameserver']
        #unique_together = (
        #    ('ip', 'nameserver'),   # This is custom addition. check if causes problems
        #    #('nameserver', 'account'),    # TODO: check what account really is. maybe we need to add a created_by field here.
        #)

    def __unicode__(self):
        return self.nameserver


class DomainMetadata(models.Model):
    """Model for PowerDNS domain metadata.
    
    More on domain metadata: http://doc.powerdns.com/domainmetadata.html
    
    """
    PER_ZONE_METADATA_CHOICES = (
        ('ALLOW-AXFR-FROM', 'ALLOW-AXFR-FROM'),
        ('AXFR-MASTER-TSIG', 'AXFR-MASTER-TSIG'),
        ('LUA-AXFR-SCRIPT', 'LUA-AXFR-SCRIPT'),
        ('NSEC3NARROW', 'NSEC3NARROW'),
        ('NSEC3PARAM', 'NSEC3PARAM'),
        ('PRESIGNED', 'PRESIGNED'),
        ('SOA-EDIT', 'SOA-EDIT'),
        ('TSIG-ALLOW-AXFR', 'TSIG-ALLOW-AXFR'),
    )
    domain = models.ForeignKey('powerdns_manager.Domain', related_name='%(app_label)s_%(class)s_domain', db_index=True, verbose_name=_('domain'), help_text=_("""Select the domain this record belongs to."""))
    kind = models.CharField(max_length=16, choices=PER_ZONE_METADATA_CHOICES, verbose_name=_('setting'), help_text="""Select a setting.""")
    # TODO: Check if content may be empty
    content = models.TextField(blank=True, null=True, verbose_name=_('content'), help_text="""Enter the metadata.""")
    
    # PowerDNS Manager internal fields
    date_modified = models.DateTimeField(auto_now=True, verbose_name=_('Last Modified'))

    class Meta:
        db_table = 'domainmetadata'
        verbose_name = _('domain metadata')
        verbose_name_plural = _('domain metadata')
        get_latest_by = 'date_modified'
        ordering = ['kind']
        
    def __unicode__(self):
        return self.kind



class CryptoKey(models.Model):
    """Model for PowerDNS domain crypto keys.
    
    See: http://doc.powerdns.com/dnssec-supported.html
    
    """
    domain = models.ForeignKey('powerdns_manager.Domain', related_name='%(app_label)s_%(class)s_domain', db_index=True, verbose_name=_('domain'), help_text=_("""Select the domain this record belongs to."""))
    flags = models.PositiveIntegerField(verbose_name=_('flags'), help_text="""Key flags.""")
    active = models.BooleanField(verbose_name=_('active'), help_text="""Check to activate key.""")
    # TODO: Check if content may be empty
    content = models.TextField(blank=True, null=True, verbose_name=_('content'), help_text="""Enter the key data.""")
    
    # PowerDNS Manager internal fields
    date_modified = models.DateTimeField(auto_now=True, verbose_name=_('Last Modified'))

    class Meta:
        db_table = 'cryptokeys'
        verbose_name = _('crypto key')
        verbose_name_plural = _('crypto keys')
        get_latest_by = 'date_modified'
        ordering = ['domain']
        
    def __unicode__(self):
        return self.domain.name



class TsigKey(models.Model):
    """Model for PowerDNS domain TSIG keys.
    
    See: http://doc.powerdns.com/tsig.html
    
    """
    ALGORITHM_CHOICES = (
        ('hmac-md5', 'hmac-md5'),
        # TODO: check for more
    )
    name = models.CharField(max_length=255, verbose_name=_('name'), help_text="""Enter a name for the key.""")
    algorithm = models.CharField(max_length=50, choices=ALGORITHM_CHOICES, verbose_name=_('algorithm'), help_text="""Select hashing algorithm.""")
    secret = models.CharField(max_length=255, verbose_name=_('secret'), help_text="""Enter the shared secret.""")

    # PowerDNS Manager internal fields
    date_modified = models.DateTimeField(auto_now=True, verbose_name=_('Last Modified'))
    created_by = models.ForeignKey(AUTH_USER_MODEL, related_name='%(app_label)s_%(class)s_created_by', null=True, verbose_name=_('created by'), help_text="""The Django user this TSIG key belongs to.""")


    class Meta:
        db_table = 'tsigkeys'
        verbose_name = _('TSIG Key')
        verbose_name_plural = _('TSIG Keys')
        get_latest_by = 'date_modified'
        ordering = ['name']
        unique_together = (
            ('name', 'algorithm'),
        )
        
    def __unicode__(self):
        return self.name



class DynamicZone(models.Model):
    """Model for Dynamic Zones.
    
    This is a PowerDNS Manager feature to support updating, the A and AAAA
    resource records of a zone over HTTP.
    
    This feature can be used to easily update the IP of hosts whose IP
    address is dynamic.
    
    """
    domain = models.ForeignKey('powerdns_manager.Domain', unique=True, related_name='%(app_label)s_%(class)s_domain', verbose_name=_('domain'), help_text=_("""Select the domain, the A and AAAA records of which might be updated dynamically over HTTP."""))
    is_dynamic = models.BooleanField(verbose_name=_('Dynamic zone'), help_text="""Check to mark this zone as dynamic. An API key will be generated for you so as to be able to update the A nd AAAA records IP addresses over HTTP.""")
    api_key = models.CharField(max_length=64, null=True, verbose_name=_('API Key'), help_text="""The API key is generated automatically. To reset it, use the relevant action in the changelist view.""")
    date_modified = models.DateTimeField(auto_now=True, verbose_name=_('Last Modified'))
    
    class Meta:
        db_table = 'dynamiczones'
        verbose_name = _('dynamic zone')
        verbose_name_plural = _('dynamic zones')
        get_latest_by = 'date_modified'
        ordering = ['-domain']
        
    def __unicode__(self):
        return self.domain.name
    
    def save(self, *args, **kwargs):
        """Saves the instance to the database.
        
        If ``is_dynamic`` has been enabled and if ``api_key`` is empty,
        then generate a new API key. If ``api_key`` is not empty, do nothing.
        
        If ``is_dynamic`` is not enabled, always set ``api_key`` to NULL.
        
        """
        if self.is_dynamic:
            if not self.api_key:
                self.api_key = generate_api_key()
        else:
            self.api_key = None
        
        return super(DynamicZone, self).save(*args, **kwargs)



class ZoneTemplate(models.Model):
    """Model for zone templates."""
    name = models.CharField(max_length=100, verbose_name=_('name'), help_text="""Enter a name for the template.""")
    content = models.TextField(blank=True, null=True, verbose_name=_('content'), help_text="""Enter the template content. The placeholder #origin# is expanded to the origin of the zone to which the template is applied.""")
    notes = models.TextField(blank=True, null=True, verbose_name=_('notes'), help_text="""Space for notes about the template.""")
    
    date_modified = models.DateTimeField(auto_now=True, verbose_name=_('Last Modified'))
    created_by = models.ForeignKey(AUTH_USER_MODEL, related_name='%(app_label)s_%(class)s_created_by', verbose_name=_('template creator'), help_text="""The Django user this template belongs to.""")
    
    class Meta:
        db_table = 'zonetemplates'
        verbose_name = _('template')
        verbose_name_plural = _('templates')
        get_latest_by = 'date_modified'
        ordering = ['name', 'date_modified']
        unique_together = (
            ('name', 'created_by'),
        )
        
    def __unicode__(self):
        return self.name


