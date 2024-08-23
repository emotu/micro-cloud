from typing import Dict

import httpx
from africastalking.Service import Service
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient

from app.config import settings
from app.models import Business


class EntityTasks:

    @classmethod
    async def register_entity_task(cls, entity_id: str, do_update: bool = False, apps: List[str] = None) -> None:
        """
        Asynchronous task to register or update an entity.
        """
        try:
            entity = await Business.get(entity_id)
            entity_data = dict(name=entity.name, email=entity.email, username=entity.username,
                               address=entity.address.to_dict(), default_currency=entity.default_currency,
                               phone=entity.phone, user_id=entity.user_id, entity_id=entity_id,
                               currency=entity.default_currency, region=entity.region,
                               banner_image_url=entity.banner_image_url,
                               enabled=entity.enabled, location_id=entity.location_id,
                               date_created=entity.date_created, last_updated=entity.last_updated,
                               logo=entity.logo, country=entity.country.code,
                               entity_type=entity.type.code)

            failed_profiles = []
            applications = list(Service.find({"required": True})) if not apps \
                else list(Service.find({"code": {"$in": apps}}))

            path = "register_entity" if not do_update else "update_entity"
            for application in applications:
                try:
                    url = f"HEADLESS_{application.code.upper()}_INTERNAL_BASE_URL"
                    base_url = getattr(settings, url, None)
                    if not base_url:
                        print("Cannot send.................")
                        continue
                    print(url, f"the url {url}.................................................")

                    await cls.post_to_url(url=f"{base_url}/engine/{path}",
                                          data=dict(request_data=json.loads(json.dumps(entity_data, default=str))))

                except Exception as e:
                    print(e)
                    failed_profiles.append(application.code)
        except Exception as e:
            print(e)

    @classmethod
    async def build_notifications_task(cls, target: str, target_id: str) -> None:
        """
        make a rest call to the notification app to build notification
        """
        try:
            payload = {"target": target, "target_id": target_id}
            url = settings.HEADLESS_NOTIFICATIONS_INTERNAL_BASE_URL + "/engine/generate_notifications"
            await cls.post_to_url(url=url, data=dict(request_data=payload))
        except Exception as e:
            print(e)

    @classmethod
    async def merge_user_records_task(cls, user_id: str, entity_id: str) -> Dict[str, str]:
        """
        Asynchronous task to merge user records in different collections.
        """
        db = AsyncIOMotorClient
        apps = {
            "payments": ["transaction", "withdrawal_request", "card", "bank_account", "virtual_bank_account"],
            "shipping": ["shipment", "price_change_history"],
            "reviews": ["reward"],
            "auth": ["address"]
        }

        for app, collections in apps.items():
            app_db = db[app]
            for collection in collections:
                print("updating collection.....", collection)
                await app_db[collection].update_many({"user_id": user_id, "entity_id": {"$in": [None, ""]}},
                                                     {'$set': {"entity_id": entity_id}}, upsert=False)
                print("updated collection.....", collection)

        await db["User"].update_one({"_id": ObjectId(user_id)}, {"$set": {"migrated_entity": True}})

        return await db["Entity"].find_one({"_id": ObjectId(entity_id)})

    @classmethod
    async def post_to_url(cls, url: str, data: Dict) -> Dict:
        """
        Asynchronous function to make a POST request to the specified URL.
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=data)
            response.raise_for_status()
            return response.json()
