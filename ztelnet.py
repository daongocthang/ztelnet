import configparser
import os
import socket
import sys
import time
from telnetlib import Telnet
import colorama
import pyfiglet
from termcolor import cprint, colored

# import wifiscan




class ZXA10:
    def __init__(self, verbose=False, port=1):
        basedir = os.path.dirname(os.path.abspath(__file__))
        self.config = configparser.ConfigParser()
        self.config.read(os.path.join(basedir, 'config.ini'))
        self.telnet = Telnet()
        self.data = []
        self.port = port
        # self.telnet.set_debuglevel(1)
        self.verbose = verbose

    def _write(self, s: str):
        self.telnet.write(s.encode('ascii') + b'\n')

    def _read_until(self, s: str):
        return self.telnet.read_until(s.encode('ascii')).decode('ascii')

    def _wait(self):
        self._read_until('#')

    def connect(self):
        host = self.config['ZTE']['host']
        port = self.config['ZTE']['port']
        self.telnet.open(host, port, 10)
        if self.verbose:
            print('Connected to the host.')

    def log_in(self):
        usr = self.config['ZTE']['usr']
        pwd = self.config['ZTE']['pwd']

        self._read_until('Username:')
        self._write(usr)
        self._read_until('Password:')
        self._write(pwd)
        self._read_until('ZXAN#')
        self._write('con t')
        self._wait()

        if self.verbose:
            print('Configuration enable.')

    def set_iface_if_not(self):
        self._write('')
        cursor = self._read_until('#')
        if 'config-if' not in cursor:
            self._write('interface gpon-olt_1/1/{}'.format(self.port))
            self._wait()

    def scan(self):
        self.data.clear()

        self.set_iface_if_not()

        self._write('show gpon onu uncfg gpon-olt_1/1/{}'.format(self.port))
        cursor = self._read_until('#')
        if len(cursor) > 0:
            i = 0
            for line in cursor.split('\n'):
                if line.startswith('gpon-onu'):
                    sn = [_ for _ in line.split(' ') if _ != ''][1]
                    self.data.append({'sn': sn, 'mac': None, 'pon': None, 'wlan': None, 'result': 'PASS'})
                    if self.verbose:
                        i += 1
                        print('{}\t{}'.format(i, sn))
        elif self.verbose:
            print('Not related information to show.')

    def add_profile(self, idx):
        if idx < len(self.data):
            self.set_iface_if_not()
            onu = self.data[idx]
            self._write('onu {} type ZTE-F608 sn {}'.format(idx + 1, onu['sn']))
            self._wait()
            self._write('onu {} profile H4I0'.format(idx + 1))
            self._wait()
            self._write('exit')
            self._read_until('ZXAN(config)#')
            self._write('interface gpon-onu_1/1/{}:{}'.format(self.port, idx + 1))
            self._wait()
            self._write('switchport mode hybrid vport 1')
            self._wait()
            self._write('service-port 1 vport 1 user-vlan 35 vlan 35')
            self._wait()
            self._write('exit')
            self._wait()

            if self.verbose:
                print('{}\t{}\tavailable'.format(idx + 1, onu['sn']))

    def check_pon_power(self):
        self.set_iface_if_not()
        self._write('show pon power onu-rx gpon-olt_1/1/{}'.format(self.port))
        cursor = self._read_until('#')
        holder = True

        for x in self.data:
            x['pon'] = None

        if len(cursor) > 0:
            i = 0
            for line in cursor.split('\n'):
                if line.startswith('gpon-onu'):
                    pwr = [_ for _ in line.split(' ') if _ != ''][1]
                    if 'N/A' in pwr:
                        holder = False
                        i += 1
                        continue
                    float_pwr = float(pwr.replace('(dbm)', ''))
                    self.data[i]['pon'] = float_pwr
                    no_power = float_pwr < float(self.config['gpon']['pon'])

                    if no_power:
                        self.data[i]['result'] = 'FAILED'

                    i += 1

            if self.verbose:
                for i2 in range(len(self.data)):
                    print('{}\t{}\t{}'.format(i2 + 1, self.data[i2]['sn'], self.data[i2]['pon']))

        return holder

    def restore_factory(self, idx):
        self.set_iface_if_not()
        self._write('exit')
        self._wait()
        self._write('pon-onu-mng gpon-onu_1/1/{}:{}'.format(self.port, idx + 1))
        self._wait()
        self._write('restore factory')
        self._wait()
        self._write('exit')
        self._wait()
        if self.verbose:
            print('{}\t{}\trestore-default'.format(idx + 1, self.data[idx]['sn']))

    def restore_default(self, count):
        for idx in range(count):
            self.restore_factory(idx)

    def learn(self):
        self.clear()
        self._write('auto-learn en')
        self._wait()

    def show_info(self):
        self._write('show this')
        cursor = self._read_until('!')
        if len(cursor) > 0:
            print(cursor)

    def show_pon(self):
        self.set_iface_if_not()
        self._write('show pon power onu-rx gpon-olt_1/1/{}'.format(self.port))
        cursor = self._read_until('#')
        if len(cursor) > 0:
            print(cursor)

    def remove(self, idx):
        self.set_iface_if_not()
        self._write('no onu {}'.format(idx + 1))
        self._wait()
        # if self.verbose:
        #     print('ONU at {} had removed'.format(self.data[idx]['sn']))

    def collect_mac(self):
        self.set_iface_if_not()
        self._write('show mac gpon olt gpon-olt_1/1/{}'.format(self.port))
        cursor = self._read_until('#')
        if len(cursor) > 0:
            i = 0
            for line in cursor.split('\n'):
                if 'gpon-onu':
                    mac = [_ for _ in line.split(' ') if _ != ''][0]
                    if '.' in mac:
                        self.data[i]['mac'] = mac.replace('.', '')
                        if self.verbose:
                            print('{}\t{}\t{}'.format(i + 1, self.data[i]['sn'], self.data[i]['mac']))

                        i += 1

    # def check_wlan(self, iface):
    #     if len(self.data) == 0:
    #         return
    #
    #     self.collect_mac()
    #
    #     results = wifiscan.scan(iface)
    #     closed = []
    #     for res in results:
    #         bssid = res[0]  # type:str
    #         # ssid = res[1]
    #
    #         if bssid in closed:
    #             continue
    #         for onu in self.data:
    #             if bssid.replace(':', '') == onu['mac']:
    #                 onu['wlan'] = float(res[3])
    #                 if not onu['wlan'] or onu['wlan'] < float(self.config['gpon']['wifi']):
    #                     onu['result'] = 'FAILED'
    #                 closed.append(bssid)
    #
    #                 if self.verbose:
    #                     print('{}\t{}'.format(onu['sn'], onu['wlan']))
    #
    #                 break

    def clear(self):
        self._write('auto-learn dis')
        self._wait()
        self._write('clear')
        self._wait()

    def close(self):
        self.telnet.close()
        if self.verbose:
            print('Connection closed.')


