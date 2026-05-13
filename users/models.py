from django.db import models
from django.contrib.auth.models import User
from django.dispatch import receiver
from django.db.models.signals import post_save
# Create your models here.


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    bio = models.TextField(blank=True)
    avatar = models.ImageField(upload_to='avatars/', default='avatars/default.png')

    def __str__(self):
        return self.user.username

    # Optional method to get avatar URL for login icon or profile display
    def get_avatar_url(self):
        if self.avatar and hasattr(self.avatar, 'url'):
            return self.avatar.url
        return '/static/images/default.png'  # fallback if avatar missing


# Signal to automatically create or update Profile when User is created
@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)
    else:
        instance.profile.save()


class SMTPConfig(models.Model):
    host = models.CharField(max_length=255, default='smtp.gmail.com')
    port = models.IntegerField(default=587)
    use_tls = models.BooleanField(default=True)
    username = models.EmailField()
    password = models.CharField(max_length=255)  # store securely in production
    active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.username} ({'Active' if self.active else 'Inactive'})"


class DBUpdate(models.Model):
    appname = models.CharField(max_length=100, blank=True, null=True, default='')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='db_update_user')
    remark = models.CharField(max_length=100, blank=False, null=False, default='DB Update')
    status = models.CharField(max_length=20, blank=True, null=True, default='Running')
    script = models.CharField(max_length=100, blank=True, null=True, default='')
    create_dt = models.DateTimeField(auto_now_add=True)
    update_dt = models.DateTimeField(auto_now=True)

    def __str__(self):
        return F'{self.appname} : {self.user} : {self.create_dt}'

    class Meta:
        db_table = 'account_db_update'
        unique_together = ('appname', 'user', 'create_dt')
        ordering = ('-update_dt',)


class AuditFileUpdate(models.Model):
    version = models.CharField(max_length=10, blank=False, null=False)
    remark = models.CharField(max_length=100, blank=False, null=False, default='Audit File Update')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='audit_file_update')
    status = models.CharField(max_length=20, blank=True, null=True, default='Running')
    script = models.CharField(max_length=100, blank=True, null=True, default='')
    create_dt = models.DateTimeField(auto_now_add=True)
    update_dt = models.DateTimeField(auto_now=True)

    def __str__(self):
        return F'{self.user} : {self.version} : {self.create_dt}'

    class Meta:
        db_table = 'account_audit_file_update'
        unique_together = ('user', 'create_dt')
        ordering = ('-create_dt',)