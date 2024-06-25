#!/usr/bin/env python3


import argparse
import os
import shutil
import time
import sys

import pywifi

AKM = ['NONE', 'WPA', 'WPA/PSK', 'WPA2', 'WPA2/PSK', 'UNKNOWN']
CIPHER = ['NONE', 'WEP', 'TKIP', 'CCMP', 'UNKNOWN']
AUTH = ['OPEN', 'SHARED']


def get_ifaces():
    w = pywifi.PyWiFi()
    return w.interfaces()


def scan(iface):
    iface.scan()
    time.sleep(5)
    bsses = iface.scan_results()
    closed = []
    networks = []
    for bss in bsses:
        if bss.bssid in closed:
            continue
        closed.append(bss.bssid)
        networks.append((
            bss.bssid,
            bss.ssid,
            bss.freq,
            bss.signal,
            bss.cipher,
            bss.akm
        ))
    return sorted(networks, key=lambda st: st[1], reverse=True)


class StoreDictKeyPair(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        my_dict = {}
        for kv in values.split(","):
            k, v = kv.split("=")
            my_dict[k] = v
        setattr(namespace, self.dest, my_dict)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', metavar='FILTER', dest='filter', action=StoreDictKeyPair, default='')

    opt = parser.parse_args()

    iface = get_ifaces()[0]
    if not iface:
        print('[-] cannot found wlan interface')
        os._exit(0)

    try:
        mac_vendors = dict()
        basedir = os.path.dirname(os.path.abspath(__file__))
        f = open(os.path.join(basedir, 'mac-vendor.txt'), 'r')
        
        for line in f.readlines():
            line = line.replace('\n', '').split('\t')
            mac_vendors[line[0].lower()] = line[1]

        while True:
            results = scan(iface)

            if os.name == 'nt':
                _ = os.system('cls')
            else:
                _ = os.system('clear')

            print("{:7}{:22}{:8}{:8}{:12}{:11}{:11}{}".format('ID', 'BSSID', 'FREQ', 'PWR', 'ENC', 'CIPHER', 'VENDOR',
                                                              'SSID'))
            max_width = shutil.get_terminal_size().columns
            print('-' * max_width)

            i = 0
            f = opt.filter
            # print(f.get('vendor', '').lower().split(';'))
            for res in results:
                bssid = res[0][:-1]
                ssid = res[1]
                freq = res[2] / 1000000
                vendor = mac_vendors.get(bssid[:8], 'Unknown')                
                if f:
                    if f.get('except'):
                        if f.get('except') in ssid:
                            continue
                    if f.get('ssid', '') not in ssid:
                        continue
                    # if f.get('vendor', '').lower() not in vendor.lower():
                    if all(v not in vendor.lower() for v in f.get('vendor', '').lower().split(';')):
                        continue
                    if f.get('freq'):
                        if f.get('freq') != '{:.0f}'.format(freq):
                            continue

                i = i + 1

                signal = res[3]
                akm = AKM[res[5][0]]
                auth = AUTH[res[4]]

                print("{:<7}{:22}{:<8}{:<8}{:<12}{:11}{:11}{}".format('%2d' % i, bssid, freq, signal, akm, auth,
                                                                      vendor.split()[0], ssid))

    except KeyboardInterrupt:
        pass
