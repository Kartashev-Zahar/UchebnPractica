from datetime import date, timedelta
import csv
import logging
from math import ceil
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, PasswordChangeView
from django.core.mail import send_mail
from django.core.paginator import Paginator
from django.urls import reverse_lazy
from django.db import transaction
from django.db.models import Avg, Count, Exists, OuterRef, Q, Sum
from django.http import HttpResponse, HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from .forms import FormaArendy, FormaInstrumenta, FormaIzmeneniyaZakaza, FormaRegistracii, FormaVhoda, FormaVozvrata
from .models import Dogovor, Ekzemplyar, Kategoriya, ModelInstrumenta, AktProverki, Raskhodnik, Tarif, Uderzhanie, Zalog

logger = logging.getLogger(__name__)


class VhodView(LoginView):
    template_name = "registration/login.html"
    form_class = FormaVhoda

    def form_valid(self, form):
        logger.info("Пользователь успешно вошёл в систему")
        messages.success(self.request, "Вы вошли в аккаунт.")
        return super().form_valid(form)

    def form_invalid(self, form):
        logger.warning("Неудачная попытка входа: форма авторизации не прошла проверку")
        return super().form_invalid(form)


class SmenaParolyaView(PasswordChangeView):
    template_name = "registration/password_change_form.html"
    success_url = reverse_lazy("password_change_done")

    def form_valid(self, form):
        messages.success(self.request, "Пароль успешно изменён.")
        return super().form_valid(form)


def cena_arendy(stavka, dney):
    tarif = Tarif.objects.filter(ot_dney__lte=dney).order_by("-ot_dney").first()
    skidka = tarif.skidka / 100 if tarif else 0
    return round(stavka * dney * (1 - skidka))


def est_rol(user, rol):
    return user.is_superuser or user.groups.filter(name=rol).exists()


def registraciya(request):
    form = FormaRegistracii(request.POST or None)
    if request.method == "POST":
        logger.info("Начата обработка формы регистрации")
    if request.method == "POST" and form.is_valid():
        try:
            user = form.save()
        except Exception:
            logger.exception("Не удалось сохранить нового пользователя")
            raise
        logger.info("Регистрация успешно завершена")
        login(request, user)
        messages.success(request, "Аккаунт создан. Вы вошли на сайт.")
        return redirect("katalog")
    if request.method == "POST":
        logger.warning("Форма регистрации отклонена: найдены ошибки валидации")
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
    if kategoriya.isdigit():
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
    logger.debug("Запрошены данные статистики каталога")
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
        try:
            form.save()
        except Exception:
            logger.exception("Не удалось сохранить новую модель инструмента")
            raise
        logger.info("Новая модель инструмента сохранена")
        messages.success(request, "Инструмент добавлен.")
        return redirect("instrumenty_upravlenie")
    return render(request, "instrumenty_upravlenie.html", {"form": form, "instrumenty": ModelInstrumenta.objects.all()})


@login_required
def instrument_redaktirovat(request, instrument_id):
    if not request.user.is_superuser:
        return HttpResponseForbidden("Нет доступа")
    instrument = get_object_or_404(ModelInstrumenta, id=instrument_id)
    form = FormaInstrumenta(request.POST or None, request.FILES or None, instance=instrument)
    if request.method == "POST" and form.is_valid():
        try:
            form.save()
        except Exception:
            logger.exception("Не удалось сохранить изменения модели инструмента")
            raise
        logger.info("Изменения модели инструмента сохранены")
        messages.success(request, "Изменения инструмента сохранены.")
        return redirect("instrumenty_upravlenie")
    return render(request, "instrumenty_upravlenie.html", {
        "form": form,
        "instrument": instrument,
        "instrumenty": ModelInstrumenta.objects.all(),
    })


@login_required
def instrument_udalenie(request, instrument_id):
    if not request.user.is_superuser:
        return HttpResponseForbidden("Нет доступа")
    if request.method == "POST":
        get_object_or_404(ModelInstrumenta, id=instrument_id).delete()
        messages.success(request, "Инструмент удалён.")
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
    form = FormaArendy(request.POST or None)
    dostupen = Ekzemplyar.objects.filter(model=instrument, ispraven=True, svoboden=True).exists()
    if request.method == "POST" and form.is_valid():
        logger.info("Начата обработка формы аренды")
        dney = form.cleaned_data["srok"]
        osnastka = form.cleaned_data["osnastka"]
        with transaction.atomic():
            ekzemplyar = Ekzemplyar.objects.select_for_update().filter(
                model=instrument, ispraven=True, svoboden=True
            ).first()
            if not ekzemplyar:
                logger.warning("Аренда не оформлена: нет свободного исправного экземпляра")
                form.add_error(None, "Свободных экземпляров больше нет. Выберите другой инструмент.")
                dostupen = False
            else:
                dogovor = Dogovor.objects.create(
                    user=request.user, ekzemplyar=ekzemplyar, data_nachala=date.today(),
                    data_vozvrata=timezone.now() + timedelta(days=dney), srok_dnej=dney,
                    summa=cena_arendy(instrument.cena_za_sutki, dney),
                )
                Zalog.objects.create(dogovor=dogovor, summa=instrument.zalog, ostatok=instrument.zalog)
                dogovor.osnastka.set(osnastka)
                if osnastka:
                    dogovor.summa += sum(item.cena for item in osnastka)
                    dogovor.save()
                ekzemplyar.svoboden = False
                ekzemplyar.save()
        if ekzemplyar:
            logger.info("Договор аренды успешно создан")
            send_mail("Аренда оформлена", f"Заказ для {instrument.nazvanie} принят.", None, [request.user.email] if request.user.email else [], fail_silently=True)
            messages.success(request, "Аренда оформлена. Заказ появился в разделе «Мои заказы».")
            return redirect("moi_zakazy")
    return render(request, "arenda.html", {
        "instrument": instrument, "form": form, "dostupen": dostupen,
        "tarify": list(Tarif.objects.order_by("ot_dney").values("ot_dney", "skidka")),
        "raskhodniki": list(Raskhodnik.objects.values("id", "cena")),
    })


