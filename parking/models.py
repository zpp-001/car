from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class User(AbstractUser):
    """用户表"""
    ROLE_CHOICES = (
        ('user', '普通用户'),
        ('admin', '管理员'),
    )
    phone = models.CharField('手机号', max_length=11, blank=True)
    role = models.CharField('角色', max_length=10, choices=ROLE_CHOICES, default='user')
    status = models.BooleanField('账号状态', default=True)

    class Meta:
        verbose_name = '用户'
        verbose_name_plural = '用户'

    def __str__(self):
        return f'{self.username} ({self.get_role_display()})'


class ParkingSpace(models.Model):
    """车位表"""
    SPACE_TYPE_CHOICES = (
        ('fixed', '固定车位'),
        ('temporary', '临时车位'),
    )
    STATUS_CHOICES = (
        ('free', '空闲'),
        ('occupied', '已占用'),
        ('locked', '已锁定'),
    )
    space_no = models.CharField('车位编号', max_length=20, unique=True)
    space_type = models.CharField('车位类型', max_length=10, choices=SPACE_TYPE_CHOICES, default='temporary')
    status = models.CharField('车位状态', max_length=10, choices=STATUS_CHOICES, default='free')
    bound_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='绑定用户')
    zone = models.CharField('所属区域', max_length=50, blank=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        verbose_name = '车位'
        verbose_name_plural = '车位'

    def __str__(self):
        return f'{self.space_no} ({self.get_status_display()})'


class Car(models.Model):
    """车辆表"""
    CAR_TYPE_CHOICES = (
        ('small', '小型车'),
        ('suv', 'SUV'),
        ('large', '大型车'),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='cars', verbose_name='所有者')
    plate_number = models.CharField('车牌号', max_length=20, unique=True)
    car_type = models.CharField('车辆类型', max_length=10, choices=CAR_TYPE_CHOICES, default='small')
    is_bound_fixed = models.BooleanField('是否绑定固定车位', default=False)
    bound_space = models.OneToOneField(ParkingSpace, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='绑定车位')
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        verbose_name = '车辆'
        verbose_name_plural = '车辆'

    def __str__(self):
        return self.plate_number


class ChargeRule(models.Model):
    """收费规则表"""
    free_minutes = models.IntegerField('免费时长（分钟）', default=15)
    first_hour_fee = models.DecimalField('首小时收费', max_digits=10, decimal_places=2, default=5.00)
    hourly_rate = models.DecimalField('超时单价（每小时）', max_digits=10, decimal_places=2, default=2.00)
    daily_max = models.DecimalField('日封顶价格', max_digits=10, decimal_places=2, default=30.00)
    is_active = models.BooleanField('启用状态', default=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        verbose_name = '收费规则'
        verbose_name_plural = '收费规则'

    def __str__(self):
        return f'免费{self.free_minutes}分钟 首小时{self.first_hour_fee}元'


class ParkingRecord(models.Model):
    """停车记录表"""
    PAY_STATUS_CHOICES = (
        ('unpaid', '未结算'),
        ('paid', '已结算'),
        ('cancelled', '已取消'),
    )
    plate_number = models.CharField('车牌号', max_length=20)
    car = models.ForeignKey(Car, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='关联车辆')
    space = models.ForeignKey(ParkingSpace, on_delete=models.SET_NULL, null=True, verbose_name='车位')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='用户')
    entry_time = models.DateTimeField('进场时间', default=timezone.now)
    exit_time = models.DateTimeField('离场时间', null=True, blank=True)
    duration_minutes = models.IntegerField('停车时长（分钟）', default=0)
    fee = models.DecimalField('费用金额', max_digits=10, decimal_places=2, default=0)
    pay_status = models.CharField('缴费状态', max_length=10, choices=PAY_STATUS_CHOICES, default='unpaid')
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        verbose_name = '停车记录'
        verbose_name_plural = '停车记录'
        ordering = ['-entry_time']

    def __str__(self):
        return f'{self.plate_number} - {self.entry_time.strftime("%Y-%m-%d %H:%M")}'
