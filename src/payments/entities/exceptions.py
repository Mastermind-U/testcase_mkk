class BaseDomainError(Exception):
    pass


class ObjectNotFoundError(BaseDomainError):
    pass


class ValidationError(BaseDomainError):
    pass
