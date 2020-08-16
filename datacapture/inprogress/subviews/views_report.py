from django.contrib import messages
from django.shortcuts import render, redirect
from inprogress.models import Setup
import json

#------------------------------------------------------------------
#        REPORTS 
#------------------------------------------------------------------

"""
METHOD CALLED WHEN ADMIN CLICKS "SETUPS" LINK. 
RETURNS PARTS LIST
"""
def reports(request):
    #--- UPDATED METHOD ----
    setupQuerySet = Setup.objects.filter(is_active = True)
    setupsList = {}
    for setup in setupQuerySet:
        st = {
            "id_code": setup.id_code,
            "name": setup.name,
            "desc": setup.desc
        }
        setupsList[st['id_code']] =  st
    setupsListJson = json.dumps(setupsList)
    return render(request, 'report/reports.html')
    # return render(request, 'setup/setups.html', 
    #                         {'setups': setupQuerySet, 
    #                         'setupsListJson': setupsListJson,
    #                         })

def generateReport(request):
    criteria = request.POST['selectedCriteria']
    print ('\n ----- GENERATING REPORT ----- \n', criteria)
    return redirect('reports')
