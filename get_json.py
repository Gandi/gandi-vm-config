#!/usr/bin/python

import json
import os
import sys
from socket import inet_pton, AF_INET

configfile = '/gandi/config'


def help_():
    print("Usage: %s (need_dhcp_config <num>|help)" % sys.argv[0])
    print("\t- help: this help")
    print("\t- need_dhcp_config <num>: need to call the DHCP client on the")
    print("\t     network interface number <num> in the system.")


def need_dhcp_config(file_, ifaceid):
    """
    Detect if the interface is IPv4 enable and need DHCP configuration
    Return: 0 is ok for DHCP call, 2 is not ok for DHCP, 3 for not found in the config
    """
    with open(file_, 'r') as jsonfile:
        content = json.load(jsonfile)
    vifs = [vif for vif in content['vif'] if vif['vif_number'] == int(ifaceid)]
    if len(vifs) == 0:
        return 3
    if is_ipv6_only(content):
         return 2
    return 0


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
            if len(sys.argv) > 2 and sys.argv[2]:
                ifaceid = sys.argv[2]
            if not os.path.exists(configfile):
                print('Configuration file is not present: %s' % configfile)
                sys.exit(1)
            sys.exit(need_dhcp_config(configfile, ifaceid))
        if sys.argv[1] == 'help':
            help_()
