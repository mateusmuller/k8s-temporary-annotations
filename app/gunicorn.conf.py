import multiprocessing

bind = "0.0.0.0:8443"
workers = multiprocessing.cpu_count() * 2 + 1
# workers = "1"
keyfile = "server.key"
certfile = "server.crt"
accesslog = "-"
errorlog = "-"
loglevel = "debug"
preload_app = "true"