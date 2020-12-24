from rest_framework import permissions


class UserPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        if view.action in ['get_me', 'update_me', 'delete_me']:
            return request.user.is_authenticated
        return (
                request.user.is_authenticated
                and request.user.role == 'admin'
        )

    def has_object_permission(self, request, view, obj):
        if view.action in ['get_me', 'update_me', 'delete_me']:
            return obj.author == request.user
        return (
                request.user.is_authenticated
                and request.user.role == 'admin'
        )


class IsAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return (
                request.method in permissions.SAFE_METHODS
                or request.user.role == 'admin'
        )


class ReviewAndComment(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        if request.method == 'POST':
            return request.user.is_authenticated
        if request.method == 'PATCH':
            return True
        if request.method == 'DELETE':
            return True

    def has_object_permission(self, request, view, obj):
        if request.method == 'GET':
            return True
        if request.method == 'PATCH' or request.method == 'DELETE':
            return (
                    obj.author == request.user
                    or request.user.role in ['moderator', 'admin']
            )
