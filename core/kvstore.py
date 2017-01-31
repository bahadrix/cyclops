from typing import Callable
from urllib.parse import urlparse

import logging
import redis


def createPool(address) -> redis.ConnectionPool:
    u = urlparse(address)
    hostParts = str(u.netloc).split(":")
    host = hostParts[0]
    port = hostParts[1]
    db = str(u.path).replace("/", "")
    return redis.ConnectionPool(host=host, port=port, db=db, decode_responses=True)


log = logging.getLogger("KVStore")


class KVStore:
    def __init__(self, pool: redis.ConnectionPool):
        self.pool = pool
        self.baseConn = self.__newConn()
        self.breakSubscription = False

    def __newConn(self) -> redis.Redis:
        return redis.Redis(connection_pool=self.pool)

    def addURLToHash(self, hashHex, url):
        key = "hash:{}:elements".format(hashHex)
        self.baseConn.sadd(key, url)

        # Reverse
        key = "url:{}".format(url)
        self.baseConn.set(key, hashHex)

    def addHash(self, node, hashHex, url):
        key = "hash:{}:node".format(hashHex)
        self.baseConn.set(key, node)

        key = "hash:{}:elements".format(hashHex)
        self.baseConn.sadd(key, url)

        # Reverse
        key = "url:{}".format(url)
        self.baseConn.set(key, hashHex)

    def hashExists(self, hashHex) -> bool:
        key = "hash:{}:elements".format(hashHex)
        return self.baseConn.exists(key)

    def getHashURLs(self, hashHex, limit=0) -> list:
        conn = self.__newConn()
        key = "hash:{}:elements".format(hashHex)
        results = []
        cursor = 0
        while True:
            cursor, elements = conn.sscan(key, cursor=cursor)
            results = results + elements
            if cursor == 0 or (limit != 0 and len(results) >= limit):
                break

        return results

    def publish(self, key, item):
        conn = self.__newConn()
        conn.lpush(key, item)

    def subscribe(self, key, fetcherName, listener: Callable[[str], None]):
        activeQueue = "fetch:active:{}:{}".format(fetcherName, key)
        conn = self.__newConn()
        while not self.breakSubscription:
            item = conn.brpoplpush(key, activeQueue, 10)
            if item is not None:
                try:
                    listener(item)
                except Exception as e:
                    conn.lpop(activeQueue)
                    conn.lpush("fetch:errors:{}:{}".format(fetcherName, key), item)
                    log.error(
                        "Subscriber '{}' has been raised an error for item '{}': {}".format(fetcherName, item, str(e)))
                    continue

                conn.lpop(activeQueue)
            else:  # No new items in given interval, refreshing the connection
                conn = self.__newConn()

    def increaseStat(self, category: str, stat: str, increment: int = 1):
        conn = self.__newConn()
        conn.hincrby("stats:{}".format(category), stat, increment)
