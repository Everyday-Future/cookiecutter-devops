# core/adapters/parsers/__init__.py
from core.adapters.parsers.enum import StrEnum
from core.adapters.parsers.json_serializer import JsonSerializer
from core.adapters.parsers.datetime import Datetime, datetime_now
from core.adapters.parsers.html import HtmlParser
from core.adapters.parsers.auto_serializer import AutoSerializer, DataclassSerializerMixin
