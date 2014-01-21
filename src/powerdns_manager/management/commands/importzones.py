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

import os
import sys
from optparse import make_option

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model

from powerdns_manager.utils import process_zone_file



class Command(BaseCommand):
    
    help = 'Import zone files.'
    args = 'zonefile1 zonefile2 ...'
    requires_model_validation = False
    
    option_list = BaseCommand.option_list + (
        #make_option('-d', '--directory', action='store', dest='directory', metavar="PATH",
        #    help='TODO'),
        make_option('-u', '--user', action='store', dest='username', metavar="USERNAME",
            help='Set the username of the owner of the domain (optional).'),
        make_option('-o', '--overwrite', action='store_true', dest='overwrite',
            help='Overwrite existing zones.'),
    )
    
    def handle(self, *zonefiles, **options):
        overwrite = options.get('overwrite')
        verbosity = int(options.get('verbosity', 1))

        # Determine owner
        User = get_user_model()
        try:
            owner = User.objects.get(username=options.get('username'))
        except User.DoesNotExist:
            owner = None

        # Process zonefiles
        for zonefile in zonefiles:
            if os.path.isfile(zonefile):
                f = open(zonefile, 'r')
                data = f.read()
                f.close()
                try:
                    process_zone_file(None, data, owner, overwrite=overwrite)
                except Exception, e:
                    sys.stderr.write('error: %s: %s\n' % (str(e), zonefile))
                    sys.stderr.flush()
                else:
                    if verbosity:
                        sys.stdout.write('success: %s\n' % zonefile)
                        sys.stdout.flush()

