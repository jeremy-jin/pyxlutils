import copy
import re
from abc import ABCMeta, abstractmethod
from collections import defaultdict
import datetime as dt

from decimal import Decimal, InvalidOperation
from typing import Any

from dateutil.parser import parse
from openpyxl.cell import Cell

from . import constants
from . import utils
from .constants import MISSING_ERROR_MESSAGE

EMPTY_VALUES = (None, "", [], (), {})
FIELDS = "fields"


class ValidationError(Exception):
    pass


class CusCell(Cell):
    pass


class Field(metaclass=ABCMeta):
    """Base class for all field types"""

    default_convert_to_none_strings = ("null",)
    default_validators = []  # Default set of validators
    default_preprocessors = []  # Default set of preprocessors
    default_error_messages = {
        "required": constants.REQUIRED.message,
        "format": constants.INCORRECT_FORMAT.message,
    }

    def __init__(
        self,
        verbose_name: str = None,
        required: bool = True,
        default: Any = None,
        convert_to_none_strings: list | tuple = (),
        validators: tuple | list = (),
        pre_processors: tuple | list = (),
        error_messages: dict = None,
    ):
        """

        Args:
            verbose_name:
            required:
            default:
            validators:
            pre_processors:
            error_messages:
        """
        self.owner = None
        self.original_value = None
        self.is_error = False
        self.errors = []

        # When Verbose name is not specified, the field name is used
        self.verbose_name = verbose_name

        self.required = required
        self.default = default

        self.convert_to_none_strings = [
            *self.default_convert_to_none_strings,
            *convert_to_none_strings,
        ]
        self.validators = [*self.default_validators, *validators]
        self.preprocessors = [*self.default_validators, *pre_processors]

        # Collect default error message from self and parent classes
        messages = {}
        for cls in reversed(self.__class__.__mro__):
            messages.update(getattr(cls, "default_error_messages", {}))
        messages.update(error_messages or {})
        self.error_messages = messages

    def __str__(self):
        return "<%s:%s>" % (self.__class__.__name__, self.attr_name)

    def __set_name__(self, owner, name):
        self.attr_name = name
        self.private_name = f"_{name}"
        self.verbose_name = self.make_verbose_name(self.verbose_name)

    def __get__(self, obj, obj_type):
        value = getattr(obj, self.private_name)
        value = self.default if value is None else value
        return value

    def __set__(self, owner, value):
        self.errors = defaultdict(list)
        self.owner = owner
        self.original_value = value
        value = self._deserialize(value)
        setattr(owner, self.private_name, value)
        fields = getattr(owner, FIELDS)
        fields.update({self.attr_name: self}) if fields else setattr(
            owner, FIELDS, {self.attr_name: self}
        )

    def make_verbose_name(self, verbose_name):
        return (
            verbose_name
            if verbose_name
            else self.attr_name.replace("_", " ").capitalize()
        )

    def pre_process_value(self, value):
        _value = value
        if isinstance(value, str):
            _value = value.strip() or None
            _value = (
                None if str(_value).lower() in self.convert_to_none_strings else _value
            )

        return _value

    def _make_error(self, key, **kwargs):
        """A helper method that format the messages."""

        # if self.is_error:
        #     return

        kwargs["row_number"] = self.owner.row_number
        kwargs["field"] = self.verbose_name

        try:
            msg = self.error_messages[key]
        except KeyError:
            msg = MISSING_ERROR_MESSAGE.format(
                class_name=self.__class__.__name__, key=key
            )

        if isinstance(msg, str):
            msg = msg.format(**kwargs)

        self.errors.append(msg)
        self.is_error = True

    def _run_preprocessors(self, value):
        # TODO(Jeremy): 存在局限性，无法确定数据类型，但是必须有，
        #  因为如果某些字符串需要预处理之后才可以使用：
        #  比如：给了一个字符串，需要把空格替换为下划线，才可以去匹配枚举类型(Enum), 类似这种处理

        if value in EMPTY_VALUES:
            return value

        original_value = copy.deepcopy(value)
        for p in self.preprocessors:
            try:
                value = p(value)
            except ValidationError:
                self._make_error("incorrect_format", value=original_value)
                value = None
                break

        return value

    @abstractmethod
    def deserialize(self, value):
        """目的: 把value格式化成对应的类型, 是为了被继承后，必须实现的method"""

        return value

    def _validate_required(self, value):
        """检查required"""

        if value is None and self.required:
            self._make_error("required", value=value)

    def _run_validators(self, value):
        if value in EMPTY_VALUES:
            return None

        for v in self.validators:
            try:
                v(value)
            except ValidationError:
                self._make_error("incorrect_format", value=self.original_value)

    def validate(self, value):
        """目的：留着特定类型执行检查"""
        pass

    def _validate(self, value):
        self.validate(value)
        self._run_validators(value)

        return value

    def _deserialize(self, value):
        """Deserialize ``value``."""

        output = self.pre_process_value(value)
        output = self._run_preprocessors(output)
        self._validate_required(value)
        if value not in EMPTY_VALUES:
            output = self.deserialize(output)

        self._validate(output)
        return output


