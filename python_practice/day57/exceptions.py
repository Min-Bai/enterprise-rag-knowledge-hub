
class TaskServiceError(Exception):
    pass

class TaskNotFoundError(TaskServiceError):
    pass

class DuplicateTitleError(TaskServiceError):
    pass

class EmptyUpdateError(TaskServiceError):
    pass

class TaskUserNotFoundError(TaskServiceError):
    pass

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

class TaskPermissionDeniedError(TaskServiceError):
    pass

class DocumentNotFoundError(Exception):
    pass