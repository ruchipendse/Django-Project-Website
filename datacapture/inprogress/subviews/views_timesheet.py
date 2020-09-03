from django.contrib.auth.models import User, auth
from django.contrib import messages
from django.shortcuts import render, redirect
from django.db import transaction

from datetime import datetime, timedelta, date
import numpy as np
import json
import time
import logging

from inprogress.loggerConfig import configure_logger
from inprogress.models import (
    Part,
    PartSetupSequence,
    Setup,
    Machine,
    TimeSheetEntryProd,
    TimeSheetEntryNonProd,
    EmployeeDateTimeSlot,
    Employee,
    EmployeeDate,
    NonProdTask,
)

configure_logger()
logger = logging.getLogger(__name__)

# TODO: GENERATE THE REPORTS PAGE.

"""
ARRIVES HERE FROM ROOT URL. NAVIGATES TO LOGIN PAGE 
"""

def gototimesheet_init(request):
    currentSession = request.session
    currentSession.set_expiry(0)
    if (request.user):
        auth.logout(request)
    return redirect("gototimesheet")

def gototimesheet(request):
    
    activeUsersListJson = None
    if request.method == "POST":
        pass
    else:
        activeUsers = User.objects.filter(is_active=True)
        users = {}
        for user in activeUsers:
            userObj = {
                "username": user.username,
                "first_name": user.first_name,
                "last_name": user.last_name,
            }
            users[user.username] = userObj
        activeUsersListJson = json.dumps(users)
    return render(
        request,
        "timesheet/timesheet_login.html",
        {"activeUsersListJson": activeUsersListJson, "activeUsers": activeUsers},
    )

"""
    ARRIVES FROM TIME SHEET LOGIN PAGE. NAVIGATES TO timsheet_entries.html 
    for displaying entries list
"""
def timesheet_entries(request, currentDate=datetime.today().strftime("%Y-%m-%d")):
    user = None
    if request.method == "POST":
        # NO ONE HAS LOGGED IN YET
        uName = request.POST["username"]
        pWord = request.POST["password"]
        user = auth.authenticate(username=uName, password=pWord)
        if user is not None:
            print("USER AUTHENTICATED")
            auth.login(request, user)
        else:
            print("USER NOT AUTHENTICATED")
            messages.info(request, "Invalid User")
            return redirect("gototimesheet")
    else:
        # USER IS ALREADY LOGGED IN
        user = request.user
        if user is None:
            messages.info(request, "Invalid User")
            return redirect("gototimesheet")

    # FETCH N DAYS RECORD HISTORY TILL TODAY
    date_highbound = datetime.today()  # FROM

    NUMBER_OF_PREV_DAYS = 30
    date_lowbound = date_highbound - timedelta(days=NUMBER_OF_PREV_DAYS)  # TO
    employeeDateStatus = EmployeeDate.objects.filter(user_id=request.user.id).filter(
        date__range=[
            date_lowbound.strftime("%Y-%m-%d"),
            date_highbound.strftime("%Y-%m-%d"),
        ]
    )

    entry_details_datewise_modular = {}
    # entry_details_datewise = {}
    for count in range(NUMBER_OF_PREV_DAYS + 1):    
        cur_date = date_lowbound + timedelta(days=int(count))
        entry_details_datewise_modular[cur_date.strftime("%Y-%m-%d")] = {
            "committed": None,
            "is_absent": None,
            "entries": [],
        }

    for status in employeeDateStatus:

        entry_details_datewise_modular[str(status.date)]["committed"] = status.committed
        entry_details_datewise_modular[str(status.date)]["is_absent"] = status.is_absent

        #TODO: USE SAME CALL FOR NEW AND UPDATE PART TO PASS COLLECTION OF ENTRIES TO THE PAGE
        entry_key = status.date.strftime("%Y-%m-%d")
        entry_details_datewise_modular[entry_key]["entries"] =  sorted(collectTimeSheetEntries(status))

    entry_details_datewise_modularJSON = json.dumps(entry_details_datewise_modular)

    return render(
        request,
        "timesheet/timesheet_entries.html",
        {
            "date_lowbound": date_lowbound.strftime("%Y-%m-%d"),
            "date_highbound": date_highbound.strftime("%Y-%m-%d"),
            "entry_details_datewise_modularJSON": entry_details_datewise_modularJSON,
            "currentDate": currentDate,
        },
    )

