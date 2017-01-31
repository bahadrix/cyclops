import logging

from core.kvstore import createPool, KVStore
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)s] %(levelname)s: %(message)s'
)

logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3.connectionpool").setLevel(logging.WARNING)
logging.getLogger("requests.packages.urllib3").setLevel(logging.WARNING)


kvs = KVStore(createPool("tcp://localhost:6379/1"))

kvs.publish("arabas", "tofasa")

def onItem(item):
    raise Exception("Boyle item mi olue?")
    print("Le item: {}".format(item))


kvs.subscribe("arabas", "cemil", onItem)