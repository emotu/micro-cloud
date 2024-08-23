import base64
from datetime import datetime

from fastapi import Depends, BackgroundTasks
from fastapi.exceptions import RequestValidationError

from app.core.api.middleware import MiddlewareFactory
from app.core.api.routing import EndpointFactory
from app.core.utils.custom_fields import ExtraParameters, AuthToken, format_validation_error
from app.core.utils.enums import RouteTypes, EndpointTypes, ApplicationErrors
from app.models import User
from app.schemas.users import LoginRequest, SignupRequest, AuthResponse, PasswordResetRequestSchema, \
    PasswordResetResponseSchema, PasswordResetSchema

# Generate required dependency methods.
user_dep = MiddlewareFactory.auth_deps(User)

# instance_dep = MiddlewareFactory.header_deps(Instance, key='x-instance-id', required=False, validate=False)
# entity_dep = MiddlewareFactory.header_deps(Entity, key='x-entity-id', required=False, validate=True)
mode_dep = MiddlewareFactory.cookie_or_query_deps(key='live-mode', default=True)

dependencies = [Depends(mode_dep)]

endpoint = EndpointFactory.generate(
    User, prefix="/auth", route_type=RouteTypes.APP,
    ignored_deps=['app_id', 'entity_id'], mode_dep=mode_dep,
    allow_create=False, allow_update=False, allow_delete=False, allow_list=False, allow_fetch=False
)


@endpoint.action(name="request_password", action_type=EndpointTypes.SINGLE,
                 form_schema=PasswordResetRequestSchema, response_model=PasswordResetResponseSchema)
async def request_password(payload: PasswordResetRequestSchema, model_class: User = None,
                           extra_parameters: ExtraParameters | None = None,
                           background_tasks: BackgroundTasks = None,
                           **kwargs):
    """
    Login endpoint to facilitate authentication with username and password
    """
    status = "success"

    user = await model_class.find_by_username(username=payload.email)

    if not user:
        raise RequestValidationError(
            errors=[dict(username=[f"user with email `{payload.email}` does not exist"])]
        )

    otp = user.generate_otp()
    print(otp)
    #TODO:: SEND EMAIL HERE

    return {"status": status,
            "message": "A password reset link has been sent to your email address. "
                       "Please click on the link to reset your password. Thank you!"}


@endpoint.action(name="reset_password", action_type=EndpointTypes.SINGLE,
                 form_schema=PasswordResetSchema, response_model=AuthResponse)
async def reset_password(payload: PasswordResetSchema, model_class: User = None,
                         extra_parameters: ExtraParameters | None = None,
                         background_tasks: BackgroundTasks = None,
                         **kwargs):
    """
    Login endpoint to facilitate authentication with username and password
    """

    obj = await User.find_by_username(username=payload.value)
    if not obj:
        raise RequestValidationError(
            errors=[dict(username=[f"user with email `{payload.value}` does not exist"])]
        )
    print(obj.validate_otp(otp=payload.code))
    if not obj.validate_otp(otp=payload.code):
        raise RequestValidationError(
            errors=[dict(code=[f"invalid otp"])]
        )

    await obj.set_password(payload.password)

    return User


@endpoint.action(name="login", action_type=EndpointTypes.SINGLE,
                 form_schema=LoginRequest, response_model=AuthResponse)
async def login(payload: LoginRequest, model_class: User = None,
                extra_parameters: ExtraParameters | None = None,
                background_tasks: BackgroundTasks = None,
                **kwargs):
    """
    Login endpoint to facilitate authentication with username and password
    """
    status = "success"

    # 1. Find the user
    print(payload)
    user = await model_class.find_by_username(username=payload.username)
    # user.is_2fa_enabled = True
    # await user.regenerate_2fa_secret()
    # await user.save()

    if not user:
        raise RequestValidationError(
            errors=format_validation_error(key="username", type=ApplicationErrors.VALIDATION_ERROR.value,
                                           message=f"`{payload.username}` does not exist")
        )

    if user.requires_password_reset:
        raise RequestValidationError(
            errors=format_validation_error(key="username", type=ApplicationErrors.VALIDATION_ERROR.value,
                                           message=f"request password reset `{payload.username}")
        )

    # 2. Check the password
    if not user.check_password(payload.password):
        raise RequestValidationError(
            errors=format_validation_error(key="username", type=ApplicationErrors.VALIDATION_ERROR.value,
                                           message=f"invalid password for user with username `{payload.username}")
        )

    # 3. If the user has 2fa enabled, do not generate a token, but respond with a status change
    if user.is_2fa_enabled and (payload.otp is None or user.validate_otp(payload.otp) is False):
        status = "needs_otp"

        # If there is no otp in the request, automatically generate and email one.
        if not payload.otp and user.otp_provider not in ["authenticator"]:
            otp = user.generate_otp()
            print(f"OTP ---> {otp}")
            # Todo: Implement notification service call that can be used across the application
            # background_tasks.add_task(send_notification, channels=["email", "sms"],
            #                           data=dict(otp=otp), user=user, template="otp")

        data = user.model_dump()
        data.update(status=status)
        print("This is where I got to instead")
        return AuthResponse.model_validate(data)

    # 4. Generate token, update date last logged in, and return Login Response
    auth_token = AuthToken(uid=str(user.id))
    user.last_logged_in = datetime.now()
    await user.save()

    data = user.model_dump()
    data.update(token=auth_token.token, status=status)

    return AuthResponse.model_validate(data)


@endpoint.action(name="signup", action_type=EndpointTypes.SINGLE,
                 form_schema=SignupRequest, response_model=AuthResponse)
async def signup(payload: SignupRequest, model_class: User | None = None,
                 extra_parameters: ExtraParameters = None,
                 background_tasks: BackgroundTasks = None,
                 **kwargs):
    """
    User registration endpoint to sign up a new users
    """

    # 1. Check if an account with the same email or phone number exists with the instance_id
    user_exists = await model_class.check_user_exists(email=payload.email, phone=payload.phone)
    if user_exists:
        raise RequestValidationError(
            errors=format_validation_error(key="-", type=ApplicationErrors.CUSTOM_ERROR.value,
                                           message=f"user with email address or phone number already exists"))

    password = payload.password

    # 2. Extract all parameters and create a user account
    data = payload.model_dump()
    # data.update(instance_id=extra_parameters.instance_id)
    print(data)
    user = model_class.model_validate(data)
    user.set_password(password)
    await user.save()
    data = user.model_dump()

    # await Account.create_account(user_id=user.id, account_type=user.account_type, currencies=["NGN"])

    return data


endpoint.init()
