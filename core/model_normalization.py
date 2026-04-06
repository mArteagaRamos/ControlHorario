from django.db import models


class UppercaseNormalizationMixin:
    """Normalize string fields to uppercase before persisting model instances."""

    uppercase_fields = set()
    uppercase_excluded_fields = set()

    def normalize_uppercase_fields(self):
        target_fields = set(getattr(self, 'uppercase_fields', set()) or set())
        if not target_fields:
            return

        excluded = set(getattr(self, 'uppercase_excluded_fields', set()) or set())

        for field in self._meta.fields:
            if field.name not in target_fields:
                continue

            if field.name in excluded:
                continue

            if not isinstance(field, (models.CharField, models.TextField)):
                continue

            if field.choices:
                continue

            value = getattr(self, field.attname, None)
            if isinstance(value, str):
                setattr(self, field.attname, value.upper())

    def save(self, *args, **kwargs):
        self.normalize_uppercase_fields()
        return super().save(*args, **kwargs)