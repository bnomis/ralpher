import pathlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ralphlib.options import RalpherOptions


def init(options: RalpherOptions) -> None:
    if options.logdir:
        logdir = log_dir(options)
        logdir.mkdir(parents=True, exist_ok=True)


def log_dir(options: RalpherOptions) -> pathlib.Path:
    if not options.logdir:
        raise ValueError('logdir is not set')
    return pathlib.Path(options.logdir).expanduser().absolute()


def iteration_to_str(options: RalpherOptions, iteration: int) -> str:
    max_iterations = options.iterations
    width = len(str(max_iterations))
    return str(iteration).zfill(width)


def log_file(options: RalpherOptions, file: str, iteration: int) -> pathlib.Path:
    iteration_str = iteration_to_str(options, iteration)
    path = pathlib.Path(file)
    path = pathlib.Path(path.stem + '-' + iteration_str + path.suffix)
    if options.logdir:
        logdir = log_dir(options)
        path = logdir / path
    return path


def state_file(options: RalpherOptions) -> pathlib.Path | None:
    if not options.state:
        return None
    path = pathlib.Path(options.state)
    if options.logdir:
        logdir = log_dir(options)
        return logdir / path
    return path
