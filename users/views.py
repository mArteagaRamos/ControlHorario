from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login as auth_login
from .forms import FormRegister, LoginForm

def register(request):
    """
if not request.user.is_authenticated or not request.user.is_admin:
            messages.error(request, 'You do not have permission to access this page.')
            return redirect('register')
    """
    
    if request.method == 'POST':
        form = FormRegister(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'User registered successfully.')
            return redirect('login')
    else:
        form = FormRegister()
    return render(request, 'sign_up.html', {'form': form})

def login_view(request):
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            email = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=email, password=password)
            if user is not None:
                if user.is_admin:
                    auth_login(request, user)
                    messages.success(request, 'Logged in successfully as admin.')
                    return redirect('home')
                else:
                    messages.error(request, 'You do not have permission to access this page.')
            else:
                messages.error(request, 'Invalid email or password.')
        else:
            messages.error(request, 'Please check the form for errors.')
    else:
        form = LoginForm(request)
    return render(request, 'login.html', {'form': form})