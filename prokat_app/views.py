from datetime import date, datetime, timedelta
import csv
from math import ceil
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Avg, Count, Exists, OuterRef, Q, Sum
from django.http import HttpResponse, HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from .forms import FormaInstrumenta, FormaRegistracii
from .models import Dogovor, Ekzemplyar, Kategoriya, ModelInstrumenta, AktProverki, Tarif, Uderzhanie, Zalog


def cena_arendy(stavka, dney):
    tarif = Tarif.objects.filter(ot_dney__lte=dney).order_by("-ot_dney").first()
    skidka = tarif.skidka / 100 if tarif else 0
    return round(stavka * dney * (1 - skidka))


def est_rol(user, rol):
    return user.is_superuser or user.groups.filter(name=rol).exists()


def registraciya(request):
    form = FormaRegistracii(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        return redirect("katalog")
    return render(request, "registration/registraciya.html", {"form": form})


def katalog(request):
    dostupnye_ekzemplyary = Ekzemplyar.objects.filter(
        model_id=OuterRef("pk"), svoboden=True, ispraven=True
    )
    spisok = ModelInstrumenta.objects.annotate(
        est_svobodny=Exists(dostupnye_ekzemplyary)
    )
    text = request.GET.get("q", "")
    kategoriya = request.GET.get("kategoriya", "")
    dostupen = request.GET.get("dostupen", "")
    cena_do = request.GET.get("cena_do", "")
    zalog_do = request.GET.get("zalog_do", "")
    sort = request.GET.get("sort", "nazvanie")
    if text:
        spisok = spisok.filter(Q(nazvanie__icontains=text) | Q(opisanie__icontains=text))
    if kategoriya:
        spisok = spisok.filter(kategoriya_id=kategoriya)
    if dostupen == "da":
        spisok = spisok.filter(est_svobodny=True)
    if cena_do.isdigit():
        spisok = spisok.filter(cena_za_sutki__lte=int(cena_do))
    if zalog_do.isdigit():
        spisok = spisok.filter(zalog__lte=int(zalog_do))
    if sort in ["nazvanie", "cena_za_sutki", "-cena_za_sutki", "zalog", "-zalog"]:
        spisok = spisok.order_by(sort)
    stranica = Paginator(spisok, 20).get_page(request.GET.get("page"))
    return render(request, "katalog.html", {
        "stranica": stranica,
        "kategorii": Kategoriya.objects.all(),
        "q": text,
        "selected_kategoriya": kategoriya,
        "selected_dostupen": dostupen,
        "selected_sort": sort,
        "cena_do": cena_do,
        "zalog_do": zalog_do,
    })


def o_servise(request):
    return render(request, "o_servise.html")


def statistika(request):
    return JsonResponse({
        "pozicij": ModelInstrumenta.objects.count(),
        "ekzemplyarov": Ekzemplyar.objects.count(),
        "svobodno": Ekzemplyar.objects.filter(svoboden=True, ispraven=True).count(),
        "srednyaya_cena": round(ModelInstrumenta.objects.aggregate(Avg("cena_za_sutki"))["cena_za_sutki__avg"] or 0),
        "summa_zalogov": Ekzemplyar.objects.filter(svoboden=True).aggregate(Sum("model__zalog"))["model__zalog__sum"] or 0,
        "zakazov": Dogovor.objects.aggregate(Count("id"))["id__count"],
        "po_kategoriyam": [
            {
                "nazvanie": item.nazvanie,
                "svobodno": Ekzemplyar.objects.filter(
                    model__kategoriya=item, svoboden=True, ispraven=True
                ).count(),
            }
            for item in Kategoriya.objects.all()
        ],
    })


@login_required
def instrumenty_upravlenie(request):
    if not request.user.is_superuser:
        return HttpResponseForbidden("Нет доступа")
    form = FormaInstrumenta(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("instrumenty_upravlenie")
    return render(request, "instrumenty_upravlenie.html", {"form": form, "instrumenty": ModelInstrumenta.objects.all()})


@login_required
def instrument_redaktirovat(request, instrument_id):
    if not request.user.is_superuser:
        return HttpResponseForbidden("Нет доступа")
    instrument = get_object_or_404(ModelInstrumenta, id=instrument_id)
    form = FormaInstrumenta(request.POST or None, request.FILES or None, instance=instrument)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("instrumenty_upravlenie")
    return render(request, "instrumenty_upravlenie.html", {"form": form, "instrument": instrument})


@login_required
def instrument_udalenie(request, instrument_id):
    if not request.user.is_superuser:
        return HttpResponseForbidden("Нет доступа")
    if request.method == "POST":
        get_object_or_404(ModelInstrumenta, id=instrument_id).delete()
    return redirect("instrumenty_upravlenie")


@login_required
def csv_zakazy(request):
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = "attachment; filename=zakazy.csv"
    response.write("\ufeff")
    writer = csv.writer(response, delimiter=";")
    writer.writerow(["Номер", "Инструмент", "Срок", "Сумма", "Статус"])
    for item in Dogovor.objects.filter(user=request.user).select_related("ekzemplyar__model"):
        writer.writerow([item.id, item.ekzemplyar.model.nazvanie, item.srok_dnej, item.summa, item.status])
    return response


@login_required
def arenda(request, instrument_id):
    instrument = get_object_or_404(ModelInstrumenta, id=instrument_id)
    if request.method == "POST":
        dnej = int(request.POST.get("srok", 1))
        if dnej < 1 or dnej > 60:
            return render(request, "arenda.html", {
                "instrument": instrument,
                "oshibka": "Укажите срок от 1 до 60 суток.",
                "dostupen": True,
            })
        with transaction.atomic():
            ekzemplyar = Ekzemplyar.objects.select_for_update().filter(model=instrument, ispraven=True, svoboden=True).first()
            if not ekzemplyar:
                return render(request, "arenda.html", {
                    "instrument": instrument,
                    "oshibka": "Свободных экземпляров больше нет. Выберите другой инструмент.",
                    "dostupen": False,
                })
            nachalo = date.today()
            dogovor = Dogovor.objects.create(
                user=request.user, ekzemplyar=ekzemplyar, data_nachala=nachalo,
                data_vozvrata=timezone.now() + timedelta(days=dnej), srok_dnej=dnej,
                summa=cena_arendy(instrument.cena_za_sutki, dnej),
            )
            Zalog.objects.create(dogovor=dogovor, summa=instrument.zalog, ostatok=instrument.zalog)
            osnastka = request.POST.getlist("osnastka")
            dogovor.osnastka.set(osnastka)
            if osnastka:
                dogovor.summa += sum(item.cena for item in dogovor.osnastka.all())
                dogovor.save()
            ekzemplyar.svoboden = False
            ekzemplyar.save()
        send_mail("Аренда оформлена", f"Заказ для {instrument.nazvanie} принят.", None, [request.user.email] if request.user.email else [], fail_silently=True)
        return redirect("moi_zakazy")
    from .models import Raskhodnik
    dostupen = Ekzemplyar.objects.filter(
        model=instrument, ispraven=True, svoboden=True
    ).exists()
    return render(request, "arenda.html", {
        "instrument": instrument,
        "osnastka": Raskhodnik.objects.all(),
        "dostupen": dostupen,
    })


@login_required
def moi_zakazy(request):
    zakazy = Dogovor.objects.filter(user=request.user).select_related("ekzemplyar__model")
    return render(request, "zakazy.html", {"zakazy": zakazy})


@login_required
def profil(request):
    return render(request, "profil.html")


@login_required
def zakaz_izmenit(request, dogovor_id):
    dogovor = get_object_or_404(Dogovor, id=dogovor_id, user=request.user, status=Dogovor.POLUCHENIE)
    if request.method == "POST":
        dnej = int(request.POST.get("srok", dogovor.srok_dnej))
        if 1 <= dnej <= 60:
            dogovor.srok_dnej = dnej
            dogovor.data_vozvrata = timezone.now() + timedelta(days=dnej)
            rashodniki = sum(item.cena for item in dogovor.osnastka.all())
            dogovor.summa = cena_arendy(dogovor.ekzemplyar.model.cena_za_sutki, dnej) + rashodniki
            dogovor.save()
            return redirect("moi_zakazy")
    return render(request, "izmenit_zakaz.html", {"dogovor": dogovor})


@login_required
def zakaz_udalenie(request, dogovor_id):
    dogovor = get_object_or_404(Dogovor, id=dogovor_id, user=request.user, status=Dogovor.POLUCHENIE)
    if request.method == "POST":
        dogovor.ekzemplyar.svoboden = True
        dogovor.ekzemplyar.save()
        dogovor.delete()
    return redirect("moi_zakazy")


@login_required
def zakaz_zavershit(request, dogovor_id):
    if request.method == "POST":
        dogovor = get_object_or_404(
            Dogovor,
            id=dogovor_id,
            user=request.user,
            status=Dogovor.POLUCHENIE,
        )
        dogovor.status = Dogovor.OZHIDAET_VOZVRATA
        dogovor.save(update_fields=["status"])
    return redirect("moi_zakazy")


@login_required
def spisok_vozvratov(request):
    if not est_rol(request.user, "Кладовщик"):
        return HttpResponseForbidden("Нет доступа")
    zakazy = Dogovor.objects.filter(status=Dogovor.OZHIDAET_VOZVRATA).select_related("ekzemplyar__model")
    return render(request, "spisok_vozvratov.html", {"zakazy": zakazy})


@login_required
def vozvrat(request, dogovor_id):
    if not est_rol(request.user, "Кладовщик"):
        return HttpResponseForbidden("Нет доступа")
    dogovor = get_object_or_404(Dogovor, id=dogovor_id, status=Dogovor.OZHIDAET_VOZVRATA)
    if request.method == "POST":
        fakt_data = datetime.fromisoformat(request.POST["data_vozvrata"])
        fakt_data = timezone.make_aware(fakt_data)
        prosrochka = max((fakt_data - dogovor.data_vozvrata).total_seconds() / 3600, 0)
        stavka = dogovor.ekzemplyar.model.cena_za_sutki
        summa = round(stavka / 24 * prosrochka) if prosrochka <= 4 else stavka * ceil(prosrochka / 24)
        with transaction.atomic():
            dogovor.data_fakt_vozvrata = fakt_data
            dogovor.status = Dogovor.VOZVRAT
            dogovor.save()
            AktProverki.objects.create(dogovor=dogovor, ispraven=request.POST.get("ispraven") == "on")
            zalog = dogovor.zalog
            uderzhanie = min(summa, zalog.ostatok)
            zalog.ostatok -= uderzhanie
            zalog.save()
            Uderzhanie.objects.create(dogovor=dogovor, summa=uderzhanie, prichina="Просрочка")
            dogovor.ekzemplyar.svoboden = True
            dogovor.ekzemplyar.ispraven = request.POST.get("ispraven") == "on"
            dogovor.ekzemplyar.save()
        return redirect("moi_zakazy")
    return render(request, "vozvrat.html", {"dogovor": dogovor})


@login_required
def remont(request):
    if not est_rol(request.user, "Мастер"):
        return HttpResponseForbidden("Нет доступа")
    instrumenty = Ekzemplyar.objects.filter(ispraven=False).select_related("model")
    return render(request, "remont.html", {"instrumenty": instrumenty})


@login_required
def remont_zavershit(request, ekzemplyar_id):
    if not est_rol(request.user, "Мастер"):
        return HttpResponseForbidden("Нет доступа")
    if request.method == "POST":
        instrument = get_object_or_404(Ekzemplyar, id=ekzemplyar_id, ispraven=False)
        instrument.ispraven = True
        instrument.save()
    return redirect("remont")
