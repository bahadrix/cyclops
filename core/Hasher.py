from PIL import Image
import requests
import imagehash
from io import BytesIO


def hashFromURL(url):
    """
    Returns hash in bytes string by getting image from given url
    :param url: Target image url
    :return: Hash in hex format prefixed with 0x
    """

    response = requests.get(url)
    if response.status_code != 200:
        raise FileNotFoundError("Response returned for url {} is {}".format(url, response.status_code))
    img = Image.open(BytesIO(response.content))
    return hashImg(img)


def hashImg(img):
    hash = imagehash.phash(img)
    return hash.hash.tobytes()
