"""
middleware.py

Authentication and authorization api that will be used throughout the application
"""
from functools import wraps
from typing import Annotated, Callable, Any, Type

from beanie import Document, PydanticObjectId
from fastapi import Header, HTTPException, status, Depends, Query, Cookie
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import ExpiredSignatureError, InvalidSignatureError
from pydantic_core import ValidationError

from app.core.utils.custom_fields import AuthToken, AppToken
from app.core.utils.enums import ApplicationErrors


def authorize_permission(klass: Type[Document], role: list):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):

            set_role = set(role)
            if len(set_role) < 1:
                return await func(*args, **kwargs)
            user_id = kwargs.get("extra_parameters").user_id if kwargs.get("extra_parameters") else kwargs.get(
                "user_id")
            user = await klass.get(user_id)
            print("user role", user.permissions)
            has_role = any(permission.value in set_role for permission in user.permissions)

            if not has_role:
                raise HTTPException(status_code=403, detail="User does not have permission to perform this action")
            return await func(*args, **kwargs)

        return wrapper

    return decorator


class MiddlewareFactory:
    """ Factory class to generate middleware"""

    @classmethod
    def authorize_permission_decorator(cls, *, klass: Type[Document], roles: list[str]) -> Callable:
        return authorize_permission(klass, roles)

    @classmethod
    def auth_deps(cls, klass: Type[Document], public: bool = False, validate: bool = True) -> Callable:

        security = HTTPBearer(auto_error=False)

        async def dependency(authorization: Annotated[HTTPAuthorizationCredentials, Depends(security)] = None):
            """
            Dependency function to check that a user is authenticated before attempting to execute the request endpoint.
            It validates the authorization header to determine if a user has successfully logged in.

            This dependency is designed to not return any parameters and so, can be used as a route dependency.

            """

            # 0. If endpoint is public, don't bother with anything else
            if public is True:
                return

            # 1. Check that the authorization header is present
            if not (authorization and authorization.credentials):
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                    detail=[
                                        dict(
                                            type="authentication_error",
                                            code=ApplicationErrors.TOKEN_REQUIRED.value,
                                            loc=["header", "authorization"],
                                            msg=ApplicationErrors.TOKEN_REQUIRED.message)
                                    ])

            # 2. Decode authorization header here and identify the user.
            # 3. Check that the user exists and is not suspended
            try:
                # validate token and extract user_id
                _user_id = AuthToken.get_user_id(authorization.credentials)
                if not _user_id:
                    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                        detail=[
                                            dict(
                                                type="authentication_error",
                                                code=ApplicationErrors.TOKEN_INVALID.value,
                                                loc=["header", "authorization"],
                                                msg=ApplicationErrors.TOKEN_INVALID.message)
                                        ])

                # check that the user exists and isn't suspended, if validate is set to True
                if validate is True:
                    user = await klass.get(_user_id)
                    if not user or user.is_suspended:
                        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                            detail=[
                                                dict(
                                                    type="authentication_error",
                                                    code=ApplicationErrors.TOKEN_DENIED.value,
                                                    loc=["header", "authorization"],
                                                    msg=ApplicationErrors.TOKEN_DENIED.message)
                                            ])

                return _user_id
            except ExpiredSignatureError:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                    detail=[
                                        dict(code=ApplicationErrors.TOKEN_EXPIRED.value,
                                             type="authentication_error",
                                             loc=["header", "authorization"],
                                             msg=ApplicationErrors.TOKEN_EXPIRED.message)
                                    ])
            except InvalidSignatureError:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                    detail=[
                                        dict(type="authentication_error",
                                             code=ApplicationErrors.TOKEN_INVALID.value,
                                             loc=["header", "authorization"],
                                             msg=ApplicationErrors.TOKEN_INVALID.message)
                                    ])

            except ValidationError as e:
                print(e)
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                    detail=[
                                        dict(
                                            type="authentication_error",
                                            code=ApplicationErrors.TOKEN_DENIED.value,

                                            loc=["header", "authorization"],
                                            msg=ApplicationErrors.TOKEN_DENIED.message)
                                    ])

        return dependency

    @classmethod
    def header_deps(cls, klass: Type[Document], key: str, required: bool = True,
                    validate: bool = False) -> Callable:
        """
        Identity and validate a required parameter in the headers for every request. This dependency is designed to
        extract parameters like instance_id, entity_id, roles, and other values required to complete transactions
        """

        async def dependency(parameter: Annotated[PydanticObjectId | str, Header(alias=key)] = None) -> Any:
            """
            Extract a specific parameter from the headers and return the parameter value as a string,
            carrying the specified key alias.
            """

            # 1. For required header dependencies, reject the request if the attribute isn't present

            if not parameter and required is True:
                # If it is a required parameter, then stop all operations and raise an exception
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                    detail=dict(code=ApplicationErrors.HEADER_ATTRIBUTE_MISSING.value,
                                                message=ApplicationErrors.HEADER_ATTRIBUTE_MISSING.message))

            # 2. Check that the requested parameter is valid if validate is set to True.
            # attribute = await klass.find({attr: parameter}).first_or_none()
            if parameter and validate is True:
                try:
                    attribute = await klass.get(parameter)
                    if not attribute and required is True:
                        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                            detail=dict(code=ApplicationErrors.HEADER_ATTRIBUTE_INVALID.value,
                                                        message=ApplicationErrors.HEADER_ATTRIBUTE_INVALID.message))
                except ValidationError:
                    if required is True:
                        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                            detail=dict(code=ApplicationErrors.HEADER_ATTRIBUTE_INVALID.value,
                                                        message=ApplicationErrors.HEADER_ATTRIBUTE_INVALID.message))

            return parameter

        return dependency

    @classmethod
    def cookie_or_query_deps(cls, key: str, default: Any = None) -> Callable:
        """
        Identity and validate a required parameter in the headers for every request. This dependency is designed to
        extract parameters like instance_id, entity_id, roles, and other values required to complete transactions
        """
        header_key = f"x-{key}" if not key.startswith("x-") else key

        async def dependency(
                header_parameter: Annotated[
                    PydanticObjectId | str,
                    Header(alias=header_key)
                ] = None, cookie_parameter: Annotated[
                    PydanticObjectId | str,
                    Cookie(alias=key)
                ] = None,
                query_parameter: Annotated[
                    PydanticObjectId | str,
                    Query(alias=key)
                ] = None
        ) -> Any:
            """
            Extract a specific parameter from the headers and return the parameter value as a string,
            carrying the specified key alias.
            """

            # In order of priority, header, then cookie, then query.
            parameter = header_parameter or cookie_parameter or query_parameter
            return parameter or default

        return dependency

    @classmethod
    def api_deps(cls, klass: Type[Document], public: bool = False) -> Callable:

        security = HTTPBearer()

        async def dependency(authorization: Annotated[HTTPAuthorizationCredentials, Depends(security)]):
            """
            Dependency function to check that a user is authenticated before attempting to execute the request endpoint.
            It validates the authorization header to determine if a user has successfully logged in.

            This dependency is designed to not return any parameters and so, can be used as a route dependency.

            """

            # 0. If endpoint is public, don't bother with anything else
            if public is True:
                return

            # 1. Check that the authorization header is present
            if not authorization.credentials:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                    detail=dict(code=ApplicationErrors.TOKEN_REQUIRED.value,
                                                message=ApplicationErrors.TOKEN_REQUIRED.message))

            # 2. Decode authorization header here and identify the app.

            # 3. Check that the user exists and is not suspended
            try:
                # validate token and extract user_id
                if not authorization.credentials:
                    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                        detail=dict(code=ApplicationErrors.TOKEN_INVALID.value,
                                                    message=ApplicationErrors.TOKEN_INVALID.message))

                # check that the user exists and isn't suspended, if validate is set to True
                api_credential = await klass.find_by_key(authorization.credentials)
                if not api_credential or api_credential.is_active is False:
                    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                        detail=dict(code=ApplicationErrors.TOKEN_DENIED.value,
                                                    message=ApplicationErrors.TOKEN_DENIED.message))

                token = AppToken(
                    key=authorization.credentials, app_id=api_credential.app_id,
                    user_id=api_credential.user_id
                )
                return token
            except ExpiredSignatureError:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                    detail=dict(code=ApplicationErrors.TOKEN_EXPIRED.value,
                                                message=ApplicationErrors.TOKEN_EXPIRED.message))

            except ValidationError as e:
                print(e)
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                    detail=dict(code=ApplicationErrors.TOKEN_DENIED.value,
                                                message=ApplicationErrors.TOKEN_DENIED.message))

        return dependency
