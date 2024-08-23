from enum import Enum
from typing import Optional, TypeVar, Any

import pymongo
from beanie import Document
from pydantic import BaseModel

ModelType = TypeVar("ModelType", BaseModel, Document)


class ApplicationErrors(Enum):
    TOKEN_REQUIRED = ("TOKEN.REQUIRED", "Access token is required. Modify your request and try again.")
    TOKEN_INVALID = ("TOKEN.INVALID", "Access token is invalid. Please provide a valid token and try again.")
    TOKEN_DENIED = ("TOKEN.DENIED", "Access token is denied. The user does not exist or is suspended.")
    TOKEN_EXPIRED = ("TOKEN.EXPIRED", "Your access token has expired. Try again with a valid token.")

    # Parameter errors
    HEADER_ATTRIBUTE_MISSING = ("HEADER.ATTRIBUTE.MISSING", "A required header parameter is missing.")
    HEADER_ATTRIBUTE_INVALID = ("HEADER.ATTRIBUTE.INVALID", "The header parameter provided is invalid.")

    # Endpoint Errors
    ENDPOINT_NOT_IMPLEMENTED = ("ENDPOINT.NOT.IMPLEMENTED", "The requested endpoint is not yet implemented.")
    ENDPOINT_OPERATION_DENIED = ("ENDPOINT.OPERATION.RESTRICTED", "This activity cannot be carried out because the "
                                                                  "endpoint is restricted")

    VALIDATION_ERROR = ("validation_error", "invalid parameter")

    CUSTOM_ERROR = ("custom_error", "invalid parameter")

    def __new__(cls, code, message):
        obj = object.__new__(cls)
        obj._value_ = code
        obj.message = message
        return obj


class Operators(Enum):
    """
    Filter operators as enums.
    The enum values will be used for comparison and validation
    """

    GREATER_THAN = "$gt"
    LESS_THAN = "$lt"
    GREATER_OR_EQUAL = "$gte"
    LESS_OR_EQUAL = "$lte"
    EQUAL = "$eq"
    NOT_EQUAL = "$ne"
    IN = "$in"
    NIN = "$nin"
    BTW = "$btw"
    # TODO: Implement contains and matches. Implementation will be done within the `format_args` method.
    CONTAINS = "$has"  # should map to $text db query
    MATCHES = "$is"  # should map to $regex db query

    # def __new__(cls, value, alt, operator):
    #     """
    #     @param value: value of the enumerator
    #     @param operator: operator to be used by the enumerator
    #     """
    #     obj = object.__new__(cls)
    #     obj._value_ = value
    #     obj.alt = alt
    #     obj.operator = operator
    #
    #     return obj
    def format_args(self, args: Any) -> dict[str, Any]:
        """ Format the argument based on what type of operator"""

        if self in [Operators.BTW]:
            return {"$gte": args["min"], "$lt": args["max"]}
        return {self.value: args}


class SortOrderingType(Enum):
    ASC = ("asc", pymongo.ASCENDING)
    DESC = ("desc", pymongo.DESCENDING)

    def __new__(cls, value, direction):
        obj = object.__new__(cls)
        obj._value_ = value
        obj.direction = direction

        return obj


class PageByResponse(BaseModel):
    page: int = 1
    per_page: int = 20
    pages: Optional[int] = None
    total: Optional[int] = None
    next_page: Optional[int] = None
    prev_page: Optional[int] = None


class SortByResponse(BaseModel):
    order_by: Optional[str] = "id"
    asc_desc: SortOrderingType = SortOrderingType.DESC.value


class ListResponse(BaseModel):
    """Standard response model for list queries."""
    filter_by: dict[str, Any]
    page_by: PageByResponse
    sort_by: Optional[list[SortByResponse]] = []
    view: Optional[str] = None
    query: Optional[str] = None
    results: Optional[list[Any]] = []


class RouteTypes(Enum):
    """Enums of route types available within the application"""

    APP = "app"
    API = "api"

    @classmethod
    def list(cls) -> list:
        return [x.value for x in cls]


class EndpointTypes(Enum):
    """Enums of endpoint types"""
    MANY = "many"  # POST|PUT - action on a list of objects
    SINGLE = "single"  # POST - create a single ( without obj_id, or _action in the path)
    DETAIL = "detail"  # POST|PUT - action on a single object, will receive obj_id in function
    CREATE = "create"  # POST - override the default create function
    UPDATE = "update"  # POST|PUT - override the default update function
    DELETE = "delete"  # DELETE - override the default delete function
    LIST = "list"  # GET - override the default list function
    FETCH = "fetch"  # GET - retrieve a single record.
    SUBLIST = "sub"  # GET - retrieve a sub-resource based on a parent

    @classmethod
    def list(cls) -> list:
        return [x.value for x in cls]


class NotificationTypes(Enum):
    SIGNUP = "signup"
    LOGIN = "login"



