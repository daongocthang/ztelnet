import configparser
import os
import sys

from contextlib import contextmanager
from telnetlib import Telnet


class ZTE:
    def __init__(self, verbose=False, port=1):
        basedir = os.path.dirname(os.path.abspath(__file__))
        self.config = configparser.ConfigParser()
        self.config.read(os.path.join(basedir, "config.ini"))
        self.telnet = Telnet()
        self.port = port
        self.verbose = verbose

    def write(self, s: str):
        self.telnet.write(s.encode("ascii") + b"\n")

    def read_until(self, s: str):
        return self.telnet.read_until(s.encode("ascii")).decode("ascii")

    def wait(self):
        self.read_until("#")

    def connect(self):
        host = self.config["ZTE"]["host"]
        port = self.config["ZTE"]["port"]
        self.telnet.open(host, port, 10)
        if self.verbose:
            print("Connected to the host.")

    def log_in(self):
        usr = self.config["ZTE"]["usr"]
        pwd = self.config["ZTE"]["pwd"]

        self.read_until("Username:")
        self.write(usr)
        self.read_until("Password:")
        self.write(pwd)
        self.read_until("ZXAN#")
        self.write("con t")
        self.wait()

        if self.verbose:
            print("Configuration enable.")

    def set_iface_if_not(self):
        self.write("")
        cursor = self.read_until("#")
        if "config-if" not in cursor:
            self.write("interface gpon-olt_1/1/{}".format(self.port))
            self.wait()

    def clear(self):
        self.write("auto-learn dis")
        self.wait()
        self.write("clear")
        self.wait()

    def restore_factory(self, idx):
        has_error = False

        self.set_iface_if_not()
        self.write("exit")
        self.wait()
        self.write("pon-onu-mng gpon-onu_1/1/{}:{}".format(self.port, idx + 1))

        cursor = self.read_until("#")
        if "config" in cursor:
            has_error = True
        else:
            self.write("restore factory")
            self.wait()
            self.write("exit")
            self.wait()

        if self.verbose:
            print("onu {} restore factory {}.".format(idx + 1, "failed" if has_error else "successful"))

    def close(self):
        self.telnet.close()
        if self.verbose:
            print("Connection closed.")


@contextmanager
def connect(p: int) -> ZTE:
    client = None
    try:
        client = ZTE(port=p)
        client.connect()
        client.log_in()
        client.set_iface_if_not()
        print("# config-gpon[{}]\n".format(p))
        yield client
    except (KeyboardInterrupt, ConnectionResetError, RuntimeError):
        print("Connection failed.")
    finally:
        if client is not None:
            client.close()


def show(p=2):
    with connect(p) as c:
        c.write("show this")
        cursor = c.read_until("!")
        for x in cursor.split("\n"):
            if "!" not in x:
                print(x)
        c.wait()
        c.set_iface_if_not()
        c.write("show pon power onu-rx gpon-olt_1/1/{}".format(c.port))
        cursor = c.read_until("#")
        for x in cursor.split("\n"):
            if "#" not in x:
                print(x)


def learn(p=2):
    with connect(p) as c:
        c.clear()
        c.write("auto-learn en")
        c.wait()
    print("Enable auto-learn successful.")


def kill(p=2, t=1):
    with connect(p) as c:
        c.write("auto-learn dis")
        c.wait()
        c.write("no onu " + t)
        c.wait()
    print(f"Negate onu {t} successfully.")


def restore(p=2, n=8):
    with connect(p) as c:
        c.verbose = True
        for i in range(int(n)):
            c.restore_factory(i)
        c.verbose = False


if __name__ == "__main__":
    args = sys.argv
    globals()[args[1]](**dict(x.split("=") for x in args[2:]))
