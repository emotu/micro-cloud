"""
routing.py

Endpoint generator for api routes.

This module contains function generators that aid in preparing all routing endpoints needed to for all api endpoints.
By default, an initialized endpoint will contain routing functionality for list, fetch,
create, update, delete and bulk actions like (put/post).

For list and fetch endpoints, it will also house functionality to handle extraction and processing of query parameters,
and preparing the standard query response structure.Route specific dependencies will also be factored into filtering,
creating and updating data as required.
"""
from typing import Annotated, Type, Any, Callable, Sequence, Optional, Awaitable

from beanie import PydanticObjectId, Document
from beanie.exceptions import DocumentNotFound
from fastapi import APIRouter, Depends, status, HTTPException, BackgroundTasks
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, computed_field

from app.core.api.middleware import MiddlewareFactory
from app.core.api.queryparams import QueryParams
from app.core.utils.custom_fields import ReferenceField, ExtraParameters, format_validation_error
from app.core.utils.enums import ListResponse, ApplicationErrors, RouteTypes, EndpointTypes

PermissionsType = Callable[[Callable[..., Awaitable[Any]]], Callable[..., Awaitable[Any]]]

default = MiddlewareFactory.authorize_permission_decorator(klass=Document,roles=[])


class EndpointAction(BaseModel):
    name: str
    func: Callable
    action_type: EndpointTypes
    ignored_deps: Optional[list[str]] = []
    service_class: Type[BaseModel]
    permissions: Optional[list[str]] = []
    form_schema: Type[BaseModel]
    response_model: Type[BaseModel]

    @computed_field
    def path(self) -> str:
        if self.action_type in [EndpointTypes.LIST, EndpointTypes.DETAIL]:
            return "/".join(["/{obj_id}", self.name])
        if self.action_type in [EndpointTypes.MANY]:
            return "/".join(["/_action", self.name])
        return f"/{self.name}"