class NumberField(Field, metaclass=ABCMeta):
    def __init__(self, *args, min_value=None, max_value=None, **kwargs):
        super(NumberField, self).__init__(*args, **kwargs)
        self.min_value = min_value
        self.max_value = max_value

    def validate(self, value):
        if value is not None and self.min_value is not None and self.min_value > value:
            self._make_error("incorrect_format", value=self.original_value)
            value = None

        if value is not None and self.max_value is not None and self.min_value < value:
            self._make_error("incorrect_format", value=self.original_value)
            value = None

        return value


class IntField(NumberField):
    """An integer field."""

    def deserialize(self, value):
        try:
            value = int(value)
        except ValueError:
            self._make_error("incorrect_format", value=self.original_value)
            value = None

        return value


class FloatField(NumberField):
    """A Float field."""

    def deserialize(self, value):
        try:
            value = float(value)
        except ValueError:
            self._make_error("incorrect_format", value=self.original_value)
            value = None

        return value


class StrField(Field):
    """A string field."""

    def __init__(self, *args, min_len=None, max_len=None, **kwargs):
        super(StrField, self).__init__(*args, **kwargs)
        self.min_len = min_len
        self.max_len = max_len

    def validate(self, value):
        try:
            if value is not None and (
                (self.min_len is not None and len(value) < self.min_len)
                or (self.max_len is not None and len(value) > self.max_len)
            ):
                raise ValueError("Invalid Value.")

        except ValueError:
            self._make_error("incorrect_format", value=self.original_value)

    def deserialize(self, value):
        try:
            value = str(value).strip()
        except ValueError:
            self._make_error("incorrect_format", value=self.original_value)
            value = None

        return value


class DecimalField(Field):
    """A Decimal field."""

    def __init__(
        self,
        *args,
        places=None,
        places_limit=None,
        rounding=None,
        min_value=None,
        max_value=None,
        **kwargs,
    ):
        super(DecimalField, self).__init__(*args, **kwargs)
        self.places = places
        self.places_limit = places_limit
        self.rounding = rounding
        self.min_value = min_value
        self.max_value = max_value

    def _validate_place(self, value):
        if self.places_limit and abs(value.as_tuple().exponent) > self.places_limit:
            self._make_error("incorrect_format", value=value.to_eng_string())
            value = None

        return value

    def validate(self, value):
        self._validate_place(value)
        if self.places is not None and value.is_finite():
            value = value.quantize(self.places, rounding=self.rounding)

        if value is not None and (
            (self.min_value is not None and value < self.min_value)
            or (self.max_value is not None and value > self.max_value)
        ):
            self._make_error("incorrect_format", value=self.original_value)

    def deserialize(self, value):
        try:
            value = Decimal(str(value))
        except (ValueError, InvalidOperation):
            self._make_error("incorrect_format", value=self.original_value)
            value = None
        return value


