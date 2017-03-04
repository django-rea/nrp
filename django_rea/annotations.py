import logging
import inspect

logger = logging.getLogger("django_rea")


def caller_name(skip=2):
    """Get a name of a caller in the format module.class.method

       `skip` specifies how many levels of stack to skip while getting caller
       name. skip=1 means "who calls me", skip=2 "who calls my caller" etc.

       An empty string is returned if skipped levels exceed stack height

       https://gist.github.com/techtonik/2151727
    """
    stack = inspect.stack()
    start = 0 + skip
    if len(stack) < start + 1:
        return ''
    parentframe = stack[start][0]

    name = []
    module = inspect.getmodule(parentframe)
    # `modname` can be None when frame is executed directly in console
    # TODO(techtonik): consider using __main__
    if module:
        name.append(module.__name__)
    # detect classname
    if 'self' in parentframe.f_locals:
        # I don't know any way to detect call from the object method
        # XXX: there seems to be no way to detect static method call - it will
        #      be just a function call
        name.append(parentframe.f_locals['self'].__class__.__name__)
    codename = parentframe.f_code.co_name
    if codename != '<module>':  # top level usually
        name.append(codename)  # function or a method

    ## Avoid circular refs and frame leaks
    #  https://docs.python.org/2.7/library/inspect.html#the-interpreter-stack
    del parentframe, stack

    return ".".join(name)


def push_down(layer=None):
    logger.warn(
        "{0} - Planned to be pushed down in the next release to layer: {1}".format(caller_name(2), layer or 'None')
    )

    def wrapper(func):
        return func

    return wrapper


def split_apart(layer=None):
    logger.warn(
        "{0} - Planned to be splitted apart in the next release to layer: {1}".format(caller_name(2), layer or 'None')
    )

    def wrapper(func):
        return func

    return wrapper
