# ---------- Custom Authentication Backend ----------

from django.contrib.auth.backends import ModelBackend
from users.models import Users


class SoftDeleteBackend(ModelBackend):
    """
    Custom authentication backend that prevents login for soft-deleted users.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        """
        Override authenticate to check if user is not deleted (deleted_at is NULL).
        """
        try:
            # Use all_with_deleted() to get even deleted users for password check
            user = Users.objects.all_with_deleted().filter(email__iexact=username).first()

            if user is None:
                return None

            # Check if user is soft-deleted
            if user.deleted_at is not None:
                return None

            # Verify password
            if not user.check_password(password):
                return None

            return user

        except Users.DoesNotExist:
            return None

    def get_user(self, user_id):
        """
        Override get_user to return only non-deleted users.
        This prevents accessing deleted users through session.
        """
        try:
            # Only return active (non-deleted) users
            return Users.objects.get(pk=user_id)
        except Users.DoesNotExist:
            return None
