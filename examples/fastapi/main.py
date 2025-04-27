import logging

import uvicorn

from engin import Supply
from engin.extensions.fastapi import FastAPIEngin
from examples.fastapi.app import AppBlock, AppConfig
from examples.fastapi.routes.cats.block import CatBlock

logging.basicConfig(level=logging.DEBUG)

app = FastAPIEngin(AppBlock(), CatBlock(), Supply(AppConfig(debug=True), override=True))


if __name__ == "__main__":
    uvicorn.run(app)
