# Virtual Envirnoment

## Create virtualenv using
It is better to create python virtual envirnoment, so that in future, the program/application can be executed without any external dependencies.
<pre>python -m venv django_venv</pre>

## Activate your virtualenv
To activate any virtual envirnonment below command can be used
<pre>source django_venv/Scripts/activate</pre>

After activating virtual envirnoment, we can install any python module inside it using pip
<pre>pip install django</pre>

using requirements.txt
<pre>pip install -r requirements.txt</pre>

## Deactivate your virtualenv
To deactivate any virtual envirnonment below command can be used
<pre>deactivate</pre>


# Django

## Django Project
In Django, Every thing is done under a project/directory which is managed by django itself. To create any django project below command is used
<pre>django-admin startproject first_project</pre>

<pre>
first_project/
    manage.py
    first_project/
        __init__.py
        settings.py
        urls.py
        asgi.py
        wsgi.py
</pre>
These files are:

- The outer first_project/ root directory is a container for your project. Its name doesn’t matter to Django. You can rename it to anything you like.
- manage.py
: A command-line utility that lets you interact with this Django project in various ways. You can read all the details about manage.py in django-admin and manage.py.
- The inner first_project/ directory is the actual Python package for your project. Its name is the Python package name you’ll need to use to import anything inside it (e.g. first_project.urls).
- first_project/__init__.py: An empty file that tells Python that this directory should be considered a Python package. If you’re a Python beginner, read more about packages in the official Python docs.
- first_project/settings.py: Settings/configuration for this Django project. Django settings will tell you all about how settings work.
- first_project/urls.py: The URL declarations for this Django project; a “table of contents” of your Django-powered site. You can read more about URLs in URL dispatcher.
- first_project/asgi.py: An entry-point for ASGI-compatible web servers to serve your project. See How to deploy with ASGI for more details.
- first_project/wsgi.py: An entry-point for WSGI-compatible web servers to serve your project. See How to deploy with WSGI for more detai

</pre>
As soon as our project is created, yo can verify your project and django in one go, using below commands
<pre>
cd first_project
python manage.py startserver
</pre>

**Copy url and goto your browser to verify its working or not**

## Django Apps

### Create Django App
Inside a django project, every subtask is added as an app. To create any app inside a django project use below commands
<pre>python manage.py startapp first_app</pre>
<pre>
first_app/
    __init__.py
    admin.py
    apps.py
    migrations/
        __init__.py
    models.py
    tests.py
    views.py
</pre>

### Register your Django App
Once any app is created, it must needs to be registerd with djgo project, to do that, Open first_project/settings.py and add your app name in INSTALLED_APPS


## Adding Views in your app
views.py basically defines the view/look of the djago. Let's create a hellow world html view for our app

Add below lines inside first_app/views.py
```python
from django.http import HttpResponse
def index(request=None):
    return HttpResponse('<h1>Hello World!!!</h1>')
```

Add below lines inside first_project/urls.py
```python
from first_app import views
# in urlpatterns add below lines
path('/',views.index,name='index'),
```
**Save and rerun your server to get your app output**

In a django project, there can be multiple apps, to mange there routing we can define a seperate urls.py for each app, and then we can include that urls.py in our main project.

Copy first_project/urls.py to first_app/urls.py and replace all content of urlpatterns with
```python
path('/',views.index,name='index')
```
Now, inside first_project/urls.py add below lines
```python
from django.urls import include
# in urlpatterns add below lines
path('first_app/',include("first_app.urls"))
```

**Save everything and rerun your server, copy url 127.0.0.1:8000/first_app/ to see the output**

## Django Templates
In views.py we can define functions for difeerent views, but  for bigger apps, we need big html output, and returning/manageing such complex html string though the functions of views.py, is very tidius. These large htmls strings can be handled using templets.

Templates are basically html files that can be retured by django view functions as a view.

