from collections import namedtuple

Tip = namedtuple("Tip", "message, description")

REQUIRED = Tip(
    message="Missing Value - {field} = : Row {row_number}.",
    description="If the field is mandatory but marked as Null or empty",
)

INCORRECT_FORMAT = Tip(
    message='Incorrect Format - {field} = "{value}" : Row {row_number}.',
    description=(
        """
        If the field value does not match the field format
        or is not in the code level options list (e.g. Gender)
        """
    ),
)

MISSING_ERROR_MESSAGE = (
    "ValidationError raised by `{class_name}`, but error key `{key}` does "
    "not exist in the `error_messages` dictionary."
)
