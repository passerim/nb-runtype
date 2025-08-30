# nb-runtype

![Build](https://github.com/passerim/nb-runtype/actions/workflows/ci.yml/badge.svg)

**nb-runtype**: Automatic runtime type validation for functions in Jupyter notebooks, with flexible configuration and per-function exclusion.

This library is a IPython/Jupyter notebook environment enhancement that automatically decorates all global function definitions with Pydantic’s [`@validate_call`](https://docs.pydantic.dev/latest/api/validate_call/). It allows flexible configuration and per-function exclusion using a custom decorator.

---

## Features

- **Automatic runtime type validation** for all global functions in notebook cells
- **Flexible configuration** (pass parameters to `@validate_call`)
- **Per-function exclusion** via `@no_runtype` decorator
- **Easy enable/disable**
- **Works transparently in Jupyter/IPython**

---


## Installation

You can install the latest release manually from the GitHub Releases page:

1. Go to [https://github.com/passerim/nb-runtype/releases](https://github.com/passerim/nb-runtype/releases)
2. Download the `.whl` file from the latest release.
3. Install it with pip:

```bash
pip install /path/to/nb_runtype-<version>-py3-none-any.whl
```

Or, install it directly with pip from the GitHub Releases page:

```bash
pip install https://github.com/passerim/nb-runtype/releases/nb_runtype-<version>-py3-none-any.whl
```

---

## Quick Start

```python
from nb_runtype import enable_runtype

# Enable runtime type validation for all new global functions.
# Note that you must execute `enable_runtype()` in a cell before defining any functions you want to be type checked in subsequent cells.
# Functions defined before enabling will not be type checked.
enable_runtype()
```

```python
from nb_runtype import no_runtype, RuntypeError

# This function will be validated at runtime
def add_numbers(x: int, y: int) -> int:
    return x + y

# This will work fine
result = add_numbers(2, 3)  # Returns: 5

# This will raise RuntypeError
try:
    add_numbers("hello", 3)  # Type error!
except RuntypeError as e:
    print(f"Validation error: {e}")

# This function will NOT be validated at runtime
@no_runtype
def my_func(x: int) -> int:
    return str(x)
```

See [`tests/test_nb_runtype.ipynb`](tests/test_nb_runtype.ipynb) for more example usages.

---

## API Reference

### `enable_runtype(...)`

Enable automatic runtime type validation for all global functions defined in subsequent notebook cells.

**Parameters:**
- `strict` (bool, default: True): Enforce strict type validation (no coercion).
- `validate_return` (bool, default: True): Validate return values.
- `validate_default` (bool, default: True): Validate default argument values.
- `arbitrary_types_allowed` (bool, default: True): Allow arbitrary types as arguments/returns.

**Usage:**
```python
# Enable with default settings (strict validation)
enable_runtype()

# Enable with custom settings
enable_runtype(
    strict=False,           # Allow type coercion
    validate_return=True,   # Validate return values
    validate_default=False, # Skip default value validation
)

# Enable with minimal validation
enable_runtype(strict=False, validate_return=False)
```

---

### `disable_runtype()`

Disable automatic runtime type validation in the current IPython environment.

**Usage:**
```python
# Disable validation
disable_runtype()

# After disabling, functions behave like standard Python
def my_func(x: int) -> int:
    return str(x)  # No error raised
```

---

### `is_runtype_enabled()`

Check if runtime type validation is currently active.

**Returns:**
- `bool`: True if enabled, False otherwise.

**Usage:**
```python
# Check current status
if is_runtype_enabled():
    print("Type validation is active!")
else:
    print("Type validation is disabled")

# Use in conditional logic
enable_runtype()
assert is_runtype_enabled() == True

disable_runtype()
assert is_runtype_enabled() == False
```

---

### `no_runtype(func)`

Decorator to exclude a function from automatic runtime type validation.

**Usage:**
```python
# Exclude specific functions from validation
@no_runtype
def my_func(...):
    ...
```

---

### `get_runtype_config()`

Get the current configuration for nb-runtype.

**Returns:**
- `dict`: The configuration dictionary (keys: `strict`, `validate_return`, `validate_default`, `arbitrary_types_allowed`).

**Usage:**
```python
# Get current configuration
config = get_runtype_config()
print(config)
# Output: {'strict': True, 'validate_return': True, 'validate_default': True, 'arbitrary_types_allowed': True}

# Use configuration for conditional logic
if get_runtype_config()['strict']:
    print("Strict validation is enabled")
```

---

### Error Handling with `RuntypeError`

When type validation fails, nb-runtype raises a `RuntypeError`, a custom exception that wraps Pydantic's `ValidationError` and provides readable error messages with detailed information:

```python
from nb_runtype import enable_runtype, RuntypeError

enable_runtype()

def divide(x: float, y: float) -> float:
    return x / y

try:
    divide(10, 0)  # This will raise ZeroDivisionError, not RuntypeError
except ZeroDivisionError:
    print("Mathematical error, not type error")

try:
    divide("10", 2)  # This will raise RuntypeError
except RuntypeError as e:
    print(f"Type validation failed: {e}")
    # Output: Type validation failed: Runtime type validation failed:
    #   Parameter 'x': Input should be a valid number [type=string_type, input_value='10', input_type=str]
```

---

### Async Function Support

nb-runtype supports async functions: argument and return value validation works for both regular and async functions.

---

### Type validation for unannotated and Any-annotated functions

- **Functions without type annotations are never validated.** If a function does not specify type annotations for its arguments or return value, nb-runtype will not enforce any type checks for that function, even if validation is enabled.
- **Any disables type checking.** If a function argument or return value is annotated as `Any`, nb-runtype will allow any value for that parameter or return, without raising errors.

This behavior is consistent with Pydantic's `validate_call` and ensures maximum flexibility: you can opt out of validation by omitting annotations or using `Any` where needed.

**Functions without type annotations are never validated.**

```python
from nb_runtype import enable_runtype
enable_runtype()

def no_annot(x, y):
    return str(x) * int(y)

# No error, even with wrong types
assert no_annot('a', 2) == 'aa'
assert no_annot(2, 3) == '222'
```

**Any disables type checking.**

```python
from typing import Any

def any_args(x: Any, y: Any) -> Any:
    return x, y

# No error for any type of argument or return value
assert any_args(1, 'a') == (1, 'a')
assert any_args([1, 2], {'k': 3}) == ([1, 2], {'k': 3})
assert any_args(None, 3.14) == (None, 3.14)

def any_return(x: int) -> Any:
    if x == 0:
        return 'zero'
    return [x]

assert any_return(0) == 'zero'
assert any_return(5) == [5]
```

---

## How it works

When enabled, nb-runtype uses an AST transformer to automatically decorate all global function definitions in notebook cells with Pydantic’s `@validate_call`. 

**Note:** You must execute `enable_runtype()` in a cell *before* defining any functions you want to be type checked in subsequent cells. Functions defined before enabling will not be type checked.

This ensures that type annotations are enforced at runtime, even for functions defined and called in the same cell. You can exclude specific functions using the `@no_runtype` decorator.

---

## Contributing

Pull requests are welcome! For major changes, please open an issue first to discuss what you would like to change.

### Development Setup

```bash
# Clone the repository
git clone https://github.com/passerim/nb-runtype.git
cd nb-runtype

# Install in development mode with all dependencies
pip install -e .[dev]

# Run tests
pytest --nbmake tests/
```

---

## License

MIT
