from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from app.api import router

app = FastAPI(
    description='Network Solution Backend',
    docs_url='/api/v1/docs',
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

app.include_router(router)
