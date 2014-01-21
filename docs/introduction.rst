
============
Introduction
============

This section contains an introduction to *django-powerdns-manager*, including general
information about how to submit bug reports and make feature requests.

django-powerdns-manager is a web based PowerDNS_ administration panel.

.. _PowerDNS: http://www.powerdns.com

Licensed under the *Apache License version 2.0*. More licensing information
exists in the license_ section.

.. warning::

   *django-powerdns-manager* should be considered **work in progress**.
   Until the first stable release is out, changes to the database schema and
   the supported features may occur without notice and without the provision
   of migration instructions or scripts.
   
   Please, do not use this software in production.
   
   As soon as the first stable release is out, backwards compatibility will be
   preserved and release notes containing migration instructions will be
   published in future releases.
   
   If you still need to use this software in production, you are on your own.
   In such a case, it is recommended to pick a release that works for you and
   stick to it without upgrading, until the first final version is out.


Features
========

- Web based administration interface based on the *admin* Django app.
- Easy management of all records of a zone from a single web page.
- Support for multiple users.
- Database schema is DNSSEC enabled.
- Automatic zone-rectify support, including support for empty non-terminals,
  using native python code.
- The application can be configured to support a user-defined subset of the
  resource records supported by PowerDNS and customize the order in which they
  appear in the administration panel.
- Zone cloning (experimental).
- Zone transfers between users.
- Zone file import through web form.
- Zone file export.
- Basic zone templates.
- Command-line interfaces to import and export zones in bulk.
- Support for secure updating of dynamic IP addresses in A and AAAA records.
- Supports using a dedicated database to store the tables needed by PowerDNS.
  This database may use a different backend than the main database of the
  Django project.
- Contains demo project for quick start and experimentation.


Quickstart Guide
================

The distribution package of *django-powerdns-manager* contains an example
project that can help you check out the features of the software and also
quickly experiment with the source code.

Although, the example project has already been configured for you, there are
still some required steps before you are able to run it using the development
server. These steps are discussed in detail in the `Quickstart Guide`_.

.. _`Quickstart Guide`: http://pythonhosted.org/django-powerdns-manager/quickstart.html


Development
===========

The source code of this project is available at the following official repositories.

Main repository (*mercurial*)::

    https://bitbucket.org/gnotaras/django-powerdns-manager

Mirror repository (*git*)::

    https://github.com/gnotaras/django-powerdns-manager

Pull requests are welcome. Please note that it may take a long time before pull
requests are reviewed.


Donations
=========

This software is released as free-software and provided to you at no cost. However,
a significant amount of time and effort has gone into developing this software
and writing this documentation. So, the production of this software has not
been free from cost. It is highly recommended that, if you use this software
*in production*, you should consider making a donation_.

.. _donation: http://bit.ly/19kIb70


Documentation
=============

Apart from the `django-powerdns-manager Online Documentation`_, more information about the
installation, configuration and usage of this application may be available
at the project's wiki_.

.. _`django-powerdns-manager Online Documentation`: http://packages.python.org/django-powerdns-manager
.. _wiki: http://www.codetrax.org/projects/django-powerdns-manager/wiki


Bugs and feature requests
=========================

In case you run into any problems while using this application or think that
a new feature should be implemented, it is highly recommended you submit_ a new
report about it at the project's `issue tracker`_.

Using the *issue tracker* is the recommended way to notify the authors about
bugs or make feature requests. Also, before submitting a new report, please
make sure you have read the `new issue guidelines`_.

.. _submit: http://www.codetrax.org/projects/django-powerdns-manager/issues/new
.. _`issue tracker`: http://www.codetrax.org/projects/django-powerdns-manager/issues
.. _`new issue guidelines`: http://www.codetrax.org/NewIssueGuidelines


Support
=======

CodeTRAX does not provide support for django-powerdns-manager.

You can still get community support at the `Community Support Forums`_:

.. _`Community Support Forums`: http://www.codetrax.org/projects/django-powerdns-manager/boards


License
=======

Copyright 2012 George Notaras <gnot [at] g-loaded.eu>

Licensed under the *Apache License, Version 2.0* (the "*License*");
you may not use this file except in compliance with the License.

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

A copy of the License exists in the product distribution; the *LICENSE* file.
For copyright and other important notes regarding this release please read
the *NOTICE* file.
