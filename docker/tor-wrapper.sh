#!/bin/sh
set -eu

mkdir -p /tmp/tor-data
exec /usr/bin/tor -f /etc/tor/torrc.silica_x "$@"
