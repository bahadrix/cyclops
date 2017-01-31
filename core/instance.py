import pprint
import string
import threading
from datetime import datetime
import redis
import yaml
import queue
import util
from core import Hasher
from core import kvstore
from core.worker import TreeWorker
import os.path
import logging

from util import binaryBytesToHex

config = {}
workers = {}  # type: dict[TreeWorker]
logger = logging.getLogger(__name__)
redisPool = None  # type: redis.ConnectionPool
kv = None  # type: kvstore.KVStore


def init(configLocation):
    global config
    global workers
    global redisPool
    global kv

    # Reading config
    with open(configLocation) as stream:
        config = yaml.load(stream)

    # Checking paths
    for key in config["path"]:
        config["path"][key] = os.path.expandvars(config["path"][key])
        os.makedirs(config["path"][key], exist_ok=True)

    logger.info("Config \n{}".format(pprint.pformat(config, indent=4)))

    # Redis

    redisAddress = string.Template(config["redis"]["address"]).substitute(os.environ)
    logger.info("Redis server address is {}".format(redisAddress))
    redisPool = kvstore.createPool(redisAddress)
    kv = kvstore.KVStore(redisPool)

    threads = []

    autoSaveEnabled = config["settings"]["autosave"]["enabled"]
    if autoSaveEnabled:
        logger.info("Auto-save is enabled with {} seconds interval.".format(config["settings"]["autosave"]["interval"]))

    def starter(workerName, workers):
        logger.info("Starting {}".format(workerName))
        fullpath = os.path.join(config["path"]["data"], "{}.mvp".format(workerName))
        kv = kvstore.KVStore(redisPool)
        w = TreeWorker(workerName, fullpath, kv,
                       autoSave=config["settings"]["autosave"]["enabled"],
                       autoSaveInterval=config["settings"]["autosave"]["interval"])
        workers[workerName] = w

    for workerName in config['workers']:
        t = threading.Thread(target=starter, args=(workerName, workers,))
        t.start()
        threads.append(t)

    for t in threads:
        t.join()

    logger.info("Workers are started.")


def getHashURLSet(hashValue, limit: int = 0) -> list:
    """
    Returns url set of given hash
    :param hashValue: Hash value. Must be long/integer or hex starts with '0x'
    :param limit: zero for no limit
    :return: URL list
    """

    if not str(hashValue).startswith("0x"):
        hashHex = hex(int(hashValue))
    else:
        hashHex = hashValue
    return kv.getHashURLs(hashHex, limit)


def publishURLToHash(url):
    kv.publish("cyclops_hashing_urls", url)


def queryByURL(url, radius, k):
    global workers
    hash = Hasher.hashFromURL(url)
    hashHex = binaryBytesToHex(hash)
    queryString = "QUERY: URL({url}), H({hash}) r({radius}) k({k})".format(url=url, hash=hashHex, radius=radius, k=k)
    logger.info(queryString)

    def execQuery(w: TreeWorker, h, r: float, limit: int, q: queue.Queue):
        results = w.query(h, r, limit)

        for point in results:
            q.put({
                "url": point.point_id,
                "dist": util.hamming(hash, point.data),
                "hash": binaryBytesToHex(point.data)
            }, False)

    threads = []
    resultQueue = queue.Queue()

    startTime = datetime.now()

    for workerName, worker in workers.items():
        t = threading.Thread(target=execQuery, args=(worker, hash, radius, k, resultQueue,))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    elapsaedTime = datetime.now() - startTime
    results = [r for r in resultQueue.queue]
    sortedResults = sorted(results, key=lambda r: r['dist'])
    return {
        "queryString": queryString,
        "ref": hashHex,
        "total_results": len(results),
        "total_elapsed": elapsaedTime.microseconds / 1000.0,
        "results": sortedResults
    }
