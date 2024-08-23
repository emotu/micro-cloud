from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import settings
from app.models import Database
from app.routes.api.assets import statuses


# UserQueryParams = QueryParams.generate(User)
# QueryDeps = Annotated[UserQueryParams, Depends(UserQueryParams)]
# check_api_header = MiddlewareFactory.api_deps(ApiCredential, public=False)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """
    Lifespan event to initialize database connections and other activity that needs to happen before the application
    accepts its first request.
    """
    _app.db = await Database.init_db(db_name=settings.DB_NAME, hostname=settings.DB_HOSTNAME, port=settings.DB_PORT)
    yield


app = FastAPI(lifespan=lifespan)
# app.include_router(users.endpoint.router)
app.include_router(statuses.router)

# app.include_router(assets.statuses.router)
# app.include_router(auth.router)


# Root api endpoint that just returns basic information about the api endpoint.
@app.get("/", tags=["Root"])
async def index():
    return dict(name=settings.API_NAME, version=settings.API_VERSION)


if __name__ == '__main__':
    import uvicorn

    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
