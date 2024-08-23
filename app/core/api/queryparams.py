"""
queryparams.py

This dependency will be utilized in extracting query params from the request.
Its job is to extract all the required query parameters from an api request, parse them and utilize them
in api requests.

Parameters that are extracted include:
    sort_by:
        order_by: str
        asc_desc: str
    page_by:
        page: int
        per_page: int
    query: str
    view: str
    filter_by:
         dict[str, dict[str, Any]]
"""
from datetime import datetime
from typing import Annotated, Optional, Any, Mapping, Type

from beanie import PydanticObjectId, Document
from fastapi import Query, Request
from pydantic import BaseModel, PositiveInt, Field, AfterValidator

from app.core.utils.custom_fields import check_object_id
from app.core.utils.enums import Operators, SortOrderingType

# Base Filter parameter value
FilterValue = Annotated[
    PydanticObjectId | int | float | datetime | str | bool, Field(), AfterValidator(check_object_id)]


class SingleValue(BaseModel):
    value: FilterValue


class ListValue(BaseModel):
    values: list[FilterValue]


class DictValue(BaseModel):
    min: Annotated[float | int | datetime, Field()]
    max: Annotated[float | int | datetime, Field()]


class FilterByAttribute(BaseModel):
    """
    filter_by arguments, parsed for validity
    """
    op: Operators
    value: Annotated[Any, Field(), AfterValidator(check_object_id)]
    _klass: Type[Document | BaseModel] = None

    # @field_serializer
    # def _serialize_value(self, value: Any):
    #     if PydanticObjectId.is_valid(value):
    #         return PydanticObjectId(value)
    #     return value

    @property
    def format_args(self):
        """ Return the database formatted pattern for this filter attribute"""
        _db_formatted = self.op.format_args(self.value)
        return _db_formatted


# filter_by validator that will be used to convert values to python.
FilterBy = Annotated[dict[str, FilterByAttribute], Field()]


