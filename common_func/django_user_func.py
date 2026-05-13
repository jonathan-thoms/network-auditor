import os, re, time
from django.conf import settings
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.core.files.storage import FileSystemStorage
from django.core.files import File
from django.core.mail import EmailMessage

def get_paginated_list(request, items, num=100):
    num = int(num)
    paginator = Paginator(items, num)
    page = 1
    try: page_items = paginator.page(page)
    except PageNotAnInteger: page_items = paginator.page(1)
    except: page_items = paginator.page(paginator.num_pages)
    return page_items

# def ajax_job_list(request):
#     data = {}
#     data = get_paginated_list(request, data)
#     data = serializers.serialize('json', data)
#     return HttpResponse(data, content_type='application/json')


# def get_paginated_list(request, items, num=20):
#     paginator = Paginator(items, 500)
#     page = 1
#     try: page_items = paginator.page(page)
#     except PageNotAnInteger: page_items = paginator.page(1)
#     except: page_items = paginator.page(paginator.num_pages)
#     return page_items

def save_file(request, file_handle, curr_dt, location='', activity='error'):
    if not request.FILES.get(file_handle):
        return None, None
    file_name_prefix = re.sub('[^a-zA-Z0-9_-]', '', str(location))
    re_file = request.FILES[file_handle]
    storage_location = os.path.join(settings.MEDIA_ROOT, activity, F'{file_name_prefix}_{curr_dt}')
    os.makedirs(storage_location, exist_ok=True)
    fs = FileSystemStorage(location=storage_location)
    filename = fs.save(re_file.name, re_file)
    full_file_path = os.path.join(storage_location, filename)
    return storage_location, full_file_path

# # @background
# def send_otp_mail(user_email, auth_otp):
#     email = EmailMessage(
#         'OTP for Login to mscripter',
#         F'Please use following OTP to login to mscripter: {auth_otp}',
#         'krsuman1092@gmail.com',
#         ['krsuman1092@gmail.com', 'ajay.ojha1@mcpsinc.com']
#         # [user_email]
#     )
#     email.send()
#     # return auth_otp
#     #request.session['auth_top'] = auth_otp

# # @background
# def send_notification_mail(user, activity):
#     from stool.settings import EMAIL_NOTIFICATION_LIST
#     email = EmailMessage(
#         F'iScript Notification',
#         F'Hi,\nBelow is the details of activity performed on iScript.\n\n'
#         F'User Name : {user.first_name} {user.last_name}\n'
#         F'User Email : {user.email}\n'
#         F'Activity Type : {activity}\n'
#         F'Requested On : {time.strftime("%m/%d/%Y %H:%M:%S")}',
#         'ajay.ojha1@mcpsinc.com',
#         EMAIL_NOTIFICATION_LIST
#     )
#     email.send()

def send_otp_mail(user_email, auth_otp): pass




def generate_otp():
    import random
    otp_str = 'ABCDEFGHIJabcdefghijklmnopqrstuvwxyzKLMNOPQRSTUVWXYZ1234567890'
    otp_len = 6
    auth_otp = []
    index = 0
    while index < otp_len:
        auth_otp.append(otp_str[random.randint(0, len(otp_str)-1)])
        index += 1
    auth_otp = ''.join(auth_otp)
    # auth_otp = '1234'
    return auth_otp