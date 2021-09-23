from container_workflow_tool.utility import RebuilderError


def _check_base(base_image):
    if not base_image:
        raise RebuilderError("Base image needs to be set.")


def needs_base(f):
    def wrapper(self, *args, **kwargs):
        _check_base(self.base_image)
        return f(self, *args, **kwargs)
    return wrapper


# Decorators for internal API methods
def needs_distgit(f):
    def wrapper(self, *args, **kwargs):
        _check_base(self.base_image)
        self._setup_distgit()
        return f(self, *args, **kwargs)
    return wrapper


def needs_brewapi(f):
    def wrapper(self, *args, **kwargs):
        self._setup_brewapi()
        return f(self, *args, **kwargs)
    return wrapper
