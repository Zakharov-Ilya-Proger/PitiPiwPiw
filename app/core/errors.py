class AppError(Exception):
    def __init__(self, message):
        self.message = message

class DBError(AppError):
    pass

class DBGetRecordsError(DBError):
    pass

class DBSearchRecordsError(DBError):
    pass

class DBNotFoundError(DBError):
    pass

class DBConflictError(DBError):
    pass

class DBDeleteRecordsError(DBError):
    pass

class DBCreateRequestError(DBError):
    pass

class DBCreateUserError(DBError):
    pass

class APIError(AppError):
    pass


__all__=[
    'AppError',
    'DBError',
    'DBGetRecordsError',
    'DBSearchRecordsError',
    'DBNotFoundError',
    'DBConflictError',
    'DBDeleteRecordsError',
    'DBCreateRequestError',
    'DBCreateUserError',
    'APIError',
]