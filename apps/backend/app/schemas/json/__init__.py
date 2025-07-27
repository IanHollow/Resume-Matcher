from .base import JSONSchemaFactory
from .resume_doc import SCHEMA as RESUME_DOC_SCHEMA

json_schema_factory = JSONSchemaFactory()
__all__ = ["json_schema_factory", "RESUME_DOC_SCHEMA"]
