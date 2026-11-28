from typing import Unpack

from fastapi import Depends

from src.api.dependencies.authentication_deps import AuthenticationDeps
from src.domain.services.authorization_service import AuthorizationService, AuthorizeParams


def get_authorization_service(**kwarg: Unpack[AuthorizeParams]):
    def authorize_service(user: AuthenticationDeps):
        authorization_service = AuthorizationService(user)
        return authorization_service.authorize(**kwarg)

    return authorize_service


# @! Call in decorator level, not path-operation level, if invoked in path-operation,
# please attach annotation to this deps
def AuthorizationDeps(
    **kwarg: Unpack[AuthorizeParams],
):
    return Depends(get_authorization_service(**kwarg))
