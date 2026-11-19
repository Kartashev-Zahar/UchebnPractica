from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User
from .models import KontaktnyeDannye, ModelInstrumenta, Raskhodnik
from .phone_utils import normalize_phone


class FormaRegistracii(UserCreationForm):
    username = forms.CharField(
        label="Логин (ник)", max_length=150,
        validators=User._meta.get_field("username").validators,
        widget=forms.TextInput(attrs={"autocomplete": "nickname"}),
    )
    contact = forms.CharField(
        label="Электронная почта или телефон", max_length=254,
        widget=forms.TextInput(attrs={"autocomplete": "email", "data-contact-input": "true"}),
    )

    class Meta:
        model = User
        fields = ["username"]

    def clean_contact(self):
        value = self.cleaned_data["contact"].strip()
        if "@" in value:
            value = forms.EmailField().clean(value).lower()
            if User.objects.filter(email__iexact=value).exists():
                raise forms.ValidationError("Аккаунт с такой почтой уже зарегистрирован.")
            self.contact_kind = "email"
            return value

        phone = normalize_phone(value)
        if not phone:
            raise forms.ValidationError("Введите корректную почту или телефон в формате +7 999 123-45-67.")
        if KontaktnyeDannye.objects.filter(telefon=phone).exists():
            raise forms.ValidationError("Аккаунт с таким телефоном уже зарегистрирован.")
        self.contact_kind = "phone"
        return phone

    def save(self, commit=True):
        user = User(
            username=self.cleaned_data["username"],
            email=self.cleaned_data["contact"] if self.contact_kind == "email" else "",
        )
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
            if self.contact_kind == "phone":
                KontaktnyeDannye.objects.create(user=user, telefon=self.cleaned_data["contact"])
        return user


class FormaVhoda(AuthenticationForm):
    username = forms.CharField(
        label="Электронная почта или телефон",
        widget=forms.TextInput(attrs={"autofocus": True, "autocomplete": "username", "data-contact-input": "true"}),
    )
    password = forms.CharField(
        label="Пароль", strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}),
    )


class FormaInstrumenta(forms.ModelForm):
    class Meta:
        model = ModelInstrumenta
        fields = ["nazvanie", "kategoriya", "opisanie", "foto", "foto_fajl", "cena_za_sutki", "zalog"]
        widgets = {
            "opisanie": forms.Textarea(attrs={"minlength": 10, "maxlength": 1000}),
        }


class FormaArendy(forms.Form):
    srok = forms.IntegerField(label="Срок аренды в сутках", min_value=1, max_value=60, initial=1)
    osnastka = forms.ModelMultipleChoiceField(
        label="Дополнительные услуги", queryset=Raskhodnik.objects.none(),
        required=False, widget=forms.SelectMultiple,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["osnastka"].queryset = Raskhodnik.objects.all()


class FormaIzmeneniyaZakaza(forms.Form):
    srok = forms.IntegerField(label="Срок аренды, дней", min_value=1, max_value=60)


class FormaVozvrata(forms.Form):
    data_vozvrata = forms.DateTimeField(
        label="Дата и время возврата", input_formats=["%Y-%m-%dT%H:%M"],
        widget=forms.DateTimeInput(format="%Y-%m-%dT%H:%M", attrs={"type": "datetime-local"}),
    )
    ispraven = forms.BooleanField(label="Состояние инструмента - исправен", required=False, initial=True)
