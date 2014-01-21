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

import os
import sys
from optparse import make_option

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model

from powerdns_manager.utils import process_axfr_response



class Command(BaseCommand):
    
    help = 'Import zone using AXFR query.'
    args = 'domain1 domain2 ...'
    requires_model_validation = False
    
    option_list = BaseCommand.option_list + (
        make_option('-n', '--nameserver', action='store', dest='nameserver', metavar="HOSTNAME or IP",
            help='Set the hostname or IP address of the nameserver to contact.'),
        make_option('-d', '--domainfile', action='store', dest='domainfile', metavar="PATH",
            help='The path of text file containing domain names to import. File format is one domain per line.'),
        make_option('-u', '--user', action='store', dest='username', metavar="USERNAME",
            help='Set the username of the owner of the domain (optional).'),
        make_option('-o', '--overwrite', action='store_true', dest='overwrite',
            help='Overwrite existing zones.'),
    )
    
    def handle(self, *arg_domains, **options):
        nameserver = options.get('nameserver')
        domainfile = options.get('domainfile')
        overwrite = options.get('overwrite')
        verbosity = int(options.get('verbosity', 1))
        
        if not nameserver:
            raise CommandError('error: nameserver is required')
        elif domainfile and not os.path.isfile(domainfile):
            raise CommandError('error: Expected path to file')
        elif not arg_domains and not domainfile:
            raise CommandError('error: Missing domain')
        
        # Domains may exist as args (arg_domains) or contained in the domainfile.
        # Create a list containing all domains.
        domains = []
        for d in arg_domains:
            domains.append(d)
        if domainfile:
            f = open(domainfile, 'rb')
            domains.extend( [line.strip() for line in f.readlines() if line.strip()] )
            f.close()
        
        # Determine owner
        User = get_user_model()
        try:
            owner = User.objects.get(username=options.get('username'))
        except User.DoesNotExist:
            owner = None
        
        # Process domains
        for domain in domains:
            try:
                process_axfr_response(domain, nameserver, owner, overwrite=overwrite)
            except Exception, e:
                sys.stderr.write('error: %s: %s\n' % (str(e), domain))
                sys.stderr.flush()
            else:
                if verbosity:
                    sys.stdout.write('success: %s\n' % domain)
                    sys.stdout.flush()

