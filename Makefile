# Debian packaging Makefile

OS = $(shell uname -s)
OS : sh = uname -s
SHELL=/bin/bash
PKGNAME=gandi-hosting-vm2
RPMBUILDROOT=./rpm/
DESTDIR=./debian/$(PKGNAME)

VERSION = $(shell head -1 debian/changelog | egrep -o '\(.*\)' | sed -e 's/[()]//g')
VERSION_MAJOR = $(shell echo $(VERSION) | cut -d'-' -f1)

default:
	@echo "Nothing."

install:
	install -d $(DESTDIR)/etc/gandi
	install -m 0750 ./manage_data_disk.py		$(DESTDIR)/etc/gandi/
	install -m 0750 ./manage_iface.sh		$(DESTDIR)/etc/gandi/
	install -m 0640 ./sysctl.conf			$(DESTDIR)/etc/gandi/
	
ifeq ($(OS),Linux)
	mkdir -p $(DESTDIR)/etc/udev/rules.d
	install -m 0640 ./udev/gandi.rules		$(DESTDIR)/etc/udev/rules.d/86-gandi.rules

	install -d -m 0755 $(DESTDIR)/lib/udev/
	install -m 0755 ./udev/cpu_online.script	$(DESTDIR)/lib/udev/cpu_online
	install -m 0755 ./udev/fake_blkid.script	$(DESTDIR)/lib/udev/fake_blkid

	install -d -m 0755 $(DESTDIR)/etc/apt/trusted.gpg.d
	install -m 0644 ./keys/gandi-archive.gpg	$(DESTDIR)/etc/apt/trusted.gpg.d/

	install -d -m 0750 $(DESTDIR)/etc/auto.master.d
	install -m 0640 autofs/auto.master.d/gandi.autofs $(DESTDIR)/etc/auto.master.d/
	install -m 0750 autofs/auto.gandi $(DESTDIR)/etc/
endif

deb:
	debuild -us -uc -b || dpkg-buildpackage -rfakeroot -uc -b

dist:   deb
	# prepare files from deb build process
	rm -rf debian/$(PKGNAME)-$(VERSION_MAJOR)
	mkdir debian/$(PKGNAME)-$(VERSION_MAJOR)
	cp -rf debian/$(PKGNAME)/* debian/$(PKGNAME)-$(VERSION_MAJOR)/
	install -m 0644 debian/changelog debian/$(PKGNAME)-$(VERSION_MAJOR)/
	#
	rm -rf debian/$(PKGNAME)-$(VERSION_MAJOR)/etc/apt/trusted.gpg.d
	install -d -m 0755 debian/$(PKGNAME)-$(VERSION_MAJOR)/etc/pki/rpm-gpg/
	install -m 0644 ./keys/RPM-GPG-KEY-Gandi \
		debian/$(PKGNAME)-$(VERSION_MAJOR)/etc/pki/rpm-gpg/
	install -d -m 0755 debian/$(PKGNAME)-$(VERSION_MAJOR)/usr/lib/sysctl.d/
	install -m 0644 sysctl_systemd.conf \
		debian/$(PKGNAME)-$(VERSION_MAJOR)/usr/lib/sysctl.d/90-gandi.conf
	#
	# create the tarball used during the rpm build process
	gzip -9 debian/$(PKGNAME)-$(VERSION_MAJOR)/changelog
	cd debian && tar cjf $(PKGNAME)-$(VERSION).tar.bz2 \
		$(PKGNAME)-$(VERSION_MAJOR)

rpm:	dist rpm_prepare
	rpmbuild -bb ${RPMBUILDROOT}/SPECS/$(PKGNAME).spec

rpm_prepare:
	mkdir -p ${RPMBUILDROOT}/{RPMS,SRPMS,SPECS,BUILD,TMP,SOURCES}
	cp debian/$(PKGNAME)-$(VERSION).tar.bz2 ${RPMBUILDROOT}/SOURCES/
	
	# prepare the spec file for the build of the current version
	sed -e "s/\(%changelog\)/\1\n* $(shell LANG=C date +"%a %b %d %Y") Gandi Maintainer <noc@gandi.net> $(VERSION)gnd\n- Bug fixing for packaging and scripts. See \/usr\/share\/doc\/$(PKGNAME)\/changelog.gz.\n/" \
	  -e "s/^\(%define version \).*/\1$(VERSION_MAJOR)/" \
	  rpm/$(PKGNAME).spec > $(RPMBUILDROOT)/SPECS/$(PKGNAME).spec

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
	@dh_clean

sinclude Makefile.specific
