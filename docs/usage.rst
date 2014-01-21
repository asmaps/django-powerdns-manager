
=====
Usage
=====

This section contains information, including examples, about how to use
*django-powerdns-manager* in your existing Django projects or applications.


Using the Web Administration Interface
======================================

*django-powerdns-manager* uses the *admin* Django app to provide an
administration interface. The layout is that of a typical Django project.

All resource records, domain metadata and crypto keys that belong to a specific
zone are managed from a single web page.

Here are some guidelines when entering DNS data::

- All hostnames must be FQDN and should be entered without a trailing dot.
- TTL and other time information should be entered in seconds.
- Strings, for instance in TXT records, must not be enclosed in double quotes.
 

Concept of Dynamic Zones
========================

Apart from updating records using the DNS UPDATE query, *django-powerdns-manager*
supports updating the IP address of A and AAAA records over HTTP.

For this to happen it is mandatory to add the zone to the Dynamic Zones table.
Once a reference for a zone is in that table, an API key will be generated,
which can be used to get authorization to update A and AAAA records over HTTP.

TODO

IP Updates over HTTP
====================

Supported arguments

``api_key``
    Should be equal to the generated API key that exists in the zone record
    in the DynamicZones table. *Mandatory* - no default.
``hostname``
    Should contain the hostname of the A or AAAA record you want to update.
    This is an *optional* setting. If omitted, all A and AAAA records of the
    zone are updated, if an IP address is provided or guessed.
``ipv4``
    Should contain an IPv4 address. This is *optional*. If omitted, the
    remote client's IP address, if it is an IPv4 address, is used.
``ipv6``
    Should contain an IPv6 address. This is *optional*. If omitted, the
    remote client's IP address, if it is an IPv6 address, is used.
    
Example request using ``curl``::

    curl -k \
        -F "api_key=UBSE1RJ0J175MRAMJC31JFUH" \
        -F "hostname=ns1.centos.example.org" \
        -F "ipv4=10.1.2.3" \
        -F "ipv6=3ffe:1900:4545:3:200:f8ff:fe21:67cf" \
        https://192.168.0.101/powerdns/zone/update/

TODO


Import zone files
=================

To import by pasting zonefile data::

    https://192.168.0.101/powerdns/import/zonefile/

To import by using ACFR query::

    https://192.168.0.101/powerdns/import/axfr/

TODO


Export zone files
=================

Visit::

    https://192.168.0.101/powerdns/export/domain.tld/
    
Replace ``domain.tld`` with the zone origin you want to export.

TODO


Zone Cloning
============

Select the zone to clone from the zone list and select the 'Clone the selected
zone action'

TODO
 

