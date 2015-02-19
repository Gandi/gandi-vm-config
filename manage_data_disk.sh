#!/bin/sh

case "$ACTION" in
    "online"|"add") 
        message="$DEVNAME / $ID_FS_LABEL_ENC is now available"
        ;;
    "offline"|"remove") 
        message="Removing $DEVNAME"
        ;;
esac

echo $message | wall
echo $message | logger -t gandi
