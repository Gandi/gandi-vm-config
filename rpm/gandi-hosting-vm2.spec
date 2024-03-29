# SPEC file for gandi-hosting-vm2
# Source file is generated by make tarball-for-rpm in the gandi-hosting-vm2
# svn default repository svn/infra/hosting/gandi-hosting-vm2

%define name    gandi-hosting-vm2
%define version 1.2
%define release 1
%define sourcedir    %{_topdir}/BUILD/%{name}-%{version}

Name:           %{name} 
Summary:        Script for GANDI hosting virtual machine.
Version:        %{version} 
Release:        %{release} 
Source0:        %{name}-%{version}.tar.bz2
URL:            http://www.gandi.net/hosting/ 
License:        Gandi License
BuildArch:      noarch
Group:          System/Configuration 
BuildRoot:      %{_tmppath}/%{name}-%{version}-%{release}-buildroot 
Requires:       openssl, udev, acpid, sed
Provides:       gandi-hosting-vm, gandi-hosting-agent
Obsoletes:      gandi-hosting-vm <= 1.1 , gandi-hosting-agent <= 1.1

%description
Collection of script to handle dynamic resources of virtual
machine on Gandi IaaS hosting solution. most configuration
is done during the first and subsequent boot.

services:
 - gandi-postboot: execute customer scrip to setup the virtual machine.
 - gandi-config: configure the system during boot
 - gandi-mount  : if virtual disk is not detected and already mounted,
   this service start a udev call to re-attach all available unmounted
   virtual disks.

In case of GPT partition on disk, you should install gdisk to
handle the partitions.

%prep 
%setup -q

%install
# $(SRCDIR) by %{sourcedir}
# $(DESTDIR) by $RPM_BUILD_ROOT

# only cp and mkdir here; script and link are done in the %post section
rm -rf $RPM_BUILD_ROOT
mkdir -p $RPM_BUILD_ROOT/etc/gandi
cp -raf %{sourcedir}/etc/gandi	$RPM_BUILD_ROOT/etc/

install -d -m 0755 $RPM_BUILD_ROOT/usr/share/gandi
cp -raf %{sourcedir}/usr/share/gandi/systemd \
    $RPM_BUILD_ROOT/usr/share/gandi/
cp -raf %{sourcedir}/usr/share/gandi/bootstrap.d \
    $RPM_BUILD_ROOT/usr/share/gandi/

install -m 0750 %{sourcedir}/usr/share/gandi/get_json.py \
    $RPM_BUILD_ROOT/usr/share/gandi/
install -m 0750 %{sourcedir}/usr/share/gandi/kvm_to_xen_migration.sh \
    $RPM_BUILD_ROOT/usr/share/gandi/

mkdir -p $RPM_BUILD_ROOT/etc/init.d
install -m 0755 %{sourcedir}/etc/init.d/gandi-config \
    $RPM_BUILD_ROOT/etc/init.d
install -m 0755 %{sourcedir}/etc/init.d/gandi-postboot \
    $RPM_BUILD_ROOT/etc/init.d
install -m 0755 %{sourcedir}/etc/init.d/gandi-bootstrap \
    $RPM_BUILD_ROOT/etc/init.d
install -m 0755 %{sourcedir}/etc/init.d/gandi-mount \
    $RPM_BUILD_ROOT/etc/init.d

mkdir -p $RPM_BUILD_ROOT/etc/sysconfig
install -m 0644 %{sourcedir}/etc/sysconfig/gandi \
    $RPM_BUILD_ROOT/etc/sysconfig/

mkdir -p $RPM_BUILD_ROOT/etc/udev/rules.d
cp -raf %{sourcedir}/etc/udev/rules.d/	$RPM_BUILD_ROOT/etc/udev/

mkdir -p $RPM_BUILD_ROOT/lib/udev/rules.d/
cp -raf %{sourcedir}/lib/udev/ $RPM_BUILD_ROOT/lib/

mkdir -p $RPM_BUILD_ROOT/etc/pki/rpm-gpg
cp -af %{sourcedir}/etc/pki/rpm-gpg/RPM-GPG-KEY-Gandi $RPM_BUILD_ROOT/etc/pki/rpm-gpg/

