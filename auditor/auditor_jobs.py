import os
import shutil
import importlib
from datetime import datetime
from .models import AuditJob
from django.conf import settings
# from background_task import background

from auditor.audit.GSAuditUSID import GSAuditUSID
from auditor.audit.GSAuditReport import GSAuditReport
from auditor.audit.GSAuditScript import GSAuditScript
from common_func.custom_log import Custom_Log


admin_users = []


def job_files(*, audit_type='') -> list:
    # modules = ['Audit00Defult', 'Audit01LTE', 'Audit02LTECell', 'Audit03LTERelation', 'Audit11NR', 'Audit12NRCell', 'Audit13NRRelation']
    modules = ['Audit00Defult']
    if 'LTE' in audit_type: modules += ['Audit01LTE', 'Audit02LTECell', 'Audit03LTERelation']
    if 'NR' in audit_type: modules += ['Audit11NR', 'Audit12NRCell', 'Audit13NRRelation']
    return modules


# @background()
def auditor_jobs(*, audit_job, software_log, outdir):
    job = AuditJob.objects.get(id=audit_job)
    job.status = 'Running'
    job.save()
    revision = job.version
    gs_admin = True if job.user.username in admin_users else False
    curr_dt = datetime.now().strftime('%Y%m%d%H%M%S')
    log_file = os.path.join(settings.MEDIA_ROOT, 'auditor', F'{job.sites}_{curr_dt}.log')
    custom_log = Custom_Log(log_file=log_file, activity='GS Audit')
    
    try:
        usid = GSAuditUSID(software_log, job, custom_log, outdir)
        revision = usid.revision
        for module in job_files(audit_type=str(job.audit_type)):
            custom_log.log.info(F'Running Module for site {job.sites} ----> {module}')
            getattr(importlib.import_module(F'auditor.audit.{module}'), module)(usid=usid)
        usid.df_report['flag'] = usid.df_report.flag.replace({'True': True, 'False': False})
        GSAuditScript(usid=usid)
        GSAuditReport(usid=usid, gs_admin=gs_admin)
        custom_log.log.info(F'Job completed for GS Audit Site : {job.sites}, Status: Successful!!!')
        job.status = 'Completed'
    except:
        custom_log.log.exception("message")
        custom_log.log.info(F'Job completed for GS Audit Site : {job.sites}, Status: Failed!!!')
        job.status = 'Failed'

    custom_log.release()
    shutil.copy(log_file, outdir)
    os.rename(outdir, F'{outdir}_{revision}')
    outdir = F'{outdir}_{revision}'
    shutil.make_archive(outdir, 'zip', outdir)
    shutil.rmtree(outdir)
    os.remove(log_file)
    job.script = os.path.basename(outdir + '.zip')
    job.save()