class QueryParams:
    GeneratedClass = None

    @classmethod
    def generate(cls, model_class: Type[Document]) -> Any:
        """
        Making the QueryParams class callable so that we can use it as a parameterized dependency.

        :param model_class: Model class that will be used to validate filter_argument keys
        :return: class ModelQueryParams
        """

        class ModelQueryParams:
            # known values in query params. All other values will be treated as possible `filter by` parameters.
            STANDARD_PARAMS = ["sort_by.order_by", "sort_by.asc_desc",
                               "page_by.page", "page_by.per_page", "query", "view"]

            def __init__(self, order_by: Annotated[Optional[str], Query(alias="sort_by.order_by")] = "_id",
                         asc_desc: Annotated[Optional[SortOrderingType],
                         Query(alias="sort_by.asc_desc")] = SortOrderingType.DESC,
                         page: Annotated[Optional[PositiveInt], Query(alias="page_by.page")] = 1,
                         per_page: Annotated[Optional[PositiveInt], Query(alias="page_by.per_page")] = 20,
                         query: str = None, view: str = None, request: Request = None):
                super().__init__()
                self.order_by = order_by
                self.asc_desc = asc_desc
                self.page = page
                self.per_page = per_page
                self.view = view
                self.query = query
                self.model_class = model_class
                self.prev_page = None
                self.next_page = None
                self.pages = 1
                self.skip = 0
                self.total = 0
                self.others = dict()
                # Extract all other query params and store in separate dictionary object for filter matching
                self.filter_by = self.prepare_filter_args(request.query_params)

            def prepare_filter_args(self, query_params: dict | Mapping) -> Optional[dict]:
                """ Function to prepare all filter args as dot notation"""
                _model_fields = self.model_class.model_fields.keys()
                _extra_fields = ["_id"]
                filter_options = dict([(k, v) for k, v in query_params.items()
                                       if k not in ModelQueryParams.STANDARD_PARAMS])
                filter_args = dict()

                for k, v in filter_options.items():
                    # unpack filter attribute to support dot notation in query with the assumption that the last
                    # attribute is the operator and all other values form the attribute path
                    (*dotpath, op) = k.split(".")
                    val = v.split("__")

                    # If filter option doesn't match our approved format, ignore as a filter argument.
                    if len(dotpath) < 1:
                        self.others[k] = v
                        continue
                    # If the base name of the dotpath doesn't exist on the model, don't include it as part of the query
                    # parameters. This way, we minimize invalid queries.
                    if dotpath[0] not in _model_fields and dotpath[0] not in _extra_fields or len(val) < 1:
                        self.others[k] = v
                        # Considerations are to ignore the value or throw an error and halt processing.
                        # raise RequestValidationError(f'`{dotpath[0]}` is not a valid attribute on this resource.')
                        continue
                    name = ".".join(dotpath)
                    # If key, op and val are valid, create the filter argument
                    value = val[0] if op not in [Operators.BTW.value] else dict(min=val[0], max=val[1])
                    # If the operator is any of the values expecting a list, parse accordingly
                    value = value.split("|") if op in [Operators.IN.value, Operators.NIN.value] else value
                    #  parse array values to actual data types:
                    if not isinstance(value, (list, tuple, dict)):
                        value = SingleValue(value=value).value
                    if isinstance(value, (list, tuple)):
                        value = ListValue(values=value).values
                    if isinstance(value, dict):
                        value = DictValue(**value).model_dump()

                    filter_args[name] = dict(op=op, value=value)

                return filter_args

                # try:
                #     ta = TypeAdapter(FilterBy)
                #     print("validating filter_args --------->", filter_args)
                #     validated = ta.validate_python(filter_args)
                #     # validated = FilterByModel(query=filter_args)
                #     return validated
                # except RequestValidationError as e:
                #     print(e)
                #     # raise

            async def get_db_query(self, default_filters: list[dict[str, Any]] | None = []) -> Any:
                """ Build the mongodb filter by query, based on the filter_args"""

                # 1. Empty dict to hold finalized query filter

                _filters = {}
                _model_fields = self.model_class.model_fields.keys()
                print("_model_fields", _model_fields)
                for k, v in self.filter_by.items():
                    if k not in _model_fields:
                        continue
                    # Attempt to fix key here before applying it to the filter
                    _key = k
                    _field_key = self.model_class.model_fields.get(k)
                    print("i am k",_field_key.annotation)
                    field_type = getattr(_field_key.annotation, "__name__", None)
                    if field_type and field_type == "Link":
                        _key = f"{k}.$id"  # convert to a DBRef query format.

                    _v_args = FilterByAttribute(**v)
                    _filters[_key] = _v_args.format_args
                # 2. update the _filters with any default values, if present
                for default_filter in default_filters:
                    for k, v in default_filter.items():
                        # ignore any None fields or fields that are not present in the model
                        if k not in _model_fields:
                            continue
                        # Attempt to fix key here before applying it to the filter
                        _key = k
                        _field_key = self.model_class.model_fields.get(k)
                        field_type = getattr(_field_key.annotation, "__name__", None)
                        if field_type and field_type == "Link":
                            _key = f"{k}.$id"  # convert to a DBRef query format.

                        _v_extra = FilterByAttribute(op=Operators.EQUAL.value, value=v)
                        _filters[_key] = _v_extra.format_args
                # Update total, skip, next_page and prev_page to properly support pagination.
                self.total = await self.model_class.find(_filters).count()

                self.skip = (self.page - 1) * self.per_page
                self.next_page = self.page + 1 if (self.skip + self.per_page) < self.total else None
                self.prev_page = self.page - 1 if self.page > 1 else None
                self.pages = max(int(self.total / self.per_page), 1)

                return _filters

            @property
            def sorting(self):
                """ Format sorting to support sorting parameters for database query"""
                return [(self.order_by, self.asc_desc.direction)]

            @property
            def sort_by(self):
                """ Format sorting data for json response """
                return [dict(order_by=self.order_by, asc_desc=self.asc_desc)]

            @property
            def page_by(self):
                return dict(page=self.page, per_page=self.per_page, total=self.total, pages=self.pages,
                            prev_page=self.prev_page, next_page=self.next_page)

        cls.GeneratedClass = ModelQueryParams
        return ModelQueryParams
