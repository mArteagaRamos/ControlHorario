from django.shortcuts import render
from django.contrib.auth.decorators import login_required

@login_required
def home(request):
    return render(request, 'dashboard/home.html')

@login_required
def control(request):
    return render(request, 'dashboard/control.html')

@login_required
def calendar(request):
    return render(request, 'user_panel/calendar.html')

@login_required
def profile(request):
    return render(request, 'user_panel/profile.html')

@login_required
def absence(request):
    return render(request, 'user_panel/absence.html')

@login_required
def request_correction(request):
    return render(request, 'user_panel/requests.html')   

@login_required
def entity_info(request):
    return render(request, 'team/entity_info.html')

@login_required
def staff(request):
    return render(request, 'team/staff.html')

@login_required
def notes(request):
    return render(request, 'team/notes.html')