def getMachinesForSetups(setupsForCurrentUser):
    machinesForSetup = {}
    setupIdCodes = []
    for setup in setupsForCurrentUser:
        setupIdCodes.append(setup.id_code)
        allActiveMachinesForSetup = (
            Machine.objects.select_related()
            .filter(is_active=True)
            .filter(setups__id_code__in = [setup.id_code])
        )
        machines = {}
        for machineForSetup in allActiveMachinesForSetup:
            machine = {
                'id_code'       : machineForSetup.id_code,
                'name'          : machineForSetup.name
            }
            machines [machineForSetup.id_code] = machine
        setupObj = {
            'id_code'           : setup.id_code,
            'name'              : setup.name,
            'machines'          : machines
        }

        machinesForSetup[setup.id_code] = setupObj
    return machinesForSetup, setupIdCodes

def getPartSetupMap(setupsForCurrentUser):
    partSetupMap = {}
    for setup in setupsForCurrentUser:
        partsForSetup = Part.objects.select_related()                       \
            .filter(is_active=True)                                         \
            .filter(setups__id_code = setup.id_code)
        for part in partsForSetup:
            if (part.id_code not in partSetupMap.keys()):
                partSetupMap [part.id_code] = {
                    'id_code': part.id_code,
                    'name': part.name,
                    'setups': {}
                }
            if (setup.id_code not in partSetupMap [part.id_code]['setups']):
                partSetupMap [part.id_code]['setups'][setup.id_code] = {
                    'id_code': setup.id_code,
                    'name': setup.name,
                }

    return partSetupMap

