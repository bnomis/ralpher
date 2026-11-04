class RalpherError(Exception):
    """Base class for every error ralphlib raises for an expected failure."""


class GitError(RalpherError):
    pass


class InvalidArgsError(RalpherError):
    pass


class InvalidIterationsError(RalpherError):
    pass


class InvalidVarFormatError(RalpherError):
    pass


class LogFileError(RalpherError):
    pass


class NoStateFilePathError(RalpherError):
    pass


class NoStateLockFilePathError(RalpherError):
    pass


class OrderFormatError(RalpherError):
    pass


class PromptTemplateError(RalpherError):
    pass


class SettingsError(RalpherError):
    pass


class StateFileError(RalpherError):
    pass


class TasksFileError(RalpherError):
    pass


class ValueNotADictError(RalpherError):
    pass


class WaitsForUnmetError(RalpherError):
    pass
