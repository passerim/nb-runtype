import ast
import asyncio
import functools
from typing import Any, Callable, Dict, List, Optional

from IPython.core.getipython import get_ipython
from IPython.core.interactiveshell import InteractiveShell
from pydantic import (
    ConfigDict,
    PydanticSchemaGenerationError,
    ValidationError,
    validate_call,
)

_RUNTYPE_WRAPPER = "_runtype"
_RUNTYPE_ENABLED = "_runtype_enabled"
_RUNTYPE_CONFIG = "_runtype_config"
_RUNTYPE_EXCLUSION = "_no_runtype"


class RuntypeError(Exception):
    def __init__(self, errors: List[Any], original_exception: Optional[Exception] = None):
        self.errors = errors
        self.original_exception = original_exception
        message = self._format_errors(errors)
        super().__init__(message)

    @staticmethod
    def _format_errors(errors: List[Any]) -> str:
        lines = ["Runtime type validation failed:"]
        for err in errors:
            loc = " -> ".join(str(x) for x in err.get("loc", []))
            msg = err.get("msg", "Invalid value")
            value = err.get("input", None)
            if loc:
                lines.append(f"  Parameter '{loc}': {msg}. Value: {value!r}")
            else:
                lines.append(f"  {msg}. Value: {value!r}")
        return "\n".join(lines)


class RuntypeASTDecorator(ast.NodeTransformer):
    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef:
        # Insert _RUNTYPE_WRAPPER as the first decorator, if not present
        for deco in node.decorator_list:
            if getattr(deco, "id", None) == _RUNTYPE_WRAPPER:
                break
        else:
            node.decorator_list.insert(0, ast.Name(id=_RUNTYPE_WRAPPER, ctx=ast.Load()))
        return node

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> ast.AsyncFunctionDef:
        for deco in node.decorator_list:
            if getattr(deco, "id", None) == _RUNTYPE_WRAPPER:
                break
        else:
            node.decorator_list.insert(0, ast.Name(id=_RUNTYPE_WRAPPER, ctx=ast.Load()))
        return node


def _get_ipython_context() -> InteractiveShell:
    """
    Get the current IPython `InteractiveShell` instance.
    Raises `RuntimeError` if not in an IPython environment.
    """
    ip = get_ipython()
    if ip is None:
        raise RuntimeError("This should be run from an IPython environment.")
    return ip


def _is_runtype_enabled(ip: InteractiveShell) -> bool:
    """
    Check if `runtype` is enabled in the given IPython instance.
    """
    return hasattr(ip, _RUNTYPE_ENABLED)


