import ast
import inspect
import sys
import textwrap
from typing import TYPE_CHECKING, Any, Dict, Tuple, Type, TypeVar


__all__ = ["get_attributes_doc", "attributes_doc", "enum_doc", "get_doc"]

PY35 = sys.version_info[0:2] >= (3, 5)

T = TypeVar("T")

if TYPE_CHECKING:  # pragma: no cover
    from enum import Enum

    TEnum = TypeVar("TEnum", bound=Enum)

assign_stmts = (ast.Assign,)  # type: Tuple[Type[ast.stmt], ...]
if PY35:
    assign_stmts = (ast.Assign, ast.AnnAssign)


class FStringFound(Exception):
    pass


def get_attributes_doc(cls):
    # type: (type) -> Dict[str, str]
    """
    Get a dictionary of attribute names to docstrings for the given class.

    Args:
        cls: The class to get the attributes' docstrings for.

    Returns:
        Dict[str, str]: A dictionary of attribute names to docstrings.
    """
    result = {}  # type: Dict[str, str]
    for parent in reversed(cls.mro()):
        if cls is object:
            continue
        try:
            source = inspect.getsource(parent)
        except (TypeError, IOError):
            continue
        source = textwrap.dedent(source)
        module = ast.parse(source)
        cls_ast = module.body[0]
        for stmt1, stmt2 in zip(cls_ast.body, cls_ast.body[1:]):  # type: ignore
            if not isinstance(stmt1, assign_stmts) or not isinstance(stmt2, ast.Expr):
                continue
            doc_expr_value = stmt2.value
            if PY35 and isinstance(doc_expr_value, ast.JoinedStr):
                raise FStringFound
            if isinstance(doc_expr_value, ast.Str):
                if PY35 and isinstance(stmt1, ast.AnnAssign):
                    attr_names = [stmt1.target.id]  # type: ignore
                else:
                    attr_names = [target.id for target in stmt1.targets]
                for attr_name in attr_names:
                    result[attr_name] = doc_expr_value.s
    return result


def attributes_doc(cls):
    # type: (Type[T]) -> Type[T]
    """Store the docstings of the attributes of a class in attributes named `__doc_NAME__`."""
    for attr_name, attr_doc in get_attributes_doc(cls).items():
        setattr(cls, "__doc_{}__".format(attr_name), attr_doc)
    return cls


def enum_doc(cls):
    # type: (Type[TEnum]) -> Type[TEnum]
    """Store the docstrings of the vaules of an enum in their `__doc__` attribute."""
    docs = get_attributes_doc(cls)
    for member in cls:
        doc = docs.get(member.name)
        if doc is not None:
            member.__doc__ = doc
    return cls


def get_doc(obj, attr_name):
    # type: (Any, str) -> str | None
    """Get the docstring of a class attribute of a class or an instance of that class.

    Args:
        obj: The class or instance with the class attribute to get the docstring of.
        attr_name: The name of the class attribute to get the docstring of.

    Returns:
        str | None: The docstring of the class attribute or None if no docstring was found.
    """
    return getattr(obj, "__doc_{}__".format(attr_name), None)
