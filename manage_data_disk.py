#!/usr/bin/python3 -tt

import posix
import sys
import os
import re
import syslog
import subprocess

default_disk_root = '/srv'
default_mount_params = 'rw,nosuid,nodev,noatime'
default_allow_mount = 1
config_file = '/etc/default/gandi'
datadisk_root = ''
debug = False

if debug:
    from pprint import pprint


def load_mount_params(config_file):
    """ Load mount parameter from config file """
    return load_config_file(config_file,
                r'^CONFIG_MOUNT_PARAMS.?=([^ #]*)$',
                default_mount_params,
                'CONFIG_MOUNT_PARAMS')


def load_disk_root(config_file):
    """ Load disk root parameter from config file """
    return load_config_file(config_file,
                r'^CONFIG_DISK_ROOT.?=([^ #]*)$',
                default_disk_root,
                'CONFIG_DISK_ROOT')


def load_allow_mount(config_file):
    """ Load flag to enable or disable mount from config file """
    return load_config_file(config_file,
            r'^CONFIG_ALLOW_MOUNT.?=([^ #]*)$',
            default_allow_mount,
            'CONFIG_ALLOW_MOUNT')


def load_hook_dir(config_file):
    """ Load hook path parameter from config file """
    return load_config_file(config_file,
            r'^GANDI_HOOK_DIR.?=([^ #]*)$',
            default_allow_mount,
            'GANDI_HOOK_DIR')


def load_config_file(config_file, pattern, default_value, label):
    """ Load specific options from config_file"""
    params = default_value
    patternc = re.compile(pattern)

    if not os.path.exists(config_file):
        config_file = '/etc/sysconfig/gandi'

    try:
        for line in open(config_file, 'r'):
            match = patternc.search(line.rstrip(os.linesep))
            if match is not None:
                defined_value = match.group(1).strip('"')
                if defined_value != "":
                    params = defined_value
                else:
                    syslog.syslog("%s is empty. Using defaults : %s." %
                        (label, default_value))
    except IOError:
        print("warning : config file not found, using default params.")
        pass
    except Exception:
        raise

    return params


def run_command(label, cmd):
    """Run a command, log its output, return its exit code"""
    if debug:
        syslog.syslog('running %s (%s)' % (label, cmd,))
    command = subprocess.Popen(cmd, stderr=subprocess.PIPE,
                stdout=subprocess.PIPE, stdin=None,
                shell=True)
    # wait until the process has completed
    (output, error) = command.communicate()
    output = output.decode('utf-8')
    error = error.decode('utf-8')
    ret = command.returncode

    # read the stdout/stderr lines
    if ret is not None:
        syslog.syslog('%s [%s]: %s stderr=%s' % (label, cmd, output, error))
    else:
        # log the return code for easy debugging
        syslog.syslog('%s [%s]: returned %s' % (label, cmd, output))
    return ret


def pre_add(device, fs_type, mountpoint):
    """Try to resize a disk to its block size before mount,
    eventually checking its filesystem"""

    resize_opts = ''

    if not fs_type == 'ext3' and not fs_type == 'ext4' \
       and not fs_type == 'ext2':
        syslog.syslog('%s: does not contain an ext2/3/4 filesystem. \
            We simply mount it as is.' % device)
        return

    if os.path.exists('/sbin/blkid'):
        res = subprocess.Popen('/sbin/blkid' + ' -o value -s TYPE ' + device,
                               stderr=subprocess.PIPE,
                               stdout=subprocess.PIPE,
                               stdin=None,
                               shell=True)
    match = re.search('^ext.', res.communicate()[0].decode('utf-8'))
    if match is not None:
        fs_type = match.group(0)

    if re.search('^ext[2-4]', fs_type):
        resize_bin = '/sbin/resize4fs'
        if not os.path.exists(resize_bin):
            resize_bin = '/sbin/resize2fs'
            if not os.path.exists(resize_bin):
                syslog.syslog("%s: resize binary is not present " % device +
                             "(either resize2fs or resize4fs).")
                return

        run_command('auto-resize', '%s %s %s' %
                    (resize_bin, resize_opts, device))
    else:
        syslog.syslog("%s: You need to resize the disk FS manually" % device)
        return


