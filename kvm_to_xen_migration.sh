#!/bin/sh

# This script installs a kernel and grub, and configures grub and the
# console such that the VM can reboot on Xen without any other update
# needed.

console=hvc0
error=1

if which lsb_release >/dev/null; then
    release=$(lsb_release -r -s)
    id=$(lsb_release -i -s)
    codename=$(lsb_release -c -s)
    error=0
elif [ -f /etc/os-release ]; then
    id=$(grep "^ID=" /etc/os-release | cut -c 4-)
    version_id=$(grep "^VERSION_ID=" /etc/os-release | cut -c 13- | cut -c -1)
    if [ "8" = "${version_id}" ] && [ "debian" = ${id} ]; then
        release="8"
        codename="jessie"
        error=0
    elif [ \"centos\" = "${id}" ]; then
        release="7"
        codename="centos"
        id=centos
        error=0
    fi
fi

if [ 1 = ${error} ]; then
    echo "we cannot detect your operating system, and thus cannot configure"
    echo "your system properly. Please open a support ticket with your"
    echo "configuration and they will help you upgrading your system."
    exit 1
fi

if [ "14.04" = "${release}" ]; then
    apt-get update
    DEBIAN_FRONTEND=noninteractive apt-get install -y -q linux-image-generic grub2-common

    if [ -f /etc/init/ttyS0.conf ]; then
        sed -i "s/ttyS0/${console}/" /etc/init/ttyS0.conf
        mv -f /etc/init/ttyS0.conf "/etc/init/${console}.conf"
    fi
elif [ "Debian" = "${id}" ] || [ "debian" = "${id}" ]; then
    apt-get update
    DEBIAN_FRONTEND=noninteractive apt-get install -y linux-image-amd64 grub-efi

    if [ -f /etc/inittab ]; then
        if grep ttyS0 /etc/inittab >/dev/null; then
            sed -i "s/ttyS0/${console}/" /etc/inittab
        fi
    fi
fi

if [ "centos" = "${id}" ]; then
    if [ ! -f /etc/default/grub ]; then
        cat << EOF > /etc/default/grub
GRUB_DEFAULT=0
GRUB_HIDDEN_TIMEOUT=0
GRUB_HIDDEN_TIMEOUT_QUIET=true
GRUB_TIMEOUT=0
GRUB_DISTRIBUTOR=CentOS
GRUB_CMDLINE_LINUX_DEFAULT="console=hvc0 nomce loglevel=5 net.ifnames=0 selinux=1 enforcing=0"
GRUB_CMDLINE_LINUX=""
GRUB_GFXPAYLOAD_LINUX=text
GRUB_TERMINAL=console
EOF
    else
        echo "we detected grub on your system, and thus we cannot configure"
        echo "your system properly. Please open a support ticket with your"
        echo "configuration and they will help you upgrading your system."
        exit 1
    fi

    yum install -y kernel
    yum install -y grub2-efi grub2-tools

    sed -i 's/#add_drivers+=""/add_drivers+="xen-blkfront xen-netfront"/' /etc/dracut.conf

    grub2-mkconfig -o /boot/grub/grub.cfg

    kernel=$(rpm -q --qf %{PROVIDEVERSION} kernel)
    mkinitrd --force /boot/initramfs-${kernel}.x86_64.img ${kernel}.x86_64

else

    if [ "16.04" = "${release}" ]; then
        sed -i "s/ttyS0/${console}/" /etc/default/grub
        sed -i 's,GRUB_CMDLINE_LINUX=",GRUB_CMDLINE_LINUX="nomce root=/dev/xvda1 ,' /etc/default/grub
    else
        sed -i 's,GRUB_CMDLINE_LINUX=",GRUB_CMDLINE_LINUX="nomce root=/dev/xvda1 console=hvc0 ,' /etc/default/grub
    fi

    update-grub2
fi

f_='/etc/securetty'
if [ -f "${f_}" ]; then
    if ! grep "${console}" "${f_}" > /dev/null; then
        echo "${console}" >> "${f_}"
    fi
fi
