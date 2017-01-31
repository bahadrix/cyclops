import time

import core.Hasher
import connexion
from pymvptree import Tree, Point
from core import instance as c
import logging
import argparse

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)s] %(levelname)s: %(message)s'
)

logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3.connectionpool").setLevel(logging.WARNING)
logging.getLogger("requests.packages.urllib3").setLevel(logging.WARNING)

parser = argparse.ArgumentParser(description='Cyclops Hash Push Client')
parser.add_argument('-c', '--config', default="~/.cyclops/config.yml",
                    help="Config file location")
args = parser.parse_args()
print(args.config)
c.init(args.config)


if __name__ == '__main__':
    app = connexion.App(__name__, specification_dir='./swagger/', )
    app.add_api('swagger.yaml', arguments={
        'title': 'Image hash storage and similarity search engine'})

    app.run(
        host=c.config['rest']['host'],
        port=c.config['rest']['port'])