In Django, youcan have templates at two levels
- Project Level Templates:
Template directory is created inside main djago project and it is shared by all other apps. This is helpfull, when you have very few apps, and size of your project is very small.
- App Level Templates:
Template directory is created separately for each application. This is helpfull, when you have multiple apps, and size of your project is very large.

### Project Level Templates
Create templates directory inside your django project, and create same structure inside templates directory as your django project and app structure is.
<pre>
first_project/
    templates/
        first_app/
            index.html
</pre>
        
Now add your code in new index.html.

Adding templates in settings.py

open first_project/first_project/settings.py, add below lines ,after BASE_DIR defination
</pre>
```python
import os
TEMPLATES_DIR = os.path.join(BASE_DIR,"templates")
# find TEMPLATE variable and add below value in DIR
TEMPLATES_DIR,
```

Now, open first_app/views.py and add below lines

```python
from django.shortcuts import render
# change defination of index function
def index(request=None):
    return render(request,'first_app/index.html')
```
**Save everything and rerun server to see your output**

### App Level Templates

**To be completed**


## Django Static files
Any web developement project have some more type of files other then html files, these other files are known as static files.
Like for html we have TEMPLATES, for other files such as images, css and javascript we have STATIC
We can have two levels of static files
- Project level Static Files
- App level Static files

### Project Level Static Files
Create below directory structure
<pre>
first_project/
    static/
        images/
        css/
        javascript/
</pre>

Now in first_project/first_project/settings.py, add below lines after the defination of TEMPLATES_DIR
</pre>
```python
STATIC_DIR = os.path.join(BASE_DIR,"static")
# scrolldown to STATIC_URL in settings.py
# add below lines
STATICFILES_DIR=[
    STATIC_DIR,
    ]
```

Now in index.html, add below lines after <!Doctype>

```html
{% load static %}
<!-- in head add below line -->
<link href="{% static 'css/mycss.css' %}" rel="stylesheet">
<!-- in body add below lines -->
<h3>Django Image</h3>
<img src="{% static 'images/DjangoFeaturedImage.jpeg' %}" alt="Image Not Found!!!" width="600px" height="400px"/>
```
**Save everything and rerun server to see output**

### App Level Static Files

**To be completed**


## Django Models
Almost every web application, works/manage on Data. These Data are stored in Databases, in the form of tables. 
- Handling of these type of data, is known as Backend.
- Handling of HTML and views is Frontend.

To communicate with data stored in databases, we use database languages, such as SQL, NO-SQL.

Complex queries are written and executed to manage data stored in the databases.

Django provides a functionality named **Model**, that can help us to avoid these extra complex querries, to handle such data.

Structure of table can be defined as a class, these classed inherit Model class of django. After **Migration**, all these models are converted into tables.

### Creating Models
Inside your app, there is a models.py, add below lines of code to models.py
```python
class Topic(models.Model):
    top_name=models.CharField(max_length=264,unique=True)
    
    def __str__(self):
        return self.top_name
```

The above class, after migrating will create below  **Topic table**

| top_name |
|----------|
| Topic-1  |
| Topic-2  |

In the same way, other tables can be created using Models

### Migrations
This basically saves/create our model for django

For migrations execute below commands
<pre>
python manage.py migrate
python manage.py makemigrations first_app
python manage.py migrate
</pre>

### Verify Migrations
Use python command line to check the migrations
```python
> python manage.py shell
>>> from first_app.models import Topic
>>> print(Topic.objects.all())
<QuerySet []>
>>> t=Topic(top_name="Social Network")
>>> t.save()
>>> print(Topic.objects.all())
<QuerySet [<Topic: Social Network>]>
>>> exit()
```

### Register Model
Newly created models, needs to be registered with django.

To register, newly created models, open first_app/admin.py and add below lines
```python
from first_app.models import Topic,Webpage,AccessRecord
admin.site.register(Topic)
```

### Superuser for admin
Execute below command to create superuser for django admin
<pre>python manage.py createsuperuser</pre>

Now login to admin portal i.e. http://127.0.0.1:8000/admin

