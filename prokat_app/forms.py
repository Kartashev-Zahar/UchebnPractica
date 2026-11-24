from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User
from django.utils import timezone
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
        error_messages={"required": "Укажите электронную почту или телефон."},
        widget=forms.TextInput(attrs={"autocomplete": "email", "data-contact-input": "true"}),
    )

    class Meta:
        model = User
        fields = ["username"]

    def clean_username(self):
        username = self.cleaned_data["username"]
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("Введите другое имя пользователя: это имя уже занято.")
        return username

    def clean(self):
        # Сверяем два поля пароля и показываем подсказку рядом с повтором пароля.
        cleaned_data = forms.Form.clean(self)
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            self.add_error("password2", "Пароли не совпадают. Проверьте оба поля.")
        return cleaned_data

    def clean_contact(self):
        value = self.cleaned_data["contact"].strip()
        if "@" in value:
            value = forms.EmailField(
                error_messages={"invalid": "Введите электронную почту в правильном формате."}
            ).clean(value).lower()
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
    error_messages = {
        "invalid_login": "Проверьте имя пользователя и пароль.",
        "inactive": "Эта учётная запись не активна.",
    }
    username = forms.CharField(
        label="Электронная почта или телефон",
        error_messages={"required": "Укажите имя пользователя, почту или телефон."},
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
    srok = forms.IntegerField(
        label="Срок аренды в сутках", min_value=1, max_value=60, initial=1,
        error_messages={
            "required": "Укажите срок аренды от 1 до 60 суток.",
            "invalid": "Укажите срок аренды целым числом от 1 до 60 суток.",
            "min_value": "Укажите срок аренды от 1 до 60 суток.",
            "max_value": "Укажите срок аренды от 1 до 60 суток.",
        },
    )
    osnastka = forms.ModelMultipleChoiceField(
        label="Дополнительные услуги", queryset=Raskhodnik.objects.none(),
        required=False, widget=forms.SelectMultiple,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["osnastka"].queryset = Raskhodnik.objects.all()


class FormaIzmeneniyaZakaza(forms.Form):
    srok = forms.IntegerField(
        label="Срок аренды, дней", min_value=1, max_value=60,
        error_messages={
            "required": "Укажите срок аренды от 1 до 60 суток.",
            "invalid": "Укажите срок аренды целым числом от 1 до 60 суток.",
            "min_value": "Укажите срок аренды от 1 до 60 суток.",
            "max_value": "Укажите срок аренды от 1 до 60 суток.",
        },
    )


class FormaVozvrata(forms.Form):
    data_vozvrata = forms.DateTimeField(
        label="Дата и время возврата", input_formats=["%Y-%m-%dT%H:%M"],
        error_messages={
            "required": "Укажите дату и время возврата.",
            "invalid": "Введите дату и время возврата в указанном формате.",
        },
        widget=forms.DateTimeInput(format="%Y-%m-%dT%H:%M", attrs={"type": "datetime-local"}),
    )
    ispraven = forms.BooleanField(label="Состояние инструмента - исправен", required=False, initial=True)

    def clean_data_vozvrata(self):
        value = self.cleaned_data["data_vozvrata"]
        if timezone.is_naive(value):
            value = timezone.make_aware(value)
        if value > timezone.now():
            raise forms.ValidationError("Дата и время возврата не могут быть в будущем.")
        return value
