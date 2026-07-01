from django.contrib import admin
from .models import User, Car, ParkingSpace, ParkingRecord, ChargeRule

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ['username', 'phone', 'role', 'status', 'date_joined']
    list_filter = ['role', 'status']
    search_fields = ['username', 'phone']

@admin.register(Car)
class CarAdmin(admin.ModelAdmin):
    list_display = ['plate_number', 'user', 'car_type', 'is_bound_fixed']
    list_filter = ['car_type', 'is_bound_fixed']
    search_fields = ['plate_number']

@admin.register(ParkingSpace)
class ParkingSpaceAdmin(admin.ModelAdmin):
    list_display = ['space_no', 'space_type', 'status', 'bound_user', 'zone']
    list_filter = ['space_type', 'status']
    search_fields = ['space_no']

@admin.register(ParkingRecord)
class ParkingRecordAdmin(admin.ModelAdmin):
    list_display = ['plate_number', 'space', 'entry_time', 'exit_time', 'fee', 'pay_status']
    list_filter = ['pay_status']
    search_fields = ['plate_number']

@admin.register(ChargeRule)
class ChargeRuleAdmin(admin.ModelAdmin):
    list_display = ['free_minutes', 'first_hour_fee', 'hourly_rate', 'daily_max', 'is_active']
