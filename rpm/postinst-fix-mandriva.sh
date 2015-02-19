#!/bin/sh

if [ -f /etc/mandrake-release ]; then
    mdkversion=$(cat /etc/mandrake-release)
    ret=$(expr match "$mdkversion" "Mandriva Linux release 2")
    
    if [ $ret -ge 16 ]; then
            sed -e 's/^# chkconfig: .*$/# chkconfig: - 13 87/g' \
                /etc/init.d/gandi-mount > /etc/init.d/gandi-mount.new
            chown --reference=/etc/init.d/gandi-mount \
                /etc/init.d/gandi-mount.new
            chmod --reference=/etc/init.d/gandi-mount \
                /etc/init.d/gandi-mount.new
            [ 0 -eq $? ] && mv -f /etc/init.d/gandi-mount.new \
                /etc/init.d/gandi-mount
    fi
fi
