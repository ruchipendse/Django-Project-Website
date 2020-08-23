from django.contrib import messages
from django.shortcuts import render, redirect
from inprogress.models import Setup

from inprogress.subviews.views_timesheet import allTimeSheetEntriesForUserDate
from inprogress.models import Machine, Employee, Setup, TimeSheetEntryProd, TimeSheetEntryNonProd, EmployeeDate, MachineSetup


import json
import datetime
#------------------------------------------------------------------
#        REPORTS 
#------------------------------------------------------------------

"""
METHOD CALLED WHEN ADMIN CLICKS "SETUPS" LINK. 
RETURNS PARTS LIST
"""
def reports(request):
    uname = "U001"
    currentDate = "2020-08-13"

    operator = Employee.objects.get(user__username = uname)
    user = operator.user

    allTimeSheetEntries                     = allTimeSheetEntriesForUserDateDeep(user, currentDate)
    allTimeSheetEntriesJSON                 = json.dumps(allTimeSheetEntries)

    #TODO: FORWARD DATE_RANGE_WISE_EMPLOYEE - PROD/NON-PROD + EXP/ACTUAL DATA
    --------

    return render(request, 'report/reports.html', 
                            {'allTimeSheetEntries': allTimeSheetEntries, 
                            'allTimeSheetEntriesJson': allTimeSheetEntriesJSON,
                            })

def generateReport(request):
    criteria = request.POST['selectedCriteria']
    print ('\n ----- GENERATING REPORT ----- \n', criteria)
    return redirect('reports')

#-------------------------- UTILITY METHOD -----------------------
# TODO: THIS METHOD NEEDS TO BE REUSED ALONG WITH SIMILAR METHOD FROM TIMESHEET ENTRY

def allTimeSheetEntriesForUserDateDeep(user_id, current_date):
# TODO: COMBINE THIS DATA IN PROPER STRUCTURE AND DISPATCH IT TO PAGE FOR DISPLAY

    employeeDateStatusQS = EmployeeDate.objects.filter(user_id = user_id, date = current_date)
    allTimeSheetEntries = []
    if (employeeDateStatusQS.count() > 0):
        allTimeSheetEntries =  collectTimeSheetEntriesDeep(employeeDateStatusQS[0])
    return allTimeSheetEntries

def collectTimeSheetEntriesDeep(status):
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
    total_handled_expected              = 0
    total_time_prod                     = 0
    total_handled_actual                = 0
    for tentry in tsheetentries:
        endTime = tentry.employee_date_time_slot.timeEnd
        startTime = tentry.employee_date_time_slot.timeStart
        dateTimeEnd = datetime.datetime.combine(datetime.date.today(), endTime)
        dateTimeStart = datetime.datetime.combine(datetime.date.today(), startTime)
        dateTimeDifference = dateTimeEnd - dateTimeStart
        totalTime = dateTimeDifference.total_seconds()

        machine = tentry.machine
        setup = tentry.setup
        machineSetup = MachineSetup.objects.get(machine__id = machine.id, setup__id = setup.id)
        cycle_time = machineSetup.cycle_time
        handled_expected = int(totalTime/cycle_time)
        total_handled_expected += handled_expected
        total_time_prod += totalTime
        total_handled_actual += tentry.quantityHandled

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
    total_time_nonprod                     = 0
    for tentry_np in tsheetentries_nonprod:
        endTime = tentry.employee_date_time_slot.timeEnd
        startTime = tentry.employee_date_time_slot.timeStart
        dateTimeEnd = datetime.datetime.combine(datetime.date.today(), endTime)
        dateTimeStart = datetime.datetime.combine(datetime.date.today(), startTime)
        dateTimeDifference = dateTimeEnd - dateTimeStart
        totalTime = dateTimeDifference.total_seconds()
        total_time_nonprod += totalTime

        entry_details_date_user_wise.append(
            (
                tentry_np.employee_date_time_slot.timeStart.strftime("%H:%M"),
                tentry_np.employee_date_time_slot.timeEnd.strftime("%H:%M"),
                "NP" + str(tentry_np.id), 
                tentry_np.as_display_line()
            )
        )
    print ('\n ----- total prod ----- \n', total_time_prod/ 3600, total_time_nonprod/ 3600, total_handled_expected, total_handled_actual)
    datewise_user_productivity = {
        'total_time_prod_mins' :round(total_time_prod/ 60, 0),
        'total_time_nonprod_mins' :round(total_time_nonprod/ 60, 0),
        'total_parts_finished_expected': total_handled_expected,
        'total_parts_finished_actual': total_handled_actual
    }
    return datewise_user_productivity

