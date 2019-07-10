import hashlib
import json
import os
import platform
import time
import zipfile

import click
import click_config_file
from mozdevice import ADBAndroid

from apps.android.firefox import GeckoViewExample, Fenix, Fennec, RefBrow
from apps.desktop.chrome import DesktopChrome as Chrome
from apps.desktop.firefox import DesktopFirefox as Firefox
from proxy.mitmproxy import MITMProxy202, MITMProxy404
from proxy.webpagereplay import WebPageReplay

APPS = {
    "Firefox": Firefox,
    "GeckoViewExample": GeckoViewExample,
    "Fenix": Fenix,
    "Fennec": Fennec,
    "Refbrow": RefBrow,
    "Chrome": Chrome,
}

PROXYS = {"mitm2": MITMProxy202, "mitm4": MITMProxy404, "wpr": WebPageReplay}

RECORD_TIMEOUT = 30


class Mode:
    def __init__(self, app, app_path, proxy, certutil, path, sites):
        self.app = app
        self.app_path = app_path
        self.proxy = proxy
        self.certutil = certutil
        self.path = path
        self.sites = sites
        self.information = {}

    def _digest_file(self, file, algorithm):
        """I take a file like object 'f' and return a hex-string containing
        of the result of the algorithm 'a' applied to 'f'."""
        with open(file, "rb") as f:
            h = hashlib.new(algorithm)
            chunk_size = 1024 * 10
            data = f.read(chunk_size)
            while data:
                h.update(data)
                data = f.read(chunk_size)
            name = repr(f.name) if hasattr(f, "name") else "a file"
            print("hashed %s with %s to be %s" % (name, algorithm, h.hexdigest()))
            return h.hexdigest()

    def recording(self):
        print("Starting record mode!!!")
        if not os.path.exists(self.path):
            print("Creating recording path: %s" % self.path)
            os.mkdir(self.path)

        recordings = self.parse_sites_json()

        for recording in recordings:
            if not os.path.exists(os.path.dirname(recording["recording_path"])):
                print(
                    "Creating recording path: %s"
                    % os.path.dirname(recording["recording_path"])
                )
                os.mkdir(os.path.dirname(recording["recording_path"]))

            if not recording.get("login", False):
                with PROXYS[self.proxy](
                    path=recording["recording_path"], mode="record"
                ) as proxy_service:
                    app_service = APPS[self.app](
                        proxy_service, self.certutil, self.app_path
                    )
                    app_service.start(recording["url"])

                    if not recording.get("login", None):
                        for i in range(0, RECORD_TIMEOUT):
                            print(i)
                            time.sleep(1)
                    else:
                        time.sleep(5)
                        raw_input("Do user input and press <Return>")

                    app_service.screen_shot(recording["screen_shot_path"])
                    self.information["browser_info"] = app_service.app_information()
                    app_service.stop()

            self.update_json_information(recording)
            self.generate_zip_file(recording)
            self.generate_manifest_file(recording)

    def parse_sites_json(self):
        print("Parsing sites json")
        recordings = []
        if self.sites is not None:
            with open(self.sites, "r") as sites:
                recordings_json = json.loads(sites.read())
                self.information["app"] = self.app.lower()
            if self.app in ["Firefox", "Chrome"]:
                self.information["os_name"] = platform.system()
                self.information["os_version"] = platform.release()
                platform_name = platform.system().lower()

            elif self.app in ["GeckoViewExample", "Fenix", "Fennec", "Refbrow"]:

                device = ADBAndroid()
                self.information["device_name"] = device.shell_output(
                    "getprop ro.product.model"
                )
                self.information["os_name"] = device.shell_output(
                    "getprop ro.build.user"
                )
                self.information["os_version"] = device.shell_output(
                    "getprop ro.build.version.release"
                )
                if self.information["device_name"] == "Pixel 2":
                    platform_name = "pixel2"
                elif self.information["device_name"] == "Moto G (5)":
                    platform_name = "motog5"

            for recording in recordings_json:
                label = recording.get("label", None)
                if label:
                    name = "-".join(
                        [
                            self.proxy,
                            platform_name,
                            self.app.lower(),
                            recording["domain"],
                            label,
                        ]
                    )
                else:
                    name = "-".join(
                        [
                            self.proxy,
                            platform_name,
                            self.app.lower(),
                            recording["domain"],
                        ]
                    )
                recording["path"] = os.path.join(self.path, name, name)
                recording["name"] = name

                recording["recording_path"] = "%s.mp" % recording["path"]
                recording["json_path"] = "%s.json" % recording["path"]
                recording["screen_shot_path"] = "%s.png" % recording["path"]
                recording["zip_path"] = os.path.join(
                    self.path, "%s.zip" % recording["name"]
                )
                recording["manifest_path"] = os.path.join(
                    self.path, "%s.manifest" % recording["name"]
                )

                recordings.append(recording)
        else:
            raise Exception("No site file found!!!")

        return recordings

    def update_json_information(self, recording):
        time.sleep(3)
        print("Updating json with recording information")

        with open(recording["json_path"], "r") as f:
            json_data = json.loads(f.read())

        self.information["proxy"] = self.proxy

        self.information["url"] = recording["url"]
        self.information["domain"] = recording["domain"]

        label = recording.get("label", None)
        if label:
            self.information["label"] = label

        json_data["info"] = self.information
        with open(recording["json_path"], "w") as f:
            f.write(json.dumps(json_data))

    def generate_zip_file(self, recording):
        print("Generating zip file")
        zf = zipfile.ZipFile(recording["zip_path"], "w")
        zf.write(
            recording["recording_path"], os.path.basename(recording["recording_path"])
        )
        zf.write(recording["json_path"], os.path.basename(recording["json_path"]))
        zf.write(
            recording["screen_shot_path"],
            os.path.basename(recording["screen_shot_path"]),
        )
        zf.close()

    def generate_manifest_file(self, recording):

        print("Generating manifest file")
        with open(recording["manifest_path"], "w") as f:
            manifest = {}
            manifest["size"] = os.path.getsize(recording["zip_path"])
            manifest["visibility"] = "public"
            manifest["digest"] = self._digest_file(recording["zip_path"], "sha512")
            manifest["algorithm"] = "sha512"
            manifest["filename"] = os.path.basename(recording["zip_path"])
            f.write(json.dumps(manifest))

    def replaying(self):
        with PROXYS[self.proxy](path=self.path, mode="replay") as proxy:
            app = APPS[self.app](proxy, self.certutil)
            app.start(self.url)


@click.command()
@click.option(
    "--app", required=True, type=click.Choice(APPS.keys()), help="App type to launch."
)
@click.option(
    "--app_path",
    default=None,
    help="Path to the app to lunch. If Android app path to APK file to install ",
)
@click.option(
    "--proxy",
    required=True,
    type=click.Choice(PROXYS.keys()),
    help="Proxy Service to use.",
)
@click.option("--record/--replay", default=False)
@click.option(
    "--certutil", help="Path to certutil. Note: Only when recording and Only on Android"
)
@click.option(
    "--sites",
    help="Json file containing the websites information we want ro record. Note: Only when recording",
)
@click.option(
    "--path", default="Recordings", help="Path where to store/are stored the recordings"
)
@click_config_file.configuration_option()
def cli(app, app_path, proxy, record, certutil, path, sites):
    mode = Mode(app, app_path, proxy, certutil, path, sites)
    if record:
        mode.recording()
    else:
        mode.replaying()


if __name__ == "__main__":
    cli()
