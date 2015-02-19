# Debian packaging Makefile

SHELL=/bin/bash
PKGNAME=gandi-hosting-vm2
HOME_=/home/package
RPMCHROOT=${HOME_}/chroot-rpm-build
RPMBUILDROOT=${RPMCHROOT}/${HOME_}/rpm/
DESTDIR=./debian/$(PKGNAME)

VERSION = $(shell head -1 debian/changelog | egrep -o '\(.*\)' | sed -e 's/[()]//g')
VERSION_MAJOR = $(shell echo $(VERSION) | cut -d'-' -f1)
VERSION_MINOR = $(shell echo $(VERSION) | cut -d'-' -f2)

default:
	@echo "Nothing."

version:
	@echo VERSION: $(VERSION) and VERSION_MAJOR: $(VERSION_MAJOR) and VERSION_MINOR: $(VERSION_MINOR)

install:
	install -d $(DESTDIR)/etc/gandi
	install -m 0750 ./manage_data_disk.py		$(DESTDIR)/etc/gandi/
	install -m 0750 ./manage_data_disk.sh		$(DESTDIR)/etc/gandi/
	install -m 0750 ./manage_iface.sh		$(DESTDIR)/etc/gandi/
	install -d -m 0750 $(DESTDIR)/etc/gandi/plugins.d
	install -m 0750 ./gandi-config/plugins.d/*	$(DESTDIR)/etc/gandi/plugins.d/
	install -m 0640 ./maintainer.gandi.key		$(DESTDIR)/etc/gandi/
	install -m 0640 ./sysctl.conf			$(DESTDIR)/etc/gandi/
	install -m 0640 ./gandi-config/plugins-lib	$(DESTDIR)/etc/gandi/
	
	install -d -m 0750 $(DESTDIR)/usr/share/gandi/bootstrap.d
	install -m 0750 ./gandi-config/bootstrap.d/*	$(DESTDIR)/usr/share/gandi/bootstrap.d/
	
	install -d -m 0750 $(DESTDIR)/etc/gandi/hooks
	install -m 0750 ./hooks/*			$(DESTDIR)/etc/gandi/hooks/
	
	mkdir -p $(DESTDIR)/etc/udev/rules.d
	install -m 0640 ./udev/gandi.rules		$(DESTDIR)/etc/udev/rules.d/86-gandi.rules
	install -d -m 0755 $(DESTDIR)/lib/udev
	install -m 0755 ./udev/cpu_online.script	$(DESTDIR)/lib/udev/cpu_online
	install -m 0755 ./udev/manage_memory.script	$(DESTDIR)/lib/udev/manage_memory
	install -m 0755 ./udev/fake_blkid.script	$(DESTDIR)/lib/udev/fake_blkid
	
	install -d -m 0755 $(DESTDIR)/etc/default
	install -m 0644 ./gandi-config/gandi-config.default 	$(DESTDIR)/etc/default/gandi
	
	install -d -m 0755 $(DESTDIR)/etc/init.d
	install -m 0755 ./gandi-config/gandi-config	$(DESTDIR)/etc/init.d
	install -m 0755 ./gandi-mount/gandi-mount	$(DESTDIR)/etc/init.d
	install -m 0755 ./gandi-config/gandi-postboot	$(DESTDIR)/etc/init.d
	install -m 0755 ./gandi-config/gandi-bootstrap	$(DESTDIR)/etc/init.d
	
	# we copy the systemd files in the debian packages. If systemd is not
	# installed, these files are useless
	install -d -m 0755 $(DESTDIR)/usr/share/gandi/systemd
	for elt in ./systemd/system/*.service; do \
	    install -m 0644 $$elt $(DESTDIR)/usr/share/gandi/systemd/; \
	done
	
deb:
	debuild -us -uc -b || dpkg-buildpackage -rfakeroot -uc -b

dist:   deb
	# install
	rm -rf debian/$(PKGNAME)-$(VERSION_MAJOR)
	mkdir debian/$(PKGNAME)-$(VERSION_MAJOR)
	cp -rf debian/$(PKGNAME)/* debian/$(PKGNAME)-$(VERSION_MAJOR)/
	mv -f debian/$(PKGNAME)-$(VERSION_MAJOR)/etc/default \
	    debian/$(PKGNAME)-$(VERSION_MAJOR)/etc/sysconfig
	cp debian/changelog debian/$(PKGNAME)-$(VERSION_MAJOR)/
	
	# compression
	gzip -9 debian/$(PKGNAME)-$(VERSION_MAJOR)/changelog
	cd debian && tar cjf $(PKGNAME)-$(VERSION).tar.bz2 \
	    $(PKGNAME)-$(VERSION_MAJOR)

rpm:	dist
	cp debian/$(PKGNAME)-$(VERSION).tar.bz2 ${RPMBUILDROOT}/SOURCES/
	
	# prepare the spec file for the build of the current version 
	sed -e "s/\(%changelog\)/\1\n* $(shell date +"%a %b %d %Y") Gandi Maintainer <noc@gandi.net> $(VERSION)gnd\n- Bug fixing for packaging and scripts. See \/usr\/share\/doc\/$(PKGNAME)\/changelog.gz.\n/" \
	  -e "s/^\(%define release \).*/\1$(VERSION_MINOR)/" \
	  -e "s/^\(%define version \).*/\1$(VERSION_MAJOR)/" \
	  rpm/$(PKGNAME).spec > $(RPMBUILDROOT)/SPECS/$(PKGNAME).spec
	
	# add the postinst fix script
	install -m 0750 rpm/postinst-fix-mandriva.sh \
	    $(RPMBUILDROOT)/SOURCES/postinst-fix-mandriva.sh
		
	# build the rpm package in the chroot
	sudo chroot ${RPMCHROOT} su - package -c "rpm -ba rpm/SPECS/$(PKGNAME).spec"

rpm-repository:
	install -m 0755 rpm/repos/generate-repository.sh ${RPMCHROOT}/${HOME_}/
	sudo chroot ${RPMCHROOT} su - package -c "./generate-repository.sh"

all: clean rpm
	@echo -e "Build rpm repository with 'make rpm-repository'."

complete-clean: clean
	for ext in deb changes tar.gz; do \
	    rm -vf ../$(PKGNAME)*.$$ext ; \
	done

clean:
	@echo "Cleaning ..."
	@rm -rf debian/$(PKGNAME)
	@rm -rf debian/$(PKGNAME).other
	@rm -rf debian/$(PKGNAME)-1*
	@rm -rf debian/$(PKGNAME).tar
	@rm -f configure-stamp build-stamp
	@dh_clean
