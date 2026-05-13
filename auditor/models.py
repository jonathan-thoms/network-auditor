from django.db import models
from django.contrib.auth.models import User


class AuditSoftware(models.Model):
    sw = models.CharField(max_length=200, blank=False, null=False)

    def __str__(self):
        return F'{self.sw}'

    class Meta:
        db_table = 'auditor_audit_software'
        unique_together = ('sw',)
        verbose_name = 'AuditSoftware'


class AuditMarket(models.Model):
    market = models.CharField(max_length=50, blank=False, null=False)
    TimeZone = models.CharField(max_length=30, blank=False, null=False)
    # timeUTC = models.CharField(max_length=5, blank=False, null=False)

    @property
    def timeUTC(self):
        time_dict = {'US/Hawaii': '10:00', 'US/Alaska': '08:00', 'US/Pacific': '07:00',
                     'US/Mountain': '06:00', 'US/Central': '05:00', 'US/Eastern': '04:00'}
        return time_dict.get(self.TimeZone, '00:00')

    def __str__(self):
        return F'{self.market}  {self.TimeZone}  {self.timeUTC}'

    class Meta:
        db_table = 'auditor_audit_market'
        unique_together = ('market',)
        verbose_name = 'AuditMarket'


class LTEBandBWLayer(models.Model):
    band = models.IntegerField()
    bandwidth = models.IntegerField()
    layer = models.CharField(max_length=10, blank=False, null=False)

    def __str__(self):
        return F'{self.band}  {self.bandwidth}  {self.layer}'

    class Meta:
        db_table = 'auditor_lte_band_bw_layer'
        unique_together = ('band', 'bandwidth')
        verbose_name = 'LTEBandBWLayer'


class LTEearfcnBandBWLayer(models.Model):
    earfcndl = models.IntegerField()
    band = models.IntegerField()
    bandwidth = models.IntegerField()

    @property
    def layer(self):
        ltebandbwlayer = LTEBandBWLayer.objects.filter(band=self.band, bandwidth=self.bandwidth)
        return ltebandbwlayer[0].layer if ltebandbwlayer.exists() else 'NA'

    def __str__(self):
        return F'{self.earfcndl}  {self.band}   {self.bandwidth}  {self.layer}'

    class Meta:
        db_table = 'auditor_lte_earfcn_band_bw_layer'
        unique_together = ('earfcndl',)
        verbose_name = 'LTEearfcnBandBWLayer'


class LTECAPair(models.Model):
    pcell = models.CharField(max_length=100, blank=False, null=False)
    scell = models.CharField(max_length=100, blank=False, null=False)

    def __str__(self):
        return F'{self.pcell}  {self.scell}'

    class Meta:
        db_table = 'auditor_lte_ca_pair'
        unique_together = ('pcell', 'scell')
        verbose_name = 'LTECAPair'


class UMTSBand(models.Model):
    start = models.IntegerField()
    end = models.IntegerField()
    band = models.IntegerField()

    def __str__(self):
        return F'{self.start}  {self.band}  {self.end}  {self.band}'

    class Meta:
        db_table = 'auditor_umts_band'
        unique_together = ('start', 'end')
        verbose_name = 'UMTSBand'


class NRBand(models.Model):
    market = models.CharField(max_length=50, default='SFO', blank=False, null=False)
    arfcndl = models.IntegerField(default=0)
    bschannelbwdl = models.IntegerField(default=0)
    ssbfrequency = models.IntegerField(default=0)
    ssboffset = models.IntegerField(default=0)
    ssbduration = models.IntegerField(default=0)
    ssbperiodicity = models.IntegerField(default=0)
    ssbsubcarrierspacing = models.IntegerField(default=0)

    @property
    def band(self):
        val = int(self.ssbfrequency)
        arfcn_band_dict = {
            '5': (173800, 178800), '12': (145800, 149200), '14': (151600, 153600), '29': (143400, 145600),
            '2': (386000, 398000), '30': (470000, 472000), '66': (422000, 440000),
            '46': (743334, 795000), '48': (636667, 646666),
            '77': (620000, 680000),
            '258': (2016667, 2070832), '260': (2229166, 2279165), '261': (2070833, 2084999),
        }
        band = [_ for _ in arfcn_band_dict if arfcn_band_dict.get(_)[0] <= val <= arfcn_band_dict.get(_)[1]]
        band = int(band[0]) if len(band) else 0
        return band

    @property
    def layer(self):
        if self.band in [260, 261, 258]:
            return 'NR_HB'
        elif self.band in [5, 12, 14, 29]:
            return 'NR_LB'
        elif self.band in [2, 66, 30]:
            return 'NR_MB'
        elif self.band in [46, 48, 77]:
            return 'NR_MB+'
        else:
            return 'NA'

    def __str__(self):
        return F'{self.market}  {self.arfcndl}   {self.bschannelbwdl}  {self.ssbfrequency}  {self.band}  {self.layer}'

    class Meta:
        db_table = 'auditor_nr_band'
        unique_together = ('market', 'arfcndl', 'bschannelbwdl')
        verbose_name = 'NRBand'


class AuditJob(models.Model):
    version = models.CharField(max_length=10, blank=True, null=True, default='')
    market = models.CharField(max_length=50, blank=True, null=True, default='')
    sites = models.CharField(max_length=20, blank=True, null=True, default='')
    dlonly = models.CharField(max_length=500, blank=True, null=True, default='')
    audit_type = models.CharField(max_length=20, blank=False, null=False, default='LTE/NR')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='auditor_audit_job_user')
    status = models.CharField(max_length=20, blank=True, null=True, default='Running')
    script = models.CharField(max_length=200, blank=True, null=True, default='')
    create_dt = models.DateTimeField(auto_now_add=True)
    update_dt = models.DateTimeField(auto_now=True)

    def __str__(self): return F'{self.sites}  {self.market}  {self.dlonly}  {self.create_dt}'

    class Meta:
        db_table = 'auditor_audit_job'
        unique_together = ('version', 'market', 'sites', 'create_dt')
        ordering = ('-update_dt',)
        verbose_name = 'AuditJob'