install -d -m 0755 $RPM_BUILD_ROOT/usr/lib/sysctl.d/
install -m 0644 %{sourcedir}/usr/lib/sysctl.d/90-gandi.conf \
    $RPM_BUILD_ROOT/usr/lib/sysctl.d/90-gandi.conf

#mkdir -p $RPM_BUILD_ROOT/etc/auto.master.d
#cp -af %{sourcedir}/etc/auto.master.d/gandi.autofs $RPM_BUILD_ROOT/etc/auto.master.d/
#cp -af %{sourcedir}/etc/auto.gandi $RPM_BUILD_ROOT/etc

%preun
#
# --- %preun ---
# 
# only in case of uninstall of package.
SYSTEMD=$(which systemd)
if [ "$1" -eq 0 ]; then
    for elt in mount config bootstrap postboot dhclient@; do
        if [ -e $SYSTEMD ]; then
            rm -f "/etc/systemd/system/default.target.wants/gandi-$elt"
            rm -f "/lib/systemd/system/gandi-$elt"
        fi

        if [ -x /sbin/chkconfig ]; then
            /sbin/chkconfig "gandi-$elt" off || \
                /sbin/chkconfig --del "gandi-$elt" || true
        fi
    done
fi
#
# --- End of %preun ---
#


# we use %posttrans has it is the last section to be called in the rpm update
# process
%posttrans
#
# --- %posttrans ---
#

# cleaning old service
find /etc/rc* -type l -iname "*gandi-kernel*" -delete

# Runlevel S is only for single, fallback to rc2 rc3 rc5 
if [ -e /etc/SuSE-release ] || [ -e /etc/centos-release ]; then
    for elt in config mount postboot bootstrap; do
        tempfile=$(mktemp --suffix gnd)
        sed -e 's/^# Default-Start:.*S/# Default-Start:\t2 3 5/g' \
            /etc/init.d/gandi-$elt > "$tempfile"
        chown --reference=/etc/init.d/gandi-$elt \
            "$tempfile"
        chmod --reference=/etc/init.d/gandi-$elt \
            "$tempfile"
        [ 0 -eq $? ] && mv -f "$tempfile" \
            /etc/init.d/gandi-$elt
        rm -f "$tempfile"
    done
fi

# When using systemd, udev depends is not available, fallback to boot.udev
if [ -e $SYSTEMD ]; then
    for elt in mount bootstrap; do
        initscript=/etc/init.d/gandi-$elt
        tempfile=$(mktemp --suffix gnd)
        sed -e "s,\(^# X-Start-After:.*\)udev,\1 boot.udev,g" \
            -e "s,\(^# Required-Start:.*\)udev,\1 boot.udev,g" \
            "$initscript" > "$tempfile"
        if [ $? = 0 ]; then
            mv "$tempfile" "$initscript"
            chmod 0755 "$initscript"
            chown root:root "$initscript"
        fi
        rm -f "$tempfile" || true
    done
fi 

# Opensuse installs systemd scripts in "/usr/lib/systemd/system"
# instead of "/lib/systemd/system"
# so we install scripts in both path

# With regular systemd boot, we want to provide symlink to gandi service file
# in other case, we rely on regular rc-sysV script
if [ -e $SYSTEMD ]; then
    mkdir -p /etc/systemd/system/default.target.wants
    for elt in config mount postboot bootstrap; do
        rm -f "/lib/systemd/system/gandi-${elt}.service" || true
        rm -f "/usr/lib/systemd/system/gandi-${elt}.service" || true
        rm -f "/etc/systemd/system/default.target.wants/gandi-${elt}.service" \
            || true
        srcfile="/usr/share/gandi/systemd/gandi-${elt}.service"
        if [ -e "$srcfile" ]; then
            ln -sf "$srcfile" /lib/systemd/system/ || true
            ln -sf "$srcfile" /usr/lib/systemd/system/ || true
            ln -sf "/lib/systemd/system/gandi-${elt}.service" \
                   /etc/systemd/system/default.target.wants/ || true
            ln -sf "/usr/lib/systemd/system/gandi-${elt}.service" \
                   /etc/systemd/system/default.target.wants/ || true
        fi
    done
    srcfile="/usr/share/gandi/systemd/gandi-dhclient@.service"
    if [ -e "$srcfile" ]; then
        ln -sf "$srcfile" /lib/systemd/system || true
        ln -sf "$srcfile" /usr/lib/systemd/system || true
    fi