class DateTime(Field):
    """A formatted datetime string."""

    DESERIALIZATION_FUNCS = {
        "iso": utils.from_iso_datetime,
        "iso8601": utils.from_iso_datetime,
        "rfc": utils.from_rfc,
        "rfc822": utils.from_rfc,
    }

    DEFAULT_FORMAT = "iso"

    OBJ_TYPE = "datetime"

    SCHEMA_OPTS_VAR_NAME = "datetimeformat"

    #: Default error messages.
    default_error_messages = {
        "invalid": "Not a valid {obj_type}.",
        "invalid_awareness": "Not a valid {awareness} {obj_type}.",
        "format": '"{input}" cannot be formatted as a {obj_type}.',
    }

    def __init__(self, format: str | None = None, **kwargs):
        super().__init__(**kwargs)
        # Allow this to be None. It may be set later in the ``_serialize``
        # or ``_deserialize`` methods. This allows a Schema to dynamically set the
        # format, e.g. from a Meta option
        self.format = format

    def deserialize(self, value):
        data_format = self.format or self.DEFAULT_FORMAT
        func = self.DESERIALIZATION_FUNCS.get(data_format)
        if func:
            try:
                return func(value)
            except (TypeError, AttributeError, ValueError) as error:
                raise self._make_error(
                    "invalid", input=value, obj_type=self.OBJ_TYPE
                ) from error
        else:
            try:
                return self._make_object_from_format(value, data_format)
            except (TypeError, AttributeError, ValueError) as error:
                raise self._make_error(
                    "invalid", input=value, obj_type=self.OBJ_TYPE
                ) from error

    @staticmethod
    def _make_object_from_format(value, data_format):
        return dt.datetime.strptime(value, data_format)


# class DateField(Field):
#     """A Date field."""
#
#     def deserialize(self, value):
#         if isinstance(value, datetime):
#             if value.time() != _time(0, 0):
#                 self._fail("incorrect_format", value=self.original_value)
#                 value = None
#         elif isinstance(value, date):
#             pass
#         elif isinstance(value, str):
#             try:
#                 # TODO(Jeremy): 如果是datetime，检查是否存在时间，存在时间，报错
#                 value = parse(value).date()
#             except ValueError:
#                 self._fail("incorrect_format", value=self.original_value)
#                 value = None
#         else:
#             self._fail("incorrect_format", value=self.original_value)
#             value = None
#
#         return value
#
#
# class DatetimeField(Field):
#     """A DateTime field."""
#
#     def deserialize(self, value):
#         if isinstance(value, datetime):
#             pass
#         elif isinstance(value, str):
#             try:
#                 value = parse(value)
#             except ValueError:
#                 self._fail("incorrect_format", value=self.original_value)
#                 value = None
#         else:
#             self._fail("incorrect_format", value=self.original_value)
#             value = None
#
#         return value


class BooleanField(Field):
    #: Values that will (de)serialize to `True`. If an empty set, any non-falsy
    #  value will deserialize to `True`.
    truthy = {"t", "T", "true", "True", "TRUE", "1", 1, True, "yes", "Yes", "YES"}
    #: Values that will (de)serialize to `False`.
    falsy = {"f", "F", "false", "False", "FALSE", "0", 0, 0.0, False, "no", "No", "NO"}

    def deserialize(self, value):
        if not self.truthy:
            return bool(value)
        else:
            try:
                if value in self.truthy:
                    return True
                elif value in self.falsy:
                    return False
                else:
                    self._make_error("incorrect_format", value=self.original_value)
                    return None
            except TypeError:
                self._make_error("incorrect_format", value=self.original_value)
                return None


class EnumField(Field):
    """Enumeration field.

    :param enumeration:
        Enumeration class (a subclass of ``enum.Enum``, Python>=3.4. only)

    :param kwargs:
        The same keyword arguments that :class:`Field` receives.

    """

    def __init__(self, enumeration, *args, **kwargs):
        self.enumeration = enumeration
        super(EnumField, self).__init__(*args, **kwargs)

    def deserialize(self, value):
        enumeration = {
            element.value.lower(): element.value for element in self.enumeration
        }
        try:
            return self.enumeration(enumeration.get(value.lower()))
        except (ValueError, AttributeError):
            self._make_error("incorrect_format", value=self.original_value)
            return None