def processRequest(request, function_mode=None, entry_id=-1, landing=None):
    #TODO: CHECK POSSIBILITY OF HANDLING ONLY POST REQUEST
    currentDate = datetime.today()
    if function_mode is None:
        function_mode = request.POST["functionMode"]
    user = request.user
    if user is None:
        messages.info(request, "Invalid User")
        return redirect("gototimesheet")
    operator = Employee.objects.prefetch_related("setups").filter(
        user__username=request.user.username
    )[0]

    if function_mode == "ADD_PR":
        currentDate = request.POST["date_cell"]
        # PROD_ENTRY_INITIALIZATION_START
        # COLLECT ALL SETUPS AVAILABLE FOR SELECTED USER
        setupsForCurrentUser                    = operator.setups.filter(is_active=True)
        machinesForSetup, setupIdCodes = getMachinesForSetups(setupsForCurrentUser)

        partSetupMap = getPartSetupMap(setupsForCurrentUser)

        allTimeSheetEntries                         = allTimeSheetEntriesForUserDate(request.user.id, currentDate)
        machinesForSetupJSON                        = json.dumps(machinesForSetup)
        allTimeSheetEntriesJSON                     = json.dumps(allTimeSheetEntries)
        partSetupMapJSON                            = json.dumps(partSetupMap)

        lastEntryEndTime = "09:00"
        if (len(allTimeSheetEntries) > 0):
            lastEntryEndTime = allTimeSheetEntries[-1][1]

        return render(
            request,
            "timesheet/newTimeEntry.html",
            {
                "partSetupMapJSON"              : partSetupMapJSON,
                "machinesForSetupJSON"          : machinesForSetupJSON,
                "currentDate"                   : currentDate,
                "allTimeSheetEntriesJSON"       : allTimeSheetEntriesJSON,
                "lastEntryEndTime"              : lastEntryEndTime
            },
        )

    elif function_mode == "ADD_NP":
        currentDate                                 = request.POST["date_cell"]
        allNonProdTasksQS                           = NonProdTask.objects.all()
        allNonProdTasks                             = {}
        for task in allNonProdTasksQS:
            allNonProdTasks[task.id_code]           = task.as_display_line()

        nonProdTasksJSON                            = json.dumps(allNonProdTasks)

        allTimeSheetEntries                         = allTimeSheetEntriesForUserDate(request.user.id, currentDate)
        allTimeSheetEntriesJSON                     = json.dumps(allTimeSheetEntries)

        lastEntryEndTime = "09:00"
        if (len(allTimeSheetEntries) > 0):
            lastEntryEndTime = allTimeSheetEntries[-1][1]

        return render(
            request,
            "timesheet/newTimeEntryNonProd.html",
            {
                "nonProdTasksJSON"              : nonProdTasksJSON, 
                "currentDate"                   : currentDate,
                "allTimeSheetEntriesJSON"       : allTimeSheetEntriesJSON,
                "lastEntryEndTime"              : lastEntryEndTime
            },
        )

    elif function_mode == "EDIT_PR":
        entry_id                                = request.POST["selectedEntry"]
        currentDate                             = request.POST["date_cell"]
        # COLLECT ALL SETUPS AVAILABLE FOR SELECTED USER
        setupsForCurrentUser                    = operator.setups.filter(is_active=True)
        machinesForSetup, setupIdCodes = getMachinesForSetups(setupsForCurrentUser)
        partSetupMap = getPartSetupMap(setupsForCurrentUser)
        tentry = TimeSheetEntryProd.objects.get(id=entry_id)
        setup = {
            "id_code": tentry.setup.id_code,
            "name": tentry.setup.name,
        }

        part = {
            "id_code": tentry.part.id_code,
            "name": tentry.part.name,
        }

        machine = {
            "id_code": tentry.machine.id_code,
            "name": tentry.machine.name,
        }

        entry = {
            "id": tentry.id,
            "date": tentry.employee_date_time_slot.employeeDate.date,
            "timeStart": tentry.employee_date_time_slot.timeStart,
            "timeEnd": tentry.employee_date_time_slot.timeEnd,
            "quantityHandled": tentry.quantityHandled,
            "quantityRejected": tentry.quantityRejected,
            "machine": machine,
            "part": part,
            "setup": setup,
        }
        selectedEntryJSON = json.dumps(entry, indent=4, sort_keys=True, default=str)
        
        allTimeSheetEntries                         = allTimeSheetEntriesForUserDate(request.user.id, currentDate)

        partSetupMapJSON                            = json.dumps(partSetupMap)
        machinesForSetupJSON                        = json.dumps(machinesForSetup)
        allTimeSheetEntriesJSON                     = json.dumps(allTimeSheetEntries)

        return render(
            request,
            "timesheet/editTimeEntry.html",
            {
                "partSetupMapJSON": partSetupMapJSON,
                "machinesForSetupJSON": machinesForSetupJSON,
                "currentDate": currentDate,
                "allTimeSheetEntriesJSON": allTimeSheetEntriesJSON,
                "selectedEntryJSON": selectedEntryJSON,
            },
        )

    elif function_mode == "EDIT_NP":
        entry_id = request.POST["selectedEntry"]
        currentDate                                 = request.POST["currentDate"]
        tentry = TimeSheetEntryNonProd.objects.get(id=entry_id)

        np_task = {
            "id_code": tentry.nonprod_task.id_code,
            "name": tentry.nonprod_task.name,
            "desc": tentry.nonprod_task.name,
        }

        entry = {
            "id": tentry.id,
            "date": tentry.employee_date_time_slot.employeeDate.date,
            "timeStart": tentry.employee_date_time_slot.timeStart,
            "timeEnd": tentry.employee_date_time_slot.timeEnd,
            "nonprod_task": np_task,
            "description": tentry.description,
        }
        allNonProdTasksQS = NonProdTask.objects.all()
        allNonProdTasks = {}
        for task in allNonProdTasksQS:
            allNonProdTasks[task.id_code] = task.as_display_line()
        nonProdTasksJSON = json.dumps(allNonProdTasks)
        selectedEntryJSON = json.dumps(entry, indent=4, sort_keys=True, default=str)
        
        allTimeSheetEntries                         = allTimeSheetEntriesForUserDate(request.user.id, currentDate)
        allTimeSheetEntriesJSON                     = json.dumps(allTimeSheetEntries)

        return render(
            request,
            "timesheet/editTimeEntryNonProd.html",
            {
                "nonProdTasksJSON": nonProdTasksJSON,
                "selectedEntryJSON": selectedEntryJSON,
                "allTimeSheetEntriesJSON": allTimeSheetEntriesJSON
            },
        )

    elif function_mode == "COMMIT":
        currentDate = request.POST["date_cell"]
        comittedDate = EmployeeDate.objects.filter(user=user, date=currentDate)[0]

        comittedDate.committed = True
        comittedDate.save()

    elif function_mode == "ABSENT_MARKED":
        currentDate = request.POST["date_cell"]
        employeeDatesQS = EmployeeDate.objects.filter(user=user, date=currentDate)
        markedEmployeeDate = None
        if employeeDatesQS.count() == 0:
            markedEmployeeDate = EmployeeDate.objects.create(
                user=user, date=currentDate, committed=False, is_absent=True
            )
        else:
            markedEmployeeDate = employeeDatesQS[0]
            markedEmployeeDate.is_absent = True
        markedEmployeeDate.save()

    elif function_mode == "ABSENT_UNMARKED":
        currentDate = request.POST["date_cell"]
        markedEmployeeDate = EmployeeDate.objects.filter(user=user, date=currentDate)[0]

        markedEmployeeDate.is_absent = False
        markedEmployeeDate.save()

    elif function_mode == "DELETE_PR":
        currentDate = deleteTimeEntryDetails_PR(request)

    elif function_mode == "DELETE_NP":
        currentDate = deleteTimeEntryDetails_NP(request)

    elif function_mode == "ADDED":
        currentDate = addTimeEntryDetails(request)

    elif function_mode == "ADDED_NP":
        currentDate = addNPTimeEntryDetails(request)

    elif function_mode == "EDITED":
        currentDate = updateTimeEntryDetails(request)

    elif function_mode == "EDITED_NP":
        currentDate = updateNPTimeEntryDetails(request)

    elif function_mode == "CANCEL":
        currentDate = request.POST["timesheetdate"]

    return redirect("timesheet_entries", currentDate)