def post_add(device, fs_type, mountpoint):
    """ shell hook called after attaching and mounting a disk """

    if debug:
        syslog.syslog("%s: call shell hook post-disk-attach" % device)
    run_command('call shell hook in post add', '%s/post-disk-attach %s %s %s' %
        (load_hook_dir(config_file), device, fs_type, mountpoint))
    return


def pre_delete(device, mountpoint):
    """ shell hook called before umount and detaching a disk """

    if debug:
        syslog.syslog("%s: call shell hook pre-disk-detach" % device)
    run_command('call shell hook in pre delete', '%s/pre-disk-detach %s %s' %
        (load_hook_dir(config_file), device, mountpoint))
    return


def on_add(device, mountpoint):
    """ mount a device on a defined mountpoint. """

    if re.match('/dev/(xv|s)da.?', device):
        return
    else:
        syslog.syslog('%s: ok to mount, going on' % device)

    mount_params = load_mount_params(config_file)

    if not os.path.exists(mountpoint):
        if debug:
            syslog.syslog('%s: creating mountpoint %s' % (device, mountpoint))
        os.mkdir(mountpoint)

    if in_mtab(device):
        if debug:
            syslog.syslog('%s: already present in /etc/mtab. Exiting.')
        syslog.syslog('%s: already mounted.' % device)
        return

    if os.environ.get('ID_FS_TYPE'):
        cmd = 'mount -t %s -o %s %s %s' % (os.environ['ID_FS_TYPE'],
            mount_params, device, mountpoint)
    else:
        cmd = 'mount -o %s %s %s' % (mount_params, device, mountpoint)

    if debug:
        syslog.syslog('%s: calling "%s".' % (device, cmd))
    os.system(cmd)
    # if the mount command is not sucessfull, we remove the mount point
    if not os.path.ismount(mountpoint):
        try:
            os.rmdir(mountpoint)
        except OSError:
            syslog.syslog('%s: error when deleting %s' % (device, mountpoint))
    else:
        if debug:
            syslog.syslog('%s: mount ok then chown and chmod' % device)
        os.chown(mountpoint, 0, 1001)
        os.chmod(mountpoint, 0o775)
        if not in_mtab(mountpoint):
            if debug:
                syslog.syslog('%s: add to /etc/mtab as missing' % device)
            add_to_mtab(mountpoint)


def in_mtab(element):
    """ look in /etc/mtab to find if element is present. """
    mntfound = 0
    for line in open('/etc/mtab', 'r'):
        result = re.compile('%s' % element).search(line.rstrip(os.linesep))
        if result is not None:
            mntfound = 1
            break
    return mntfound


def add_to_mtab(mountpoint):
    """ add mountpoint to /etc/mtab when reading information
    from /proc/mounts.
    """
    for line in open('/proc/mounts', 'r'):
        result = re.compile('^%s' % mountpoint).search(line.rstrip(os.linesep))
        if result is not None:
            mtab_fd = open('/etc/mtab', 'a')
            mtab_fd.write(line.rstrip(os.linesep))
            mtab_fd.close()


def remove_mountpoint(device, mountpoint):
    """ remove a directory """

    if not os.path.ismount(mountpoint):
        try:
            os.rmdir(mountpoint)
        except OSError:
            syslog.syslog('%s: error when deleting %s' % (device, mountpoint))
    else:
        syslog.syslog('%s: warning, something is mounted on %s' %
            (device, mountpoint))


def umount_device_pattern(device_pattern):
    """ umount all partitions according to device pattern. """

    patternc = re.compile(device_pattern)
    for line in open('/proc/mounts', 'r'):
        result = patternc.search(line.rstrip(os.linesep))
        if result is not None:
            cmd_result = os.system('umount -l ' + result.group(1))
            if cmd_result != 0:
                syslog.syslog('error when unmounting ' + result.group(1))


