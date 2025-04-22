from typing import Generic, TypeVar, Optional
from pydantic import BaseModel
from pydantic.generics import GenericModel
from fastapi import status

T = TypeVar("T")

class BaseResponse(GenericModel, Generic[T]):
    statusCode: int
    message: str
    data: Optional[T] = None
