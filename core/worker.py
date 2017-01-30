import logging
import os.path
import threading
from threading import Lock
from pymvptree import Tree, Point
import util
from core import Hasher
from core.kvstore import KVStore


class TreeWorker:
    def __init__(self, name, dbFile, kvStore: KVStore, leafCap=4096, autoSave=False, autoSaveInterval=10):

        self.kvStore = kvStore
        self.logger = logging.getLogger("TreeWorker:{}".format(name))
        self.mutex = Lock()
        self.name = name
        self.dbFile = dbFile
        self.autoSave = autoSave
        self.autoSaveInterval = int(autoSaveInterval)
        self.dirty = False

        if os.path.isfile(dbFile):  # File exists
            self.logger.info("Reading file {}".format(dbFile))
            self.tree = Tree.from_file(dbFile)
        else:
            self.tree = Tree(leafcap=leafCap)
        self.listenHashQueue()

        if autoSave:
            self.logger.debug("Starting auto-save cycle.")
            self.__autoSaveCycle()
        self.increaseStat("initialized")

    def increaseStat(self, stat: str, increment: int = 1):
        self.kvStore.increaseStat("worker:{}".format(self.name), stat, increment)

    def __autoSaveCycle(self):
        if self.dirty:
            self.logger.info("Tree is dirty, auto-saving now..")
            self.save()
            self.logger.info("Auto-save done.")
        threading.Timer(self.autoSaveInterval, self.__autoSaveCycle).start()

    def onHashURL(self, url):

        self.addFromURL(url)
        self.increaseStat("consumed_url")
        self.logger.info("URL added: {}".format(url))

    def __consumeCycle(self):
        key = "cyclops_hashing_urls"
        self.logger.info("Listening key {}".format(key))
        self.kvStore.subscribe(key, self.name, lambda url: self.onHashURL(url))

    def listenHashQueue(self):
        self.logger.debug("Starting queue listeners.")
        threading.Thread(target=self.__consumeCycle).start()

    def save(self):
        self.mutex.acquire()
        try:
            self.logger.info("Save tree to file {}".format(self.dbFile))
            self.tree.to_file(self.dbFile)
            self.dirty = False
        finally:
            self.mutex.release()
            self.increaseStat("db_saved")

    def query(self, hash, radius, limit=65535):
        self.logger.info("Query received")
        self.mutex.acquire()
        try:
            return self.tree.filter(hash, radius, limit)
        finally:
            self.mutex.release()
            self.increaseStat("query_executed")

    def addHash(self, hash, url, lock=True):

        if lock:
            self.mutex.acquire()
        try:
            hashHex = util.binaryBytesToHex(hash)
            if self.kvStore.hashExists(hashHex):  # Hash exists, just append url
                self.logger.debug("Hash already exist, just appending url. {}".format(url))
                self.kvStore.addURLToHash(hashHex, url)
                self.increaseStat("url_append")
            else:  # Add hash first time
                self.tree.add(Point(url, hash))
                self.kvStore.addHash(self.name, hashHex, url)
                self.dirty = True
                self.increaseStat("hash_add")
        finally:
            if lock:
                self.mutex.release()

    def addHashes(self, hashes):
        """dict[url]hash"""
        self.mutex.acquire()
        try:
            for url, hash in hashes.items:
                self.addHash(hash, url, lock=False)
        finally:
            self.mutex.release()

    def addFromURL(self, url):
        try:
            hash = Hasher.hashFromURL(url)
            self.addHash(hash, url)
        except FileNotFoundError as err:
            self.logger.error(err)
            raise err
