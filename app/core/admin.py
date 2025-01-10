from django.contrib import admin # noqa
from core import models  # noqa
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin  # noqa
from django.utils.translation import gettext as _  # noqa


class UserAdmin(BaseUserAdmin):
    """Custom user admin."""
    ordering = ["id"]
    list_display = ["email", "name"]
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (_('permissions'),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser"
                )
            }
        ),
        (_('important dates'), {"fields": ("last_login",)})
    )
    readonly_fields = ("last_login",)
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "password1", "password2", "name", "is_active", "is_staff", "is_superuser"),
        }),
    )

admin.site.register(models.User, UserAdmin)
