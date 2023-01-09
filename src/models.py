# class IntField:
#     def __init__(self):
#         print("####### init going.....")
#
#     def __get__(self, instance, owner):
#         if instance is None:
#             return self
#         return instance.__dict__[self.name]
#
#     def __set__(self, instance, value):
#         self.original_value = value
#         if not isinstance(value, int):
#             raise ValueError("expecting integer")
#         instance.__dict__[self.name] = value
#
#     def __set_name__(self, owner, name):
#         print("####### set_name going.....")
#         self.name = name
#         fields = {self.name: self}
#         setattr(owner, "fields", fields)
#
#
# class Example:
#     a = IntField()
#
#
# e = Example()
# e.a = 1
# print("#######", e.fields["a"].original_value)
from enum import Enum


class StaffNoteStatusTypes(Enum):
    OPEN = "open"
    REOPENED = "reopened"
    RESOLVED = "resolved"

    def follow(self, other):
        allowed_map = {
            self.OPEN: self.RESOLVED,
            self.RESOLVED: self.REOPENED,
            self.REOPENED: self.RESOLVED
        }
        return self == allowed_map.get(other) or self == other


a = StaffNoteStatusTypes.RESOLVED.follow(StaffNoteStatusTypes.REOPENED)

print("#####", a)