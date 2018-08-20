from django.db import models

# Create your models here#


class Post(models.Model):
	title = models.CharField(max_length = 100)
	content = models.TextField(blank = True)
	photo = models.URLField(blank = True)
	location = models.CharField(max_length = 100)
	creat_at = models.DateTimeField(auto_now_add = True)


	def __str__(self):
		return self.title

class PersonalInfo(models.Model):

	user_name = models.CharField(max_length = 30)
	user_id = models.TextField(blank = True)

	img_url_set = models.TextField(blank = True)  # URL_1::URL_2
	img_url_date = models.TextField(blank = True) # YYYY/MM/DD::YYYY/MM/DD
	img_url_num = models.IntegerField(default = 0)


	def __str__(self):
		return self.user_name