# Gandi VM config

Collection of script used to setup a virtual machine on first boot and to manage the dynamic resources during the life of the virtual machine: adding/removing memory or CPU, attaching/detaching disk or network interfaces

## OVERVIEW

Install a couple of services in the OS running on the VM on Gandi hosting:
 - gandi-bootstrap: read the JSON configuration find in the swap file and configure some basic element of the OS : root password, network configuration, ... to allow customer to simply access the VM. It also install the module tree associated with the booted kernel.
 - gandi-mount: trigger udev to rescan all block device and start the manage_data_disk.py script on each umounted device. This assure VM user that all disks attached to the VM during each step of the boot of the VM are mounted at the end of the boot process.
 - gandi-config: run a couple of quick shell script to configure some element of the system : console, motd, timezone, ... taking in consideration user preferences set in /etc/default/gandi
 - gandi-postboot: read the JSON configuration find in the swap file and execute the post boot commands

## NOTES ON VIRTUAL DISK MOUNTING

The variable CONFIG_ALLOW_MOUNT in /etc/default/gandi is available to disable the automatic mount of additional disks in the virtual machine.

### 0. Note on detaching virtual disk

Since the move to Xen grub and the use of Linux kernel inside the system of the virtual machine, the automatic detach of a disk can only be done if the virtual disk is already umounted in the system. Otherwise it will trigger a kernel bug.
This bug is known and Gandi is working on upstreaming a patch to fix this issue.

### 1. udev solution

Since the beginning of Gandi hosting, attaching an additional virtual disk to a virtual machine triggered a notification to the Linux kernel and then to the udev daemon.

This daemon starts a python script called /etc/gandi/manage_data_disk.py which handles the creation of the mount point, resizes the disk and attachs the virtual disk to the mount point.
The script is also launched when a virtual disk is detached from a virtual machine.

To disable the udev automatic handling:
 - edit /etc/udev/rules.d/86-gandi.rules (or /lib/udev/rules.d/86-gandi.rules) and comment (add '#') at the beginning of lines containing "RUN+="/etc/gandi/manage_data_disk.py",".
 - then restart the VM or simply reload the list of rules with the command 'udevadm control --reload-rules'

### 2. autofs solution

Due to technical choices by the systemd project, we had to find another solution as the python script started by the udev daemon was not able to mount the virtual disk anymore (udevd is running in a low privilege container in systemd 232 and higher).
An automount configuration is available for newer system. It uses the /etc/auto.master.d/gandi.autofs definition and /etc/auto.gandi to handle the automatic mounting of virtual disk in /srv.
User or application will be able to access directly the content of the virtual disk. After a long amount of time without access, the virtual disk is automaticaly umounted.

To disable the autofs automatic handling:
 - edit /etc/auto.master.d/gandi.autofs and comment (add '#') at the beginning of line containing "/srv	/etc/auto.gandi",
 - then restart autofs with the command 'service autofs restart'.

To activate automounting in *another mountpoint*:
 - edit /etc/auto.master.d/gandi.autofs and change /srv at the beginning of the only line in the file to your chosen mount point,
 - then restart autofs with the command 'service autofs restart'.

**Note**: the `CONFIG_DISK_ROOT` variable in `/etc/{default,sysconfig}/gandi` is not used by the autofs setup as auto.master files cannot have dynamic content for configuration.

## CONFIGURATION

Check /etc/default/gandi (or /etc/sysinit/gandi) which contains a couple of flags to manage Gandi autoconfiguration and action during the boot of the VM.

## BUILD

### Deployment

Practical command to build :

make clean && \
make build && \
make rpm

## CONTRIBUTING

### Create issues

Any major changes should be documented as [a GitHub issue](#) before you start working on it.

### Proposing your changes

Don't hesitate -- we appreciate every contribution, no matter how small.

Create a git branch with your new feature or bugfix and either (in order of preference):

* open a Pull Request on GitHub
* mail the patch to feedback@gandi.net,
* send the URL for your branch and we will review/merge it if correct

We'll check your pull requests in the timeliest manner possible. If we can't accept your PR for some reason,
we'll give you feedback and you're encouraged to try again!

### Submission conventions

Fork the repository and make changes on your fork in a feature branch:

- If it's a bug fix branch, name it XXXX-something where XXXX is the number of the issue.
- If it's a feature branch, create an enhancement issue to announce your intentions, and name it XXXX-something where XXXX is the number of the issue.

## LICENSE

Please see the `LICENSE` file.