class Endpoint:
    """
    Class generator with default functions that can provide default functionality for basic crud functions.
    To customize any of the endpoints, use the wrapper function to override the internally defined endpoint.

    The class will support the following endpoints:
        list, 'fetch', 'create', 'update', 'delete', 'list_action', 'object_action', 'search'

    """

    def __init__(
            self, model_class: Type[Document],
            prefix: str, route_type: RouteTypes,
            list_func: Callable, fetch_func: Callable,
            create_func: Callable, update_func: Callable,
            delete_func: Optional[Callable] = None,
            dependencies: Sequence[Depends] = [],
            user_dep: Callable = None,
            instance_dep: Callable = None,
            entity_dep: Callable = None,
            currency_dep: Callable = None,
            mode_dep: Callable = None,
            api_dep: Callable = None,
            create_schema: Type[BaseModel] = None,
            update_schema: Type[BaseModel] = None,
            allow_list: bool = True,
            allow_fetch: bool = True,
            allow_create: bool = True,
            allow_update: bool = True,
            allow_delete: bool = False,
            ignored_deps: list = [],
            permissions: PermissionsType | None= None
    ):
        self.prefix = prefix
        self.model_class = model_class
        self.route_type = route_type

        self._list: Callable = list_func
        self._fetch: Callable = fetch_func
        self._create: Callable = create_func
        self._update: Callable = update_func
        self._delete: Callable = delete_func
        self.instance_dep = instance_dep
        self.entity_dep = entity_dep
        self.user_dep = user_dep
        self.mode_dep = mode_dep
        self.api_dep = api_dep
        self.currency_dep = currency_dep
        self.create_schema = create_schema
        self.update_schema = update_schema
        self.allow_list = allow_list
        self.allow_fetch = allow_fetch
        self.allow_create = allow_create
        self.allow_update = allow_update
        self.allow_delete = allow_delete
        self.ignored_deps = ignored_deps
        self.permissions =  permissions
        self._list_actions_registry: Sequence[EndpointAction] = []
        self._detail_actions_registry: Sequence[EndpointAction] = []
        self._sub_query_registry: Sequence[EndpointAction] = []

        self.router = APIRouter(prefix=prefix, dependencies=dependencies)

    def init(self):
        """
        Initialization function that triggers the connection of all routes and other actions requirements to
        generate the connected api routes
        """

        self.init_list_endpoint()
        self.init_fetch_endpoint()
        self.init_create_endpoint()
        self.init_update_endpoint()
        self.init_delete_endpoint()

    def action(
            self, *, action_type: EndpointTypes = EndpointTypes.DETAIL,
            name: str = None, ignored_deps: list[str] = [], form_schema: Optional[Type[BaseModel]] = None,
            model_class: Optional[Type[BaseModel]] = None, response_model: Optional[Type[BaseModel]] = None
    ) -> Callable:
        """
        Decorator method to dynamically register new endpoints into the registry. The endpoint acts as a decorator
        that registers the decorated function as a handler for a configured url.


        :param action_type: one of 'list|detail'. Used to define the route path for the action
        :param name: function name, used as an alternative if the path isn't specified
        :param ignored_deps: dependencies to ignore when processing action function
        :param form_schema: data validation schema (optional). If non is provided, data will be transmitted as is.
        :param model_class: alternative model class to work on. If not provided, model_class from endpoint is used
        :param response_model: alternative response_model. If not provided, response_model from endpoint is used
        :return:

        """

        def decorator(func: Callable):
            """ Decorator that executes registration """
            _ignored_deps = ignored_deps if ignored_deps else self.ignored_deps
            _response_model = response_model if response_model else self.model_class
            _model_class = model_class if model_class else self.model_class

            func_name = name if name else func.__name__
            _form_schema = form_schema if form_schema else self.model_class

            _action = EndpointAction(
                func=func, name=func_name, service_class=_model_class,
                action_type=action_type, ignored_deps=_ignored_deps,
                response_model=_response_model, form_schema=_form_schema)

            # If actions are create, update or delete, replace default function
            if action_type is EndpointTypes.CREATE:
                self._create = func
            if action_type is EndpointTypes.UPDATE:
                self._update = func
            if action_type is EndpointTypes.DELETE:
                self._delete = func
            if action_type is EndpointTypes.LIST:
                self._list = func

            # If actions are to fetch or update single or many items, append as action endpoints
            if action_type in [EndpointTypes.SINGLE, EndpointTypes.MANY, EndpointTypes.DETAIL]:
                self.init_action_endpoint(_action)
            if action_type in [EndpointTypes.FETCH, EndpointTypes.SUBLIST]:

                self.init_resource_endpoint(_action)

        return decorator

    def init_list_endpoint(self):
        """ Generates the list endpoint to be added to the router """
        # 1. build dependencies
        _GeneratedQueryParams = QueryParams.generate(self.model_class)
        _ParamDeps = Annotated[_GeneratedQueryParams, Depends(_GeneratedQueryParams)]

        _ModeDep = Annotated[bool | None, Depends(self.mode_dep)] if self.mode_dep else bool

        # Support 2 types of route configurations, for app routing or api routing.
        _InstanceDep = Annotated[str | None, Depends(self.instance_dep)] if self.route_type is RouteTypes.APP else Any
        _ApiDep = Annotated[str | None, Depends(self.api_dep)] if self.route_type is RouteTypes.API else Any

        _EntityDep = Annotated[str | None, Depends(self.entity_dep)] if self.entity_dep else Any
        _CurrentUserDep = Annotated[str | None, Depends(self.user_dep)] if self.user_dep else Any
        _CurrencyDep = Annotated[str | None, Depends(self.currency_dep)] if self.currency_dep else Any
        _Permissions =self.permissions if self.permissions else default
        name = self._list.__name__  # set a unique function name to the route


        @self.router.get("", include_in_schema=self.allow_list,name=name, response_model=ListResponse)
        @_Permissions
        async def _route_func(
                params: _ParamDeps,
                user_id: _CurrentUserDep = None,
                # instance_id: _InstanceDep = None,
                entity_id: _EntityDep = None,
                api_token: _ApiDep = None,
                live_mode: _ModeDep = None,
                background_tasks: BackgroundTasks = None
        ):

            if self.allow_list is False:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                    detail=dict(code=ApplicationErrors.ENDPOINT_OPERATION_DENIED.value,
                                                message=ApplicationErrors.ENDPOINT_OPERATION_DENIED.message))

            extra_parameters = ExtraParameters(
                entity_id=entity_id, route_type=self.route_type,
                user_id=user_id, live_mode=live_mode, token=api_token,
                # user=user_id
            )
            # print(extra_parameters)
            # b

            query_parameters = [dict([(param, value)]) for param, value in
                                extra_parameters.as_dict().items()
                                if param not in self.ignored_deps and value is not None]

            results = await self._list(
                params,
                query_parameters=query_parameters,
                extra_parameters=extra_parameters,
                ignored_deps=self.ignored_deps,
                background_tasks=background_tasks,
            )

            # Add extra validation to enable full override of response_model
            return dict(filter_by=params.filter_by, query=params.query, view=params.view,
                        sort_by=params.sort_by, page_by=params.page_by, results=results)



        return _route_func

    def init_fetch_endpoint(self):
        """ Generates the list endpoint to be added to the router """

        # 1. build dependencies
        _GeneratedQueryParams = QueryParams.generate(self.model_class)
        _ParamDeps = Annotated[_GeneratedQueryParams, Depends(_GeneratedQueryParams)]

        _ModeDep = Annotated[str | None, Depends(self.mode_dep)] if self.mode_dep else Any

        # Support 2 types of route configurations, for app routing or api routing.
        _InstanceDep = Annotated[str | None, Depends(self.instance_dep)] if self.route_type is RouteTypes.APP else Any
        _ApiDep = Annotated[str | None, Depends(self.api_dep)] if self.route_type is RouteTypes.API else Any

        _EntityDep = Annotated[str | None, Depends(self.entity_dep)] if self.entity_dep else Any
        _CurrentUserDep = Annotated[str | None, Depends(self.user_dep)] if self.user_dep else Any
        _CurrencyDep = Annotated[str | None, Depends(self.currency_dep)] if self.currency_dep else Any
        _Permissions =self.permissions if self.permissions else default

        name = self._fetch.__name__  # set a unique function name to the route

        @self.router.get("/{obj_id}", include_in_schema=self.allow_fetch,name=name, response_model=self.model_class)
        @_Permissions
        async def _route_func(
                obj_id: str,
                user_id: _CurrentUserDep = None,
                # instance_id: _InstanceDep = None,
                entity_id: _EntityDep = None,
                api_token: _ApiDep = None,
                live_mode: _ModeDep = None,
                background_tasks: BackgroundTasks = None
        ):

            if not self.allow_fetch:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                    detail=dict(code=ApplicationErrors.ENDPOINT_OPERATION_DENIED.value,
                                                message=ApplicationErrors.ENDPOINT_OPERATION_DENIED.message))

            extra_parameters = ExtraParameters(
                entity_id=entity_id, route_type=self.route_type,
                user_id=user_id, live_mode=live_mode, token=api_token
            )

            obj = await self._fetch(obj_id, self.model_class, extra_parameters=extra_parameters,
                                    background_tasks=background_tasks)

            return obj

        return _route_func

    def init_create_endpoint(self):
        """ Generates the create endpoint to be added to the router """

        # 1. build dependencies
        _FormModel = self.create_schema if self.create_schema else self.model_class

        _ModeDep = Annotated[str | None, Depends(self.mode_dep)] if self.mode_dep else Any

        # Support 2 types of route configurations, for app routing or api routing.
        _InstanceDep = Annotated[str | None, Depends(self.instance_dep)] if self.route_type is RouteTypes.APP else Any
        _ApiDep = Annotated[str | None, Depends(self.api_dep)] if self.route_type is RouteTypes.API else Any

        _EntityDep = Annotated[str | None, Depends(self.entity_dep)] if self.entity_dep else Any
        _CurrentUserDep = Annotated[str | None, Depends(self.user_dep)] if self.user_dep else Any
        _CurrencyDep = Annotated[str | None, Depends(self.currency_dep)] if self.currency_dep else Any
        _Permissions =self.permissions if self.permissions else default

        name = self._create.__name__  # set a unique function name to the route

        @self.router.post("", include_in_schema=self.allow_create,name=name, response_model=self.model_class)
        @_Permissions
        async def _route_func(
                payload: _FormModel,
                user_id: _CurrentUserDep = None,
                # instance_id: _InstanceDep = None,
                entity_id: _EntityDep = None,
                api_token: _ApiDep = None,
                live_mode: _ModeDep = False,
                background_tasks: BackgroundTasks = None
        ):
            if not self.allow_create:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                    detail=dict(code=ApplicationErrors.ENDPOINT_OPERATION_DENIED.value,
                                                message=ApplicationErrors.ENDPOINT_OPERATION_DENIED.message))

            extra_parameters = ExtraParameters(entity_id=entity_id, route_type=self.route_type,
                user_id=user_id, live_mode=live_mode, token=api_token
            )

            # if _app_id:
            #     extra_parameters.update(app_id=_app_id)

            obj = await self._create(model_class=self.model_class , payload=payload, extra_parameters=extra_parameters, background_tasks=background_tasks,)
            return obj

        if self.permissions:
            _route_func = self.permissions(_route_func)

        return _route_func

    def init_update_endpoint(self):
        """ Generates the update endpoint to be added to the router """

        # 1. build dependencies
        _FormModel = self.create_schema if self.create_schema else self.model_class

        _ModeDep = Annotated[str | None, Depends(self.mode_dep)] if self.mode_dep else Any

        # Support 2 types of route configurations, for app routing or api routing.
        _InstanceDep = Annotated[str | None, Depends(self.instance_dep)] if self.route_type is RouteTypes.APP else Any
        _ApiDep = Annotated[str | None, Depends(self.api_dep)] if self.route_type is RouteTypes.API else Any

        _EntityDep = Annotated[str | None, Depends(self.entity_dep)] if self.entity_dep else Any
        _CurrentUserDep = Annotated[str | None, Depends(self.user_dep)] if self.user_dep else Any
        _CurrencyDep = Annotated[str | None, Depends(self.currency_dep)] if self.currency_dep else Any
        _Permissions =self.permissions if self.permissions else default

        name = self._update.__name__  # set a unique function name to the route

        @self.router.put("/{obj_id}", name=name, include_in_schema=self.allow_update,response_model=self.model_class)
        @self.router.post("/{obj_id}", name=name, include_in_schema=self.allow_update,response_model=self.model_class)
        @_Permissions
        async def _route_func(
                obj_id: PydanticObjectId | str,
                payload: _FormModel,
                user_id: _CurrentUserDep = None,
                # instance_id: _InstanceDep = None,
                entity_id: _EntityDep = None,
                live_mode: _ModeDep = False,
                api_token: _ApiDep = None,
                background_tasks: BackgroundTasks = None
        ):
            if self.allow_update is False:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                    detail=dict(code=ApplicationErrors.ENDPOINT_OPERATION_DENIED.value,
                                                message=ApplicationErrors.ENDPOINT_OPERATION_DENIED.message))

            extra_parameters = ExtraParameters(entity_id=entity_id, route_type=self.route_type,
                user_id=user_id, live_mode=live_mode, token=api_token
            ).as_dict()

            # if _app_id:
            #     extra_parameters.update(app_id=_app_id)

            obj = await self._update(obj_id, self.model_class, payload=payload, extra_parameters=extra_parameters, background_tasks=background_tasks,)
            return obj

        return _route_func

    def init_delete_endpoint(self):
        """ Generates the delete endpoint to be added to the router """

        _ModeDep = Annotated[str | None, Depends(self.mode_dep)] if self.mode_dep else Any

        # Support 2 types of route configurations, for app routing or api routing.
        _InstanceDep = Annotated[str | None, Depends(self.instance_dep)] if self.route_type is RouteTypes.APP else Any
        _ApiDep = Annotated[str | None, Depends(self.api_dep)] if self.route_type is RouteTypes.API else Any

        _EntityDep = Annotated[str | None, Depends(self.entity_dep)] if self.entity_dep else Any
        _CurrentUserDep = Annotated[str | None, Depends(self.user_dep)] if self.user_dep else Any
        _CurrencyDep = Annotated[str | None, Depends(self.currency_dep)] if self.currency_dep else Any
        _Permissions =self.permissions if self.permissions else default

        name = self._delete.__name__  # set a unique function name to the route

        @self.router.delete("/{obj_id}", include_in_schema=self.allow_delete,name=name)
        @_Permissions
        async def _route_func(
                obj_id: PydanticObjectId | str,
                user_id: _CurrentUserDep = None,
                # instance_id: _InstanceDep = None,
                entity_id: _EntityDep = None,
                live_mode: _ModeDep = False,
                api_token: _ApiDep = None,
                background_tasks: BackgroundTasks = None
        ):
            if not self.allow_delete:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                    detail=dict(code=ApplicationErrors.ENDPOINT_OPERATION_DENIED.value,
                                                message=ApplicationErrors.ENDPOINT_OPERATION_DENIED.message))

            obj = await self._delete(obj_id, self.model_class, background_tasks=background_tasks,)
            return obj

        return _route_func

    def init_action_endpoint(self, action: EndpointAction):
        """ Generate a new function for each action endpoint based on the internal action registry """

        path = action.path

        _ResponseModel = action.response_model
        _FormModel = action.form_schema

        _ModeDep = Annotated[str | None, Depends(self.mode_dep)] if self.mode_dep else Any

        # Support 2 types of route configurations, for app routing or api routing.
        _InstanceDep = Annotated[str | None, Depends(self.instance_dep)] if self.route_type is RouteTypes.APP else Any
        _ApiDep = Annotated[str | None, Depends(self.api_dep)] if self.route_type is RouteTypes.API else Any

        _EntityDep = Annotated[str | None, Depends(self.entity_dep)] if self.entity_dep else Any
        _CurrentUserDep = Annotated[str | None, Depends(self.user_dep)] if self.user_dep else Any
        _CurrencyDep = Annotated[str | None, Depends(self.currency_dep)] if self.currency_dep else Any
        _Permissions =self.permissions if self.permissions else default

        print(path)
        @self.router.put(path, name=action.name, include_in_schema=self.allow_update, response_model=_ResponseModel)
        @self.router.post(path, name=action.name, response_model=_ResponseModel)
        @_Permissions
        async def _route_func(
                obj_id: ReferenceField = None,
                payload: _FormModel = None,
                user_id: _CurrentUserDep = None,
                # instance_id: _InstanceDep = None,
                entity_id: _EntityDep = None,
                live_mode: _ModeDep = False,
                api_token: _ApiDep = None,
                background_tasks: BackgroundTasks = None
        ):
            extra_parameters = ExtraParameters(entity_id=entity_id, route_type=self.route_type,
                user_id=user_id, live_mode=live_mode, token=api_token
            )

            obj = await action.func(
                obj_id=obj_id,
                model_class=action.service_class,
                payload=payload,
                extra_parameters=extra_parameters,
                background_tasks=background_tasks,
            )
            return obj

        return _route_func

    def init_resource_endpoint(self, action: EndpointAction):
        """ Generate a new function for each action endpoint based on the internal action registry """
        path = action.path
        # print("was i called", path)

        _ResponseModel = action.response_model if (action.action_type not in
                                                   [EndpointTypes.SUBLIST, EndpointTypes.LIST]) else ListResponse

        _GeneratedQueryParams = QueryParams.generate(action.service_class if action.service_class else self.model_class)
        _ParamDeps = Annotated[_GeneratedQueryParams, Depends(_GeneratedQueryParams)]

        _ModeDep = Annotated[str | None, Depends(self.mode_dep)] if self.mode_dep else Any

        # Support 2 types of route configurations, for app routing or api routing.
        _InstanceDep = Annotated[str | None, Depends(self.instance_dep)] if self.route_type is RouteTypes.APP else Any
        _ApiDep = Annotated[str | None, Depends(self.api_dep)] if self.route_type is RouteTypes.API else Any

        _EntityDep = Annotated[str | None, Depends(self.entity_dep)] if self.entity_dep else Any
        _CurrentUserDep = Annotated[str | None, Depends(self.user_dep)] if self.user_dep else Any
        _CurrencyDep = Annotated[str | None, Depends(self.currency_dep)] if self.currency_dep else Any
        _Permissions =self.permissions if self.permissions else default

        @self.router.get(path, name=action.name, response_model=_ResponseModel)
        @_Permissions
        async def _route_func(
                obj_id: ReferenceField = None,
                params: _ParamDeps = None,
                user_id: _CurrentUserDep = None,
                # instance_id: _InstanceDep = None,
                entity_id: _EntityDep = None,
                live_mode: _ModeDep = False,
                api_token: _ApiDep = None,
                background_tasks: BackgroundTasks = None
        ):
            print("params, path")
            extra_parameters = ExtraParameters(entity_id=entity_id, route_type=self.route_type,
                user_id=user_id, live_mode=live_mode, token=api_token
            )



            query_parameters = [dict([(param, value)]) for param, value in
                                extra_parameters.as_dict().items() if param not in self.ignored_deps]
            results = await action.func(
                obj_id=obj_id,
                model_class=action.service_class,
                params=params,
                query_parameters=query_parameters,
                extra_parameters=extra_parameters,
                background_tasks=background_tasks,
            )

            # Support query result set with pagination and other parameters, if endpoint type is LIST.
            print("hereeeee")
            if action.action_type in [EndpointTypes.LIST, EndpointTypes.SUBLIST]:
                return dict(filter_by=params.filter_by, query=params.query, view=params.view,
                            sort_by=params.sort_by, page_by=params.page_by, results=results)

            return results

        return _route_func


