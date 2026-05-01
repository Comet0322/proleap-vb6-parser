class ParseError(Exception):
    def __init__(self, message: str, stderr: str = ""):
        super().__init__(message)
        self.stderr = stderr

class VbRuntimeError(Exception):
    pass

class InternalError(Exception):
    pass
