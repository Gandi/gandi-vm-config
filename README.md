# Gandi VM config

Collection of script used to setup a virtual machine on first boot and to manage the dynamic resources during the life of the virtual machine: adding/removing memory or CPU, attaching/detaching disk or network interfaces

## OVERVIEW

Install a couple of services in the OS running on the VM on Gandi hosting:
 - gandi-bootstrap: read the JSON configuration find in the swap file and configure some basic element of the OS : root password, network configuration, ... to allow customer to simply access the VM. It also install the module tree associated with the booted kernel.
 - gandi-mount: trigger udev to rescan all block device and start the manage_data_disk.py script on each umounted device. This assure VM user that all disks attached to the VM during each step of the boot of the VM are mounted at the end of the boot process.
 - gandi-config: run a couple of quick shell script to configure some element of the system : console, motd, timezone, ... taking in consideration user preferences set in /etc/default/gandi
 - gandi-postboot: read the JSON configuration find in the swap file and execute the post boot commands

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
