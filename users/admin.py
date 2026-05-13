from django.contrib import admin
from .models import SMTPConfig, DBUpdate, AuditFileUpdate

admin.site.site_header = "AMENTUM G-SMART Services Admin Portal"
admin.site.site_title = "AMENTUM G-SMART Admin"
admin.site.index_title = "Welcome to AMENTUM G-SMART Admin Portal "

admin.site.register(DBUpdate)
admin.site.register(AuditFileUpdate)


@admin.register(SMTPConfig)
class SMTPConfigAdmin(admin.ModelAdmin):
    list_display = ('username', 'host', 'port', 'use_tls', 'active')

