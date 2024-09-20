from google.protobuf import timestamp_pb2 as _timestamp_pb2
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class Value(_message.Message):
    __slots__ = ["payload", "updated_at"]
    PAYLOAD_FIELD_NUMBER: _ClassVar[int]
    UPDATED_AT_FIELD_NUMBER: _ClassVar[int]
    payload: int
    updated_at: _timestamp_pb2.Timestamp
    def __init__(self, payload: _Optional[int] = ..., updated_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ...) -> None: ...

class PushRequest(_message.Message):
    __slots__ = ["value"]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    value: Value
    def __init__(self, value: _Optional[_Union[Value, _Mapping]] = ...) -> None: ...

class PushResponse(_message.Message):
    __slots__ = []
    def __init__(self) -> None: ...

class PopRequest(_message.Message):
    __slots__ = []
    def __init__(self) -> None: ...

class PopResponse(_message.Message):
    __slots__ = ["value"]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    value: Value
    def __init__(self, value: _Optional[_Union[Value, _Mapping]] = ...) -> None: ...

class DrainRequest(_message.Message):
    __slots__ = []
    def __init__(self) -> None: ...
