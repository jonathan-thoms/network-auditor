from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from .views import reset_password
from .views import smtp_config_view
from auditor.views import audit

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('users/', views.user_list, name='user_list'),
    path('user/new/', views.user_create, name='user_create'),
    path('user/<int:id>/', views.user_update, name='user_update'),
    path('user/<int:id>/delete/', views.user_delete, name='user_delete'),  # <- add this
    path('profile/', views.profile, name='profile'),
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    path('<int:id>/view/', views.user_detail, name='user_detail'),  # <- add this
    path('<int:id>/toggle/', views.toggle_user_status, name='toggle_user_status'),
    path('reset-password/', reset_password, name='reset_password'),
    path('smtp-config/', smtp_config_view, name='smtp_config'),
    path('auditfile/', views.audit_file, name='audit_file'),
    path('dbupdate/', views.db_update, name='db_update'),
    path('audit/', audit, name='audit'),
]
