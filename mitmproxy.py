import os
import subprocess


class MITMProxy(object):
    def __init__(self, path, record=True):
        self.binary = "mitmdump"
        self.path = path
        self.record = record
        home = os.path.join(os.path.expanduser("~"), ".mitmproxy")
        self.cert = os.path.join(home, "mitmproxy-ca-cert.cer")
        self.scripts = os.path.join(os.getcwd(), "scripts")

    def __enter__(self):
        # subprocess.call([self.binary, "--version"], os.environ)

        if self.record:
            command = [
                self.binary,
                "-v",
                "--save-stream-file",
                self.path,

                "--scripts",
                os.path.join(self.scripts, "inject-deterministic.py"),


            ]
        else:
            command = [
                self.binary,
                '--listen-host',
                "127.0.0.1",
                '--listen-port',
                '8080',
                "--scripts",
                os.path.join(self.scripts, "mitm_port_fw.py"),
                "--set",  "portmap=80:8090,443:8091",
                '--ssl-insecure',
            ]
        print(" ".join(command))
        self.process = subprocess.Popen(command)
        return self

    def __exit__(self, *args):
        try:
            self.process.wait()
        finally:
            self.process.terminate()