def on_delete(device, mountpoint):
    """ umount a device and remove a mountpoint. """

    if debug:
        syslog.syslog('%s: on_delete() on path %s' % (device, mountpoint))

    # stopping services using the datadisk
    if os.path.exists(os.path.join(mountpoint, '.gandi')):
        if os.path.exists(os.path.join(mountpoint, '.gandi', 'services')):
            data = file(os.path.join(mountpoint, '.gandi', 'services'), 'r')
            services = data.read().rstrip(os.linesep)
            for service in services:
                # /etc/init.d/service stop
                command = subprocess.Popen('/etc/init.d/' + service + ' stop',
                                     stderr=subprocess.PIPE,
                                     stdout=subprocess.PIPE,
                                     stdin=None,
                                     shell=True)

                ret = command.returncode
                syslog.syslog('Trying to stop %s' % service)
                (output, error) = command.communicate()
                output = output.decode('utf-8')
                error = error.decode('utf-8')

                if ret is not None:
                    syslog.syslog('stopping %s, output : %s and error : %s' %
                        (service, output, error))

    # first we unmount the specific device from the system
    umount_device_pattern('^(' + device + ') .*$')

    # we remove specific mountpoing
    if os.path.exists(mountpoint) and not os.path.ismount(mountpoint):
        remove_mountpoint(device, mountpoint)

    # ... and even mountpoint build the the label from udev
    if 'ID_FS_LABEL_SAFE' in os.environ:
        if len(os.environ['ID_FS_LABEL_SAFE']) > 0:
            mountpoint = datadisk_root + '/' + os.environ['ID_FS_LABEL_SAFE']
            if os.path.exists(mountpoint):
                remove_mountpoint(device, mountpoint)

    # then we remove existing partition on the device
    umount_device_pattern('^(' + device + '[0-9a-z]+)\s*.*')


def is_mounted(device):
    """ Is the specific device mounted on the filesystem ? """

    # if the disk is already mounted, do nothing
    pattern = re.compile(device)
    if debug:
        syslog.syslog('%s: looking for device in /proc/mounts' % device)
    for line in open('/proc/mounts', 'r'):
        match = pattern.search(line.rstrip(os.linesep))
        if match is not None:
            if debug:
                syslog.syslog('%s: found match' % device)
            syslog.syslog('%s: already mounted on the system.' %
                device)
            sys.exit(0)


def get_mountpoint(device, rawdevice, disk_root):
    """ Find the correct mount point for a device. """
    # udev is providing us a label name if present
    if 'ID_FS_LABEL_SAFE' in os.environ and os.environ['ID_FS_LABEL_SAFE']:
        mountpoint = disk_root + '/' + os.environ['ID_FS_LABEL_SAFE']
    else:
        if 'ID_FS_LABEL_ENC' in os.environ and \
           os.environ['ID_FS_LABEL_ENC']:
            mountpoint = disk_root + '/' + \
                os.environ['ID_FS_LABEL_ENC']
            if debug:
                msg = 'label from udev is'
                syslog.syslog('%s: %s is %s and mountpoint is %s' %
                    (device, msg, os.environ['ID_FS_LABEL_ENC'], mountpoint))
        else:
            # in some distribution, we have to ask e2label about it
            command = subprocess.Popen('/sbin/e2label ' + device,
                  shell=True,
                  stdin=subprocess.PIPE,
                  stdout=subprocess.PIPE,
                  stderr=subprocess.PIPE,
                  close_fds=True)
            ret = command.returncode
            (output, error) = command.communicate()
            output = output.decode('utf-8')
            error = error.decode('utf-8')
            if ret is None and not re.compile('^$').match(output.decode('utf-8')):
                mountpoint = disk_root + '/' + output
            else:
                mountpoint = disk_root + '/' + \
                    os.path.basename(rawdevice)
            if debug:
                syslog.syslog('%s: label info from e2label, mountpoint is %s' %
                    (device, mountpoint))

    if re.match('add', os.environ['ACTION']) or \
       re.match('change', os.environ['ACTION']):
        if debug:
            syslog.syslog('%s: looking for mountpoint %s in /proc/mounts.' %
                (device, mountpoint))

        # Fix two disks that have the same label not to mount
        # on same mountpoint
        # Fix also a behavior of add/change of udev (need more research)
        pattern = re.compile('%s ' % mountpoint)
        pattern2 = re.compile('%s ' % device)
        for line in open('/proc/mounts', 'r'):
            match = pattern.search(line.rstrip(os.linesep))
            match2 = pattern2.search(line.rstrip(os.linesep))
            if match is not None and match2 is None:
                mountpoint_ = mountpoint
                mountpoint = '%s_2' % mountpoint_
                msg = "a disk with the same fs label is already present"
                syslog.syslog('%s: %s %s; mounting it in %s' %
                    (device, msg, mountpoint_, mountpoint))

    if re.match('offline', os.environ['ACTION']):
        if debug:
            msg = 'looking for mountpoint in /proc/mounts matching the device'
            syslog.syslog('%s: %s %s' % (device, msg, device))

        pattern = re.compile('^%s ([^ ]*) ' % device)
        for line in open('/proc/mounts', 'r'):
            match = pattern.search(line.rstrip(os.linesep))
            if match is not None:
                mountpoint = match.group(1)

    if debug:
        syslog.syslog('%s: new mountpoint is %s' % (device, mountpoint))

    return mountpoint


