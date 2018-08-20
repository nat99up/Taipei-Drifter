from django.contrib import admin

# Register your models here.
from .models import Post , PersonalInfo

admin.site.register(Post)
admin.site.register(PersonalInfo)