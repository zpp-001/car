from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib import messages
from django.db.models import Count, Sum, Q
from django.utils import timezone
from django.db.models.functions import TruncDate
from datetime import timedelta
from decimal import Decimal
import json

from .models import User, Car, ParkingSpace, ParkingRecord, ChargeRule
from .forms import RegisterForm, LoginForm, ProfileForm, CarForm, ParkingSpaceForm
from .decorators import admin_required, user_required


# ==================== Helper Functions ====================

def calculate_fee(entry_time, exit_time):
    """计算停车费用"""
    charge_rule = ChargeRule.objects.filter(is_active=True).first()
    if not charge_rule:
        return 0

    duration = (exit_time - entry_time).total_seconds() / 60
    duration_minutes = int(duration)

    if duration_minutes <= charge_rule.free_minutes:
        return 0

    billable_minutes = duration_minutes - charge_rule.free_minutes
    hours = (billable_minutes + 59) // 60  # 向上取整

    fee = charge_rule.first_hour_fee + max(0, hours - 1) * charge_rule.hourly_rate

    # 不超过日封顶
    if fee > charge_rule.daily_max:
        fee = charge_rule.daily_max

    return fee


# ==================== Auth Views ====================

def home(request):
    if request.user.is_authenticated:
        if request.user.role == 'admin' or request.user.is_superuser:
            return redirect('admin_dashboard')
        return redirect('dashboard')
    return render(request, 'home.html')


def user_login(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        form = LoginForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f'欢迎回来，{user.username}！')
            if user.role == 'admin' or user.is_superuser:
                return redirect('admin_dashboard')
            return redirect('dashboard')
        else:
            messages.error(request, '用户名或密码错误')
    else:
        form = LoginForm()
    return render(request, 'registration/login.html', {'form': form})


def register(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.phone = form.cleaned_data['phone']
            user.role = 'user'
            user.save()
            login(request, user)
            messages.success(request, '注册成功！')
            return redirect('dashboard')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{error}')
    else:
        form = RegisterForm()
    return render(request, 'registration/register.html', {'form': form})


def user_logout(request):
    logout(request)
    return redirect('login')


@user_required
def profile(request):
    if request.method == 'POST':
        form = ProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, '个人信息已更新')
            return redirect('profile')
    else:
        form = ProfileForm(instance=request.user)
    return render(request, 'registration/profile.html', {'form': form})


# ==================== User Views ====================

@user_required
def dashboard(request):
    spaces_total = ParkingSpace.objects.count()
    spaces_free = ParkingSpace.objects.filter(status='free').count()
    my_cars = Car.objects.filter(user=request.user)
    active_records = ParkingRecord.objects.filter(user=request.user, pay_status='unpaid').count()
    recent_records = ParkingRecord.objects.filter(
        Q(user=request.user) | Q(car__in=my_cars)
    )[:5]

    context = {
        'spaces_total': spaces_total,
        'spaces_free': spaces_free,
        'my_cars': my_cars,
        'active_records': active_records,
        'recent_records': recent_records,
    }
    return render(request, 'parking/dashboard.html', context)


@user_required
def car_list(request):
    cars = Car.objects.filter(user=request.user)
    return render(request, 'parking/car_list.html', {'cars': cars})


@user_required
def car_add(request):
    if request.method == 'POST':
        form = CarForm(request.POST)
        if form.is_valid():
            car = form.save(commit=False)
            car.user = request.user
            car.save()
            messages.success(request, '车辆添加成功')
            return redirect('car_list')
    else:
        form = CarForm()
    return render(request, 'parking/car_form.html', {'form': form, 'title': '添加车辆'})


@user_required
def car_delete(request, car_id):
    car = get_object_or_404(Car, id=car_id, user=request.user)
    car.delete()
    messages.success(request, '车辆已删除')
    return redirect('car_list')


@user_required