def enable_runtype(
    *,
    strict: bool = True,
    validate_return: bool = True,
    validate_default: bool = True,
    arbitrary_types_allowed: bool = True,
) -> None:
    """
    Enable automatic decoration of all subsequent function definitions with Pydantic's @validate_call.
    Parameters:
        strict (bool): Enforce strict type validation.
        validate_return (bool): Validate return values.
        validate_default (bool): Validate default values.
        arbitrary_types_allowed (bool): Allow arbitrary types.
    Usage:
        enable_runtype()
    """
    # Validate parameters
    if not all(
        isinstance(param, bool)
        for param in [
            strict,
            validate_return,
            validate_default,
            arbitrary_types_allowed,
        ]
    ):
        raise TypeError("All parameters must be boolean values")

    # Get the IPython instance
    ip = _get_ipython_context()

    # Check if the transformer is already enabled
    if _is_runtype_enabled(ip):
        print("runtype already enabled.")
        return

    # Construct the configuration dictionary
    config: ConfigDict = {
        "strict": strict,
        "validate_return": validate_return,
        "validate_default": validate_default,
        "arbitrary_types_allowed": arbitrary_types_allowed,
    }

    # Define the custom decorator
    def _runtype(func: Callable[..., Any]) -> Callable[..., Any]:
        # If the marker is present, skip validate_call
        if getattr(func, _RUNTYPE_EXCLUSION, False):
            return func

        def get_validated_func() -> Callable[..., Any]:
            return validate_call(config=config, validate_return=validate_return)(func)

        if asyncio.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                try:
                    validated = get_validated_func()
                    return await validated(*args, **kwargs)
                except ValidationError as e:
                    raise RuntypeError(e.errors(), original_exception=e) from e
                except PydanticSchemaGenerationError as e:
                    raise RuntypeError(
                        [{"msg": "Failed to generate Pydantic schema"}],
                        original_exception=e,
                    ) from e
                except Exception as e:
                    raise e

            return async_wrapper
        else:

            @functools.wraps(func)
            def wrapper(*args: Any, **kwargs: Any) -> Any:
                try:
                    validated = get_validated_func()
                    return validated(*args, **kwargs)
                except ValidationError as e:
                    raise RuntypeError(e.errors(), original_exception=e) from e
                except PydanticSchemaGenerationError as e:
                    raise RuntypeError(
                        [{"msg": "Failed to generate Pydantic schema"}],
                        original_exception=e,
                    ) from e
                except Exception as e:
                    raise e

            return wrapper

    # Inject the custom decorator into user/global namespace
    try:
        ip.push({_RUNTYPE_WRAPPER: _runtype})  # type: ignore
    except Exception as e:
        raise RuntimeError(f"Failed to inject runtype decorator: {e}") from e

    # Register the AST transformer
    try:
        ip.ast_transformers.append(RuntypeASTDecorator())
        setattr(ip, _RUNTYPE_ENABLED, True)
        setattr(ip, _RUNTYPE_CONFIG, config)
    except Exception as e:
        # Clean up if transformer registration fails
        if _RUNTYPE_WRAPPER in ip.user_ns:
            del ip.user_ns[_RUNTYPE_WRAPPER]
        raise RuntimeError(f"Failed to register AST transformer: {e}") from e

    print(f"runtype enabled with config={config}")


def disable_runtype() -> None:
    """
    Disable runtype in the current IPython environment.
    Usage:
        disable_runtype()
    """
    ip = _get_ipython_context()

    if not _is_runtype_enabled(ip):
        print("runtype is not enabled.")
        return

    # Remove AST transformers
    if hasattr(ip, "ast_transformers"):
        ip.ast_transformers[:] = [t for t in ip.ast_transformers if not isinstance(t, RuntypeASTDecorator)]

    # Clean up attributes
    if hasattr(ip, _RUNTYPE_ENABLED):
        delattr(ip, _RUNTYPE_ENABLED)
    if hasattr(ip, _RUNTYPE_CONFIG):
        delattr(ip, _RUNTYPE_CONFIG)

    # Remove decorator from namespace
    if _RUNTYPE_WRAPPER in ip.user_ns:
        del ip.user_ns[_RUNTYPE_WRAPPER]

    print("runtype disabled.")


def is_runtype_enabled() -> bool:
    """
    Check if runtype is currently enabled.
    Returns:
        bool: True if runtype is enabled, False otherwise.
    Usage:
        if is_runtype_enabled():
            print("Type validation is active")
    """
    try:
        ip = _get_ipython_context()
        return _is_runtype_enabled(ip)
    except RuntimeError:
        return False


def get_runtype_config() -> Dict[str, Any]:
    """
    Get the current configuration for runtype.
    Returns:
        dict: The configuration dictionary.
    Raises:
        RuntimeError: If the transformer is not enabled.
    Usage:
        config = get_runtype_config()
    """
    ip = _get_ipython_context()
    if not _is_runtype_enabled(ip):
        raise RuntimeError("runtype is not enabled.")
    return getattr(ip, _RUNTYPE_CONFIG, {})


def no_runtype(func: Callable[..., Any]) -> Callable[..., Any]:
    """
    Marker decorator to exclude a function from runtype.
    Usage:
        @no_runtype
        def my_func(...):
            ...
    """
    setattr(func, _RUNTYPE_EXCLUSION, True)
    return func
