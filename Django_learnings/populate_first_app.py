import os 
os.environ.setdefault('DJANGO_SETTINGS_MODULE','first_project.settings')

import django 
django.setup() 

import random 
from first_app.models import Topic,Webpage,AccessRecord
from faker import Faker 

fakegen=Faker() 
topics=['Search',"Social","Marketplace","News","Games"]

def add_topic():
    t=Topic.objects.get_or_create(top_name=random.choice(topics))[0]
    t.save()
    return t 

def populate(N=5):
    for enrty in range(N):
        top=add_topic()
        
        fake_url=fakegen.url()
        fake_date=fakegen.date()
        fake_name=fakegen.name()
        
        web_pg=Webpage.objects.get_or_create(topic=top,url=fake_url,name=fake_name)[0]
        
        acc_rcd=AccessRecord.objects.get_or_create(name=web_pg,date=fake_date)[0] 

if __name__ == '__main__':
    print("populating Script!")
    populate(20)
    print("populating complete!!")