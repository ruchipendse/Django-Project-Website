import numpy as np
from django.contrib import messages
from django.shortcuts import render, redirect
from inprogress.models import Setup

import os
from django.conf import settings
from django.http import HttpResponse, Http404

from inprogress.subviews.views_timesheet import allTimeSheetEntriesForUserDate
from inprogress.subviews.views_batchprocess import force_commit, force_uncommit
from inprogress.models import Machine, Employee, Setup, TimeSheetEntryProd, TimeSheetEntryNonProd, EmployeeDate, MachineSetup

import json
import datetime
from datetime import datetime as dt
from datetime import timedelta, date
from django.db.models import Q

import pandas as pd
#------------------------------------------------------------------
#        REPORTS 
#------------------------------------------------------------------

def report_download(request, report_criteria = None, report_date = None):

    if (report_criteria is None):
        report_criteria = "USER"
        if ("report_criteria" in request.POST.keys()):
            report_criteria = request.POST["report_criteria"]

    if (report_date is None):
        report_date = dt.today().strftime("%Y-%m-%d")
        if ("to_date" in request.POST.keys()):
            report_date = request.POST["to_date"]

    dummy1, dummy2, userwise_report_data = getReportsData(request, report_criteria, report_date)
    # userwise_report_dataJson = json.dumps(userwise_report_data)    
    file_name_preffix = dt.today().strftime("%Y%m%d%H%M%S")
    file_name = "tmp/" + file_name_preffix + "user_date.csv"
    file_path = os.path.join("", file_name)

    report_df = pd.DataFrame.from_dict(userwise_report_data, orient="index")
    cols = len(report_df.iloc[0])
    for i in range(len(report_df)) :
        for c in range(cols):
            element = report_df.iloc[i, c] 
            if (element['absent']):
                new_element = "\nAbsent\n"    
            else:
                new_element = "EF["                                                                   \
                                + str(element['efficiency']) + "]\nPR["              \
                                + str(element['production']) + "]\nAC["              \
                                + str(element['activity'])                           \
                            + "]"

            report_df.iloc[i, c] = new_element
    report_df.to_csv(file_path)

    if os.path.exists(file_path):
        with open(file_path, 'rb') as fh:
            response = HttpResponse(fh.read(), content_type="application/vnd.ms-excel")
            response['Content-Disposition'] = 'inline; filename=' + file_path

            return response
    raise Http404
 
"""
METHOD CALLED WHEN ADMIN CLICKS "REPORTS" LINK. 
RETURNS DATA REPORT
1. efficiency = (achieved qty % target qty)
     colorcode: act >= 80% Green, bet 60-80 Yellow, below 60 Red - 
2. Production = prod + non-prod/ (total time)
     colorcode: act >= 92.5% Green, bet 85-92.5 Yellow, below 85 Red
3. Activity = prod + non-prod/ total ideal time(8 hours) activity to be truncated to 100%
     colorcode: act >= 96% Green, bet 94-96 Yellow, below94 Red
"""
def reports(request):
    file_name = "tmp/report_data.csv"
    if os.path.exists(file_name):
        # delete file after use
        os.remove(file_name)

    report_criteria = "USER"
    if ("report_criteria" in request.POST.keys()):
        report_criteria = request.POST["report_criteria"]

    target_date = dt.today()
    if ("to_date" in request.POST.keys()):
        target_date = dt.strptime(request.POST["to_date"], "%Y-%m-%d")

    if ("functionMode" in request.POST.keys()):
        functionMode = request.POST["functionMode"]
        if functionMode == "FORCE_COMMIT":
            force_commit(request, report_date = target_date.strftime("%Y-%m-%d"))
        elif functionMode == "FORCE_UNCOMMIT":
            force_uncommit(request, report_date = target_date.strftime("%Y-%m-%d"))
    week_day = target_date.strftime("%w")
    go_back = 0
    if (int(week_day) > 0):
        go_back = int(week_day) - 0 # 0 for SUNDAY
    last_sunday = target_date - timedelta(days=go_back)  # TO
    report_date = last_sunday.strftime("%Y-%m-%d")

    report_dates, upper_date, userwise_report_data, userwise_report_entries, all_committed              \
                        = getReportsData(request, report_criteria, report_date)
    userwise_report_entries_json = json.dumps(userwise_report_entries)
    report_datesJson = json.dumps(report_dates)    
    return render(request, 'report/reports.html', 
                            {
                                'report_dates'          : report_dates,
                                'report_datesJson'      : report_datesJson,
                                'selected_date'         : upper_date,
                                'userwise_report_data'  : userwise_report_data,
                                'userwise_report_entries_json'  : userwise_report_entries_json,
                                'all_committed'         : all_committed
                            })

