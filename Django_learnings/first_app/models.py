from django.db import models
from django.contrib.auth.models import User as DUser
from django.urls import reverse

# Create your models here.
class Topic(models.Model):
    top_name=models.CharField(max_length=264,unique=True)
    
    def __str__(self):
        return self.top_name

class Webpage(models.Model):
    topic=models.ForeignKey(Topic,on_delete=models.CASCADE)
    name=models.CharField(max_length=264,unique=True)
    url=models.URLField(unique=True)
    
    def __str__(self):
        return self.name 
    
class AccessRecord(models.Model):
    name=models.ForeignKey(Webpage,on_delete=models.CASCADE)
    date=models.DateField()
    
    def __str__(self):
        return str(self.date)
    
class User(models.Model):
    fname=models.CharField(max_length=50)
    lname=models.CharField(max_length=50)
    email=models.CharField(max_length=50)
    
    def __str__(self):
        return self.fname+" "+self.lname
    
    
class UserProfileInfo(models.Model):
    user= models.OneToOneField(DUser,on_delete=models.CASCADE)
    
    # additional
    portfolio_site=models.URLField(blank=True)
    
    profile_pic = models.ImageField(upload_to='profile_pics',blank=True)
    
    def __str__(self):
        return self.user.username
    
class School(models.Model):
    name=models.CharField(max_length=256)
    principal=models.CharField(max_length=256)
    location=models.CharField(max_length=256)
    
    def __str__(self):
        return self.name
    
    # No URL to redirect to.  Either provide a url or define a get_absolute_url method on the Model.
    # to avoid add below function 
    def get_absolute_url(self):
        return reverse("first_app:detail",kwargs={'pk':self.pk})
    
    
class Student(models.Model):
    name=models.CharField(max_length=256)
    age=models.PositiveIntegerField()
    school=models.ForeignKey(School,related_name='students',on_delete=models.CASCADE)
    
    def __str__(self):
        return self.name
    
