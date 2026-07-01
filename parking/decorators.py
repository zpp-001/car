from django.shortcuts import redirect
from django.contrib import messages


def admin_required(view_func):
    """管理员权限装饰器"""
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if request.user.role != 'admin' and not request.user.is_superuser:
            messages.error(request, '没有管理员权限')
            return redirect('dashboard')
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def user_required(view_func):
    """普通用户权限装饰器"""
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return _wrapped_view
