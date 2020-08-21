from django.contrib import messages
from django.shortcuts import render, redirect
from inprogress.models import Setup
from inprogress.models import Holiday
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
    # TO DO: YOU NEED TO REPLACE THIS LOGIC SUITABLE FOR HOLIDAY ----
    holidayQuerySet = Holiday.objects.filter(is_active = True)
    holidaysList = {}
    for holiday in holidayQuerySet:
        st = {
            "id_code": holiday.id_code,
            "desc": holiday.name, #changed name to desc for holiday
            "date": holiday.desc  #changed desc to date for holiday
        }
        holidaysList[st['id_code']] =  st
    holidaysListJson = json.dumps(holidaysList)
    # TO DO: REPLACE THIS TEMP CALL BY SUITABLE FOR HOLIDAYS
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
        holiday = Holiday.objects.get(id_code = request.POST['selectedHoliday'])
        return render(request, 'holiday/editHoliday.html', {'selectedHoliday': holiday})

    elif mode == 'DELETE':
        deleteHoliday(request)

    elif mode == "ADDED":
        addNewHoliday(request)

    elif mode == "EDITED":
        updateHolidayDetails(request)     

    return redirect(returnPage)

def updateHolidayDetails(request):
    holiday_code = request.POST['hcode']
    holiday_desc = request.POST['hdesc']
    holiday_date = request.POST['hdate']
    holiday = Holiday.objects.get(id_code = holiday_code)
    holiday.name = holiday_name
    holiday.desc = holiday_desc
    # TO DO: UNCOMMENT THIS WHEN YOU MAKE ALL CHANGES, ELSE THIS WILL SAVE IN TO SETUP TABLES
    holiday.save()   #was setup.save() before
    return redirect('holidays')

def addNewHoliday(request):
    holiday_code = request.POST['hcode']
    holiday_desc = request.POST['hdesc']
    holiday_date = request.POST['hdate']

    if Holiday.objects.filter(id_code = holiday_code).exists():
        messages.info(request, 'Setup code already exists')
        return redirect('holidays')
    else:
        try:
            holiday = Holiday.objects.create(id_code = holiday_code, 
                                        desc = holiday_desc, 
                                        date = setup_date)
            # TO DO: UNCOMMENT THIS WHEN YOU MAKE ALL CHANGES, ELSE THIS WILL SAVE IN TO SETUP TABLES
            holiday.save() #was setup.save()
                
        except Exception as e:
            print ('--Exception while creating Setup ---', e)
    return redirect('holidays')

def editHoliday(request):
    return render(request, 'setup/editHoliday.html')

def deleteHoliday(request):
    holiday = Holiday.objects.get(id_code = request.POST['selectedHoliday'])

    if holiday is not None:
        holiday.is_active = False
        holiday.save()
    return redirect('holidays')
