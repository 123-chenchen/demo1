from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, model_validator


class AppSchema(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        extra="forbid",
    )

    @model_validator(mode="before")
    @classmethod
    def normalize_model_input(cls, value: Any) -> Any:
        if value is None:
            return value

        if isinstance(value, dict):
            data = dict(value)
        elif hasattr(value, "__dict__"):
            data = {
                key: val
                for key, val in vars(value).items()
                if not key.startswith("_")
            }
        else:
            return value

        normalized: dict[str, Any] = {}
        allowed_fields = set(cls.model_fields)

        for key, val in data.items():
            if key == "extra_metadata" and "metadata" in allowed_fields:
                normalized["metadata"] = val
            elif key in allowed_fields:
                normalized[key] = val

        return normalized

    def to_model_dict(self, *, exclude_unset: bool = False) -> dict[str, Any]:
        data = self.model_dump(exclude_unset=exclude_unset)
        if "metadata" in data:
            data["extra_metadata"] = data.pop("metadata")
        return data