async def _list_func(
        params: QueryParams.GeneratedClass,
        query_parameters,
        extra_parameters: ExtraParameters | None = None,
        ignored_deps: Optional[list[str]] = [],
        background_tasks = None,

) -> list[Any]:
    """
    Default list query function that will be used on every model.
    Parameters above will be prepared and provided by the function decorator that wraps this function.
    """

    print("query_parameters ????",query_parameters)

    _filter_query = await params.get_db_query(query_parameters)

    print("_filter_query", _filter_query)

    results = await (params.model_class.find(_filter_query, fetch_links=True).
                     skip(params.skip).limit(params.per_page).
                     sort(params.sorting).to_list())

    return results


async def _fetch_func(
        obj_id: str, service_class: Type[Document],
        extra_parameters: ExtraParameters | None = None,
        background_tasks = None,
) -> Any | Type[Document]:
    """
    Default detail query function that will be used on every model.
    Parameters above will be prepared and provided by the function decorator that wraps this function.
    """
    # Implement object level permission checking in permission checks here.
    # It will be a combination of route based permission checks and object level permissions.
    # In addition, validation checks on instance_id, entity_id and user_id can be applied
    try:
        obj = await service_class.get(obj_id, fetch_links=True)
        return obj
    except Exception as e:
        print(e)
        raise RequestValidationError(
            errors=format_validation_error(key="id", type=ApplicationErrors.VALIDATION_ERROR.value, message=f"resource id does not exist")
        )