def detect_devicename(re_deviceline, pattern_id):
    """ Look in /proc/partitions for the device name and all the
        partitions.

        This method is Linux specific.
    """
    re_device = re.compile('^((xv|s)d[a-z]+)')
    # we build a return hash to know how many partitions we have for each
    # device
    partitions = {}
    device_label = ''
    device = None

    for line in open('/proc/partitions', 'r').readlines():
        result = re_deviceline.match(line)
        if result is None:
            continue

        if debug:
            syslog.syslog('detect in /proc/partitions, line is %s, result %s'
                    % (line, ", ".join(result.groups())))
        device_name = result.group(pattern_id)
        device = '/dev/' + device_name
        if debug:
            syslog.syslog('manage_data_disk: correct name detected is %s'
                    % device)

        # device label as dict key (xvdb), list of partitions
        # ['xvdb', 'xvdb1'] etc. as value.
        device_label = re_device.match(device_name).group(1)
        partitions[device_label] = partitions.get(device_label, [])
        partitions[device_label].append(device_name)

        if debug:
            syslog.syslog('partitions: %s, %s'
                    % (device_label, ", ".join(partitions)))

    return (device, partitions, device_label)


def writable_root():
    """ Check if the root partition is writable. """
    if posix.access('/', posix.W_OK) or os.environ['TAGS'] == ':systemd:':
        return True
    return False


