from django.shortcuts import render
from django.contrib.auth.models import User, auth
from django.contrib import messages
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import Machine, Part, PartSetupSequence, Setup, Employee
import json

from inprogress.subviews.views_machine import machines, processMachine, addNewMachine, updateMachineDetails,  deleteMachine

from inprogress.subviews.views_setup import setups, processSetup
from inprogress.subviews.views_nonprodtask import nonprodtasks, processNonProdTask
from inprogress.subviews.views_part import parts, addNewPart, deletePart, processPart
from inprogress.subviews.views_timesheet import gototimesheet, gototimesheet_init, timesheet_entries, processRequest, timesheetLogout
from inprogress.subviews.views_user import users, updateUserDetails, addNewUser, deleteUser

# Create your views here.

def init_start(request):
    currentSession = request.session
    currentSession.set_expiry(0)
    if (request.user):
        auth.logout(request)
    return redirect("home")

def home(request):
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

def index(request):
    return render(request, 'xtra_index.html')

def myaction(request, op_mode = None, id = -1):
    print ('MODE AND ID ARE: ', op_mode, id)