@user_required
def car_bind_space(request, car_id):
    car = get_object_or_404(Car, id=car_id, user=request.user)
    
    if car.bound_space:
        old_space = car.bound_space
        old_space.bound_user = None
        old_space.save()
        car.bound_space = None
        car.is_bound_fixed = False
        car.save()
    
    if request.method == 'POST':
        space_id = request.POST.get('space_id')
        if space_id:
            space = get_object_or_404(ParkingSpace, id=space_id, status='free', space_type='fixed')
            car.bound_space = space
            car.is_bound_fixed = True
            car.save()
            space.bound_user = request.user
            space.save()
            messages.success(request, f'车辆 {car.plate_number} 已绑定车位 {space.space_no}')
            return redirect('car_list')
        else:
            messages.error(request, '请选择一个固定车位')
    
    my_bound = ParkingSpace.objects.filter(bound_user=request.user)
    available_spaces = ParkingSpace.objects.filter(status='free', space_type='fixed').exclude(bound_user__isnull=False)
    if car.bound_space:
        from django.db.models import Q
        available_spaces = ParkingSpace.objects.filter(
            Q(status='free', space_type='fixed') | Q(id=car.bound_space.id)
        ).exclude(bound_user__isnull=False).exclude(bound_user=request.user).distinct()
        # re-include the car's own space
        available_spaces = available_spaces | ParkingSpace.objects.filter(id=car.bound_space.id)
    
    return render(request, 'parking/car_bind_space.html', {
        'car': car,
        'available_spaces': available_spaces.distinct(),
    })


def space_list(request):
    spaces = ParkingSpace.objects.all()
    my_cars = Car.objects.filter(user=request.user) if request.user.is_authenticated else []
    bound_space_ids = set(my_cars.exclude(bound_space=None).values_list('bound_space_id', flat=True))

    if request.method == 'POST':
        space_id = request.POST.get('space_id')
        car_id = request.POST.get('car_id')
        if space_id and car_id:
            car = get_object_or_404(Car, id=car_id, user=request.user)
            space = get_object_or_404(ParkingSpace, id=space_id, status='free', space_type='fixed')
            # 解绑旧车位
            if car.bound_space:
                old_space = car.bound_space
                old_space.bound_user = None
                old_space.save()
            # 绑定新车位
            car.bound_space = space
            car.is_bound_fixed = True
            car.save()
            space.bound_user = request.user
            space.save()
            messages.success(request, f'已绑定车位 {space.space_no}')
        else:
            messages.error(request, '参数错误')
        return redirect('space_list')

    return render(request, 'parking/space_list.html', {
        'spaces': spaces,
        'my_cars': my_cars,
        'bound_space_ids': bound_space_ids,
    })


@user_required
def record_list(request):
    my_cars = Car.objects.filter(user=request.user)
    records = ParkingRecord.objects.filter(
        Q(user=request.user) | Q(car__in=my_cars)
    )
    return render(request, 'parking/record_list.html', {'records': records})


@user_required
def order_list(request):
    my_cars = Car.objects.filter(user=request.user)
    orders = ParkingRecord.objects.filter(
        Q(user=request.user) | Q(car__in=my_cars)
    ).exclude(pay_status='cancelled')
    return render(request, 'parking/order_list.html', {'orders': orders})


@user_required
def order_pay(request, record_id):
    record = get_object_or_404(ParkingRecord, id=record_id)
    my_cars = Car.objects.filter(user=request.user)
    if record.user != request.user and record.car not in my_cars:
        messages.error(request, '无权操作')
        return redirect('order_list')

    if record.pay_status == 'paid':
        messages.info(request, '该订单已结算')
        return redirect('order_list')

    if request.method == 'POST':
        record.pay_status = 'paid'
        record.save()
        messages.success(request, '缴费成功！')
        return redirect('order_list')

    return render(request, 'parking/order_pay.html', {'record': record})


# ==================== Admin Views ====================

