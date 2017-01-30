import logging
import os.path
import threading
from threading import Lock
import pika
from pymvptree import Tree, Point
import util
from core import Hasher
from core.kvstore import KVStore


class TreeWorker:
    def __init__(self, name, dbFile, amqpAddress, kvStore: KVStore, leafCap=4096, autoSave=False, autoSaveInterval=10,
                 prefetch=10):

        self.prefetch = int(prefetch)
        self.kvStore = kvStore
        self.logger = logging.getLogger("TreeWorker:{}".format(name))
        self.mutex = Lock()
        self.name = name
        self.dbFile = dbFile
        self.autoSave = autoSave
        self.autoSaveInterval = int(autoSaveInterval)
        self.dirty = False
        self.amqpAddress = amqpAddress
        self.produceChannel = util.newAMQPConnection(self.amqpAddress).channel()

        if os.path.isfile(dbFile):  # File exists
            self.logger.info("Reading file {}".format(dbFile))
            self.tree = Tree.from_file(dbFile)
        else:
            self.tree = Tree(leafcap=leafCap)
        self.listenHashQueue()

        if autoSave:
            self.logger.debug("Starting auto-save cycle.")
            self.__autoSaveCycle()

    def __autoSaveCycle(self):
        if self.dirty:
            self.logger.info("Tree is dirty, auto-saving now..")
            self.save()
            self.logger.info("Auto-save done.")
        threading.Timer(self.autoSaveInterval, self.__autoSaveCycle).start()

    def onHashURL(self, ch, method, properties, body):
        err = ""
        url = str(body, "utf-8")
        try:
            self.addFromURL(url)
            self.logger.info("URL added: {}".format(url))
        except FileNotFoundError as e:
            err = "Download error: {}".format(e)
        except Exception as e:
            err = "Unknown error: {}".format(e)
        finally:
            ch.basic_ack(delivery_tag=method.delivery_tag)
            if err != "":
                self.produceChannel.basic_publish(
                    exchange='',
                    routing_key="cyclops_hashing_urls_errors",
                    properties=pika.BasicProperties(headers={
                        "error": err,
                        "worker": self.name,
                    }),
                    body=url
                )

    def __consumeCycle(self):
        while True:
            consumeChannel = util.newAMQPConnection(self.amqpAddress).channel()
            consumeChannel.basic_qos(prefetch_count=self.prefetch)
            consumeChannel.basic_consume(self.onHashURL,
                                         queue='cyclops_hashing_urls')
            try:
                consumeChannel.start_consuming()
            except Exception as e:
                self.logger.warning("Queue listener stopped, restarting immediately. Error is {}".format(e))

    def listenHashQueue(self):
        self.logger.debug("Starting queue listeners.")

        self.produceChannel.queue_declare(queue="cyclops_hashing_urls_errors", durable=True)

        threading.Thread(target=self.__consumeCycle).start()

        self.logger.info("Queue listeners started.")

    def save(self):
        self.mutex.acquire()
        try:
            self.logger.info("Save tree to file {}".format(self.dbFile))
            self.tree.to_file(self.dbFile)
            self.dirty = False
        finally:
            self.mutex.release()

    def query(self, hash, radius, limit=65535):
        self.mutex.acquire()
        self.logger.info("Query received")
        try:
            return self.tree.filter(hash, radius, limit)
        finally:
            self.mutex.release()

    def addHash(self, hash, url, lock=True):

        if lock:
            self.mutex.acquire()
        try:
            hashHex = util.binaryBytesToHex(hash)
            if self.kvStore.hashExists(hashHex):  # Hash exists, just append url
                self.logger.debug("Hash already exist, just appending url. {}".format(url))
                self.kvStore.addURLToHash(hashHex, url)
            else:  # Add hash first time
                self.tree.add(Point(url, hash))
                self.kvStore.addHash(self.name, hashHex, url)
                self.dirty = True
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

    def addFromURLs(self, urls):
        hashes = {}
        for url in urls:
            try:
                hash = Hasher.hashFromURL(url)
                hashes[url] = hash
            except FileNotFoundError as err:
                self.logger.error(err)

        self.addHashes(hashes)
