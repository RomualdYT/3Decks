"""Application failures; transport adapters choose their representation."""


class ServiceError(Exception):
    def __init__(
        self, status: int, message: str, code: str = "operation_failed"
    ) -> None:
        super().__init__(message)
        self.status = status
        self.message = message
        self.code = code
