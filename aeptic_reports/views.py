from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import MonthlyReport
from django.db.models import Q


@login_required
def report_history(request):

    query = request.GET.get('q')
    

    reports = MonthlyReport.objects.filter(user_id=request.user.id).order_by('-report_date')
    
    # Aplicar buscador si existe (busca por mes o año en la fecha)
    if query:
        reports = reports.filter(
            Q(report_date__icontains=query) | 
            Q(status__icontains=query)
        )
    
    return render(request, 'aeptic/report_history.html', {
        'reports': reports,
        'query': query
    })

@login_required
def report_summary(request):

    return render(request, 'aeptic/report_summary.html')