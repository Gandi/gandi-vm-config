#!/bin/sh

# This script installs a kernel and grub, and configures grub and the
# console such that the VM can reboot on Xen without any other update
# needed.

set -eu

console=hvc0

install_package_rpm () {
    if ! rpm -q $1 >/dev/null ; then
        yum install -y $1
    fi
}

install_package_deb () {
    if ! dpkg-query -W $1 >/dev/null ; then
        DEBIAN_FRONTEND=noninteractive apt-get install -y -q $1
    fi
}


if which lsb_release >/dev/null; then
    id=$(lsb_release -i -s | tr '[A-Z]' '[a-z]')
elif [ -f /etc/os-release ]; then
    id=$(grep "^ID=" /etc/os-release | cut -c 4- | tr -d '"')
else
    echo "We cannot detect your operating system, and thus cannot"
    echo "configure it properly. Please open a support ticket with your"
    echo "configuration and they will help you upgrading your system."
    exit 1
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
    fi

    install_package_rpm 'kernel'
    install_package_rpm 'grub2-tools'
    install_package_rpm 'grub2-efi'

    sed -i 's/#add_drivers+=""/add_drivers+="xen-blkfront xen-netfront"/' /etc/dracut.conf

elif [ "ubuntu" = "${id}" ]; then

    apt-get update
    install_package_deb 'grub2-common'
    install_package_deb 'linux-image-generic'

elif [ "debian" = "${id}" ]; then

    apt-get update
    install_package_deb 'grub-efi'
    install_package_deb 'linux-image-amd64'

else
    echo "We do not support you operating system. Please open a"
    echo "support ticket with your configuration and they will help"
    echo "you upgrading your system."
    exit 1
fi

if [ -f /etc/default/grub ]; then

    if ! grep -q '^GRUB_CMDLINE_LINUX=' /etc/default/grub; then
        echo "We cannot read your grub configuration. Please open a"
        echo "support ticket with your configuration and they will"
        echo "help you upgrading your system."
        exit 1
    fi

    # fix console
    if ! grep -q console=${console} /etc/default/grub; then
        if grep -q console=ttyS0 /etc/default/grub; then
            sed -i "s/ttyS0/${console}/" /etc/default/grub
        else
            sed -i 's,^GRUB_CMDLINE_LINUX="\(.*\)",GRUB_CMDLINE_LINUX="\1 console=hvc0",' /etc/default/grub
        fi
    fi

    # add nomce
    if ! grep -q nomce /etc/default/grub; then
        sed -i 's,^GRUB_CMDLINE_LINUX="\(.*\)",GRUB_CMDLINE_LINUX="\1 nomce",' /etc/default/grub
    fi

    # fix root
    if ! grep root=/dev/xvda1 /etc/default/grub | grep -q "^GRUB_CMDLINE"; then
        if grep root= /etc/default/grub | grep -q "^GRUB_CMDLINE"; then
            sed -i 's,root=\([a-zA-Z0-9/]*\),root=/dev/xvda1,' /etc/default/grub
        else
            sed -i 's,^GRUB_CMDLINE_LINUX="\(.*\)",GRUB_CMDLINE_LINUX="\1 root=/dev/xvda1",' /etc/default/grub
        fi
    fi

    if [ "centos" = "${id}" ]; then

        grub2-mkconfig -o /boot/grub/grub.cfg

        kernel=$(rpm -q --qf %{PROVIDEVERSION} kernel)
        output=$(mkinitrd --force /boot/initramfs-${kernel}.x86_64.img ${kernel}.x86_64 2>&1)
        if echo "${output}" | grep -qi "fail"; then
            printf "\n$(tput bold)$(tput setaf 9)WARNING:$(tput sgr0) we could not generate a ramdisk for kernel ${kernel}"
            printf "\n         This usually means the kernel does not have the xen drivers."
            printf "\n         Please be careful when rebooting as your system might not"
            printf "\n         boot properly with grub.\n"
        fi
    else
        update-grub2
    fi

else
    echo "we could not detect grub on your system, and thus we cannot"
    echo "configure your system properly. Please open a support"
    echo "ticket with your configuration and they will help you"
    echo "upgrading your system."
    exit 1
fi

if [ -f /etc/inittab ]; then
    if grep -q ttyS0 /etc/inittab; then
        sed -i "s/ttyS0/${console}/" /etc/inittab
    fi
fi

if [ -f /etc/init/ttyS0.conf ]; then
    sed -i "s/ttyS0/${console}/" /etc/init/ttyS0.conf
    mv -f /etc/init/ttyS0.conf "/etc/init/${console}.conf"
fi

if [ -f /etc/securetty ]; then
    if ! grep -q "${console}" /etc/securetty; then
        echo "${console}" >> /etc/securetty
    fi
fi

f_='/etc/fstab'
if [ -f "${f_}" ]; then
    if grep -qE '^[[:space:]]*/dev/sd[[:alpha:]][[:digit:]]* ' "${f_}"; then
        printf "\n$(tput bold)$(tput setaf 9)WARNING:$(tput sgr0) You MUST change your fstab before rebooting your VM or some disk"
        printf "\n         will fail to be mounted and boot will abort, allowing you only"
        printf "\n         to recover your VM with the console.\n"
    fi
    for d in $(egrep -o '^[[:space:]]*/dev/sd[[:alpha:]][[:digit:]]*' "${f_}") ; do
        device="$(echo ${d} | tr -d '[[:space:]]')"
        uuid=$(blkid -o value -s UUID "${device}")
        line=$(grep "$d" "${f_}")
        newline=$(echo "${line}" | sed -e "s,^[[:space:]]*${device},UUID=${uuid}\t,")
        printf "In the file /etc/fstab, replace:\n    ${line}\nwith:\n    ${newline}\n"
    done
fi

exit 0
