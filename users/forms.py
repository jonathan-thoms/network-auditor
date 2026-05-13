# users/forms.py
from django import forms
from django.contrib.auth.models import User
from .models import Profile
from django.contrib.auth.forms import UserCreationForm

class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['avatar']
        widgets = {
            'avatar': forms.ClearableFileInput(attrs={'class': 'custom-select col-md-6'})
        }


class UserForm(UserCreationForm):
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'class': 'custom-select col-md-6'}))
    first_name = forms.CharField(required=True, widget=forms.TextInput(attrs={'class': 'custom-select col-md-6'}))
    last_name = forms.CharField(required=True, widget=forms.TextInput(attrs={'class': 'custom-select col-md-6'}))
    username = forms.CharField(required=True, widget=forms.TextInput(attrs={'class': 'custom-select col-md-6'}))

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'password1', 'password2']


class UserUpdateForm(forms.ModelForm):
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'class': 'custom-select col-md-6'}))
    first_name = forms.CharField(required=True, widget=forms.TextInput(attrs={'class': 'custom-select col-md-6'}))
    last_name = forms.CharField(required=True, widget=forms.TextInput(attrs={'class': 'custom-select col-md-6'}))
    username = forms.CharField(required=True, widget=forms.TextInput(attrs={'class': 'custom-select col-md-6'}))

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].help_text = None

    def clean_username(self):
        username = self.cleaned_data['username']
        qs = User.objects.filter(username=username).exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("This username is already taken.")
        return username
