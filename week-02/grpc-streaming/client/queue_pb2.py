# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: queue.proto
"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import symbol_database as _symbol_database
from google.protobuf.internal import builder as _builder
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()


from google.protobuf import timestamp_pb2 as google_dot_protobuf_dot_timestamp__pb2


DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\x0bqueue.proto\x12\x05queue\x1a\x1fgoogle/protobuf/timestamp.proto\"\\\n\x05Value\x12\x0f\n\x07payload\x18\x01 \x01(\x04\x12\x33\n\nupdated_at\x18\x02 \x01(\x0b\x32\x1a.google.protobuf.TimestampH\x00\x88\x01\x01\x42\r\n\x0b_updated_at\"*\n\x0bPushRequest\x12\x1b\n\x05value\x18\x01 \x01(\x0b\x32\x0c.queue.Value\"\x0e\n\x0cPushResponse\"\x0c\n\nPopRequest\"9\n\x0bPopResponse\x12 \n\x05value\x18\x01 \x01(\x0b\x32\x0c.queue.ValueH\x00\x88\x01\x01\x42\x08\n\x06_value\"\x0e\n\x0c\x44rainRequest2\xd1\x01\n\x05Queue\x12/\n\x04Push\x12\x12.queue.PushRequest\x1a\x13.queue.PushResponse\x12\x35\n\x08PushMany\x12\x12.queue.PushRequest\x1a\x13.queue.PushResponse(\x01\x12,\n\x03Pop\x12\x11.queue.PopRequest\x1a\x12.queue.PopResponse\x12\x32\n\x05\x44rain\x12\x13.queue.DrainRequest\x1a\x12.queue.PopResponse0\x01\x62\x06proto3')

_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'queue_pb2', _globals)
if _descriptor._USE_C_DESCRIPTORS == False:

  DESCRIPTOR._options = None
  _globals['_VALUE']._serialized_start=55
  _globals['_VALUE']._serialized_end=147
  _globals['_PUSHREQUEST']._serialized_start=149
  _globals['_PUSHREQUEST']._serialized_end=191
  _globals['_PUSHRESPONSE']._serialized_start=193
  _globals['_PUSHRESPONSE']._serialized_end=207
  _globals['_POPREQUEST']._serialized_start=209
  _globals['_POPREQUEST']._serialized_end=221
  _globals['_POPRESPONSE']._serialized_start=223
  _globals['_POPRESPONSE']._serialized_end=280
  _globals['_DRAINREQUEST']._serialized_start=282
  _globals['_DRAINREQUEST']._serialized_end=296
  _globals['_QUEUE']._serialized_start=299
  _globals['_QUEUE']._serialized_end=508
# @@protoc_insertion_point(module_scope)
