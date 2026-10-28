import abc
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

class BaseAppError(Exception, abc.ABC):
    """Abstract base class for all application specific errors."""
    def __init__(self, message: str, error_code: str):
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)

    @property
    @abc.abstractmethod
    def status_code(self) -> int:
        pass

class UnauthenticatedError(BaseAppError):
    status_code = status.HTTP_401_UNAUTHORIZED

class PermissionDeniedError(BaseAppError):
    status_code = status.HTTP_403_FORBIDDEN

class NotFoundError(BaseAppError):
    status_code = status.HTTP_404_NOT_FOUND

class ValidationBusinessError(BaseAppError):
    status_code = status.HTTP_400_BAD_REQUEST

async def app_error_handler(request: Request, exc: BaseAppError) -> JSONResponse:
    """Catches app exceptions globally and returns a unified JSON format."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error_code": exc.error_code,
            "message": exc.message
        }
    )

def register_exception_handlers(app: FastAPI) -> None:
    """Registers the centralized app handler into the FastAPI instance."""
    app.add_exception_handler(BaseAppError, app_error_handler)