async def _create_func(
        model_class: Type[Document],
        *,
        payload: Type[BaseModel],
        extra_parameters: ExtraParameters | None = None,
        background_tasks = None,
) -> Any:
    """
    Default create functionality for any model. This can be overriden using the override decorator,
    :param model_class: Model class of the specified object
    :param payload: Values to change on the model object
    :param extra_parameters: additional values to insert into the object if they don't exist
    :return:
    """
    try:
        # Convert payload into python dictionary
        data = payload.model_dump(exclude_none=True, exclude_unset=True)
        # update the model with any additional values from default_attributes
        data.update(extra_parameters.model_dump())
        print(extra_parameters)
        # trigger the create method for the object

        obj = model_class.model_validate(data)
        await obj.save()
        await obj.fetch_all_links()

        return obj
    except ValueError as e:
        print(e)
        raise RequestValidationError(errors=[e])


async def _update_func(
        obj_id: ReferenceField,  # convert this to an automatic field that parses object id out of strings
        model_class: Type[Document],
        payload: Type[BaseModel],
        extra_parameters: ExtraParameters | None = None,
        background_tasks = None,
) -> Any:
    """
    Default update functionality for any model. This can be overriden using the override decorator,
    :obj_id: ObjectId of the specified model object.
    :param model_class: Model class of the specified object
    :param payload: Values to change on the model object
    :param extra_parameters: additional values to insert into the object if they don't exist
    :return:
    """

    try:
        # Convert payload into python dictionary
        data = payload.model_dump(exclude_unset=True, exclude_none=True)
        # update the model with any additional values from default_attributes
        data.update(extra_parameters)
        # trigger the create method for the object

        obj = await model_class.get(obj_id)
        if not obj:
            raise RequestValidationError(errors=[dict(type="missing", msg=f"Object with id `{obj_id}` not found")])

        updated_data = obj.model_copy(update=data).model_dump()
        obj = await model_class.model_validate(updated_data).replace()

        return obj
    except ValueError as e:
        raise e
    except Exception as ex:
        print(ex)
        raise ex


