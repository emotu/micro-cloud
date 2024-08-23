from datetime import datetime

from app.config import settings
from app.core.kyc.smile import SmileID
from app.core.kyc.smile.face import UserImageKYCSchema
from app.core.kyc.smile.identity import SmileIDKYCSchema
from app.core.utils.utils import token_generator
from app.models import UserKycRequest, User, UserKyc, IdType
from app.schemas.kyc import KYCRequestIdentitySchema
from fastapi import HTTPException, status

smileId = SmileID(settings)


class UserKYCRequestService(UserKycRequest):

    @classmethod
    async def validate_identity(cls, data: KYCRequestIdentitySchema):
        # ::TODO USER_ID COMING FROM PAYLOAD NEEDS TO CHANGE
        user = await User.get(data.user_id)
        ver_status = "pending"
        extra = dict()
        if data.selfie_image:
            selfie_response = await cls.register_selfie(data)
            extra["selfie_request_id"] = selfie_response.get("selfie_request_id")
            print("alright i got here", selfie_response)

        if data.id_number:
            id_response = await cls.register_identity(data)
            extra["id_request_id"] = id_response.get("id_request_id")
            ver_status = id_response.get('request_status')

        # kyc = cls.

    @classmethod
    async def register_selfie(cls, data: KYCRequestIdentitySchema):
        user = await User.get(data.user_id)
        img2 = data.id_document_string
        image_details = [dict(image_type_id="2", image=data.selfie_image)]
        id_number = data.id_number
        id_type = data.id_type
        first_name = data.first_name
        last_name = data.last_name
        dob = data.dob
        job_type = 1
        if img2:
            image_details.append(dict(image_type_id="3", image=img2))
            job_type = 1

        data = UserImageKYCSchema(user_id=str(user.pk),
                                  job_id=f"{str(user.pk)}_{token_generator(4)}", job_type=job_type,
                                  image_details=image_details,
                                  id_info=dict(id_number=id_number, id_type=id_type.upper(), first_name=first_name,
                                               last_name=last_name,
                                               dob=dob, entered=True, country=user.country or "NG"))

        instance = cls(
            name=user.name, email=user.email, phone=user.phone, user_id=str(data.user_id), type='selfie',
            country=user.country or "NG", selfie_image=data.selfie_image, id_document_image=img2,
            provider="smile", job_id=data.get("job_id")
        )

        try:
            res = smileId.face.check(data)
            res["selfie_request_id"] = data.user_id
            status = res.get("request_status")
            instance.responses = [res],
            instance.status = status
            await instance.save()
            return res
        except Exception as e:
            print(e, "smile error")
            res = {'selfie_request_id': data.user_id}

            return res

    @classmethod
    async def register_identity(cls, data):
        # ::TODO USER_ID COMING FROM PAYLOAD NEEDS TO CHANGE


        try:
            print("CHECKING THE SERVER",data)
            obj = cls.model_validate(data)
            print('',obj)
            await obj.save()
            res = smileId.identity.check(obj)
            obj.status = res.status
            obj.responses = [res]
            obj = await obj.save()
            return obj
        except Exception as e:
            print(e)
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))

class UserKYCService(UserKyc):

    @classmethod
    async def get_or_create(cls, user_id):
        """"""
        user_kyc = await cls.find(user_id=user_id).first_or_none()

        if not user_kyc:
            user = await User.get(user_id)
            user_kyc = await cls(name=user.name, email=user.email, phone=user.phone, user_id=user.pk,
                                 level=0, country=user.country, identity_kyc_status="undone",
                                 address_kyc_status="undone").save()

        return user_kyc

    @classmethod
    async def confirm_id_validation(cls, user_id):

        kyc = await cls.get_or_create(user_id)

        if kyc.identity_kyc_status in ["failed", "undone"]:
            return
        statuses = []
        selfie_request = id_request = dict(status="pending")
        if kyc.selfie_request_id:
            selfie_request = await UserKYCRequestService.get(kyc.selfie_request_id)
            statuses.append(selfie_request.status)
            if selfie_request.status == "successful":
                obj = await User.get(user_id)
                level = kyc.level if kyc.level >= 1 else 1
                kyc.level = level
                kyc.identity_kyc_status = selfie_request.status
                kyc.last_id_confirmation = datetime.utcnow()
                await kyc.save()
                template_data = {"name": obj.name}

                # ::TODO add notification here

        if kyc.id_request_id:
            id_request = await UserKYCRequestService.get(kyc.id_request_id)
            statuses.append(id_request.status)
            if id_request.status == "successful":
                obj = await User.get(user_id)
                level = kyc.level if kyc.level >= 1 else 1
                kyc.level = level
                kyc.identity_kyc_status = id_request.status
                kyc.last_id_confirmation = datetime.utcnow()
                await kyc.save()
                template_data = {"name": obj.name}

                # ::TODO add notification here

        if "failed" in statuses:
            errors = []
            if selfie_request.status == "failed":
                res = selfie_request.responses[-1]
                errors.append(res.get("ResultText", "Error with the provided Selfie"))
            if id_request.status == "failed":
                res = id_request.responses[-1]
                errors.append(res.get("ResultText", "Error with the provided ID number"))
                kyc.identity_kyc_status= "failed"
                kyc.last_id_confirmation = datetime.utcnow()
                kyc.id_errors = errors
                await kyc.save()

                template_data = {"name": kyc.name, "errors": errors}
                # ::TODO add notification here
            return