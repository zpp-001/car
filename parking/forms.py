from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import User, Car, ParkingSpace


class RegisterForm(UserCreationForm):
    phone = forms.CharField(max_length=11, label='手机号')

    class Meta:
        model = User
        fields = ['username', 'phone', 'password1', 'password2']


class LoginForm(AuthenticationForm):
    username = forms.CharField(label='用户名', max_length=50)
    password = forms.CharField(label='密码', widget=forms.PasswordInput)


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username', 'phone', 'email']


class CarForm(forms.ModelForm):
    class Meta:
        model = Car
        fields = ['plate_number', 'car_type']


class ParkingSpaceForm(forms.ModelForm):
    class Meta:
        model = ParkingSpace
        fields = ['space_no', 'space_type', 'status', 'bound_user', 'zone']