async def _delete_func(
        obj_id: PydanticObjectId | str,  # convert this to an automatic field that parses object id out of strings
        model_class: Type[Document],
        extra_parameters: ExtraParameters | None = None,
        background_tasks = None,

) -> Any:
    """
    Default delete functionality for any model. This can be overriden using the override decorator,
    :obj_id: ObjectId of the specified model object.
    :param model_class: Model class of the specified object
    :return:
    """
    try:
        obj = await model_class.get(obj_id)
        if not obj:
            raise RequestValidationError(errors=[dict(type="missing", msg=f"Object with id `{obj_id}` not found")])

        await obj.delete()
        return dict(status="processed")
    except (ValueError, DocumentNotFound) as e:
        raise RequestValidationError(errors=[e])


async def _default_func(**kwargs):
    """ Default function used to plug endpoints that have yet to be populated."""
    raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail=dict(code=ApplicationErrors.ENDPOINT_NOT_IMPLEMENTED.value,
                                    message=ApplicationErrors.ENDPOINT_NOT_IMPLEMENTED.message))


class EndpointFactory:
    """
    Endpoint generator factory class. This class will be responsible for building the default routes,
    """

    @classmethod
    def generate(
            cls,
            model_class: Type[Document], prefix: str, route_type: RouteTypes = RouteTypes.APP,
            dependencies: list[Callable] = [], user_dep: Callable = None, instance_dep: Callable = None,
            entity_dep: Callable = None, currency_dep: Callable = None,permissions:PermissionsType = None,
            mode_dep: Callable = None,
            api_dep: Callable = None, ignored_deps: list = [],
            allow_delete: bool = False, allow_create: bool = True, allow_update: bool = True,
            allow_list: bool = True, allow_fetch: bool = True,
            create_schema: Type[BaseModel] = None, update_schema: Type[BaseModel] = None,
    ):
        """
        Class generator with default functions that can provide default functionality for basic crud functions.
        To customize any of the endpoints, use the wrapper function to override the internally defined endpoint.

        The class will support the following endpoints:
            list, 'fetch', 'create', 'update', 'delete', 'list_action', 'object_action', 'search'

        :param model_class: db model / service class used throughout this endpoint
        :param prefix: base path prefix used for the endpoint
        :param route_type: 'app|api' define if route should be treated as app route or api route.
        :param dependencies: dependency parameters to be checked across all route calls
        :param user_dep:
        :param mode_dep:
        :param api_dep:
        :param instance_dep:
        :param entity_dep:
        :param currency_dep:
        :param allow_list:
        :param allow_fetch:
        :param allow_create:
        :param allow_update:
        :param allow_delete:
        :param ignored_deps:
        :param update_schema:
        :param create_schema:

        :return: instance of type `Endpoint` with additional routing functionality
        """

        endpoint = Endpoint(
            model_class, prefix, route_type=route_type, list_func=_list_func, fetch_func=_fetch_func,
            create_func=_create_func, update_func=_update_func, delete_func=_delete_func,
            dependencies=dependencies, ignored_deps=ignored_deps, user_dep=user_dep, instance_dep=instance_dep,
            entity_dep=entity_dep, currency_dep=currency_dep, api_dep=api_dep, mode_dep=mode_dep,
            allow_create=allow_create, allow_update=allow_update, allow_delete=allow_delete,
            allow_list=allow_list, allow_fetch=allow_fetch, permissions=permissions,
            create_schema=create_schema, update_schema=update_schema
        )

        return endpoint

