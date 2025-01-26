import logging

import uvicorn

from engin import Supply
from engin.ext.asgi import ASGIEngin
from examples.asgi.app import AppBlock, AppConfig
from examples.asgi.common.db.block import DatabaseBlock
from examples.asgi.features.cats.block import CatBlock

logging.basicConfig(level=logging.DEBUG)

app = ASGIEngin(AppBlock(), DatabaseBlock(), CatBlock(), Supply(AppConfig(debug=True)))

uvicorn.run(app)