@admin_required
def admin_dashboard(request):
    today = timezone.now().date()
    today_records = ParkingRecord.objects.filter(entry_time__date=today)
    total_today = today_records.count()
    income_today = today_records.filter(pay_status='paid').aggregate(Sum('fee'))['fee__sum'] or 0

    spaces_total = ParkingSpace.objects.count()
    spaces_free = ParkingSpace.objects.filter(status='free').count()
    spaces_occupied = ParkingSpace.objects.filter(status='occupied').count()

    total_users = User.objects.filter(role='user').count()
    pending_records = ParkingRecord.objects.filter(pay_status='unpaid').count()

    recent_records = ParkingRecord.objects.all()[:10]

    context = {
        'total_today': total_today,
        'income_today': float(income_today),
        'spaces_total': spaces_total,
        'spaces_free': spaces_free,
        'spaces_occupied': spaces_occupied,
        'total_users': total_users,
        'pending_records': pending_records,
        'recent_records': recent_records,
    }
    return render(request, 'admin/dashboard.html', context)


@admin_required
def admin_spaces(request):
    spaces = ParkingSpace.objects.all()
    return render(request, 'admin/space_list.html', {'spaces': spaces})


@admin_required
def admin_space_add(request):
    if request.method == 'POST':
        form = ParkingSpaceForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, '车位添加成功')
            return redirect('admin_spaces')
    else:
        form = ParkingSpaceForm()
    return render(request, 'admin/space_form.html', {'form': form, 'title': '添加车位'})


@admin_required
def admin_space_edit(request, space_id):
    space = get_object_or_404(ParkingSpace, id=space_id)
    if request.method == 'POST':
        form = ParkingSpaceForm(request.POST, instance=space)
        if form.is_valid():
            form.save()
            messages.success(request, '车位信息已更新')
            return redirect('admin_spaces')
    else:
        form = ParkingSpaceForm(instance=space)
    return render(request, 'admin/space_form.html', {'form': form, 'title': '编辑车位'})


@admin_required
def admin_space_delete(request, space_id):
    space = get_object_or_404(ParkingSpace, id=space_id)
    if space.status == 'occupied':
        messages.error(request, '该车位已占用，无法删除')
        return redirect('admin_spaces')
    space.delete()
    messages.success(request, '车位已删除')
    return redirect('admin_spaces')


@admin_required
def admin_users(request):
    users = User.objects.filter(role='user')
    return render(request, 'admin/user_list.html', {'users': users})


@admin_required
def admin_user_toggle(request, user_id):
    user_obj = get_object_or_404(User, id=user_id)
    user_obj.status = not user_obj.status
    user_obj.save()
    action = '启用' if user_obj.status else '禁用'
    messages.success(request, f'用户{user_obj.username}已{action}')
    return redirect('admin_users')


@admin_required
def admin_records(request):
    records = ParkingRecord.objects.all()
    return render(request, 'admin/record_list.html', {'records': records})


@admin_required
def admin_record_entry(request):
    if request.method == 'POST':
        plate_number = request.POST.get('plate_number', '').strip()
        space_id = request.POST.get('space_id')

        if not plate_number:
            messages.error(request, '请输入车牌号')
            return redirect('admin_records')

        space = get_object_or_404(ParkingSpace, id=space_id) if space_id else None

        if space and space.status != 'free':
            messages.error(request, '该车位不是空闲状态')
            return redirect('admin_records')

        # 查找对应车辆和用户
        car = Car.objects.filter(plate_number=plate_number).first()

        # 如果车辆绑定了固定车位，使用绑定车位
        if car and car.bound_space and car.bound_space.status == 'free':
            space = car.bound_space
        elif not space:
            # 自动分配空闲车位
            space = ParkingSpace.objects.filter(status='free').first()
            if not space:
                messages.error(request, '没有空闲车位')
                return redirect('admin_records')

        record = ParkingRecord.objects.create(
            plate_number=plate_number,
            car=car,
            space=space,
            user=car.user if car else None,
            entry_time=timezone.now(),
        )

        space.status = 'occupied'
        space.save()

        messages.success(request, f'车辆 {plate_number} 已登记进场，车位 {space.space_no}')
        return redirect('admin_records')

    free_spaces = ParkingSpace.objects.filter(status='free')
    return render(request, 'admin/record_entry.html', {'free_spaces': free_spaces})


