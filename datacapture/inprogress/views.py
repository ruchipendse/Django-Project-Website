from django.shortcuts import render
from django.contrib.auth.models import User, auth
from django.contrib import messages
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import Machine, Part, PartSetupSequence, Setup, Employee
import json
from django.db import transaction
from inprogress.subviews.views_machine import machines, processMachine, addNewMachine, updateMachineDetails,  deleteMachine

from inprogress.subviews.views_setup import setups, processSetup
from inprogress.subviews.views_holiday import holidays, processHoliday
from inprogress.subviews.views_report import reports, report_download
from inprogress.subviews.views_nonprodtask import nonprodtasks, processNonProdTask
from inprogress.subviews.views_part import parts, addNewPart, deletePart, processPart
from inprogress.subviews.views_timesheet import gototimesheet, gototimesheet_init, timesheet_entries, processRequest, timesheetLogout
from inprogress.subviews.views_user import users, updateUserDetails, addNewUser, deleteUser
from inprogress.subviews.views_batchprocess import prepopulate
# from inprogress.subviews.views_batchprocess import commit_timesheets_all_daterange
from inprogress.models import (
     EmployeeDate, 
     EmployeeDateTimeSlot, 
     TimeSheetEntryProd, 
     TimeSheetEntryNonProd, 
     NonProdTask,
     OperatorSetup,
     MachineSetup,
     Holiday
     )

# Create your views here.

def init_start(request):
    currentSession = request.session
    currentSession.set_expiry(0)
    if (request.user):
        auth.logout(request)
    return redirect("home")

def home(request):
    prepopulate(request)
    # commit_timesheets_all_daterange(request)
    return render(request, 'home.html')

def timesheet_base(request):
    return render(request, 'timesheet/timesheet_base.html')

def manageResources(request, restype):
    print ('Resource Type: ' + restype)
    handler_page = 'manage' + restype + '.html' 
    return render(request, handler_page)

def adminLogin(request):
    if (request.method == 'POST'):
        uName = request.POST['username']
        pWord = request.POST['password']
        user = auth.authenticate(username = uName, password = pWord)
        if user is not None:
            if (user.is_staff):
                auth.login(request, user)
                return  redirect ('home')
            else:
                messages.info(request, 'Invalid admin User - User is not staff')
                return redirect ('home')
        else:
            messages.info(request, 'Invalid admin User')
            return redirect ('home')
    else:
        print ('Something wrong: POST method NOT called')
        return render(request, 'home.html')

def adminLogout(request):
    auth.logout(request)
    print ('----- LOGGED OUT -----')
    return render(request, 'home.html')

def resetdatabase(request):
    # THIS DISABLING SHOULD NEVER BE REMOVED UNLESS THERE IS NEED TO RESET THE DATABASE. 
    # ELSE WE WILL LOSE ALL THE DATA
    DELETE_TRANSACTIONS                 = False
    DELETE_ENTITIES                     = False
    if (DELETE_TRANSACTIONS):
        deleteTransactions()
        if (DELETE_ENTITIES):
            deleteEntities()
    return render(request, 'home.html')

def deleteTransactions():
    deleteNonprodEntries()
    deleteProdEntries()
    deleteEmployeeDateTimeSlots()
    deleteEmployeeDates()

def deleteEntities():
    deletePartSetupSequences()
    deleteParts()
    deleteMachineSetups()
    deleteMachines()
    deleteOperatorSetups()
    deleteNonProdTasks()
    deleteHolidays()
    deleteSetups()

def deleteProdEntries():
    try:
        with transaction.atomic():
            tentries = TimeSheetEntryProd.objects.all()
            for tentry in tentries:
                tentry.delete()
    except Exception as e:
        log_message = 'Delete Non Production Time entry update Failed:' + str(e)
        print (log_message)

def deleteNonprodEntries():
    try:
        with transaction.atomic():
            tentries = TimeSheetEntryNonProd.objects.all()
            for tentry in tentries:
                tentry.delete()
    except Exception as e:
        log_message = 'Delete Non Production Time entry update Failed:' + str(e)
        print (log_message)

def deleteEmployeeDateTimeSlots():
    try:
        with transaction.atomic():
            tentries = EmployeeDateTimeSlot.objects.all()
            for tentry in tentries:
                tentry.delete()
    except Exception as e:
        log_message = 'Delete EmployeeDateTimeSlot update Failed:' + str(e)
        print (log_message)

def deleteEmployeeDates():
    try:
        with transaction.atomic():
            tentries = EmployeeDate.objects.all()
            for tentry in tentries:
                tentry.delete()
    except Exception as e:
        log_message = 'Delete Non EmployeeDate entry Failed:' + str(e)
        print (log_message)

def deletePartSetupSequences():
    try:
        with transaction.atomic():
            tentries = PartSetupSequence.objects.all()
            for tentry in tentries:
                tentry.delete()
    except Exception as e:
        log_message = 'Delete PartSetupSequence Failed:' + str(e)
        print (log_message)

def deleteParts():
    try:
        with transaction.atomic():
            tentries = Part.objects.all()
            for tentry in tentries:
                tentry.delete()
    except Exception as e:
        log_message = 'Delete Part Failed:' + str(e)
        print (log_message)

def deleteMachineSetups():
    try:
        with transaction.atomic():
            tentries = MachineSetup.objects.all()
            for tentry in tentries:
                tentry.delete()
    except Exception as e:
        log_message = 'Delete Part Failed:' + str(e)
        print (log_message)

def deleteMachines():
    try:
        with transaction.atomic():
            tentries = Machine.objects.all()
            for tentry in tentries:
                tentry.delete()
    except Exception as e:
        log_message = 'Delete Part Failed:' + str(e)
        print (log_message)

def deleteOperatorSetups():
    try:
        with transaction.atomic():
            tentries = OperatorSetup.objects.all()
            for tentry in tentries:
                tentry.delete()
    except Exception as e:
        log_message = 'Delete OperatorSetup Failed:' + str(e)
        print (log_message)

def deleteNonProdTasks():
    try:
        with transaction.atomic():
            tentries = NonProdTask.objects.all()
            for tentry in tentries:
                tentry.delete()
    except Exception as e:
        log_message = 'Delete NonProdTask Failed:' + str(e)
        print (log_message)

def deleteHolidays():
    try:
        with transaction.atomic():
            tentries = Holiday.objects.all()
            for tentry in tentries:
                tentry.delete()
    except Exception as e:
        log_message = 'Delete NonProdTask Failed:' + str(e)
        print (log_message)

def deleteSetups():
    try:
        with transaction.atomic():
            tentries = Setup.objects.all()
            for tentry in tentries:
                tentry.delete()
    except Exception as e:
        log_message = 'Delete Setup Failed:' + str(e)
        print (log_message)

def index(request):
    return render(request, 'xtra_index.html')

def myaction(request, op_mode = None, id = -1):
    print ('MODE AND ID ARE: ', op_mode, id)
