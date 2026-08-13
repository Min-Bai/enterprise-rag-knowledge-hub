
class UserServiceError(Exception):
    pass

class DuplicateUsernameError(UserServiceError):
    pass

class UserNotFoundError(UserServiceError):
    pass

class EmptyUserUpdateError(UserServiceError):
    pass

class InvalidCredentialsError(UserServiceError):
    pass

class UserInactiveError(UserServiceError):
    pass

class IncorrectPasswordError(UserServiceError):
    pass

class DocumentNotFoundError(Exception):
    pass

class DocumentRetryNotAllowedError(Exception):
    pass
