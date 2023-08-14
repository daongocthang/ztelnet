import configparser
import os
import sys
from contextlib import contextmanager
from telnetlib import Telnet


class DASAN:
    def __init__(self, verbose=False, port=1):
        basedir = os.path.dirname(os.path.abspath(__file__))
        self.config = configparser.ConfigParser()
        self.config.read(os.path.join(basedir, 'config.ini'))
        self.telnet = Telnet()
        self.port = port
        self.verbose = verbose

    def write(self, s: str):
        self.telnet.write(s.encode('ascii') + b'\n')

    def read_until(self, s: str):
        return self.telnet.read_until(s.encode('ascii')).decode('ascii')

    def wait(self):
        self.read_until('#')

    def connect(self):
        host = self.config['DASAN']['host']
        port = self.config['DASAN']['port']
        self.telnet.open(host, port, 10)
        if self.verbose:
            print('Connected to the host.')

    def log_in(self):
        usr = self.config['DASAN']['usr']
        pwd = self.config['DASAN']['pwd']

        self.read_until('login:')
        self.write(usr)
        self.read_until('Password:')
        self.write(pwd)
        self.read_until('>')
        self.write('en')
        self.wait()
        self.write('con t')
        self.wait()
        self.write('gp')
        self.wait()

        if self.verbose:
            print('Configuration enable.')

    def set_iface_if_not(self):
        self.write('')
        cursor = self.read_until('#')
        if 'config-gpon-olt' not in cursor:
            self.write('gp {}'.format(self.port))
            self.wait()

    def restore_factory(self, idx):
        self.write('onu restore-factory reset {}'.format(idx + 1))
        self.wait()
        if self.verbose:
            print('onu {} restore factory successful.'.format(idx + 1))

    def close(self):
        self.telnet.close()
        if self.verbose:
            print('Connection closed.')


@contextmanager
def connect(p: int) -> DASAN:
    client = None
    try:
        client = DASAN(port=p)
        client.connect()
        client.log_in()
        client.set_iface_if_not()
        print("# config-gpon[{}]\n".format(p))
        yield client
    except (KeyboardInterrupt, ConnectionResetError, RuntimeError):
        print('Connection failed.')
    finally:
        if client is not None:
            client.close()


def show(p=1):
    with connect(p) as c:
        c.write('show onu info')
        cursor = c.read_until('#')
        for x in cursor.split("\n"):
            if all(c not in x for c in ['#', 'show onu info']):
                print(x)


def learn(p=1):
    with connect(p) as c:
        c.write('discover-serial-number stop')
        c.wait()
        c.write('no onu 1-30')
        c.wait()
        c.write('discover-serial-number start 3')
        c.wait()
        c.write('onu fix all')
        c.wait()
    print("Enable auto-learn successful.")


def restore(p=1, count=8):
    with connect(p) as c:
        c.verbose = True
        for i in range(int(count)):
            c.restore_factory(i)
        c.verbose = False


if __name__ == '__main__':
    args = sys.argv
    globals()[args[1]](**dict(x.split("=") for x in args[2:]))
