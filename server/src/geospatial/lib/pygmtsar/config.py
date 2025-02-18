import os

env = os.environ.copy()
env["GMTSAR_PATH"] = "/usr/local/GMTSAR"
env["PATH"] = f"{env['GMTSAR_PATH']}/bin:{env['PATH']}"
