from django.contrib import messages
from django.shortcuts import render, redirect
from inprogress.models import Setup
import json

#------------------------------------------------------------------
#        HOLIDAYS 
#------------------------------------------------------------------

"""
METHOD CALLED WHEN ADMIN CLICKS "HOLIDAYS" LINK. 
RETURNS PARTS LIST
"""
#---------------------------------------------------
#TODO: MAKE APPROPRIATE CHANGES IN THE METHOD BODY AND CREATE PAGE FOR 
#---------------------------------------------------
# YOU WILL HAVE TO CHANGE THE REFERENCES AND FIELDS SUITABLE FOR HOLIDAY AS DATE FROM SETUP 
# DO NOT CHANGE OVERALL STRUCTURE. 
# DO NOT CHANGE METHOD NAMES
# THIS PAGE IS COPY-PASTED FROM STEUPS AS FUNCTIONALITY IS VERY 
# YOu CAN REFER TO SETUP FUNCTIONALITY FOR REFERENCE
# REFER TO IMAGE FOR "HOW THE FINAL PAGE SHOULD LOOK LIKE"
#---------------------------------------------------

def holidays(request):
    # TODO: YOU NEED TO REPLACE THIS LOGIC SUITABLE FOR HOLIDAY ----
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
    # TODO: REPLACE THIS TEMP CALL BY SUITABLE FOR HOLIDAYS
    # REFERE THE COMMENTED ONE FOR CHANGES
    # -------------------------------------- 
    return render(request, 'holiday/holidays.html')
    # return render(request, 'holiday/holidays.html', 
    #                         {'setups': setupQuerySet, 
    #                         'setupsListJson': setupsListJson,
    #                         })


def processHoliday(request):
    mode = request.POST['functionMode']
    returnPage = 'holidays'
    if mode == "CANCEL":
        return redirect(returnPage)

    if mode == 'ADD':
        return render(request, 'holiday/addHoliday.html')

    elif mode == 'EDIT':
        setup = Setup.objects.get(id_code = request.POST['selectedSetup'])
        return render(request, 'holiday/editHoliday.html', {'selectedSetup': setup})

    elif mode == 'DELETE':
        deleteHoliday(request)

    elif mode == "ADDED":
        addNewHoliday(request)

    elif mode == "EDITED":
        updateHolidayDetails(request)     

    return redirect(returnPage)

def updateHolidayDetails(request):
    setup_code = request.POST['scode']
    setup_name = request.POST['sname']
    setup_desc = request.POST['sdesc']
    setup = Setup.objects.get(id_code = setup_code)
    setup.name = setup_name
    setup.desc = setup_desc
    # TODO: UNCOMMENT THIS WHEN YOU MAKE ALL CHANGES, ELSE THIS WILL SAVE IN TO SETUP TABLES
    # setup.save()  
    return redirect('holidays')

def addNewHoliday(request):
    setup_code = request.POST['scode']
    setup_name = request.POST['sname']
    setup_desc = request.POST['sdesc']

    if Setup.objects.filter(id_code = setup_code).exists():
        messages.info(request, 'Setup code already exists')
        return redirect('holidays')
    else:
        try:
            setup = Setup.objects.create(id_code = setup_code, 
                                        name = setup_name, 
                                        desc = setup_desc)
            # TODO: UNCOMMENT THIS WHEN YOU MAKE ALL CHANGES, ELSE THIS WILL SAVE IN TO SETUP TABLES
            # setup.save()
                
        except Exception as e:
            print ('--Exception while creating Setup ---', e)
    return redirect('holidays')

def editHoliday(request):
    return render(request, 'setup/editSetup.html')

def deleteHoliday(request):
    setup = Setup.objects.get(id_code = request.POST['selectedSetup'])

    if setup is not None:
        setup.is_active = False
        setup.save()
    return redirect('holidays')
