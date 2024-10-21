import logging

import uvicorn

from engin import Supply
from engin.extensions.asgi import ASGIEngin
from examples.asgi.app import AppConfig, AppModule

logging.basicConfig(level=logging.DEBUG)

app = ASGIEngin(AppModule(), Supply(AppConfig(debug=True)))

uvicorn.run(app)