@admin_required
def admin_record_exit(request, record_id):
    record = get_object_or_404(ParkingRecord, id=record_id)

    if record.exit_time:
        messages.error(request, '该记录已离场')
        return redirect('admin_records')

    if request.method == 'POST':
        record.exit_time = timezone.now()
        duration = (record.exit_time - record.entry_time).total_seconds() / 60
        record.duration_minutes = int(duration)
        record.fee = calculate_fee(record.entry_time, record.exit_time)
        record.save()

        # 释放车位
        if record.space:
            record.space.status = 'free'
            record.space.save()

        messages.success(request, f'车辆 {record.plate_number} 已离场，费用：{record.fee}元')
        return redirect('admin_records')

    return render(request, 'admin/record_exit.html', {'record': record})


@admin_required
def admin_orders(request):
    orders = ParkingRecord.objects.exclude(pay_status='cancelled').order_by('-entry_time')
    return render(request, 'admin/order_list.html', {'orders': orders})


@admin_required
def admin_order_confirm(request, record_id):
    record = get_object_or_404(ParkingRecord, id=record_id)
    if request.method == 'POST':
        record.pay_status = 'paid'
        record.save()
        messages.success(request, '缴费已确认')
        return redirect('admin_orders')
    return render(request, 'admin/order_confirm.html', {'record': record})


@admin_required
def admin_charge_rules(request):
    rule = ChargeRule.objects.filter(is_active=True).first()
    if not rule:
        rule = ChargeRule.objects.create()

    if request.method == 'POST':
        rule.free_minutes = int(request.POST.get('free_minutes', 15))
        rule.first_hour_fee = Decimal(request.POST.get('first_hour_fee', 5))
        rule.hourly_rate = Decimal(request.POST.get('hourly_rate', 2))
        rule.daily_max = Decimal(request.POST.get('daily_max', 30))
        rule.save()
        messages.success(request, '收费规则已更新')
        return redirect('admin_charge_rules')

    return render(request, 'admin/charge_rules.html', {'rule': rule})


@admin_required
def admin_statistics(request):
    today = timezone.now().date()
    week_ago = today - timedelta(days=7)

    # 每日停车量和收益
    daily_stats = []
    for i in range(7):
        day = today - timedelta(days=i)
        day_records = ParkingRecord.objects.filter(entry_time__date=day)
        day_income = day_records.filter(pay_status='paid').aggregate(Sum('fee'))['fee__sum'] or 0
        daily_stats.append({
            'date': day.strftime('%m-%d'),
            'count': day_records.count(),
            'income': float(day_income),
        })
    daily_stats.reverse()

    # 车位使用率
    total_spaces = ParkingSpace.objects.count()
    occupied = ParkingSpace.objects.filter(status='occupied').count()
    usage_rate = round(occupied / total_spaces * 100, 1) if total_spaces > 0 else 0

    # 车位类型统计
    fixed_spaces = ParkingSpace.objects.filter(space_type='fixed').count()
    temp_spaces = ParkingSpace.objects.filter(space_type='temporary').count()

    context = {
        'daily_stats': json.dumps(daily_stats),
        'total_spaces': total_spaces,
        'occupied': occupied,
        'free': total_spaces - occupied,
        'usage_rate': usage_rate,
        'fixed_spaces': fixed_spaces,
        'temp_spaces': temp_spaces,
        'today_count': daily_stats[-1]['count'] if daily_stats else 0,
        'today_income': daily_stats[-1]['income'] if daily_stats else 0,
    }
    return render(request, 'admin/statistics.html', context)