def addTimeEntryDetails(request):
    if request.method == "POST":
        selectedUser = request.user
        selectedPart = Part.objects.get(id_code=request.POST["partselect"])
        selectedSetup = Setup.objects.get(id_code=request.POST["setupselect"])
        selectedMachine = Machine.objects.get(id_code=request.POST["machineselect"])
        selectedDate = request.POST["timesheetdate"]
        selectedTimeStart = request.POST["timesheetstart"]
        selectedTimeEnd = request.POST["timesheetend"]
        selectedQuantityHandled = request.POST["timesheetqtyhandled"]
        selectedQuantityRejected = request.POST["timesheetqtyrejected"]
        try:
            with transaction.atomic():
                employeeDateStatus = None
                employeeDateStatusQS = EmployeeDate.objects.filter(
                    user_id=selectedUser.id
                ).filter(date=selectedDate)
                if len(employeeDateStatusQS) == 0:
                    employeeDateStatus = EmployeeDate.objects.create(
                        date=selectedDate, user=selectedUser, committed=False, is_absent=False
                    )
                    employeeDateStatus.save()
                else:
                    employeeDateStatus = employeeDateStatusQS[0]

                employee_date_time_slot = EmployeeDateTimeSlot.objects.create(
                    employeeDate=employeeDateStatus,
                    timeStart=selectedTimeStart,
                    timeEnd=selectedTimeEnd,
                )

                tsEntry = TimeSheetEntryProd.objects.create(
                    part=selectedPart,
                    employee_date_time_slot=employee_date_time_slot,
                    # employeeDate        = employeeDateStatus,
                    setup=selectedSetup,
                    machine=selectedMachine,
                    quantityHandled=selectedQuantityHandled,
                    quantityRejected=selectedQuantityRejected,
                )
                tsEntry.save()
                logger.info('Time entry saved')
                #TODO: IF THIS IS FIRST ENTRY, ADD LUNCH BREAK ENTRY (12.30-13.00)
                if (isFirstEntryAdded(employeeDateStatus)):
                    addLunchBreak(employeeDateStatus)
                logger.info('Production Time entry saved')
        except Exception as e:
            messages.info(request, 'Tme entry Failed')
            log_message = 'Time entry Failed:' + str(e)
            logger.debug(log_message)

        return selectedDate


