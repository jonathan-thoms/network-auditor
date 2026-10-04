from django.db import migrations


def update_mb_layers(apps, schema_editor):
    LTEBandBWLayer = apps.get_model('auditor', 'LTEBandBWLayer')
    # MB is 5, 10 MHz (5000, 10000) and MB+ is 15, 20 MHz (15000, 20000)
    LTEBandBWLayer.objects.filter(
        band__in=[2, 4, 5, 66],
        bandwidth__in=[15000, 20000]
    ).update(layer='MB+')
    LTEBandBWLayer.objects.filter(
        band__in=[2, 4, 66],
        bandwidth__in=[5000, 10000]
    ).update(layer='MB')
    LTEBandBWLayer.objects.filter(
        band=5,
        bandwidth=10000
    ).update(layer='MB')

    # HB is 5 MHz (5000) and HB+ is 10, 15, 20 MHz (10000, 15000, 20000)
    LTEBandBWLayer.objects.filter(
        band=30,
        bandwidth__in=[10000, 15000, 20000]
    ).update(layer='HB+')
    LTEBandBWLayer.objects.filter(
        band=30,
        bandwidth__in=[3000, 5000]
    ).update(layer='HB')


def reverse_mb_layers(apps, schema_editor):
    LTEBandBWLayer = apps.get_model('auditor', 'LTEBandBWLayer')
    LTEBandBWLayer.objects.filter(
        band__in=[2, 4, 5, 66],
        bandwidth=15000
    ).update(layer='MB')
    LTEBandBWLayer.objects.filter(
        band=30,
        bandwidth=10000
    ).update(layer='HB+')


class Migration(migrations.Migration):

    dependencies = [
        ('auditor', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(update_mb_layers, reverse_mb_layers),
    ]