def getReportsData(request, report_criteria, upper_date):
    NUMBER_OF_PREV_DAYS = 6
    all_committed = True
    date_highbound = dt.strptime(upper_date, "%Y-%m-%d")
    date_lowbound = date_highbound - timedelta(days=NUMBER_OF_PREV_DAYS)  # TO
    report_dates = []
    to_date_entry = date_highbound.strftime("%Y-%m-%d")
    report_dates.append(to_date_entry)

    for day in range(1, NUMBER_OF_PREV_DAYS + 1):
        to_date = date_highbound - timedelta(days=day)
        report_dates.append(to_date.strftime("%Y-%m-%d"))

    report_dates.sort()

    if (report_criteria == "USER"):
        # USER-WISE REPORT REQUIRED
        operators = Employee.objects.filter(is_active = True)
        userwise_report_data = {}
        userwise_report_entries = {}
        for op in operators:
            user = op.user

            employeeDateStatus = EmployeeDate.objects.filter(
                Q(user_id=user.id),
                Q(date__range=[
                    date_lowbound.strftime("%Y-%m-%d"),
                    date_highbound.strftime("%Y-%m-%d")
                ])
            )

            entry_details_datewise_modular  = {}
            entries_datewise_modular        = {}
            for report_date in report_dates:
                entry_details_datewise_modular[report_date] = {
                    'committed'                 : False,
                    'force_committed'           : False,
                    'absent'                    : False,
                    'prod_value'                : 0,
                    'production'                : "{:5.2f}".format(0),

                    'efficiency_value'          : 0,
                    'efficiency'                : "{:5.2f}".format(0),

                    'activity_value'            : 0,
                    'activity'                  : "{:6.2f}".format(0),
                }

            for status in employeeDateStatus:
                if all_committed :
                    all_committed = status.committed or status.forceCommitted
                entry_key = status.date.strftime("%Y-%m-%d")
                entry_details_datewise_modular[entry_key]                     = {}
                entry_details_datewise_modular[entry_key]['absent']           = status.is_absent
                entry_details_datewise_modular[entry_key]['committed']        = status.committed
                entry_details_datewise_modular[entry_key]['forceCommitted']   = status.forceCommitted
                if status.is_absent:
                    entry_details_datewise_modular[entry_key]['prod_value']       = 0
                    entry_details_datewise_modular[entry_key]['production']       = "{:5.2f}".format(0),

                    entry_details_datewise_modular[entry_key]['efficiency_value'] = 0,
                    entry_details_datewise_modular[entry_key]['efficiency']       = "{:5.2f}".format(0),

                    entry_details_datewise_modular[entry_key]['activity_value']   = 0,
                    entry_details_datewise_modular[entry_key]['activity']         = "{:6.2f}".format(0),
                else:
                    entry_details_datewise_modular[entry_key] =  allTimeSheetEntriesForUserDateDeep(user, status.date)
                    entries_datewise_modular[entry_key]       =  allTimeSheetEntriesForUserDate(user.id, status.date)
            userwise_report_data [user.first_name + " " + user.last_name] = entry_details_datewise_modular
            userwise_report_entries [user.first_name + " " + user.last_name] = entries_datewise_modular

    elif (report_criteria == "MACHINE"):
        #TODO: DEVELOP THE MACHINE SPECIFIC REPORT HERE
        pass
    return report_dates, upper_date, userwise_report_data, userwise_report_entries, all_committed

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

    # APPEND ALL PRODUCTION ENTRIES AS A STRING
    target_quantity                 = 0
    achieved_quantity               = 0
    prod_time                       = 0
    for tentry in tsheetentries:
        endTime = tentry.employee_date_time_slot.timeEnd
        startTime = tentry.employee_date_time_slot.timeStart
        dateTimeEnd = datetime.datetime.combine(datetime.date.today(), endTime)
        dateTimeStart = datetime.datetime.combine(datetime.date.today(), startTime)
        dateTimeDifference = dateTimeEnd - dateTimeStart
        totalEntryTime = dateTimeDifference.total_seconds()

        machine = tentry.machine
        setup = tentry.setup
        machineSetup = MachineSetup.objects.get(machine__id = machine.id, setup__id = setup.id)
        cycle_time = machineSetup.cycle_time
        target_quantity_entry = int(totalEntryTime/cycle_time)
        target_quantity += target_quantity_entry
        prod_time += totalEntryTime
        achieved_quantity += tentry.quantityHandled

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
    nonprod_time                     = 0
    for tentry_np in tsheetentries_nonprod:
        endTime = tentry_np.employee_date_time_slot.timeEnd
        startTime = tentry_np.employee_date_time_slot.timeStart
        dateTimeEnd = datetime.datetime.combine(datetime.date.today(), endTime)
        dateTimeStart = datetime.datetime.combine(datetime.date.today(), startTime)
        dateTimeDifference = dateTimeEnd - dateTimeStart
        totalEntryTime = dateTimeDifference.total_seconds()
        nonprod_time += totalEntryTime

    efficiency = 0
    if (target_quantity > 0):
        efficiency = achieved_quantity * 100 / target_quantity
    activity = (prod_time + nonprod_time) * 100/(8*3600)
    if activity > 100:
        activity = 100
    production = 0
    if ((prod_time + nonprod_time) > 0):
        production = prod_time * 100/ (prod_time + nonprod_time)
    datewise_user_productivity = {
        'absent'                    : False,
        'prod_value'        : production,
        'production'        : "{:5.2f}".format(production),

        'efficiency_value'        : efficiency,
        'efficiency'        : "{:5.2f}".format(efficiency),

        'activity_value'        : activity,
        'activity'          : "{:6.2f}".format(activity),
    }
    datewise_user_productivity['absent']           = status.is_absent
    datewise_user_productivity['committed']        = status.committed
    datewise_user_productivity['forceCommitted']   = status.forceCommitted

    return datewise_user_productivity