else
    if [ -x /sbin/chkconfig ]; then
        for elt in config mount postboot bootstrap; do
            /sbin/chkconfig "gandi-$elt" off || \
                /sbin/chkconfig --del "gandi-$elt" || true
            /sbin/chkconfig "gandi-$elt" on || true
        done
    else
        echo "Please enable Gandi services." | logger -t gandi
    fi
fi

sed -i -e 's,^gpgcheck=0,gpgcheck=1\ngpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-Gandi,g' /etc/yum.repos.d/Gandi-Base.repo

if [ -f /lib/udev/rules.d/gandi.rules ]; then
    mv /lib/udev/rules.d/gandi.rules /lib/udev/rules.d/gandi.disabled
fi

# remove old and obsolete plugins
rm -f /etc/gandi/plugins.d/04-config_network
rm -f /etc/gandi/plugins.d/06-vm-fix-cron
rm -f /etc/gandi/plugins.d/05-vm-fix-ext3
rm -f /etc/gandi/plugins.d/07-vm-fix-gandikey
rm -f /etc/gandi/plugins.d/07-timezone
rm -f /etc/gandi/plugins.d/09-config_timezone

# obsolete plugin in 1.2 version
rm -f /etc/gandi/plugins.d/04-config_local_network
rm -f /etc/gandi/plugins.d/05-config_hostname
rm -f /etc/gandi/plugins.d/06-config_nameserver
rm -f /etc/gandi/plugins.d/08-config_user_group
rm -f /etc/gandi/plugins.d/12-vm-fix-umask
rm -f /etc/gandi/plugins.d/15-misc
rm -f /etc/gandi/dhclient-exit-hooks
rm -f /etc/gandi/dhcp-postconf
rm -f /etc/gandi/dhcp-hostname
rm -f /etc/gandi/dhcp-hostname-static-net
rm -rf /etc/gandi/bootstrap.d

# obsolete plugins in gandi-hosting-vm2 version
rm -rf /etc/gandi/plugins.d/00-config_swap
rm -rf /etc/gandi/plugins.d/10-config_sysctl

#
# --- End of %posttrans ---
#


%clean 
rm -rf $RPM_BUILD_ROOT 


%files 
%doc changelog.gz
%defattr(0755,root,root) 
/etc/gandi/plugins.d
/etc/init.d/gandi-mount
/etc/init.d/gandi-postboot
/etc/init.d/gandi-bootstrap
/etc/init.d/gandi-config
/etc/gandi/manage_data_disk.py
/etc/gandi/manage_data_disk.sh
/etc/gandi/manage_iface.sh
/usr/share/gandi/bootstrap.d
/lib/udev/cpu_online
/lib/udev/manage_memory
/lib/udev/fake_blkid
/usr/share/gandi/get_json.py
/usr/share/gandi/kvm_to_xen_migration.sh
#/etc/auto.gandi
%config(noreplace) /etc/gandi/hooks/*
%defattr(0644,root,root)
%config(noreplace) /etc/sysconfig/gandi
%config /etc/udev/rules.d/86-gandi.rules
#%config /lib/udev/rules.d/gandi.rules
/etc/pki/rpm-gpg/RPM-GPG-KEY-Gandi
/etc/gandi/plugins-lib
/etc/gandi/sysctl.conf
/usr/lib/sysctl.d/90-gandi.conf
/usr/share/gandi/systemd/gandi-config.service
/usr/share/gandi/systemd/gandi-mount.service
/usr/share/gandi/systemd/gandi-postboot.service
/usr/share/gandi/systemd/gandi-bootstrap.service
/usr/share/gandi/systemd/gandi-dhclient@.service
/usr/share/gandi/systemd/gandi-sshdkeygen.service

%changelog 
* Fri Sep 19 2008 Nicolas Chipaux <aegiap@gandi.net> 1.0.0-1474-1gnd
- Bug fixing for packaging and scripts