def addNPTimeEntryDetails(request):
    if request.method == "POST":
        selectedUser = request.user
        selectedTask = NonProdTask.objects.get(
            id_code=request.POST["nonprodtaskselect"]
        )
        selectedDesc = request.POST["description"]
        selectedDate = request.POST["timesheetdate"]
        selectedTimeStart = request.POST["timesheetstart"]
        selectedTimeEnd = request.POST["timesheetend"]
        try:
            with transaction.atomic():
                employeeDateStatus = None
                employeeDateStatusQS = EmployeeDate.objects.filter(
                    user_id=selectedUser.id
                ).filter(date=selectedDate)
                if len(employeeDateStatusQS) == 0:
                    employeeDateStatus = EmployeeDate.objects.create(
                        date=selectedDate, user=selectedUser, committed=False, is_absent=False
                    )
                    employeeDateStatus.save()
                else:
                    employeeDateStatus = employeeDateStatusQS[0]

                employee_date_time_slot = EmployeeDateTimeSlot.objects.create(
                    employeeDate=employeeDateStatus,
                    timeStart=selectedTimeStart,
                    timeEnd=selectedTimeEnd,
                )

                tsEntry = TimeSheetEntryNonProd.objects.create(
                    nonprod_task=selectedTask,
                    employee_date_time_slot=employee_date_time_slot,
                    description=selectedDesc
                    # employeeDate        = employeeDateStatus,
                )
                tsEntry.save()
                #TODO: IF THIS IS FIRST ENTRY, ADD LUNCH BREAK ENTRY (12.30-13.00)
                if (isFirstEntryAdded(employeeDateStatus)):
                    addLunchBreak(employeeDateStatus)
                logger.info('Non production Time entry saved')
        except Exception as e:
            messages.info(request, 'Non production Time entry saved Failed')
            log_message = 'Non production Time entry saved:' + str(e)
            logger.debug(log_message)

        return selectedDate


def updateTimeEntryDetails(request):
    if request.method == "POST":
        try:
            with transaction.atomic():
                entryId = request.POST["entryId"]
                entry = TimeSheetEntryProd.objects.get(id=entryId)

                # entry.user                      = request.user
                entry.part = Part.objects.get(id_code=request.POST["partselect"])
                entry.setup = Setup.objects.get(id_code=request.POST["setupselect"])
                entry.machine = Machine.objects.get(id_code=request.POST["machineselect"])

                # entry.date                      = request.POST['timesheetdate'] # DEPRECATED

                entry.employee_date_time_slot.timeStart = request.POST["timesheetstart"]
                entry.employee_date_time_slot.timeEnd = request.POST["timesheetend"]
                entry.quantityHandled = request.POST["timesheetqtyhandled"]
                entry.quantityRejected = request.POST["timesheetqtyrejected"]
                entry.employee_date_time_slot.save()
                entry.save()
                logger.info('Production Time entry updated')
        except Exception as e:
            messages.info(request, 'Production Time entry update Failed')
            log_message = 'Production Time entry update Failed:' + str(e)
            logger.debug(log_message)
    return entry.employee_date_time_slot.employeeDate.date

def updateNPTimeEntryDetails(request):
    if request.method == "POST":
        entryId = request.POST["entryId"]
        try:
            with transaction.atomic():
                entry = TimeSheetEntryNonProd.objects.get(id=entryId)

                entry.nonprod_task = NonProdTask.objects.get(
                    id_code=request.POST["nonprodtaskselect"]
                )
                entry.description = request.POST["description"]

                entry.employee_date_time_slot.timeStart = request.POST["timesheetstart"]
                entry.employee_date_time_slot.timeEnd = request.POST["timesheetend"]
                entry.employee_date_time_slot.save()
                entry.save()
                logger.info('Non Production Time entry updated')
        except Exception as e:
            messages.info(request, 'Non Production Time entry update Failed')
            log_message = 'Non Production Time entry update Failed:' + str(e)
            logger.debug(log_message)
    return entry.employee_date_time_slot.employeeDate.date


def deleteTimeEntryDetails_PR(request):
    try:
        with transaction.atomic():
            tentry = TimeSheetEntryProd.objects.get(id=request.POST["selectedEntry"])
            currentDate = tentry.employee_date_time_slot.employeeDate.date
            tentry.delete()
            logger.info('Production Time entry deleted')
    except Exception as e:
        messages.info(request, 'Delete Production Time entry Failed')
        log_message = 'Delete Production Time entry Failed:' + str(e)
        logger.debug(log_message)
    return currentDate

