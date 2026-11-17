from django.urls import path
from . import views

urlpatterns = [
    path("", views.katalog, name="katalog"),
    path("statistika/", views.statistika, name="statistika"),
    path("instrumenty/upravlenie/", views.instrumenty_upravlenie, name="instrumenty_upravlenie"),
    path("instrumenty/<int:instrument_id>/izmenit/", views.instrument_redaktirovat, name="instrument_redaktirovat"),
    path("instrumenty/<int:instrument_id>/udalit/", views.instrument_udalenie, name="instrument_udalenie"),
    path("zakazy.csv", views.csv_zakazy, name="csv_zakazy"),
    path("registraciya/", views.registraciya, name="registraciya"),
    path("arenda/<int:instrument_id>/", views.arenda, name="arenda"),
    path("moi-zakazy/", views.moi_zakazy, name="moi_zakazy"),
    path("zakazy/<int:dogovor_id>/izmenit/", views.zakaz_izmenit, name="zakaz_izmenit"),
    path("zakazy/<int:dogovor_id>/udalit/", views.zakaz_udalenie, name="zakaz_udalenie"),
    path("vozvraty/", views.spisok_vozvratov, name="spisok_vozvratov"),
    path("vozvrat/<int:dogovor_id>/", views.vozvrat, name="vozvrat"),
    path("remont/", views.remont, name="remont"),
    path("remont/<int:ekzemplyar_id>/gotovo/", views.remont_zavershit, name="remont_zavershit"),
]
