from __future__ import absolute_import, print_function


import time
from mitmproxy import ctx


class AddDetrministic():

    def response(self, flow):
        millis = int(round(time.time() * 1000))

        # ---------Inject into HTML----------#
        if "content-type" in flow.response.headers:

            if 'text/html' in flow.response.headers["content-type"]:
                ctx.log.info("Working on {}".format(flow.response.headers["content-type"]))

                flow.response.decode()

                html = bytes(flow.response.content).decode("utf-8")
                firstScriptIndex = html.find("<script>")
                if firstScriptIndex >0:
                    with open("scripts/deterministic.js", "r") as jsfile:
                        js = jsfile.read().replace("REPLACE_LOAD_TIMESTAMP", str(millis))
                        new_html = html[:firstScriptIndex] + "<script>" + js + "</script>" + html[firstScriptIndex:]

                        flow.response.content = bytes(new_html, "utf-8")
                    ctx.log.info("Success In request {} added deterministic JS".format(flow.request.url))
                else:
                    ctx.log.info("Fail In request {} no <head> tag found".format(flow.request.url))

def start():
    ctx.log.info("Load Detrministic")
    return AddDetrministic()

