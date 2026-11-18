from datetime import timedelta
from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone
from django.contrib.auth.models import Group
from .models import AktProverki, Dogovor, Ekzemplyar, Kategoriya, ModelInstrumenta, Tarif, Uderzhanie, Zalog


class ProkatTests(TestCase):
    def setUp(self):
        for days, discount in [(1, 0), (3, 10), (7, 20), (14, 30)]:
            Tarif.objects.update_or_create(ot_dney=days, defaults={"skidka": discount})
        self.kategoriya = Kategoriya.objects.create(nazvanie="Дрели")
        self.model = ModelInstrumenta.objects.create(
            nazvanie="Перфоратор", kategoriya=self.kategoriya,
            cena_za_sutki=1000, zalog=5000,
        )
        self.ekzemplyar = Ekzemplyar.objects.create(
            model=self.model, seriinij_nomer="TEST-01",
        )
        self.user = User.objects.create_user("klient", password="test-pass-123")

    def test_katalog_i_filtry(self):
        response = self.client.get(
            "/?q=Перфоратор&kategoriya=1&dostupen=da&cena_do=1200&sort=-cena_za_sutki"
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Перфоратор")
        self.assertContains(response, '<option value="1" selected>')
        self.assertContains(response, 'name="dostupen" value="da" checked')
        self.assertContains(response, '<option value="-cena_za_sutki" selected>')
        self.assertContains(response, 'name="cena_do"')
        self.assertContains(response, 'value="1200"')

    def test_arenda_i_skidka(self):
        self.client.force_login(self.user)
        response = self.client.post("/arenda/1/", {"srok": 7})
        self.assertRedirects(response, "/moi-zakazy/")
        dogovor = Dogovor.objects.get(user=self.user)
        self.assertEqual(dogovor.summa, 5600)
        self.assertFalse(self.ekzemplyar.__class__.objects.get(pk=self.ekzemplyar.pk).svoboden)

    def test_prosrochka_i_u_full_return(self):
        staff = User.objects.create_user("kladovshik", password="test-pass-123")
        staff.groups.add(Group.objects.get(name="Кладовщик"))
        dogovor = Dogovor.objects.create(
            user=self.user, ekzemplyar=self.ekzemplyar,
            data_nachala=timezone.localdate(),
            data_vozvrata=timezone.now().replace(second=0, microsecond=0),
            srok_dnej=1, summa=1000,
        )
        Zalog.objects.create(dogovor=dogovor, summa=5000, ostatok=5000)
        self.client.force_login(self.user)
        response = self.client.post(f"/zakazy/{dogovor.id}/zavershit/")
        self.assertRedirects(response, "/moi-zakazy/")
        dogovor.refresh_from_db()
        self.assertEqual(dogovor.status, Dogovor.OZHIDAET_VOZVRATA)
        self.client.force_login(staff)
        fakt_data = timezone.localtime(dogovor.data_vozvrata + timedelta(hours=3)).strftime("%Y-%m-%dT%H:%M")
        response = self.client.post(f"/vozvrat/{dogovor.id}/", {"data_vozvrata": fakt_data, "ispraven": "on"})
        self.assertRedirects(response, "/moi-zakazy/")
        self.assertEqual(Uderzhanie.objects.get(dogovor=dogovor).summa, 125)
        self.assertTrue(AktProverki.objects.filter(dogovor=dogovor).exists())
        self.assertEqual(Dogovor.objects.get(pk=dogovor.pk).status, Dogovor.VOZVRAT)
        dogovor.zalog.refresh_from_db()
        self.assertEqual(dogovor.zalog.ostatok, 4875)

    def test_registraciya_i_pokazateli(self):
        response = self.client.post("/registraciya/", {
            "username": "noviy", "email": "noviy@example.com",
            "password1": "practice-pass-9182", "password2": "practice-pass-9182",
        })
        self.assertRedirects(response, "/")
        response = self.client.get("/statistika/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["pozicij"], 1)

    def test_master_mozhet_zakryt_remont(self):
        master = User.objects.create_user("master", password="test-pass-123")
        master.groups.add(Group.objects.get(name="Мастер"))
        self.ekzemplyar.ispraven = False
        self.ekzemplyar.save()
        self.client.force_login(master)
        self.assertEqual(self.client.get("/remont/").status_code, 200)
        response = self.client.post(f"/remont/{self.ekzemplyar.id}/gotovo/")
        self.assertRedirects(response, "/remont/")
        self.ekzemplyar.refresh_from_db()
        self.assertTrue(self.ekzemplyar.ispraven)

    def test_admin_crud_instrumenta_i_csv(self):
        staff = User.objects.create_superuser("admin", password="test-pass-123")
        self.client.force_login(staff)
        response = self.client.post("/instrumenty/upravlenie/", {
            "nazvanie": "Пила", "kategoriya": self.kategoriya.id,
            "opisanie": "Для теста", "foto": "pila",
            "cena_za_sutki": 500, "zalog": 2000,
        })
        self.assertRedirects(response, "/instrumenty/upravlenie/")
        pila = ModelInstrumenta.objects.get(nazvanie="Пила")
        self.client.post(f"/instrumenty/{pila.id}/udalit/")
        self.assertFalse(ModelInstrumenta.objects.filter(pk=pila.id).exists())
        self.client.force_login(self.user)
        self.assertEqual(self.client.get("/zakazy.csv").status_code, 200)

    def test_izmenenie_i_otmena_arendy(self):
        self.client.force_login(self.user)
        dogovor = Dogovor.objects.create(
            user=self.user, ekzemplyar=self.ekzemplyar,
            data_nachala=timezone.localdate(), data_vozvrata=timezone.now() + timedelta(days=2),
            srok_dnej=2, summa=2000,
        )
        Zalog.objects.create(dogovor=dogovor, summa=5000, ostatok=5000)
        self.client.post(f"/zakazy/{dogovor.id}/izmenit/", {"srok": 3})
        dogovor.refresh_from_db()
        self.assertEqual(dogovor.summa, 2700)
        self.client.post(f"/zakazy/{dogovor.id}/udalit/")
        self.assertFalse(Dogovor.objects.filter(pk=dogovor.id).exists())
