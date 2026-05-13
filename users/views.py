import os
import re
import secrets
import string
import shutil
from datetime import datetime
from django.conf import settings
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash, authenticate, login
from django.contrib import messages
from django.core.mail import send_mail
from django.core.files.storage import FileSystemStorage

from .forms import UserForm, UserUpdateForm, ProfileForm
from .models import SMTPConfig, Profile, DBUpdate, AuditFileUpdate
from auditor.models import AuditJob

from common_func.django_user_func import get_paginated_list, save_file
from .db_update_auditor import DBUpdateAuditor
from common_func.custom_log import Custom_Log


@login_required
def dashboard(request):
    # Integration stats
    # integrations = AuditJob.objects.all()  # Or filter by user if normal user
    jobs = AuditJob.objects.all()
    # For normal users, show only integration stats
    if not request.user.is_superuser:
        jobs = jobs.filter(user=request.user)
        return render(request, 'dashboard.html', {
            'jobs_count': jobs.count(),
            'success_jobs_count': jobs.filter(status='Completed').count(),
            'jobs': jobs.filter(user=request.user),
        })

    # For admin, show user stats too
    total_users = User.objects.count()
    active_users = User.objects.filter(is_active=True).count()
    inactive_users = total_users - active_users

    return render(request, 'dashboard.html', {
        'total_users': total_users,
        'active_users': active_users,
        'inactive_users': inactive_users,
        'jobs_count': jobs.count(),
        'success_jobs_count': jobs.filter(status='Completed').count(),
        'jobs': jobs,  # show all
    })


@login_required
def user_list(request):
    users = User.objects.all()
    return render(request, 'user_list.html', {'users': users})


# Only admin can access user creation
@login_required
@user_passes_test(lambda u: u.is_superuser)
def user_create(request):
    if request.method == 'POST':
        user_form = UserForm(request.POST)
        profile_form = ProfileForm(request.POST, request.FILES)
        if user_form.is_valid() and profile_form.is_valid():
            user = user_form.save()

            # Check if profile exists, else create
            profile, created = Profile.objects.get_or_create(user=user)
            # Update profile fields
            if 'avatar' in request.FILES:
                profile.avatar = request.FILES['avatar']
            profile.save()

            return redirect('user_list')
    else:
        user_form = UserForm()
        profile_form = ProfileForm()
    return render(request, 'user_form.html', {'user_form': user_form, 'profile_form': profile_form})


@login_required
def user_update(request, id):
    user = get_object_or_404(User, id=id)
    profile, _ = Profile.objects.get_or_create(user=user)

    if request.method == 'POST':
        user_form = UserUpdateForm(request.POST, instance=user)
        profile_form = ProfileForm(request.POST, request.FILES, instance=profile)
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            return redirect('user_list')
    else:
        user_form = UserUpdateForm(instance=user)
        profile_form = ProfileForm(instance=profile)

    return render(request, 'user_form.html', {
        'user_form': user_form,
        'profile_form': profile_form
    })


@login_required
def profile(request):
    profile = request.user.profile
    if request.method == "POST":
        form = ProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            return redirect('profile')
    else:
        form = ProfileForm(instance=profile)
    return render(request, 'users/profile.html', {'form': form})


@login_required
def change_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Important, keeps user logged in
            return redirect('profile')
    else:
        form = PasswordChangeForm(request.user)
    return render(request, 'users/change_password.html', {'form': form})


# Only admin can delete users
@login_required
@user_passes_test(lambda u: u.is_superuser)
def user_delete(request, id):
    user = get_object_or_404(User, id=id)
    user.delete()
    return redirect('user_list')


def update_avatar(request):
    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=request.user.profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Avatar updated successfully!')
            return redirect('profile')
    else:
        form = ProfileForm(instance=request.user.profile)
    return render(request, 'users/profile.html', {'form': form})


@login_required
def user_detail(request, id):
    user = get_object_or_404(User, id=id)
    return render(request, 'user_detail.html', {'user': user})


@login_required
def toggle_user_status(request, id):
    if not request.user.is_superuser:
        return redirect('dashboard')

    user = get_object_or_404(User, id=id)

    # Prevent admin from deactivating themselves
    if user == request.user:
        messages.warning(request, "You cannot deactivate your own account!")
        return redirect('user_list')

    user.is_active = not user.is_active
    user.save()
    status = "activated" if user.is_active else "deactivated"
    messages.success(request, f"User {user.username} has been {status}.")
    return redirect('user_list')


def user_login(request):
    if request.method == "POST":
        if "login" in request.POST:  # login form submitted
            username = request.POST.get("username")
            password = request.POST.get("password")
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect("dashboard")  # replace with your dashboard/home
            else:
                messages.error(request, "Invalid username or password")  # Error message
        elif "reset" in request.POST:  # reset form submitted
            identifier = request.POST.get("identifier")
            try:
                user = User.objects.get(username=identifier)
            except User.DoesNotExist:
                try:
                    user = User.objects.get(email=identifier)
                except User.DoesNotExist:
                    messages.error(request, "No user found with that Username/Email")
                    return redirect("login")
            # generate & save new password
            new_password = generate_random_password()
            user.set_password(new_password)
            user.save()
            messages.success(request, f"Password reset successful! New password: {new_password}")
            return redirect("login")
    return render(request, "users/login.html")


