#!/bin/bash

# script called when an ethernet virtual interface is attached
# (action 'add') or detached (action 'remove') from a virtual 
# machine.

umask 022 

[ -f /etc/gandi/plugins-lib ] && . /etc/gandi/plugins-lib || exit 1
load_config

export PATH=$PATH:/sbin
IP=/bin/ip
[ ! -x $IP ] && IP=$(which ip)

remove_defaults_route() {
    # first param is the current iface we try to configure
    # We check for 11 network interfaces but the VM should only have
    # four iface maximum.
    gw_dev="eth0"
    for i in `seq 0 10`; do
        if $IP -4 addr show dev eth${i} | grep "inet .*brd" | \
          grep -E -q -v 'inet (10\.|127\.0|224\.0|192\.168\.|172\.1[6-9]\.|172\.2[0-9]\.|172.3[0-1]\.)'; then
            gw_dev="eth${i}"
            break
        fi
    done

    $IP -4 route list exact default | grep -v "dev $gw_dev" | while read elt; do
        $IP -4 route del $elt
    done
}

stop_dhcp_client() {
    for file_ in dhclient.$1.pid dhclient-$1.pid dhclient.pid; do
        if [ -f /var/run/$file_ ]; then
            dhpid=$(cat /var/run/$file_)
            if [ "o$dhpid" != "o" ]; then
                if (ps -eo pid,cmd | grep "$dhpid" | grep -v grep | grep -q "$1"); then
                    kill "$dhpid" && rm -f "/var/run/$file_"
                fi
            fi
        fi
    done

    # for all the other cases of running dhclient on the interface
    pkill -9 -f "dhclient.*$1"
}

iface_link_up() {
    # fix for 3.2-xenU kernel

    # try to flag the network interface up
    # if unsuccessful, we wait 3 seconds
    $IP link set $1 up > /dev/null 2>&1
    if [ $? -gt 0 ]; then
        sleep 2
        $IP link set $1 up > /dev/null 2>&1
    fi
}

iface_up() {
    # When the iface is IPv6 only, no need to start the DHCP client and
    # wait for a couple of seconds.

    # for now, iface name has a pattern ethX
    iface_num=`echo "$1" | sed -e 's/eth//'`

    # if DHCP is mandatory (0) or if the network iface is not defined in the
    # configuration file available at boot time (3).
    /usr/share/gandi/get_json.py need_dhcp_config $iface_num
    dhcp_code=$?
    if [ 0 -eq $dhcp_code ] || [ 3 -eq $dhcp_code ]; then
        rm -f /var/lib/dhclient.eth0.leases /var/lib/dhclient.leases
        if [ -x /usr/bin/systemctl ]; then
            # systemd-udev put the script in a sandbox so we can't call
            # dhclient directly.
            /usr/bin/systemctl --no-block start "gandi-dhclient@$1.service"
        else
            dhbin="/sbin/dhclient"
            [ -x /usr/sbin/dhclient ] && dhbin="/usr/sbin/dhclient"
            $dhbin -1 -q -pf "/var/run/dhclient.$1.pid" "$1"
            stop_dhcp_client "$1"
        fi
    fi

    if [ -e /sys/module/virtio_net ] && [ $CONFIG_MULTIQUEUE -eq 1 ]; then
        virtio_config $1
    fi

    remove_defaults_route
}

virtio_config() {
    # $1 is virtual interface to setup
    nb_proc=`grep -c processor /proc/cpuinfo`
    [ $nb_proc -gt 8 ] && nb_proc=8
    [ $nb_proc -gt 1 ] && ethtool -L $1 combined $nb_proc
}

sysctl_call() {
    # $1 is patch of sysctl key and $2 is the value
    sysctl -q -w "$1=$2" 
    if [ $? -ne 0 ]; then
        echo "Error when setting $1 with $2" | logger -t gandi
    fi
}

sysctl_config() {
    # $1 is the network interface name
    if [ "$1" != 'eth0' ]; then
        # set the ARP behavior when additionnal iface are set
        sysctl_call "net.ipv4.conf.$1.arp_announce" 2
        sysctl_call "net.ipv4.conf.$1.rp_filter" 0
        sysctl_call "net.ipv4.conf.$1.arp_filter" 0
    fi
}

if [ -z "$INTERFACE" ]; then
        echo Interface is not defined.
        exit 1
fi

case "$ACTION" in
    "add")
        NODHCP=$CONFIG_NODHCP
        iface_link_up "${INTERFACE}"
        if [ "$CONFIG_NODHCP" = "${NODHCP/$INTERFACE/}" ]; then 
            echo "Setup of $INTERFACE" | logger -t gandi
            iface_up "${INTERFACE}"
            sysctl_config "${INTERFACE}"

            if [ -e "$GANDI_HOOK_DIR"/post-iface-attach ]; then
                "$GANDI_HOOK_DIR"/post-iface-attach
            fi
        fi
    ;;
    "remove")
        echo "Removing of $INTERFACE" | logger -t gandi
        # nothing to do
    ;;
esac

exit 0

# vim:et:sw=4:ts=4:sta:tw=79:fileformat=unix
