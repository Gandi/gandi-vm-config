#!/bin/bash

# note : problem with the multiarch opensuse repository ? override index file ?

if [ ! -d repository ]; then
	echo "Directory repository is not present, creating."
	echo "Did you init your build env ?"
	mkdir repository
        mkdir -p specific/centos/{i586,x86_64}
fi

# noarch packages are linked at the same time
archs="i586 x86_64"

distrib_name[0]="mandriva"
distrib_path[0]="__ARCH__"
distrib_name[1]="centos"
distrib_path[1]="__ARCH__/RPMS"
distrib_name[2]="fedora"
distrib_path[2]="__ARCH__/Packages"
distrib_name[3]="opensuse"
distrib_path[3]="__ARCH__"
distrib_name[4]="mageia"
distrib_path[4]="__ARCH__"

distributions=4


#
# Add specific package available in specific/distrib_name[0]
# $1 is the indice, $2 is the arch
#
add_specific() {
    local dest_="repository/${distrib_name[$1]}/${distrib_path[$1]}"
    local dest=${dest_/__ARCH__/$2}
    if [ -d "specific/${distrib_name[$1]}/$2" ]; then
        for rpmfile in specific/${distrib_name[$1]}/$2/*.rpm; do
            ln -f "$rpmfile" "${dest}/"
        done
    fi
}

#
# Hard link package from the build repository to the distrib specific directory
# params : $1 : index of the distribution in the array, $2 : arch of the package
# 
link_pkg() {
    for pkg in $(find rpm/RPMS/noarch rpm/RPMS/i586 rpm/RPMS/x86_64 -type f -iname "*$2.rpm" -o -type f -iname "*noarch.rpm"); do
        dest_="repository/${distrib_name[$1]}/${distrib_path[$1]}"
        dest="${dest_/__ARCH__/$2}"
        if [ ! -d "$dest" ]; then
            # Mandriva use a media_info subdirectory
            if [ $1 -eq -0 -o  $1 -eq 4 ]; then
                mkdir  -p "${dest}"/media_info
            else
                mkdir -p "${dest}"
            fi
        fi

        ln -f "$pkg" "${dest}/"
    done
}

#
# Create repository structure using genhdlist2 (for Mandriva) or createrepo.
# params : $1 : index of the distribution in the array, $2 : arch of the repository
#
genrepo() {
    opwd=$(pwd)
    dest="repository/${distrib_name[$1]}/${distrib_path[$1]}"
    cd "${dest/__ARCH__/$2}"
    case $1 in
        0|4) 
            [ ! -d media_info ] && mkdir media_info
            genhdlist2 --xml-info .
            ;;
        *) 
            cd ..
            createrepo .
            ;;
    esac
    cd $opwd
}

# clean
find repository -iname "*.rpm" -delete

[ -f repository/RPM-GPG-KEY.txt ] || echo "-----BEGIN PGP PUBLIC KEY BLOCK-----
Version: GnuPG v1.4.6 (GNU/Linux)

mQGiBEddYRARBADRoSjNvOtEJRbK6ShQGRSQlSSqeQw531zvWeuuxFntY0K0HpAn
2rOILltKwZd0t3hOQPjE8wWQ2Gpauk8FxMXb3FIgexfVOI/wpD8ykRliAWeIui4P
C7QJCdEHF1IZa3+g8ZMMEim9O3MENrKNGc2JrqfCJSMyWjcIuCOVuPFjfwCgplLt
ZEIvk+7ibIv3eRNF1n3BMvMD/2v0e9nwZUskDmVgOEOZFnQUSQk2cS1rqgUueaiS
HDpPJw0NVUVcEVLUjyNjBtgngk/9BavfrT5rt0r8U1xUAIxZSD9NskkFwzLquEGI
iq8vjPZxnOSK5CpgFB4HZgEXKrzPpsjkIAn6hkIYULttfwOkClEcvchzme74WTXs
nHK3BACDoEHg63v+l/7XIHpfTu5gPWyhVpKOU7nICtPf8pwzO1Kex/oA5FbIe4Qm
S25umx7drQufX+lhJWL5h7i0WGgjhCvYgv/C7W24oAZD1l0a4PF0EQLX78Zf2Nsi
OhCA3oBKskoYAtAf/r4giBkmP2eyUSeQq5OFetn2H2EWX913X7QgR2FuZGkgTWFp
bnRhaW5lciA8bm9jQGdhbmRpLm5ldD6IYAQTEQIAIAUCR11hEAIbAwYLCQgHAwIE
FQIIAwQWAgMBAh4BAheAAAoJENjqwvTa/j+lgEwAniOL1gSWtkoW2rnz2YRimRNB
jkziAJ9BmY1T3iIvXleaOsgk6z86gBxZC4hGBBARAgAGBQJHXWYRAAoJEJDUrdNJ
/lnm5kkAnjDH5sGMc8466Ul85oxIKjoorVlkAJ9/fX+m9L0Rf8efpn6sXVS9ZGxH
57kCDQRHXWEYEAgAjQwyAk2d8GeSuRJLZWuLPd1fTPmslna0fVjVIfOVPbrGT7/g
waO/RWF7pe6aQ8w4eMS20hx2xPR1F8fhE1zrulOCKFNzE7/tNdZeP5LaJCP9luU4
5hD1QMEyZ5veP3IpIrnwnPW73v7KrW1iPyKD2PFnoDOCooWg0u1yoO4NUToDwWtZ
EbmhRwOn2ViHVCpm0ng4fIdqWOS4KJw+xPFXbgFK2h1PeXCJvZ9lh61oASpePeV3
e4IdSghShG5Ml8rCaIZ2O2xm4MIvLXt61TayWqnUcORGR5Z2utP2Sb8p4/c0Lx6T
92yv6rNh0H/VvhiyoOpBkVuUaiAl+9gW5no2EwADBQf/fPvV0NTmuP41y7ZdhSL4
NHg09wHE9nRqncta/j22Nm7PUfCehIuMjKUIa4n8lCM7GSO8lS1PjhLZ70u1k7I3
X+s8TxmxUHmFt+A59EGyGW3Q6lTlzbi+8ugBgEyu4nRGeexzsQ4ipS7h7B7pzWuR
Lm3oGSA8j/ozoGALLralpTdEvQarqDSe+5riDWNISpSWV6lADLB0rB90bm9qNAJv
d28v5ZPb9E5x11tdPIGfpR9qdjeY9zkY3KEKMG9SZhmtsZKKLcgNbCB7YKHdUrVp
KmOmBn/i/+imNpMXC53xw8eYDpC42T5peGajUY9y/yWDbPIMlTJVymctDmhVXZ6H
N4hJBBgRAgAJBQJHXWEYAhsMAAoJENjqwvTa/j+lkbgAnAjUS3yjYrErusKd92eg
V+ko0MJxAJ9FX++KhHhdx8GlFos2RjHfl6dOUw==
=FyDm
-----END PGP PUBLIC KEY BLOCK-----" > repository/RPM-GPG-KEY.txt

# copy packages
for arch in $archs; do
    for index in $(seq -w 0 $distributions); do 
        link_pkg "$index" "$arch"
        add_specific "$index" "$arch"
        genrepo "$index" "$arch"
    done
done

