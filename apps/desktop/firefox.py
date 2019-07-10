from mozversion import mozversion
from selenium.webdriver import Firefox, FirefoxOptions

from apps.desktop.base_desktop_app import BaseDesktopApp


class DesktopFirefox(BaseDesktopApp):
    def start(self, url="about:blank"):
        options = FirefoxOptions()
        options.set_preference("network.proxy.type", 1)
        options.set_preference("network.proxy.http", "127.0.0.1")
        options.set_preference("network.proxy.http_port", 8080)
        options.set_preference("network.proxy.ssl", "127.0.0.1")
        options.set_preference("network.proxy.ssl_port", 8080)
        options.set_preference("security.csp.enable", True)

        self.driver = Firefox(options=options, firefox_binary=self.app_path)
        self.driver.get(url)

    def app_information(self):
        if self.app_path:
            self.version = mozversion.get_version(binary=self.app_path)
        else:
            self.version["browserName"] = self.driver.capabilities["browserName"]
            self.version["browserVersion"] = self.driver.capabilities["browserVersion"]
            self.version["buildID"] = self.driver.capabilities["moz:buildID"]

        return self.version