def main():
    syslog.openlog('gandi')

    if debug:
        re_info = re.compile('^(LANG|TERM|SHELL|SSH|LC_|LS_|HOME|MAIL|OLD|SHL|LOGNAME|USER).*$')
        syslog.syslog('# -- content of the environment variables --')
        for entry in os.environ:
            r = re_info.match(entry)
            if r is None:
                syslog.syslog(" %s = %s" % (entry, os.environ[entry]))
        syslog.syslog('# -- end of content of the environment variables --')

    if debug:
        syslog.syslog('manage_data_disk: main function.')

    if int(load_allow_mount(config_file)) == 0:
        if debug:
            syslog.syslog('Disable by config file.')
        sys.exit(0)

    if not writable_root():
        if debug:
            syslog.syslog('Root FS is not writable.')
        sys.exit(1)

    datadisk_root = load_disk_root(config_file)

    if not os.path.exists(datadisk_root):
        os.mkdir(datadisk_root)
        syslog.syslog('creating ' + datadisk_root)

    if 'ID_FS_TYPE' in os.environ and os.environ.get('ID_FS_TYPE') == 'swap':
        if debug:
            syslog.syslog('Device is swap. We stop there.')
        sys.exit(0)

    if debug:
        syslog.syslog('manage_data_disk: DEVPATH is %s' % os.environ.get('DEVPATH'))

    pattern = '.*/block/(.*)'
    device = None

    if os.environ.get('DEVPATH'):
        rawdevice = os.environ['DEVPATH']

    # we use the DEVPATH udev variable to get the device name
    if not os.environ.get('DEVNAME') and os.environ.get('DEVPATH') and \
       re.match(pattern, os.environ['DEVPATH']):
        if debug:
            syslog.syslog('manage_data_disk: using DEVPATH')
        majmin = re.compile('^([0-9][0-9]*):([0-9][0-9]*)$')

        try:
            # we look in /sys tree to get minor and major information
            # for the device
            for line in open('/sys' + rawdevice + '/dev', 'r').readlines():
                r = majmin.match(line)
                if r is not None and len(r.groups()) >= 2:
                    major = r.group(1)
                    minor = r.group(2)

        except IOError:
            syslog.syslog('%s: not present.' % rawdevice)
            sys.exit(0)

        if not major or not minor:
            syslog.syslog('%s: cannot find major:minor value.' % rawdevice)
            sys.exit(0)

        if debug:
            syslog.syslog('%s: %s:%s (major/minor)' %
                (rawdevice, major, minor))

        # as long as the device is connected, we can find the real name with
        # minor and major info
        re_deviceline = re.compile('\s+(%s)\s+(%s)\s+.*((xv|s)d[a-z0-9]+)$' %
            (major, minor))
        (device, partitions, device_label) = detect_devicename(re_deviceline, 3)

    if os.environ.get('DEVNAME'):
        if debug:
            syslog.syslog('manage_data_disk: using DEVNAME (%s)' % os.environ.get('DEVNAME'))
        r = re.match('/dev/((xv|s)d.*)$', os.environ['DEVNAME'])
        if r is not None:
            re_deviceline = re.compile('^.*(%s)' % r.group(1))
            (device, partitions, device_label) = detect_devicename(re_deviceline, 1)
            # could not get info in proc/partitions but we have the devicename
            if device is None:
                device = os.environ['DEVNAME']

    if device is None:
        syslog.syslog('manage_data_disk: cannot find device name.')
        sys.exit(0)

    try:
        if debug:
            syslog.syslog('%s: get_mountpoint(), raw: %s and root: %s' %
                (device, rawdevice, datadisk_root))
        mountpoint = get_mountpoint(device, rawdevice, datadisk_root)
    except NameError:
        syslog.syslog('manage_data_disk: cannot find device name.')
        sys.exit(0)

    if re.match('add', os.environ['ACTION']) or \
       re.match('change', os.environ['ACTION']):
        fs_type = os.environ.get('ID_FS_TYPE')

        if debug:
            syslog.syslog('%s: check before adding disk : is_mounted()' %
                device)
        is_mounted(device)

        # we only resize disks without partitions
        if len(partitions.get(device_label, [])) == 1:
            if debug:
                syslog.syslog('%s: action is %s, calling pre_add()' %
                    (device, os.environ['ACTION']))
            pre_add(device, fs_type, mountpoint)
        if debug:
            syslog.syslog('%s: action is %s, calling on_add()' %
                (device, os.environ['ACTION']))
        on_add(device, mountpoint)
        post_add(device, fs_type, mountpoint)

    # For disk in SATA, we set a bogus ID_VENDOR
    if 'ID_VENDOR' not in os.environ:
        os.environ['ID_VENDOR'] = 'None'

    if re.match('offline', os.environ['ACTION']) or \
       (re.match('remove', os.environ['ACTION']) and
        re.match('gandi\.ne', os.environ['ID_VENDOR'])):
        if debug:
            syslog.syslog('%s: action is %s, calling on_delete()' %
                (device, os.environ['ACTION']))
        pre_delete(device, mountpoint)
        on_delete(device, mountpoint)

try:
    main()
except Exception:
    syslog.syslog('manage_data_disk: caught exception')
    import traceback
    syslog.syslog(traceback.format_exc())

# vim:ft=python:et:sw=4:ts=4:sta:tw=79:fileformat=unix
