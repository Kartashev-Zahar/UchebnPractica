from django.conf import settings
from django.db import migrations


def sozdat_tarify_i_roli(apps, schema_editor):
    Tarif = apps.get_model('prokat_app', 'Tarif')
    for days, discount in [(1, 0), (3, 10), (7, 20), (14, 30)]:
        Tarif.objects.update_or_create(ot_dney=days, defaults={'skidka': discount})
    Group = apps.get_model('auth', 'Group')
    Group.objects.get_or_create(name='Кладовщик')
    Group.objects.get_or_create(name='Мастер')


class Migration(migrations.Migration):
    dependencies = [
        ('prokat_app', '0002_tarif_remove_dogovor_zalog_zalog'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [migrations.RunPython(sozdat_tarify_i_roli, migrations.RunPython.noop)]
