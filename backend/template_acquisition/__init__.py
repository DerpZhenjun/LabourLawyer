"""Official document template acquisition pipeline."""

__all__ = ["run_acquisition"]

def __getattr__(name):
    # Importing the standalone OpenClaw bridge must not load every acquisition
    # adapter and HTTP dependency in the bundled document runtime.
    if name=='run_acquisition':
        from .runner import run_acquisition
        return run_acquisition
    raise AttributeError(name)