def generate_random_password(length=8):
    characters = string.ascii_letters + string.digits + string.punctuation
    return ''.join(secrets.choice(characters) for i in range(length))
    # return ''.join(random.choice(characters) for i in range(length))


def reset_password(request):
    if request.method == "POST":
        email = request.POST.get("email")
        try:
            user = User.objects.get(email=email)
            # Generate a random password
            new_password = generate_random_password()
            user.set_password(new_password)
            user.save()

            # Send email
            send_mail(
                subject="Your Password Has Been Reset",
                message=f"Hello {user.username},\n\nYour new password is: {new_password}\n\nPlease login and change it immediately.",
                from_email=None,
                recipient_list=[email],
                fail_silently=False,
            )
            messages.success(request, "A new password has been sent to your email.")
        except User.DoesNotExist:
            messages.error(request, "No user is registered with this email.")
    return render(request, "reset_password.html")


def smtp_config_view(request):
    smtp = SMTPConfig.objects.first()
    if request.method == "POST":
        host = request.POST.get("host")
        port = request.POST.get("port")
        use_tls = request.POST.get("use_tls") == 'on'
        username = request.POST.get("username")
        password = request.POST.get("password")
        active = request.POST.get("active") == 'on'
        if smtp:
            smtp.host = host
            smtp.port = port
            smtp.use_tls = use_tls
            smtp.username = username
            smtp.password = password
            smtp.active = active
            smtp.save()
        else:
            SMTPConfig.objects.create(
                host=host, port=port, use_tls=use_tls,
                username=username, password=password, active=active
            )
        messages.success(request, "SMTP configuration saved successfully.")
        return redirect("smtp_config")

    return render(request, "smtp_config.html", {"smtp": smtp})



@login_required
@user_passes_test(lambda u: u.is_superuser)
def db_update(request):
    if request.method == 'POST':
        appname = request.POST.get('appname')
        remark = request.POST.get('remark')
        user = User.objects.get(username=request.user.username)
        if appname not in ['auditor']: return redirect('db_update')
        job = DBUpdate.objects.create(appname=appname, remark=remark, user=user)
        job.save()
        curr_datetime = datetime.now().strftime('%Y%m%d%H%M%S')
        _, db_update_file = save_file(request, 'db_update_file', curr_datetime, location=appname, activity='db_update')
        log_file = os.path.join(settings.MEDIA_ROOT, 'db_update', F'db_update_{datetime.now().strftime("%Y%m%d%H%M%S")}.log')
        custom_log = Custom_Log(log_file=log_file, activity=F'Updating DB Tables for {appname} ')
        job.status = 'Running'
        job.save()
        if appname == 'auditor':
            update_db = DBUpdateAuditor(db_update_file=db_update_file, custom_log=custom_log)
            print(update_db.status)
            if update_db.status:
                custom_log.log.info(F'Status: Successful!!!')
                custom_log.log.info(F'Job completed for Updating DB Tables : {appname}')
                custom_log.log.info(F'Status: Successful !!!')
                job.status = 'Completed'
            else:
                custom_log.log.info(F'Status: Failed!!!')
                custom_log.log.info(F'Job completed for Updating DB Tables : {appname}')
                custom_log.log.info(F'Status: Failed !!!')
                job.status = 'Failed'
        custom_log.release()
        if job.status == 'Running': job.status = 'Failed'
        job.script = os.path.basename(log_file)
        job.save()
    jobs = DBUpdate.objects.all()
    jobs = get_paginated_list(request, jobs)
    return render(request, 'db_update.html', {'jobs': jobs, 'appname': ['auditor']})


@login_required
@user_passes_test(lambda u: u.is_superuser)
def audit_file(request):
    if request.method == 'POST':
        job = AuditFileUpdate.objects.create(
            version=re.sub(r'[^\.0-9]', '', str(request.POST.get('version'))).replace('.', '_'),
            remark=request.POST.get('remark'),
            user=User.objects.get(username=request.user.username)
        )
        job.save()
        curr_datetime = datetime.now().strftime('%Y%m%d%H%M%S')
        _, audit_file = save_file(request, 'audit_file', curr_datetime, location=F'gs', activity='audit_file')
        if str(audit_file).endswith('.xlsx'):
            a_file = os.path.join(settings.MEDIA_ROOT, 'audit_file', 'att_gs.xlsx')
            shutil.copyfile(a_file, os.path.join(os.path.dirname(audit_file), F'att_gs_old_{curr_datetime}.xlsx'))
            shutil.copyfile(audit_file, a_file)
            messages.success(request, "File Updated Successfully!!!")
            job.status = 'Completed'
        else:
            job.status = 'Failed'
            messages.success(request, "File Type is invalid!!!")

        audit_file = os.path.dirname(audit_file)
        shutil.make_archive(audit_file, 'zip', audit_file)
        shutil.rmtree(audit_file)
        job.script = os.path.basename(audit_file + '.zip')
        job.save()
        redirect('audit_file')
    jobs = AuditFileUpdate.objects.all()
    jobs = get_paginated_list(request, jobs)
    return render(request, 'audit_file.html', {'jobs': jobs})

