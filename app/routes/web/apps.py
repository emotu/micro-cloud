from typing import Optional, Any

from fastapi import Depends
from fastapi.exceptions import RequestValidationError, HTTPException
from pydantic import BaseModel
from starlette import status

from app.core.api.middleware import MiddlewareFactory
from app.core.api.routing import EndpointFactory
from app.core.utils.custom_fields import ReferenceField
from app.core.utils.enums import RouteTypes, EndpointTypes
from app.models import ApiCredential, User
from app.schemas.apps import ApplicationSchema, ResetApplicationSchema

# Generate required dependency methods.
user_dep = MiddlewareFactory.auth_deps(User)

# instance_dep = MiddlewareFactory.header_deps(Instance, key='x-instance-id', required=True, validate=True)
# entity_dep = MiddlewareFactory.header_deps(Business, key='x-entity-id', required=False, validate=True)
mode_dep = MiddlewareFactory.cookie_or_query_deps(key='live-mode')

# currency_dep = MiddlewareFactory.cookie_or_query_deps('currency')

dependencies = [Depends(user_dep)]

endpoint = EndpointFactory.generate(
    ApiCredential, prefix="/apps", dependencies=dependencies, route_type=RouteTypes.APP,
    user_dep=user_dep, mode_dep=mode_dep, ignored_deps=['app_id', 'entity_id'],
    create_schema=ApplicationSchema, update_schema=ApplicationSchema,
    allow_list=False, allow_fetch=False, allow_create=False, allow_update=False
)


@endpoint.action(name="reset", action_type=EndpointTypes.DETAIL, form_schema=ResetApplicationSchema)
async def _reset(
        obj_id: ReferenceField,
        model_class: ApiCredential,
        payload: BaseModel,
        extra_parameters: Optional[dict[str, str]] = None,
        **kwargs
) -> Any:
    """
    Custom action for resetting an application.
    """

    try:
        obj = await model_class.get(obj_id)
        if obj is None:
            raise RequestValidationError(errors=[dict(type="missing", msg=f"Object with id `{obj_id}` not found")])

        data = payload.model_dump()
        # trigger the create method for the object
        await obj.reset_credentials(**data)
        return obj
    except ValueError as e:
        print(e)
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail="Unknown error occurred")


@endpoint.action(name="toggle", action_type=EndpointTypes.DETAIL, form_schema=ResetApplicationSchema)
async def _toggle(
        obj_id: ReferenceField,
        model_class: ApiCredential,
        payload: BaseModel,
        **kwargs
) -> Any:
    """
    Custom action for resetting an application.
    """

    try:
        obj = await model_class.get(obj_id)
        if obj is None:
            raise RequestValidationError(errors=[dict(type="missing", msg=f"Object with id `{obj_id}` not found")])

        data = payload.model_dump()
        # trigger the create method for the object
        await obj.toggle_active()
        return obj
    except ValueError as e:
        print(e)
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail="Unknown error occurred")


endpoint.init()
