from larry import ClientError
from botocore.exceptions import ClientError as BotoClientError
import inspect


def is_arn(value):
    return value.startswith('arn:aws:')


def attach_exception_handler(func):
    """
    When used as a decorator, it will catch Boto ClientErrors and wrap them with the larry implementation
    of ClientError.
    :param func: The function being decorated
    :return: Decorated function
    """
    def exception_handler(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except BotoClientError as e:
            raise ClientError.from_boto(e) from None
    return exception_handler


def resolve_client(client_callback, key):
    """
    When used as a decorator, it will update the client or resource parameter of the function with the module level
    value, if a value is not provided in the call.
    :param client_callback: A function to retrieve the current client or resource from the module
    :param key: The name of the parameter for the client or resource in the function call
    :return: Decorated function
    """
    def decorate(func):
        func_args = inspect.getfullargspec(func).args
        arg_index = func_args.index(key) if key in func_args else None

        def boto_obj_handler(*args, **kwargs):
            if arg_index is not None and len(args) > arg_index:
                if args[arg_index] is None:
                    args = list(args)
                    args[arg_index] = client_callback()
            elif key not in kwargs or kwargs.get(key) is None:
                kwargs[key] = client_callback()
            return func(*args, **kwargs)
        return boto_obj_handler
    return decorate


class ResourceWrapper:
    def __init__(self, obj):
        self.__resource = obj

    def __dir__(self):
        return dir(self.__resource)

    def __getattr__(self, name):
        try:
            if hasattr(self.__resource, name):
                attr = getattr(self.__resource, name)
                if callable(attr):
                    return attach_exception_handler(attr)
                else:
                    return attr
            else:
                super().__getattribute__(name)
        except BotoClientError as e:
            raise ClientError.from_boto(e) from None


def copy_non_null_keys(param_list):
    result = {}
    for key, val in param_list.items():
        if val is not None:
            result[key] = val
    return result


def map_parameters(parameters, key_map):
    result = {}
    for k, i in key_map.items():
        if parameters.get(k) is not None:
            result[i] = parameters[k]
    return result