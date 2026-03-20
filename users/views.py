# ---------- Backend Views: users/views.py ----------

from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login as auth_login
from .forms import FormRegister, LoginForm

# Authentication / registration views

def register(request):

    """
    if not request.user.is_authenticated or not request.user.is_admin:
                messages.error(request, 'You do not have permission to access this page.')
                return redirect('register')
        """

    """Handle user registration via sign-up form."""

    # If request is POST, process submitted registration form data
    if request.method == 'POST':
        form = FormRegister(request.POST)
        if form.is_valid():
            # Save user record to database
            form.save()
            messages.success(request, 'User registered successfully.')
            return redirect('login')
        else:
            messages.error(request, 'Please correct the highlighted fields and try again.')
    else:
        # GET request: display an empty registration form
        form = FormRegister()
    return render(request, 'login/sign_up.html', {'form': form})


# User login section

def login_view(request):
    """Authenticate user credentials and log in admin users."""

    if request.method == 'POST':
        # Bind submitted credentials to authentication form
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            # Extract cleaned data from the form
            email = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')

            # Authenticate against Django auth backend
            user = authenticate(request, username=email, password=password)
            if user is not None:
                # Only allow admin users to log in here
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
        # GET request: show login form
        form = LoginForm(request)
    return render(request, 'login/login.html', {'form': form})


# User panel section

def user_panel(request):
    return render(request, 'user_panel/user_panel.html')