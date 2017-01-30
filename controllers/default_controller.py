import logging
import os

from pymvptree import MVPError

from core import instance as c

logger = logging.getLogger(__name__)
myloc = os.path.dirname(os.path.realpath(__file__))
helpDoc = os.path.abspath(os.path.join(myloc, os.pardir, "docs", "api", "index.html"))


def db_save_get() -> str:
    return 'do some magic!'


def hash_hash_count_get(hash) -> str:
    return 'do some magic!'


def hash_hash_get(hash, limit=0):
    urls = c.getHashURLSet(hash, limit)
    return {"urls": urls}


def hashes_put(body) -> str:
    return 'do some magic!'


def doc_get() -> str:
    with open(str(helpDoc), 'r') as content_file:
        contents = content_file.read()
    return contents


def query_mvp_url_post(body):
    try:
        return c.queryByURL(body["URL"], body["radius"], body["k"])
    except FileNotFoundError as e:
        logger.error(e)
        raise e
    except MVPError as e:
        logger.error(e)
        raise Exception("MVP Error", e)


def urls_put(body):
    for url in body:
        c.publishURLToHash(url)

    return {"status": "success"}