def deleteTimeEntryDetails_NP(request):
    try:
        with transaction.atomic():
            tentry = TimeSheetEntryNonProd.objects.get(id=request.POST["selectedEntry"])
            currentDate = tentry.employee_date_time_slot.employeeDate.date
            tentry.delete()
            logger.info('Not Production Time entry deleted')
    except Exception as e:
        messages.info(request, 'Delete Non Production Time entry update Failed')
        log_message = 'Delete Non Production Time entry update Failed:' + str(e)
        logger.debug(log_message)
    return currentDate

def timesheetLogout(request, landing=None):
    auth.logout(request)
    print("----- LOGGED OUT -----")
    return redirect("gototimesheet")

def allTimeSheetEntriesForUserDate(user_id, current_date):
    employeeDateStatusQS = EmployeeDate.objects.filter(user_id = user_id, date = current_date)
    allTimeSheetEntries = []
    if (employeeDateStatusQS.count() > 0):
        allTimeSheetEntries =  sorted(collectTimeSheetEntries(employeeDateStatusQS[0]))
    return allTimeSheetEntries

def collectTimeSheetEntries(status):
    tsheetentries = (
        TimeSheetEntryProd.objects.select_related(
            "setup", "part", "machine", "employee_date_time_slot"
        )
        .filter(employee_date_time_slot__employeeDate__user_id = status.user.id)
        .filter(
            employee_date_time_slot__employeeDate__date = status.date.strftime(
                "%Y-%m-%d"
            )
        )
    )
    entry_details_date_user_wise = []
    # APPEND ALL PRODUCTION ENTRIES AS A STRING
    for tentry in tsheetentries:
        entry_details_date_user_wise.append(
            (
                tentry.employee_date_time_slot.timeStart.strftime("%H:%M"),
                tentry.employee_date_time_slot.timeEnd.strftime("%H:%M"),
                "PR" + str(tentry.id), 
                tentry.as_display_line()
            )
        )

    # COLLECT ALL NON-PRODUCTION ENTRIES
    tsheetentries_nonprod = (
        TimeSheetEntryNonProd.objects.select_related(
            "nonprod_task", "employee_date_time_slot"
        )
        .filter(employee_date_time_slot__employeeDate__user_id = status.user.id)
        .filter(
            employee_date_time_slot__employeeDate__date=status.date.strftime(
                "%Y-%m-%d"
            )
        )
    )

    # APPEND ALL NON-PRODUCTION ENTRIES AS A STRING
    for tentry_np in tsheetentries_nonprod:
        entry_details_date_user_wise.append(
            (
                tentry_np.employee_date_time_slot.timeStart.strftime("%H:%M"),
                tentry_np.employee_date_time_slot.timeEnd.strftime("%H:%M"),
                "NP" + str(tentry_np.id), 
                tentry_np.as_display_line()
            )
        )
    return entry_details_date_user_wise

def addLunchBreak(employeeDateStatus):
    non_prod_lunch_break = NonProdTask.objects.filter(id_code = "NPLN")
    lunch_break = None
    if non_prod_lunch_break.count() == 0:
        lunch_break = NonProdTask.objects.create(id_code = "NPLN", name = "Lunch Break", desc = "Luch Break", is_active = False)
        lunch_break.save()
    else:
        lunch_break = non_prod_lunch_break[0]
    employee_date_time_slot = EmployeeDateTimeSlot.objects.create(
        employeeDate=employeeDateStatus,
        timeStart = "12:30",
        timeEnd = "13:00",
    )

    tsEntry = TimeSheetEntryNonProd.objects.create(
        nonprod_task = lunch_break,
        employee_date_time_slot=employee_date_time_slot,
        description = lunch_break.desc
    )
    tsEntry.save()

def isFirstEntryAdded(employeeDateStatus):
    entryCountPR = (
        TimeSheetEntryProd.objects
            .filter(employee_date_time_slot__employeeDate__user_id = employeeDateStatus.user.id)
            .filter(
                    employee_date_time_slot__employeeDate__date = employeeDateStatus.date.strftime(
                        "%Y-%m-%d"
            )
        )
    ).count()
    entryCountNP = (
        TimeSheetEntryNonProd.objects
        .filter(employee_date_time_slot__employeeDate__user_id = employeeDateStatus.user.id)
        .filter(
            employee_date_time_slot__employeeDate__date = employeeDateStatus.date.strftime(
                "%Y-%m-%d"
            )
        )
    ).count()
    totalEntryCount = entryCountPR + entryCountNP
    return totalEntryCount == 1