@login_required
def moi_zakazy(request):
    zakazy = Dogovor.objects.filter(user=request.user).select_related("ekzemplyar__model", "zalog")
    return render(request, "zakazy.html", {"zakazy": zakazy})


@login_required
def profil(request):
    return render(request, "profil.html")


@login_required
def zakaz_izmenit(request, dogovor_id):
    dogovor = get_object_or_404(Dogovor, id=dogovor_id, user=request.user, status=Dogovor.POLUCHENIE)
    form = FormaIzmeneniyaZakaza(request.POST or None, initial={"srok": dogovor.srok_dnej})
    if request.method == "POST" and form.is_valid():
        dney = form.cleaned_data["srok"]
        dogovor.srok_dnej = dney
        dogovor.data_vozvrata = timezone.now() + timedelta(days=dney)
        rashodniki = sum(item.cena for item in dogovor.osnastka.all())
        dogovor.summa = cena_arendy(dogovor.ekzemplyar.model.cena_za_sutki, dney) + rashodniki
        dogovor.save()
        messages.success(request, "Срок аренды изменён.")
        return redirect("moi_zakazy")
    return render(request, "izmenit_zakaz.html", {"dogovor": dogovor, "form": form})


@login_required
def zakaz_udalenie(request, dogovor_id):
    dogovor = get_object_or_404(Dogovor, id=dogovor_id, user=request.user, status=Dogovor.POLUCHENIE)
    if request.method == "POST":
        dogovor.ekzemplyar.svoboden = True
        dogovor.ekzemplyar.save()
        dogovor.delete()
        messages.success(request, "Аренда отменена.")
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
        messages.success(request, "Аренда завершена. Передайте инструмент кладовщику для приёма.")
    return redirect("moi_zakazy")


@login_required
def spisok_vozvratov(request):
    if not est_rol(request.user, "Кладовщик"):
        return HttpResponseForbidden("Нет доступа")
    zakazy = Dogovor.objects.filter(status=Dogovor.OZHIDAET_VOZVRATA).select_related(
        "ekzemplyar__model", "user"
    )
    return render(request, "spisok_vozvratov.html", {"zakazy": zakazy})


@login_required
def vozvrat(request, dogovor_id):
    if not est_rol(request.user, "Кладовщик"):
        return HttpResponseForbidden("Нет доступа")
    dogovor = get_object_or_404(Dogovor, id=dogovor_id, status=Dogovor.OZHIDAET_VOZVRATA)
    form = FormaVozvrata(request.POST or None)
    if request.method == "POST" and form.is_valid():
        zalog = Zalog.objects.filter(dogovor=dogovor).first()
        if zalog is None:
            logger.error("Возврат не проведён: для договора отсутствует запись о залоге")
            form.add_error(None, "Для договора не найден залог. Возврат не проведён, обратитесь к администратору.")
            return render(request, "vozvrat.html", {"dogovor": dogovor, "form": form})
        fakt_data = form.cleaned_data["data_vozvrata"]
        if timezone.is_naive(fakt_data):
            fakt_data = timezone.make_aware(fakt_data)
        ispraven = form.cleaned_data["ispraven"]
        prosrochka = max((fakt_data - dogovor.data_vozvrata).total_seconds() / 3600, 0)
        stavka = dogovor.ekzemplyar.model.cena_za_sutki
        summa = round(stavka / 24 * prosrochka) if prosrochka <= 4 else stavka * ceil(prosrochka / 24)
        with transaction.atomic():
            dogovor.data_fakt_vozvrata = fakt_data
            dogovor.status = Dogovor.VOZVRAT
            dogovor.save()
            AktProverki.objects.create(dogovor=dogovor, ispraven=ispraven)
            uderzhanie = min(summa, zalog.ostatok)
            zalog.ostatok -= uderzhanie
            zalog.save()
            Uderzhanie.objects.create(dogovor=dogovor, summa=uderzhanie, prichina="Просрочка")
            dogovor.ekzemplyar.svoboden = True
            dogovor.ekzemplyar.ispraven = ispraven
            dogovor.ekzemplyar.save()
        logger.info("Возврат успешно обработан")
        messages.success(request, "Возврат принят.")
        return redirect("moi_zakazy")
    return render(request, "vozvrat.html", {"dogovor": dogovor, "form": form})


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
        messages.success(request, "Инструмент отмечен как исправный.")
    return redirect("remont")
