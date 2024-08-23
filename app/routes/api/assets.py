from fastapi import Depends

from app.core.api.middleware import MiddlewareFactory
from app.core.api.routing import EndpointFactory
from app.core.utils.enums import RouteTypes
from app.models import Status, ApiCredential
from app.schemas.users import StatusCreateSchema, StatusUpdateSchema

check_api_credentials = MiddlewareFactory.api_deps(ApiCredential)

dependencies = [Depends(check_api_credentials)]

statuses = EndpointFactory.generate(
    ApiCredential, prefix="/solids", route_type=RouteTypes.API, dependencies=dependencies,
    api_dep=check_api_credentials, create_schema=StatusCreateSchema, update_schema=StatusUpdateSchema,
    allow_create=False, allow_update=False, allow_delete=False
)

statuses.init()
