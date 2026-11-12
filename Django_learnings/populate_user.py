import os 
os.environ.setdefault('DJANGO_SETTINGS_MODULE','first_project.settings')

import django 
django.setup() 

import random 
from first_app.models import User
from faker import Faker 

fakegen=Faker() 
topics=['Search',"Social","Marketplace","News","Games"]


def populate(N=5):
    for enrty in range(N):
        fake_fname=fakegen.first_name()
        fake_lname=fakegen.last_name()
        fake_email=fakegen.email()
        
        u=User.objects.get_or_create(fname=fake_fname,lname=fake_lname,email=fake_email)[0]
        
        u.save()

if __name__ == '__main__':
    print("populating Script!")
    populate(20)
    print("populating complete!!")