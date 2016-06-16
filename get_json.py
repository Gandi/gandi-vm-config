#!/usr/bin/python

import json
import os
import sys
from socket import inet_pton, AF_INET

configfile = '/gandi/config'


def help_():
    print("Usage: %s (need_dhcp_config|help)" % sys.argv[0])
    print("\t- help: this help")
    print("\t- need_dhcp_config: need to call the DHCP client")


def need_dhcp_config(file_, ifaceid):
    """ Detect if the interface is IPv4 enable and need DHCP configuration """
    with open(file_, 'r') as jsonfile:
        content = json.load(jsonfile)
    vifs = [vif for vif in content['vif'] if vif['vif_number'] == ifaceid]
    if not vifs:
        return False
    ipv6_only = is_ipv6_only(content)
    return not ipv6_only or False


def is_ipv6_only(conf):
    """ if no network interface has IPv4 configuration """
    vifs = conf.get('vif', {})
    for vif in vifs:
        for elt in vif['pna']:
            # we also need to know if the IP address is an IPv6 and we check
            # with both subnet of Gandi (another dirty detection)
            netw = elt['pbn']['pbn_network'].split('/')[0]
            if valid_ipv4(elt['pbn']['pbn_gateway']) and \
               valid_ipv4(netw):
                return False
    return True


def valid_ipv4(addr):
    """ is this addr an IPv4 or IPV6 ? """
    try:
        inet_pton(AF_INET, addr)
    except Exception:
        return False
    return True


if __name__ == '__main__':
    if len(sys.argv) > 1:
        if sys.argv[1] == 'need_dhcp_config':
            ifaceid = 0
            if sys.argv[2]:
                ifaceid = sys.argv[2]
            if os.path.exists(configfile):
                if need_dhcp_config(configfile, ifaceid):
                    sys.exit(0)
                else:
                    sys.exit(1)
            else:
                print('Configuration file is not present: %s' % configfile)
                sys.exit(2)
        if sys.argv[1] == 'help':
            help_()
