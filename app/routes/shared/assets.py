from fastapi import Depends

from app.core.api.middleware import MiddlewareFactory
from app.core.api.routing import EndpointFactory
from app.models import User, Status
from app.schemas.users import StatusCreateSchema, StatusUpdateSchema

# Generate required dependency methods.
user_dep = MiddlewareFactory.auth_deps(User, public=True)
# instance_dep = MiddlewareFactory.header_deps(Instance, key='x-instance-id', required=False, validate=False)
entity_dep = MiddlewareFactory.header_deps(User, key='x-entity-id', required=False, validate=False)

# Build Endpoint parameters
dependencies = [Depends(user_dep)]
# Define ignored dependencies that do not apply to this specific endpoint.
ignored_deps = ["entity_id", "user_id", "currency"]

# Generate endpoint
statuses = EndpointFactory.generate(
    Status, prefix="/statuses", dependencies=dependencies, user_dep=user_dep,
    entity_dep=entity_dep, ignored_deps=ignored_deps, allow_delete=False, allow_update=False,
    allow_create=False,
    create_schema=StatusCreateSchema, update_schema=StatusUpdateSchema
)

statuses.init()
