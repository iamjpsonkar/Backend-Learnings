from django.shortcuts import render
from django.http import HttpResponse
from first_app.models import Topic, Webpage, AccessRecord, User , School , Student
from . import forms
from first_app.forms import NewUserForm, UserForm, UserProfileInfoForm

from django.views.generic import View 
from django.http import HttpResponse
from django.views.generic import TemplateView
from django.views.generic import ListView
from django.views.generic import DetailView
from django.views.generic import (CreateView,UpdateView,
                                  DeleteView)
from django.urls import reverse_lazy

class CBVHello(View):
    def get(self,request):
        return HttpResponse("Hello using Class Based View CBV")
    
class CBTVIndex(TemplateView):
    template_name='first_app/Tindex.html'
    
    def get_context_data(self,**kwargs):
        context=super().get_context_data(**kwargs)
        context['yourname']='Jay Prakash Sonkar'
        return context
    
class SchoolListView(ListView):
    model=School
    context_object_name ='schools' # default value is lower(model)+"_list"
    
class SchoolDetailView(DetailView):
    model=School
    context_object_name ='school_detail' # default value is lower(model)"
    template_name='first_app/school_detail.html'
    
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
    



# Create your views here.
def index(request=None):
    my_dict={'myname':'Jay Prakash Sonkar','text':"I am Text.",'number':1000}
    return render(request,'first_app/index.html',context=my_dict)

def data_index(request=None):
    webpage_list=AccessRecord.objects.order_by('date')
    date_dict={'access_record':webpage_list}
    return render(request,'first_app/data_index.html',context=date_dict)
    
def user_index(request=None):
    user_list=User.objects.values()
    user_dict={
        'user_data':user_list
    }
    return render(request,'first_app/user_index.html',context=user_dict)

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

def relative_url(request):
    return render(request,'first_app/relative_url.html')

def other_page(request):
    return render(request,'first_app/otherpage.html')

def register(request):
    registered=False
    
    if request.method=='POST':
        user_form= forms.UserForm(data=request.POST)
        profile_form = forms.UserProfileInfoForm(data=request.POST)
        
        if user_form.is_valid() and profile_form.is_valid():
            user=user_form.save()
            user.set_password(user.password)
            user.save()
            
            profile=profile_form.save(commit=False)
            profile.user=user
            
            if 'profile_pic' in request.FILES:
                profile.profile_pic=request.FILES['profile_pic']
                
            profile.save()
            
            registered=True
        else:
            print(user_form.errors)
            print(profile_form.errors)
    else:
        user_form=UserForm()
        profile_form=UserProfileInfoForm()
        
    return render(request,'first_app/registration.html',context={
        'user_form':user_form,
        'profile_form':profile_form,
        'registered':registered
    })
            