### Populating Models
For testing purpose, we can creata a python script, to populate some data to our models

Steps to populate data to models
1. Install Faker Module
<pre>pip install Faker</pre>

2. Create Faker Script:
Create a python script first_project/populate_first_app.py and add below lines of code
```python
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
```

3. Execute populating Script
<pre>python populate_first_app.py</pre>

4. Verify the populated data:
Go to admin login and see the tables

## Django MVT
The MVT (Model View Template) is a software design pattern. It is a collection of three important components **Model View and Template**. 

- The Model helps to handle database. It is a data access layer which handles the data.
- The Template is a presentation layer which handles User Interface part completely.
- The View is used to execute the business logic and interact with a model to carry data and renders a template.

Although Django follows MVC pattern but maintains it's own conventions. So, control is handled by the framework itself.

There is no separate controller and complete application is based on Model, View and Template. That's why it is called MVT application.

Open first_app/views.py and add new function which retrives data from database, and send it as a context
```python
from first_app.models import Topic, Webpage, AccessRecord
def data_index(request=None):
    webpage_list=AccessRecord.objects.order_by('date')
    date_dict={'access_record':webpage_list}
    return render(request,'first_app/data_index.html',context=date_dict)
```

Create templates/first_app/data_index.html
```html
<h1>Below is data from database</h1>
<table style="border:1px solid black;">
    <tr style="border:1px solid black;">
        <th style="border:1px solid black;">Site Name</th>
        <th style="border:1px solid black;">Accessed Date</th>
    </tr>
    {% for acc in access_record %}
        <tr style="border:1px solid black;">
            <td style="border:1px solid black;">{{ acc.name }}</td>
            <td style="border:1px solid black;">{{ acc.date }}</td>
        </tr>
    {% endfor %}
</table>
```

Open first_app/urls.py and add new url for the data_index
```python
path('data/',views.data_index,name="data_index"),
```
Save and reload

## Django Forms
Django provides a Form class which is used to create HTML forms. It describes a form and how it works and appears.

Create first_app/forms.py and add below lines
```python
from django import forms
class FormName(forms.Form):
    name=forms.CharField()
    email=forms.EmailField()
    text=forms.CharField(widget=forms.Textarea)
```

Open views.py add new function and logic
```python
from . import forms
def form_name_view(request):
    form=forms.FormName()
    
    if request.method=='POST':
        form=forms.FormName(request.POST)
        
        if form.is_valid():
            print("Validation Success!!!")
            print("Name:  ",form.cleaned_data['name'])
            print("Email: ",form.cleaned_data['email'])
            print("Text:  ",form.cleaned_data['text'])
    return render(request,'first_app/basicform.html',context={'form':form})
```

create basicform.html and html code
```html
<!DOCTYPE html>
<html lang="en">
    <head>
        <title></title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet" integrity="sha384-1BmE4kWBq78iYhFldvKuhfTAU6auU8tT94WrHftjDbrCEXSU1oBoqyl2QvZ6jIW3" crossorigin="anonymous">
        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js" integrity="sha384-ka7Sk0Gln4gmtz2MlQnikT1wXgYsOg+OMhuP+IlRH9sENBO0LRn5q+8nbTov4+1p" crossorigin="anonymous"></script>
    </head>
    <body>
        <h1>Basic Form</h1>
        <div class="container">
            <form method="POST">
                {{ form.as_p }}
                {% csrf_token %}
                <input type="Submit" value="Submit"/>
            </form>
        </div>
    </body>
</html>
```
**csrf_toke** This is very important for django forms, it basically pprovides a unique identification to the form.

## Django Model Form
It is a class which is used to create an HTML form by using the Model. It is an efficient way to create a form without writing HTML code.

Django automatically does it for us to reduce the application development time. For example, suppose we have a model containing various fields, we don't need to repeat the fields in the form file.

For this reason, Django provides a helper class which allows us to create a Form class from a Django model.

