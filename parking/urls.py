from django.urls import path
from . import views

urlpatterns = [
    # 认证
    path('', views.home, name='home'),
    path('login/', views.user_login, name='login'),
    path('register/', views.register, name='register'),
    path('logout/', views.user_logout, name='logout'),
    path('profile/', views.profile, name='profile'),

    # 用户功能
    path('dashboard/', views.dashboard, name='dashboard'),
    path('cars/', views.car_list, name='car_list'),
    path('cars/add/', views.car_add, name='car_add'),
    path('cars/<int:car_id>/delete/', views.car_delete, name='car_delete'),
    path('cars/<int:car_id>/bind-space/', views.car_bind_space, name='car_bind_space'),
    path('spaces/', views.space_list, name='space_list'),
    path('records/', views.record_list, name='record_list'),
    path('orders/', views.order_list, name='order_list'),
    path('orders/<int:record_id>/pay/', views.order_pay, name='order_pay'),

    # 管理员功能
    path('admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin/spaces/', views.admin_spaces, name='admin_spaces'),
    path('admin/spaces/add/', views.admin_space_add, name='admin_space_add'),
    path('admin/spaces/<int:space_id>/edit/', views.admin_space_edit, name='admin_space_edit'),
    path('admin/spaces/<int:space_id>/delete/', views.admin_space_delete, name='admin_space_delete'),
    path('admin/users/', views.admin_users, name='admin_users'),
    path('admin/users/<int:user_id>/toggle/', views.admin_user_toggle, name='admin_user_toggle'),
    path('admin/records/', views.admin_records, name='admin_records'),
    path('admin/records/entry/', views.admin_record_entry, name='admin_record_entry'),
    path('admin/records/<int:record_id>/exit/', views.admin_record_exit, name='admin_record_exit'),
    path('admin/orders/', views.admin_orders, name='admin_orders'),
    path('admin/orders/<int:record_id>/confirm/', views.admin_order_confirm, name='admin_order_confirm'),
    path('admin/charge-rules/', views.admin_charge_rules, name='admin_charge_rules'),
    path('admin/statistics/', views.admin_statistics, name='admin_statistics'),
]
