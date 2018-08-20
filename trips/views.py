from django.shortcuts import render

# Create your views here.

# For kaffine
from django.http import HttpResponse

# For home/app_url/brocast
from datetime import datetime, timedelta
from .models import Post, PersonalInfo


def kaffine(request):
    return HttpResponse('For Kaffine')


def home(request):
    post_list = Post.objects.all()
    return render(request, 'index.html', {'post_list': post_list, 'current_time': str(datetime.now() + timedelta(hours=8))[0:-7]
                                          })


def app_url(request):
    register_num = len(PersonalInfo.objects.all())
    return render(request, 'app_url.html', {'register_num': register_num, 'current_time': str(datetime.now() + timedelta(hours=8))[0:-7]
                                            })


def brocast(request):
    last_message = Post.objects.all().filter(title='last_message')[0].content
    last_photo = Post.objects.all().filter(title='last_photo')[0].photo
    last_photo_provider = Post.objects.all().filter(
        title='last_photo')[0].content
    return render(request, 'brocast.html',
                  {'last_message': last_message,
                   'last_photo': last_photo,
                   'last_photo_provider': last_photo_provider,
                   'current_time': str(datetime.now() + timedelta(hours=8))[0:-7]
                   })
