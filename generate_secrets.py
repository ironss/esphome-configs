# Secret generation
# Copyright © Stephen Irons 2026

import base64
import math
import os
import pykeepass
import random
import sys


# Utility functions

RFC4648_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"
CROCKFORD_ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
TRANSLATION_TABLE = str.maketrans(RFC4648_ALPHABET, CROCKFORD_ALPHABET)

def b32encode_crockford(data):
    return base64.b32encode(data).decode('ascii').rstrip('=').translate(TRANSLATION_TABLE)

def group_str(s, size=4, separator='-'):
    return separator.join([ s[i:i+size] for i in range(0, len(s), size)])


# Secret-specific generation functions

def gen_ota_password(bits=80):
    data = random.randbytes(int(math.ceil(bits/8)))
    data_b32_crockford = b32encode_crockford(data)
    return group_str(data_b32_crockford)

def gen_ha_api_key(bits=256):
    data = random.randbytes(int(math.ceil(bits/8)))
    data_b64 = base64.b64encode(data).decode('ascii')
    return (data_b64)

def gen_ap_ssid(suffix='-AP'):
    return '%s%s' % (dev_id, suffix)

def gen_ap_psk(bits=80):
    data = random.randbytes(int(math.ceil(bits/8)))
    data_b32_crockford = b32encode_crockford(data)
    return group_str(data_b32_crockford)

def gen_web_username(user='admin'):
    return user

def gen_web_password(bits=80):
    data = random.randbytes(int(math.ceil(bits/8)))
    data_b32_crockford = b32encode_crockford(data)
    return group_str(data_b32_crockford)

def gen_tb_api_key(bits=80):
    data = random.randbytes(int(math.ceil(bits/8)))
    data_b32_crockford = b32encode_crockford(data)
    return group_str(data_b32_crockford)


if __name__ == '__main__':
    expected_properties = {
        'ha_api_key': gen_ha_api_key,
        'ota_password': gen_ota_password,
        'ap_ssid': gen_ap_ssid,
        'ap_psk': gen_ap_psk,
        'web_username': gen_web_username,
        'web_password': gen_web_password,
        'tb_api_key': gen_tb_api_key,
    }

    expected_networks = {
        1: 'ioSphere dev',
        2: 'wodexisixes-6',
        # 3: 'wodexitose',
    }

    # Argument parsing
    # * database file
    # * database password
    # * which device

    dev_id = os.getenv('DEVICE_ID')
    if not dev_id:
        print("Missing DEVICE_ID", file=sys.stderr)
        sys.exit(1)

    fn = os.getenv('KEEPASS_DATABASE')
    pw = os.getenv('KEEPASS_PASSWORD')

    if not fn:
        print('Missing KEEPASS_DATABASE', file=sys.stderr)
        sys.exit(1)

    if not pw:
        print('Missing KEEPASS_PASSWORD', file=sys.stderr)
        sys.exit(1)


    # Read existing entries, update if needed

    kp = pykeepass.PyKeePass(fn, password=pw)

    grname = 'esphome-devices'
    gr = kp.find_groups(name=grname, first=True)
    if not gr:
        gr = kp.add_group(kp.root_group, group_name=grname)

    en = kp.find_entries(path=(grname, dev_id), first=True)
    if not en:
        gr = kp.find_groups(name=grname, first=True)
        en = kp.add_entry(gr, title=dev_id, username=dev_id, password="")

    dirty = False
    properties = {}
    for prop, gen in expected_properties.items():
        if prop not in en.custom_properties:
            en.set_custom_property(prop, gen())
            dirty = True
        properties[prop] = en.custom_properties[prop]

    if dirty:
        kp.save()


    # Device-specific secrets

    secrets = { '%s-%s' % (dev_id, prop): properties[prop] for prop in properties.keys() }


    # Shared network secrets

    for nwid, nwssid in expected_networks.items():
        en = kp.find_entries(username=nwssid, first=True)
        secrets['%s-%s-ssid' % ('wifi', nwid)] = nwssid
        secrets['%s-%s-psk' % ('wifi', nwid)] = en.password if en else 'not-found'


    # Generate secrets file

    print("# Secrets for %s" % dev_id)
    print("# Generated from keepass database %s" % fn)
    print("# DO NOT EDIT")
    print()

    for k, v in secrets.items():
        print('"%s": "%s"' % (k, v))
