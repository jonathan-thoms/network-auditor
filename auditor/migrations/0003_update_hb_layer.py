from django.db import migrations


def update_hb_layers(apps, schema_editor):
    LTEBandBWLayer = apps.get_model('auditor', 'LTEBandBWLayer')
    LTEBandBWLayer.objects.filter(
        band=30,
        bandwidth__in=[10000, 15000, 20000]
    ).update(layer='HB+')
    LTEBandBWLayer.objects.filter(
        band=30,
        bandwidth__in=[3000, 5000]
    ).update(layer='HB')


def reverse_hb_layers(apps, schema_editor):
    LTEBandBWLayer = apps.get_model('auditor', 'LTEBandBWLayer')
    LTEBandBWLayer.objects.filter(
        band=30,
        bandwidth=10000
    ).update(layer='HB')


class Migration(migrations.Migration):

    dependencies = [
        ('auditor', '0002_update_mb_layer'),
    ]

    operations = [
        migrations.RunPython(update_hb_layers, reverse_hb_layers),
    ]
