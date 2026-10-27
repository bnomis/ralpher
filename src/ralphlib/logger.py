import pathlib
import threading
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ralphlib.options import RalpherOptions

log_file_cache_lock = threading.Lock()
log_file_cache: dict[tuple[str | None, str, int], pathlib.Path] = {}


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


def fetch_log_path(logdir: str | None, file: str, iteration: int) -> pathlib.Path | None:
    key = (logdir, file, iteration)
    with log_file_cache_lock:
        return log_file_cache.get(key)


def log_file(options: RalpherOptions, file: str, iteration: int) -> pathlib.Path:
    # we want a unique name at the start of a run, not every time this is called
    path = fetch_log_path(options.logdir, file, iteration)
    if path:
        return path

    with log_file_cache_lock:
        iteration_str = iteration_to_str(options, iteration)
        path = pathlib.Path(file)
        path = pathlib.Path(path.stem + '-' + iteration_str + path.suffix)
        if options.logdir:
            logdir = log_dir(options)
            path = logdir / path
        unique_path = make_unique(path)
        key = (options.logdir, file, iteration)
        log_file_cache[key] = unique_path
        return unique_path


def make_unique(path: pathlib.Path) -> pathlib.Path:
    counter = 1
    new_path = path
    while new_path.exists():
        new_path = path.with_name(f'{path.stem}-{counter}{path.suffix}')
        counter += 1
    return new_path


def state_file(options: RalpherOptions) -> pathlib.Path | None:
    if not options.state:
        return None
    path = pathlib.Path(options.state)
    if options.logdir:
        logdir = log_dir(options)
        return logdir / path
    return path


def state_lock_file(options: RalpherOptions) -> pathlib.Path | None:
    if not options.state:
        return None
    path = pathlib.Path(options.state + '.lock')
    if options.logdir:
        logdir = log_dir(options)
        return logdir / path
    return path
