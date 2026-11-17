from django.contrib import admin
from .models import Kategoriya, ModelInstrumenta, Ekzemplyar, Raskhodnik, Dogovor, AktProverki, Tarif, Uderzhanie, Zalog

admin.site.register([Kategoriya, ModelInstrumenta, Ekzemplyar, Raskhodnik, Dogovor, AktProverki, Tarif, Uderzhanie, Zalog])
