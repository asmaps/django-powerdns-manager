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
from django.db.models.loading import cache

from powerdns_manager.utils import generate_zone_file



class Command(BaseCommand):
    
    help = 'Export zone files.'
    args = 'origin1 origin2 ...'
    requires_model_validation = False
    
    option_list = BaseCommand.option_list + (
        make_option('-d', '--directory', action='store', dest='directory', metavar="PATH",
            help='Directory where zone files should be stored.'),
        make_option('-a', '--all', action='store_true', dest='all',
            help='Export all zones.'),
    )
    
    def handle(self, *origins, **options):
        outdir = os.path.abspath(options.get('directory'))
        export_all = options.get('all')
        verbosity = int(options.get('verbosity', 1))
        
        if export_all and len(origins) > 0:
            raise CommandError('No origins should be specified when the --all switch is used.')
        
        Domain = cache.get_model('powerdns_manager', 'Domain')
        if export_all:
            origins = [d.name for d in Domain.objects.all()]
        
        for origin in origins:
            try:
                data = generate_zone_file(origin)
            except Domain.DoesNotExist:
                sys.stderr.write('error: zone not found: %s\n' % origin)
                sys.stderr.flush()
            else:
                path = os.path.join(outdir, '%s.zone' % origin)
                f = open(path, 'w')
                f.write(data)
                f.close()
                if verbosity:
                    sys.stdout.write('success: %s\n' % origin)
                    sys.stdout.flush()

