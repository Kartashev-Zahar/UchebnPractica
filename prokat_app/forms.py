from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import ModelInstrumenta


class FormaRegistracii(UserCreationForm):
    email = forms.EmailField(label="Электронная почта")

    class Meta:
        model = User
        fields = ["username", "email", "password1", "password2"]


class FormaInstrumenta(forms.ModelForm):
    class Meta:
        model = ModelInstrumenta
        fields = ["nazvanie", "kategoriya", "opisanie", "foto", "foto_fajl", "cena_za_sutki", "zalog"]
