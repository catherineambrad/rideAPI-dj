from rest_framework.permissions import BasePermission


class IsAdminRole(BasePermission):
    message = "Admin role required."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == request.user.Role.ADMIN
        )