In first_app/forms.py add below lines of code
```python
from first_app.models import User

class NewUserForm(forms.ModelForm):
    class Meta:
        model=User
        fields='__all__'
```

In first_app/urls.py add below paths
```python
path('signup/',views.signup_user,name="signup_user"),
```

In first_app/views.py add below lines of code
```python
from first_app.forms import NewUserForm


def signup_user(request):
    form=NewUserForm()

    if request.method=='POST':
        form=NewUserForm(request.POST) 
        if form.is_valid():
            form.save(commit=True)
            return index(request)
        else:
            print("Form Invalid!!!")

    return render(request,'first_app/signup.html',{'form':form}) 
```

In templates/first_app/signup.html add below lines of code
```html
<!DOCTYPE html>
<html lang="en">
    <head>
        <title></title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <link href="css/style.css" rel="stylesheet">
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet" integrity="sha384-1BmE4kWBq78iYhFldvKuhfTAU6auU8tT94WrHftjDbrCEXSU1oBoqyl2QvZ6jIW3" crossorigin="anonymous">
        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js" integrity="sha384-ka7Sk0Gln4gmtz2MlQnikT1wXgYsOg+OMhuP+IlRH9sENBO0LRn5q+8nbTov4+1p" crossorigin="anonymous"></script>
    </head>
    <body>
        <div class="container">
            <h2>Signup Here!!!</h2>
            <form method="POST">
                {{ form.as_p }}
                {% csrf_token %}
                <input type="submit" class="btn btn-primary" value="Submit"/>
            </form>
        </div>
    </body>
</html>
```

## Django Template Inheritance
We can inherit one html file in other, using django

Steps for template inheritance

1. Create base html file : templates/first_app/base_template.html
```html
<!DOCTYPE html>
{% load static %}
<html lang="en">
    <head>
        <link href="{% static 'css/mycss.css' %}" rel="stylesheet">
    </head>
    <body>
        <div class="container">
            <!--  Your Code -->
        </div>
        <div class="container">
            {% block body_block %}
            <!-- Everything Inside this will be replaced!!! -->
            {% endblock %}
        </div>

    </body>
</html>
```

2. Create child html files : templates/first_app/basicform.html
```html
<!DOCTYPE html>
{% extends 'first_app/base_template.html' %}
{% load static %}
{% block body_block %}
    <h1>Basic Form</h1>
    <div class="container">
        <form method="POST">
            {{ form.as_p }}
            {% csrf_token %}
            <input type="Submit" value="Submit"/>
        </form>
    </div>
{% endblock %}
```

## Django Template Filters
There are some filters provided by django
```html
<p>text in CAPITAL: {{ text|upper }}</p>
<p>number: {{ number }}</p>
<p>number+998: {{ number|add:"998" }}</p>
```

## Django Class-Based Views
Class-based views can be used in place of function-based views. All the operations handle using Python objects instead of functions. They provide some excellent example over the function-based views. Class-based views can implement CRUD operation in easy manner.

In first_app/views.py
```python
from django.views.generic import View 
from django.http import HttpResponse

class CBVHello(View):
    def get(self,request):
        return HttpResponse("Hello using Class Based View CBV")
```

In first_app/urls.py
```python
path('cbvhello/',views.CBVHello.as_view(),name="cbvhello"),
```

In templates/first_app/base_template.html
```html
<li class="nav-item">
    <a class="nav-link" href="{% url 'first_app:cbvhello' %}">CBVHello</a>
</li>
```

### Context Passing

In first_app/urls.py
```python
path('cbvhello/',views.CBVHello.as_view(),name="cbvhello"),
```

In first_app/views.py
```python
from django.views.generic import TemplateView

class CBTVIndex(TemplateView):
    template_name='first_app/Tindex.html'

    def get_context_data(self,**kwargs):
        context=super().get_context_data(**kwargs)
        context['yourname']='Jay Prakash Sonkar'
        return context
```