def welcome_screen(content, port=None):
    if os.name == 'nt':
        _ = os.system('cls')
    else:
        _ = os.system('clear')

    _max = 50
    text_font = pyfiglet.figlet_format(content, font='big')
    print(sep='\n')
    cprint(text_font, 'green')
    if port:
        print('Selected Port: {}'.format(port))
    print('=' * _max)
    print(sep='\n')


if __name__ == '__main__':
    title = 'ZTELNET'
    client = None
    colorama.init()
    exitflag = False
    try:
        welcome_screen(title)

        p = input("Select port: ")

        client = ZXA10(verbose=True, port=int(p))
        client.connect()
        client.log_in()

        client.set_iface_if_not()
        # client.clear()
        max_width = 50
        interval = 300

        while True:
            welcome_screen(title, p)

            print('Choose an option in the below:')
            print(sep='\n')
            print('[1] Show unconfigured ONTs')
            print('[2] Start to test ONTs')
            print('[3] Clear all configuration')
            print('[4] Show power PONs')
            print('[0] Exit')
            print(sep='\n')
            print('=' * max_width)

            ev = input("Press number to choose: ")
            print('\n')

            if ev == '0':
                break
            if ev == '1':
                print('[+] List of unconfigured ONT')
                client.scan()
            if ev == '2':
                welcome_screen(title, p)
                print('[+] Adding profile')
                client.clear()
                for i in range(len(client.data)):
                    client.add_profile(i)
                    time.sleep(0.5)

                startTime = time.time()
                client.verbose = False
                time.sleep(10)
                while not client.check_pon_power():
                    welcome_screen(title, p)
                    print('[+] Checking PON power')

                    for i in range(len(client.data)):
                        print('{}\t{}\t{}'.format(i + 1, client.data[i]['sn'], client.data[i]['pon']))

                    diff = time.time() - startTime
                    if diff >= interval:
                        client.clear()
                        cprint('\rChecking PON failed ', 'red')
                        exitflag = True
                        break
                    time.sleep(5)
                client.verbose = True

                if not exitflag:
                    welcome_screen(title, p)
                    print('[+] Checking PON power')
                    client.check_pon_power()

                    # reset-factory
                    time.sleep(5)
                    welcome_screen(title, p)
                    print('[+] Reseting factory')
                    for i in range(len(client.data)):
                        client.restore_factory(i)

                    client.verbose = False
                    time.sleep(10)
                    while not client.check_pon_power():
                        welcome_screen(title, p)
                        print('[+] Checking PON power after restored factory')

                        for i in range(len(client.data)):
                            print('{}\t{}\t{}'.format(i + 1, client.data[i]['sn'], client.data[i]['pon']))

                        time.sleep(5)
                    client.verbose = True

                    '''
                    # scan-wifi
                    iface = wifiscan.get_ifaces()[0]
                    if not iface:
                        print('[-] cannot found wlan interface')
                        sys.exit()
    
                    client.check_wlan(iface)
                    '''

                    # display
                    welcome_screen(title, p)
                    print('[+] Resulting')
                    time.sleep(5)
                    for i in range(len(client.data)):
                        onu = client.data[i]
                        result = colored(onu['result'], 'green')
                        if onu['result'] == 'FAILED':
                            client.remove(i)
                            result = colored(onu['result'], 'red')
                        print('{}\t{}\t{}\t{}'.format(i + 1, onu['sn'], onu['pon'], result))

                    print(sep='\n')
                    print('[+] Completed')

            if ev == '3':
                client.clear()
                print('[+] Clear completed')

            if ev == '4':
                print('[+] Checking PON power')
                client.check_pon_power()

            # if ev == '5':
            #     # TODO: appearing an error, not fix yet
            #     iface = wifiscan.get_ifaces()[0]
            #     if not iface:
            #         print('[-] cannot found wlan interface')
            #         sys.exit(1)
            #     client.check_wlan(iface)

            input('\nPress Enter key to continue... ')
    except (KeyboardInterrupt, ConnectionResetError, socket.timeout):
        cprint('\nOops! Connection to the host lost.', 'red')
        sys.exit(-1)
    finally:
        if client is not None:
            client.close()
