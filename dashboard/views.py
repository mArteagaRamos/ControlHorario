from django.shortcuts import render
from django.contrib.auth.decorators import login_required

@login_required
def home(request):
    return render(request, 'dashboard/home.html')


def control(request):
    return render(request, 'dashboard/control.html')

def calendar(request):
    return render(request, 'user_panel/calendar.html')

def profile(request):
    return render(request, 'user_panel/profile.html')

def absence(request):
    return render(request, 'user_panel/absence.html')

def request_correction(request):
    return render(request, 'user_panel/requests.html')   

def entity_info(request):
    return render(request, 'team/entity_info.html')

def staff(request):
    return render(request, 'team/staff.html')

def notes(request):
    return render(request, 'team/notes.html')