class Statuses(Enum):
    ABANDONED = "abandoned"
    ACCEPTED = "accepted"
    ACTIVE = "active"
    ARRIVED_AT_CONSOLIDATION_CENTER = "arrived_at_consolidation_center"
    ARRIVED_AT_DESTINATION_HUB = "arrived_at_destination_hub"
    ARRIVED_AT_TRANSFER_FACILITY = "arrived_at_transfer_facility"
    ASSIGNED = "assigned"
    ASSIGNED_FOR_TRANSFER = "assigned_for_transfer"
    ASSIGNED_TO_AGENT = "assigned_to_agent"
    ASSIGNED_TO_DELIVERY_COURIER = "assigned_to_delivery_courier"
    AT_HUB = "at_hub"
    ATTEMPTED = "attempted"
    ATTEMPTED_DELIVERY = "attempted_delivery"
    ATTEMPTED_PICKUP = "attempted_pickup"
    CANCELLED = "cancelled"
    CLOSE = "close"
    CLOSED = "closed"
    COMPLETED = "completed"
    DECLINED = "declined"
    DELIVERED = "delivered"
    DELIVERED_TO_BROKER = "delivered_to_broker"
    DELIVERED_TO_HUB = "delivered_to_hub"
    DELIVERY_ACCEPTED = "delivery_accepted"
    DELIVERY_ASSIGNED = "delivery_assigned"
    DELIVERY_ATTEMPT_FAILED = "delivery_attempt_failed"
    DELIVERY_COMPLETED = "delivery_completed"
    DELIVERY_REQUESTED = "delivery_requested"
    DELIVERY_STARTED = "delivery_started"
    DEPART_TRANSFER_FACILITY = "depart_transfer_facility"
    DOCREQ = "docreq"
    DRAFTED = "drafted"
    DROP_OFF_COMPLETED = "drop_off_completed"
    EXCEPTION = "exception"
    EXPIRED = "expired"
    FAILED = "failed"
    IN_DELIVERY = "in_delivery"
    IN_TRANSFER = "in_transfer"
    IN_TRANSIT = "in_transit"
    INACTIVE = "inactive"
    INCOMPLETE = "incomplete"
    ONGOING = "ongoing"
    OPEN = "open"
    OVERDUE = "overdue"
    OVERPAID = "overpaid"
    PACKAGE_TRANSFERRED = "package_transferred"
    PAID = "paid"
    PARTIAL = "partial"
    PENDING = "pending"
    PICKUP_ACCEPTED = "pickup_accepted"
    PICKUP_ASSIGNED = "pickup_assigned"
    PICKUP_ATTEMPT_FAILED = "pickup_attempt_failed"
    PICKUP_COMPLETED = "pickup_completed"
    PICKUP_STARTED = "pickup_started"
    PROCESSED = "processed"
    PROCESSED_AT_CONSOLIDATION_CENTER = "processed_at_consolidation_center"
    PROCESSED_FOR_TRANSFER = "processed_for_transfer"
    PROCESSING = "processing"
    QUEUED_FOR_TRANSFER = "queued_for_transfer"
    READY_TO_SHIP = "ready_to_ship"
    REJECTED = "rejected"
    REJECTED_DELIVERY = "rejected_delivery"
    RESCHEDULED = "rescheduled"
    RETURNED = "returned"
    REVOKED = "revoked"
    SHIPPED = "shipped"
    STARTED = "started"
    SUCCESSFUL = "successful"


class AccountTypes(Enum):
    PLATFORM = "platform"
    BUSINESS = "business"
    PERSONAL = "personal"

class PaymentSourceCodes(Enum):
    WALLET = "wallet"
    CARD = "card"
    USSD = "ussd"


class ProductTypes(Enum):
    SHIPMENT = "shipment"
    TOPUP = "topup"
    ORDER = "order"
    ECOMMERCE = "ecommerce"

class ServiceTypes(Enum):
    IMPORTS = "imports"
    PICKUP = "pickup"
    DROP_OFF = "drop_off"

class ChargeTypes(Enum):
    PERCENTAGE = "percentage"
    FLAT = "flat"
    RANGE = "range"
    PERCENTAGE_RANGE = "percentage_range"

class PermissionTypes(Enum):
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    PERFORM_ACTION = "perform_action"


class BusinessTypes(Enum):
    ECOMMERCE = ("shipping", "e-commerce.")
    LOGISTICS = ("logistics", "logistics")
    FASHION = ("fashion", "fashion")


    def __new__(cls, code, message):
        obj = object.__new__(cls)
        obj._value_ = code
        obj.message = message
        return obj


class ValidatorStatuses(Enum):
    BAD_ADDRESS = "bad_address"
    ADDRESS_OK = "address ok"


# class PickupETATypes(Enum):
#     SPECIFIC = "specific"
#     DEFAULT = "default"


class EtaWindows(Enum):
    HOURS = ("HOURS", "hours")
    DAYS = ("DAYS", "days")
    WORKING_DAYS = ("WORKING_DAYS", "working days")

    def __new__(cls, code, message):
        obj = object.__new__(cls)
        obj._value_ = code
        obj.message = message
        return obj