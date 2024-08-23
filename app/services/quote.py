import re

from beanie.odm.operators.find.comparison import Eq, GT, In, LTE, GTE
from beanie.odm.operators.find.logical import And, Or
from fastapi import HTTPException
from fastapi.exceptions import RequestValidationError
from starlette import status
import datetime
from app.core.utils.custom_fields import format_validation_error
from app.core.utils.enums import AccountTypes, ApplicationErrors
from app.core.utils.helpers import normalize_text
from app.models import ConnectorAccount, ConnectorRate, PickupETA, next_business_day, City, State, CourierMeta
from app.schemas.quote import QuoteRequestSchema
from app.core.utils.utils import slugify_with_exclude



class QuoteService:

    @classmethod
    def build_hash_key(cls, route_type: str, data: QuoteRequestSchema):
        origin = data.origin
        destination = data.destination
        origin_country = origin.country
        destination_country = destination.country
        hash_key = f"{origin_country}:{origin_country}:{destination_country}:{destination_country}:{route_type}"
        return slugify_with_exclude(hash_key.lower().replace(" ", "-"), excluded_char=":")

    @classmethod
    def get_route_type(cls, data: QuoteRequestSchema):
        origin = data.origin
        destination = data.destination
        origin_country = origin.country
        destination_country = destination.country
        origin_state = origin.state
        destination_state = destination.state
        route_type = "international" if origin_country != destination_country else "nationwide"
        if route_type in ("nationwide", "local"):
            route_type = "local" if origin_state == destination_state else "nationwide"

        return route_type


    @classmethod
    async def calculate_duties(cls, customs_option: str | None = "DAP",
                               data: QuoteRequestSchema | None = None,
                               fee: float | None = None):

        """"""
        #todo:: make a request to an engine to calculate the option
        #who will pay should able to be called multiple times
        #if it is ddp add to additional charge if it is dap don't.
        #new model custom duty payment model --- if it has been paid for record the information else
        # it should prevent the shipment from getting completed

    @classmethod
    async def fetch_quote(cls, data: QuoteRequestSchema, entity_id: str | None =None,  user_id: str | None =None, live_mode: bool | None = False):
        route_type = cls.get_route_type(data)
        service_code =data.service_code
        customs_option = data.customs_option
        pick_eta = None
        message = None
        destination_country = data.destination.country


        print("route_type package_type", )
        connectors = ConnectorAccount.find(ConnectorAccount.route_type.id == route_type,
                                           Eq(ConnectorAccount.package_types, data.package_type),
                                           Or(
                                               ConnectorAccount.account_type == AccountTypes.PLATFORM,
                                               And(ConnectorAccount.account_type == AccountTypes.BUSINESS,
                                                   ConnectorAccount.entity_id == str(entity_id))
                                           ),
                                           fetch_links=True)

        connectors = await connectors.to_list()
        package_type = await data.package_type.fetch()


        print("connectors here i am",package_type, data.package_type)
        rate_card_ids = [connector.rate_card.id for connector in connectors]
        hash_key = cls.build_hash_key(route_type,data)
        search_query = {
            "hash_keys": hash_key,
            "rate_card.$id": {"$in": rate_card_ids},
            "weight_range.0": {"$lte": data.weight},
            "weight_range.1": {"$gt": data.weight}
        }
        print("search_query",search_query)

        rates = []

        print(" data.billable_weight",  data.billable_weight)
        wei =  data.billable_weight
        rates = await ConnectorRate.find(
            And(GTE(ConnectorRate.weight_range[1], wei),
            LTE(ConnectorRate.weight_range[0], wei)),
            In(ConnectorRate.rate_card.id, rate_card_ids),
            ConnectorRate.hash_keys == hash_key,
            fetch_links=True
        ).to_list()
        print("here rate",rates)
        selected_rate = None
        for rate in rates:
            print("herrr we go")
            #todo: send an extra charge array
            await rate.compute_breakdown(extra_charges = [])
            await rate.check_customs_options(destination_country)

            #todo:: if destination in courier customs country DDP IS SUPPORTED ELSE DAP



        if service_code:
            selected_rate =next((rate for rate in rates if rate.connector.code == service_code), None)
            await selected_rate.check_customs_options(destination_country)

        if customs_option:
            """"""
            await cls.calculate_duties(customs_option, data, selected_rate)

        if len(rates) == 0:
            raise RequestValidationError(
                errors=format_validation_error(key="-", type=ApplicationErrors.CUSTOM_ERROR.value,
                                               message="no rate found for this specific route")
            )


        #todo: once pickup not supported include messages to it
        city_name = normalize_text(data.origin.city.lower())
        state_name = normalize_text(data.origin.state.lower())

        state = await State.find_one({"name": re.compile(state_name, re.IGNORECASE), "country": data.origin.country},fetch_links=True)

        if not state:
            print("here world")
            raise RequestValidationError(
                errors=format_validation_error(key="-", type=ApplicationErrors.CUSTOM_ERROR.value,
                                               message="We can't ship from this state")
            )

        print("state", state)
        city = await City.find_one({"name": re.compile(city_name, re.IGNORECASE),
                                    "state":state, "country": data.origin.country}, fetch_links=True)
        print("city", city)

        pickup = state.pickup_eta if not city else city.pickup_eta

        if  pickup:
            print("pickup eta", pickup)
            pickup_description = pickup.description

            min_pickup_eta = pickup.min
            max_pickup_eta = pickup.max
            min_eta_date = next_business_day(min_pickup_eta, data.origin.country)
            max_eta_date = next_business_day(max_pickup_eta, data.origin.country)

            pick_eta = {
                "description": pickup_description,
                "min_date": min_eta_date,
                "max_date": max_eta_date
            }
        else:
            data.pickup_type = "drop_off"
            message = [dict(type="info", body="pickup is not supported for your specified city")]


        return dict(
            origin= data.origin,
            items = data.items,
            dimensions= data.dimensions,
            service_code=service_code,
            messages = message,
            delivery_type=data.delivery_type,
            package_type=package_type.id,
            pickup_type= data.pickup_type,
            route_type=route_type,
            destination= data.destination,
            weight = data.weight,
            billable_weight = data.billable_weight,
            rates = rates,
            selected_rate = selected_rate,
            pickup_eta = pick_eta,
            customs_option = data.customs_option
        )


#todo generate rate on staging from 0-100--- sendbox standard, sendbox priority,
#todo platform rate --- dhl:standard, fedex:economy, fedex:priority, redstar:standard multiple by 1.42, baseline_weight == 2kg