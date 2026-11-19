from django.contrib import admin
from .models import Kategoriya, ModelInstrumenta, Ekzemplyar, Raskhodnik, Dogovor, AktProverki, Tarif, Uderzhanie, Zalog, KontaktnyeDannye

admin.site.register([Kategoriya, ModelInstrumenta, Ekzemplyar, Raskhodnik, Dogovor, AktProverki, Tarif, Uderzhanie, Zalog, KontaktnyeDannye])
