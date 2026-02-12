

import base64
import json
import math
import os
import pykeepass
import random
import sys


category = 'esphome-devices'
category_wifi = 'esphome-networks'

product = os.getenv('PRODUCT')

if not product:
    print("Missing PRODUCT")
    sys.exit(1)
    
fn = os.getenv('KEEPASS_DATABASE')
pw = os.getenv('KEEPASS_PASSWORD')

if not fn or not pw:
    print('Missing KEEPASS_DATABASE or KEEPASS_PASSWORD')
    sys.exit(1)
    
    
RFC4648_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"
CROCKFORD_ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
TRANSLATION_TABLE = str.maketrans(RFC4648_ALPHABET, CROCKFORD_ALPHABET)

def b32encode_crockford(data):
    return base64.b32encode(data).decode('ascii').rstrip('=').translate(TRANSLATION_TABLE)

def group(s, size=4, separator='-'):
    return separator.join([ s[i:i+size] for i in range(0, len(s), size)])
    
    
def gen_ota_password(bits=80):
    data = random.randbytes(int(math.ceil(bits/8)))
    data_b32_crockford = b32encode_crockford(data)
    return group(data_b32_crockford)
    
def gen_ha_key(bits=256):
    data = random.randbytes(int(math.ceil(bits/8)))
    data_b64 = base64.b64encode(data).decode('ascii')
    return (data_b64)

def gen_ap_ssid(suffix='-AP'):
    return '%s%s' % (product, suffix)

def gen_ap_psk(bits=80):
    data = random.randbytes(int(math.ceil(bits/8)))
    data_b32_crockford = b32encode_crockford(data)
    return group(data_b32_crockford)

def gen_web_username(user='admin'):
    return user
    
def gen_web_password(bits=80):
    data = random.randbytes(int(math.ceil(bits/8)))
    data_b32_crockford = b32encode_crockford(data)
    return group(data_b32_crockford)


expected_properties = {
    'ota_password': gen_ota_password,
    'ha_key': gen_ha_key,
    'web_username': gen_web_username,
    'web_password': gen_web_password,
    'ap_ssid': gen_ap_ssid,
    'ap_psk': gen_ap_psk,
}

expected_networks = {
    1: 'ioSphere dev',
    2: 'wodexisixes-6',
    # 3: 'wodexitose',
}


kp = pykeepass.PyKeePass(fn, password=pw)
en = kp.find_entries(path=(category, product), first=True)

dirty = False
properties = {}
for prop, gen in expected_properties.items():
    if prop not in en.custom_properties:
        en.set_custom_property(prop, gen())
        dirty = True
    properties[prop] = en.custom_properties[prop]

if dirty:
    kp.save()


secrets = { '%s-%s' % (product, prop): properties[prop] for prop in sorted(properties.keys()) }

for nwid, nwssid in expected_networks.items():
    en = kp.find_entries(username=nwssid, first=True)
    secrets['%s-%s-ssid' % ('wifi', nwid)] = nwssid
    secrets['%s-%s-psk' % ('wifi', nwid)] = en.password if en else 'not-found'


# Generate secrets file

print("# Secrets for %s" % product)
print("# Generated from keepass database %s" % fn)
print("# DO NOT EDIT")
print()

for k, v in secrets.items():
    print('"%s": "%s"' % (k, v))