In templates/first_app/Tindex.html
```html
<!DOCTYPE html>
{% extends 'first_app/base_template.html' %}
{% load static %}
{% load my_extras %}
    {% block body_block %}
        <h3>Hello I am using Class Based Template View (CBTV) to print your name</h3>
        <h1>{{ yourname }}</h1>
    {% endblock %}
```

### Class Based List View

In first_app/models.py
```python
class School(models.Model):
    name=models.CharField(max_length=256)
    principal=models.CharField(max_length=256)
    location=models.CharField(max_length=256)

    def __str__(self):
        return self.name


class Student(models.Model):
    name=models.CharField(max_length=256)
    age=models.PositiveIntegerField()
    school=models.ForeignKey(School,related_name='students',on_delete=models.CASCADE)

    def __str__(self):
        return self.name
```

In first_app/templates/first_app/school_list.html
```html
{% extends 'first_app/first_app_base.html' %}

{% block body_block %}
<h1>List Of schools</h1>
<ol>
    {% for school in schools %}
    <li><h2><a href="{{school.id}}">{{school.name}}</a></h2></li>
    {% endfor %}
</ol>
{% endblock %}
```

In first_app/views.py
```python
from django.views.generic import ListView

class SchoolListView(ListView):
    model=School
    context_object_name ='schools' # default value is lower(model)+"_list"
```


### Class Based Detail View


In first_app/models.py
```python
class School(models.Model):
    name=models.CharField(max_length=256)
    principal=models.CharField(max_length=256)
    location=models.CharField(max_length=256)

    def __str__(self):
        return self.name


class Student(models.Model):
    name=models.CharField(max_length=256)
    age=models.PositiveIntegerField()
    school=models.ForeignKey(School,related_name='students',on_delete=models.CASCADE)

    def __str__(self):
        return self.name
```

In first_app/templates/first_app/school_detail.html
```html
{% extends 'first_app/first_app_base.html' %}

{% block body_block %}
<h1>Details Of schools</h1>
<p>Name: {{school_detail.name }}</p>
<p>Prinicipal: {{school_detail.principal }}</p>
<p>Location: {{school_detail.location }}</p>
<p>Students: </p>
<ol>
    {% for student in school_detail.students.all %}
        <li> {{student.name}} who is {{student.age}} years old</li>
    {%endfor%}
</ol>


{% endblock %}
```

In first_app/views.py
```python
from django.views.generic import DetailView

class SchoolDetailView(DetailView):
    model=School
    context_object_name ='school_detail' # default value is lower(model)"
    template_name='first_app/school_detail.html'
```

### CreateView, UpdateView, DeleteView
In first_app/views.py
```python
from django.views.generic import (CreateView,UpdateView,DeleteView)
from django.urls import reverse_lazy

class SchoolCreateView(CreateView):
    # Using ModelFormMixin (base class of SchoolCreateView) without the 'fields' attribute is prohibited.
    # add below line to avoid above errors
    fields=('name','principal','location') # to avoid field error
    model=School

class SchoolUpdateView(UpdateView):
    # Using ModelFormMixin (base class of SchoolCreateView) without the 'fields' attribute is prohibited.
    # add below line to avoid above errors
    fields=('name','principal') # to avoid field error
    model=School

class SchoolDeleteView(DeleteView):
    model=School
    success_url=reverse_lazy("first_app:list")
```

In first_app/templates/first_app/school_form.html
```html
{% extends 'first_app/first_app_base.html' %}
{% block body_block %}
<h1>
    {% if not form.instance.pk %}
    Create School 
    {% else %} 
    Update School 
    {% endif %}
</h1>
<form method="post">
    {% csrf_token %}
    {{ form.as_p }}
    <input type="submit" class="btn btn-info" value="submit"/>
</form>


{% endblock %}
```

In first_app/urls.py
```python
path('create/',views.SchoolCreateView.as_view(),name="create"),
path('update/<int:pk>/',views.SchoolUpdateView.as_view(),name="update"),
path('delete/<int:pk>/',views.SchoolDeleteView.as_view(),name="delete"),
```
