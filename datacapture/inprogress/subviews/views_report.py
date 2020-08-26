import numpy as np
from django.contrib import messages
from django.shortcuts import render, redirect
from inprogress.models import Setup

from inprogress.subviews.views_timesheet import allTimeSheetEntriesForUserDate
from inprogress.models import Machine, Employee, Setup, TimeSheetEntryProd, TimeSheetEntryNonProd, EmployeeDate, MachineSetup


import json
import datetime
from datetime import datetime as dt
from datetime import timedelta, date
#------------------------------------------------------------------
#        REPORTS 
#------------------------------------------------------------------

"""
METHOD CALLED WHEN ADMIN CLICKS "SETUPS" LINK. 
RETURNS PARTS LIST
"""

def reports(request):
    NUMBER_OF_PREV_DAYS = 6

    report_criteria = "USER"
    if ("report_criteria" in request.POST.keys()):
        report_criteria = request.POST["report_criteria"]

    upper_date = dt.today().strftime("%Y-%m-%d")
    if ("to_date" in request.POST.keys()):
        upper_date = request.POST["to_date"]

    date_highbound = dt.strptime(upper_date, "%Y-%m-%d")
    date_lowbound = date_highbound - timedelta(days=NUMBER_OF_PREV_DAYS)  # TO
    report_dates = []
    to_date_entry = date_highbound.strftime("%Y-%m-%d")
    report_dates.append(to_date_entry)

    for day in range(1, NUMBER_OF_PREV_DAYS + 1):
        to_date = date_highbound - timedelta(days=day)
        report_dates.append(to_date.strftime("%Y-%m-%d"))

    if (report_criteria == "USER"):
        operators = Employee.objects.filter(is_active = True)
        userwise_report_data = {}
        for op in operators:
            user = op.user
            employeeDateStatus = EmployeeDate.objects.filter(user_id=user.id).filter(
                date__range=[
                    date_lowbound.strftime("%Y-%m-%d"),
                    date_highbound.strftime("%Y-%m-%d"),
                ],
            ).filter(committed = True)
            entry_details_datewise_modular = {}
            for report_date in report_dates:
                entry_details_datewise_modular[report_date] = {
                    'total_time_prod_mins' :"-",
                    'total_time_nonprod_mins' :"-",
                    'total_parts_finished_expected': "-",
                    'total_parts_finished_actual': "-"
                }

            for status in employeeDateStatus:
                entry_key = status.date.strftime("%Y-%m-%d")
                entry_details_datewise_modular[entry_key] =  allTimeSheetEntriesForUserDateDeep(user, status.date)
            userwise_report_data [user.username] = entry_details_datewise_modular
    elif (report_criteria == "MACHINE"):
        #TODO: DEVELOP THE MACHINE SPECIFIC REPORT HERE
        pass
    
    return render(request, 'report/reports.html', 
                            {
                                'report_dates'          : report_dates,
                                'selected_date'            : upper_date,
                                'userwise_report_data'  : userwise_report_data,
                            })

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
    datewise_user_productivity = {
        'total_time_prod_mins' :round(total_time_prod/ 60, 0),
        'total_time_nonprod_mins' :round(total_time_nonprod/ 60, 0),
        'total_parts_finished_expected': total_handled_expected,
        'total_parts_finished_actual': total_handled_actual
    }
    return datewise_user_productivity

