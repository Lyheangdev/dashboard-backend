from typing import Annotated

from fastapi import Depends
from fastapi.security import OAuth2PasswordRequestForm

AuthFormDeps = Annotated[OAuth2PasswordRequestForm, Depends()]
