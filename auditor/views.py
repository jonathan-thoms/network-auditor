import re
from datetime import datetime
from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required, user_passes_test
from common_func.django_user_func import get_paginated_list, save_file

from .models import AuditJob, AuditSoftware, AuditMarket
from .auditor_jobs import auditor_jobs


last_sw = 'ATT_24Q3'


@login_required(login_url='/login/')
def audit(request):
    if request.method == 'POST':
        sites = re.sub('[^a-zA-Z0-9_-]', '', request.POST.get('sites'))
        version = request.POST.get('swrel')
        market = request.POST.get('mname')
        dlonly = request.POST.get('dlonly')
        audit_type = request.POST.get('audit_type')
        user = User.objects.get(username=request.user.username)
        audit_job = AuditJob.objects.create(version=version, market=market, sites=sites, dlonly=dlonly, audit_type=audit_type, user=user)
        audit_job.save()
        curr_datetime = datetime.now().strftime('%Y%m%d%H%M%S')
        out_dir, software_log = save_file(request, 'software_log', curr_datetime, location=sites, activity='auditor')
        auditor_jobs(audit_job=audit_job.id, software_log=software_log, outdir=out_dir)
        return redirect('/audit/')
    client_audit = {}
    cols = ['sw', 'name']
    swrel = [_.get('sw') for _ in AuditSoftware.objects.all().values('sw') if _.get('sw') > last_sw]
    mname = [_.get('market') for _ in AuditMarket.objects.all().values('market') if _.get('market') > last_sw]
    audit_type = ['LTE/NR', 'NR', 'LTE']
    jobs = AuditJob.objects.all()
    if not request.user.is_superuser: jobs = jobs.filter(user=request.user)
    jobs = get_paginated_list(request, jobs)
    return render(request, 'audit.html', {'mname': mname, 'swrel': swrel, 'audit_type': audit_type, 'jobs': jobs})

