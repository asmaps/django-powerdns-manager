
=========================================
Quick start - Running the example project
=========================================

This section contains information, about how to use the example Django project,
which ships with the distribution package, in order to quickly test the
features of *django-powerdns-manager*.

.. warning::

   The example project has been configured for testing and debugging,
   therefore it should only be used for such purposes. Please, do not
   use the example project in production.
   
The example Django project has been configured to use two SQLite databases,
*default* (``main.db``), which is the main database for the Django project,
and *powerdns* (``powerdns.db``), which is the database where DNS data is stored.
DNS data can be perfectly stored to the *default* database, but separate
databases are used in this example project for demonstration purposes.
 
Consequently, PowerDNS has to be configured to use the SQLite backend in
order to be able to communicate with the managed database. A sample
configuration file for PowerDNS is included in the example directory.

The following instructions will guide you run the Django project's application
server and also run an instance of PowerDNS for testing purposes.

It is assumed that you have obtained a copy of *django-powerdns-manager*
and have changed to the ``example`` directory::
    
    hg clone https://bitbucket.org/gnotaras/django-powerdns-manager
    cd django-powerdns-manager/example/


Install required software
=========================

The recommended version of PowerDNS is 3.3.1.

Install the required software by following the operating system specific
instructions below.


Red Hat Enterprise Linux, CentOS and Fedora
-------------------------------------------

Install system packages::

    yum install pdns pdns-backend-sqlite sqlite python-sqlite2 python-virtualenv


Debian and Ubuntu
-----------------

Install system packages::

    apt-get install ...


Install Python modules
----------------------

.. note::

   Current directory is: ``django-powerdns-manager/example/``

It is highly recommended to use the ``virtualenv`` utility to create a virtual
environment, in which all Python module dependencies can be installed without
affecting the system-wide Python library. However, this step is completely
*optional*::
    
    virtualenv --system-site-packages testenv
    source testenv/bin/activate

Install the required Python modules in order to be able to run the example
*django-powerdns-manager* project and build this documentation::
    
    pip install -r ../requirements.txt


Populate the database
=====================

.. note::

   Current directory is: ``django-powerdns-manager/example/``

First, populate the Django project's database::

    python manage.py syncdb

You will be prompted to create a superuser. Create this user and take a note
of the username and password as this is what you will use to log into the
web based administration interface.

Finally, populate the dedicated django-powerdns-manager database::

    python manage.py syncdb --database=powerdns

Optional step: load the default 'PowerDNS Managers' group to make it easier to
to test the interface using multiple users::

    python manage.py loaddata default_pdns_groups


Start the PowerDNS server
=========================

.. note::

   Current directory is: ``django-powerdns-manager/example/``
   
The example project contains a configuration file for PowerDNS.

First, start the server in the **foreground** to check that everything is
working as expected::
    
    $ pdns_server --local-address=192.168.0.101 --config-dir=`pwd`
    Nov 02 11:42:33 Reading random entropy from '/dev/urandom'
    Nov 02 11:42:33 This is module gsqlite3 reporting
    Nov 02 11:42:33 This is a standalone pdns
    Nov 02 11:42:33 Listening on controlsocket in '/var/run/pdns.controlsocket'
    Nov 02 11:42:33 UDP server bound to 192.168.0.101:53
    Nov 02 11:42:33 TCP server bound to 192.168.0.101:53
    Nov 02 11:42:33 PowerDNS 3.1 (C) 2001-2012 PowerDNS.COM BV (Oct 22 2012, 04:10:24, gcc 4.4.6 20120305 (Red Hat 4.4.6-4)) starting up
    Nov 02 11:42:33 PowerDNS comes with ABSOLUTELY NO WARRANTY. This is free software, and you are welcome to redistribute it according to the terms of the GPL version 2.
    Nov 02 11:42:33 Creating backend connection for TCP
    Nov 02 11:42:33 gsqlite3: connection to 'powerdns.db' successful
    Nov 02 11:42:33 gsqlite3: connection to 'powerdns.db' successful
    Nov 02 11:42:33 About to create 3 backend threads for UDP
    Nov 02 11:42:33 gsqlite3: connection to 'powerdns.db' successful
    Nov 02 11:42:33 gsqlite3: connection to 'powerdns.db' successful
    Nov 02 11:42:33 gsqlite3: connection to 'powerdns.db' successful
    Nov 02 11:42:33 gsqlite3: connection to 'powerdns.db' successful
    Nov 02 11:42:33 gsqlite3: connection to 'powerdns.db' successful
    Nov 02 11:42:33 gsqlite3: connection to 'powerdns.db' successful
    Nov 02 11:42:33 Done launching threads, ready to distribute questions

``--local-address=192.168.0.101`` is used to make PowerDNS bind on the network
interface with IP ``192.168.0.101``. Set this according to your network
configuration or omit this option completely to make PowerDNS bind on all
available network interfaces.

.. note::

    If you try to run the server as an unprivileged user, you will probably
    encounter permission issues. In such a case, you can bind PowerDNS to a
    port number greater than 1024 and also instruct it to create its
    control socket in the current directory. For example::
    
        pdns_server --local-address=192.168.0.220 --local-port=5353 --config-dir=`pwd` --socket-dir=`pwd`

The output above indicates that everything is running fine, so stop this
process by pressing ``Ctrl-C`` and start PowerDNS in the **background** by adding
``--daemon`` to the command line arguments. For example::

    pdns_server --daemon --local-address=192.168.0.101 --config-dir=`pwd`

.. note::

    To kill the background server at any time invoke the command::

        killall pdns_server
    

Start the PowerDNS Manager application server
=============================================

.. note::

   Current directory is: ``django-powerdns-manager/example/``


Start the internal Django HTTP server::

    python manage.py runserver 192.168.0.101:9999


Visit the administration interface
==================================

Use your browser to visit::

    http://192.168.0.101:9999/admin/


Other notes
===========

After you have finished testing *django-powerdns-manager* and only if you had
used ``virtualenv``, it is now time to deactivate the virtual Python environment.
Run the following command::

    deactivate

