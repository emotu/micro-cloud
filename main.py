from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import settings
from app.models import Database

from app.routes.web import apps, auth

from app.routes.shared import assets


# UserQueryParams = QueryParams.generate(User)
# QueryDeps = Annotated[UserQueryParams, Depends(UserQueryParams)]


# check_instance_id = MiddlewareFactory.header_deps(Instance, key='x-instance-id', required=True, validate=True)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """
    Lifespan event to initialize database connections and other activity that needs to happen before the application
    accepts its first request.
    """
    _app.db = await Database.init_db(db_name=settings.DB_NAME, hostname=settings.DB_HOSTNAME, port=settings.DB_PORT,
                                     password=settings.MONGO_PASSWORD, username=settings.MONGO_USERNAME,
                                     params=settings.MONGO_URI_PARAMS)
    yield

app = FastAPI(lifespan=lifespan)

app.include_router(auth.endpoint.router)
app.include_router(apps.endpoint.router)

app.include_router(assets.statuses.router)

# app.include_router(addresses.shipment_address_endpoint.router)


# Root api endpoint that just returns basic information about the api endpoint.
@app.get("/", tags=["Root"])
async def index():
    return dict(name=settings.API_NAME, version=settings.API_VERSION)


if __name__ == '__main__':
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8003, reload=True, workers=1)
