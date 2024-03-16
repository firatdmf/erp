from django.shortcuts import render, redirect
from django.http import HttpResponse

# Create your views here.
from django.contrib.auth.models import User
from .models import Member
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages

from django.contrib.auth.decorators import login_required


# @login_required
def home(request):
    # try:
    #     member = Member.objects.get(user=request.user)
    # except Member.DoesNotExist:
    #     # Handle the case where the Member object does not exist for the logged-in user
    #     member = None

    # return render(request, 'authentication/home.html', {'member': member})
    # return render(request, "authentication/index.html")
    if request.user:
        print("There is user!")
        try:
            member = Member.objects.get(user=request.user)
        except:
            member = None
        return render(request, "authentication/index.html", {'member':member})
    else:
        print("There is no user!")

        return render(request, "authentication/index.html")


def signup(request):
    if request.method == "POST":
        print('hello')
        # this is based on name, not id
        # username = request.POST.get('username')
        # below is same as above
        username = request.POST["username"]
        fname = request.POST["fname"]
        lname = request.POST["lname"]
        email = request.POST["email"]
        password = request.POST["password"]
        cname = request.POST["cname"]

        myuser = User.objects.create_user(username, email, password)
        myuser.first_name = fname
        myuser.last_name = lname
        print(myuser)
        myuser.save()
        mymember = Member.objects.create(user=myuser, company_name=cname)
        mymember.save()

        messages.success(request, "Your acccount has been successfully created.")
        return redirect("signin")

    return render(request, "authentication/signup.html")


def signin(request):
    # go_to_url = request.GET['next']
    # print(go_to_url)
    if request.method == "GET":
        go_to_url = request.GET.get('next','home')
        return render(request,"authentication/signin.html",{"next":go_to_url})

        # print('-------')
        # print(type(str(go_to_url)))
        # print(go_to_url)
        # print('-------')
    # def change():
    #     go_to_url = request.GET['next']
    if request.method == "POST":
        username = request.POST["username"]
        password = request.POST["password"]
        go_to_url = request.POST["next"]
        print('-------')
        print(type(str(go_to_url)))
        print(go_to_url)
        print('-------')
        user = authenticate(username=username, password=password)
        if user is not None:
            login(request, user)
            fname = user.first_name
            lname = user.last_name
            # return render(
            #     request,
            #     "authentication/index.html",
            #     {
            #         "fname": fname,
            #     },
            # )
            # print(go_to_url)
            # below takes it back to where they started in the url
            # return redirect(go_to_url)
            return redirect("/authentication/home")
        else:
            messages.error(request, "Bad Credentials!")
            # this is the name of the url
            return redirect("/authentication/home")
            

    return render(request, "authentication/signin.html")


def signout(request):
    logout(request)
    messages.success(request, "Logged out successfully")
    return redirect("index")
