from django.contrib.auth.models import User, auth
from django.contrib import messages
from django.shortcuts import render, redirect
from inprogress.models import Setup
from django.db import transaction

import json
import datetime
from datetime import datetime as dt
from datetime import timedelta, date

from inprogress.models import (
     EmployeeDate, 
     EmployeeDateTimeSlot, 
     TimeSheetEntryProd, 
     TimeSheetEntryNonProd, 
     NonProdTask
     )
from inprogress.subviews.views_report import allTimeSheetEntriesForUserDateDeep

def prepopulate():
    # FOR EACH PRESENT USER THERE SHOULD BE AN ENTRY IN USER-DATE TABLE FOR EACH DATE WITHIN SCOPE   
    #TODO: PRE-POPULATE THESE ENTRIES
    end_date = dt.today()
    no_days = 7
    for go_back in range(no_days):
        current_date = end_date - timedelta(days=go_back)
        users = User.objects.filter(is_active = True)
        for user in users:
            emp_date = EmployeeDate.objects.filter(user__id = user.id, date= current_date.strftime("%Y-%m-%d"))
            if emp_date.count() == 0:
                emp_date = EmployeeDate.objects.create(user = user, date= current_date, committed = False, is_absent = False)
                emp_date.save()

def autocommit(request):
    prepopulate()
    day_before                                  =  dt.today() - timedelta(days=2)
    day_before_week_day                         = day_before.strftime("%w")
    go_back = 0
    if (int(day_before_week_day) > 0):
        go_back = int(day_before_week_day) - 0 # 0 for SUNDAY
    latest_sunday = day_before - timedelta(days=go_back)  # TO
    date_lowbound =  dt.strptime("2020-08-01", "%Y-%m-%d")
    employeeDateStatus = EmployeeDate.objects.filter(committed = False,
        date__range=[
            date_lowbound.strftime("%Y-%m-%d"),
            latest_sunday.strftime("%Y-%m-%d"),
        ]
    )

    for status in employeeDateStatus:
        tslots = []
        tsheetentries = (
            TimeSheetEntryProd.objects.select_related(
                "employee_date_time_slot"
            )
            .filter(employee_date_time_slot__employeeDate__user_id = status.user.id)
            .filter(
                employee_date_time_slot__employeeDate__date = status.date.strftime(
                    "%Y-%m-%d"
                )
            )
        )

        for tsheet_entry in tsheetentries:
            tslots.append((tsheet_entry.employee_date_time_slot.timeStart, tsheet_entry.employee_date_time_slot.timeEnd))

        tsheetnonprodentries = (
            TimeSheetEntryNonProd.objects.select_related(
                "employee_date_time_slot"
            )
            .filter(employee_date_time_slot__employeeDate__user_id = status.user.id)
            .filter(
                employee_date_time_slot__employeeDate__date = status.date.strftime(
                    "%Y-%m-%d"
                )
            )
        )

        for tsheet_npentry in tsheetnonprodentries:
            tslots.append((tsheet_npentry.employee_date_time_slot.timeStart, tsheet_npentry.employee_date_time_slot.timeEnd))

        slots_sorted = sorted(tslots, key=lambda tup: tup[0])
        slot_count = len(slots_sorted)

        blankEntryTask = NonProdTask.objects.filter(id_code = 'NPBE')  # Dummy entry for blank timesheet entries
        blank_entry = None
        if blankEntryTask.count() == 0:
            blank_entry = NonProdTask.objects.create(id_code = "NPBE", name = "Blank Entry", desc = "NO Valid entry exists", is_active = False)
            blank_entry.save()
        else:
            blank_entry = blankEntryTask[0]
        if slot_count > 0:
            if slots_sorted[0][0] >  datetime.time(hour=9, minute=0):
                # work hours did not start at 9AM so add empty entry
                employee_date_time_slot = EmployeeDateTimeSlot.objects.create(
                    employeeDate=status,
                    timeStart=datetime.time(hour=9, minute=0),
                    timeEnd=slots_sorted[0][0],
                )

                tsEntry = TimeSheetEntryNonProd.objects.create(
                    nonprod_task=blank_entry,
                    employee_date_time_slot=employee_date_time_slot,
                    description= "No Valid time entry"
                )
                tsEntry.save()
                slots_sorted.append((tsEntry.employee_date_time_slot.timeStart, tsEntry.employee_date_time_slot.timeEnd))
                slots_sorted = sorted(slots_sorted, key=lambda tup: tup[0])

            for slot_index in range(1, slot_count):
                if (slots_sorted[slot_index][0] != slots_sorted[slot_index - 1][1]):
                    employee_date_time_slot = EmployeeDateTimeSlot.objects.create(
                        employeeDate=status,
                        timeStart=slots_sorted[slot_index - 1][1],
                        timeEnd=slots_sorted[slot_index][0],
                    )

                    tsEntry = TimeSheetEntryNonProd.objects.create(
                        nonprod_task=blank_entry,
                        employee_date_time_slot=employee_date_time_slot,
                        description= "No Valid time entry"
                    )
                    tsEntry.save()
            # CHECK IF 8 HOURS ENTRIES ARE THERE
            if slots_sorted[-1][1] <  datetime.time(hour=17, minute=0):
                employee_date_time_slot = EmployeeDateTimeSlot.objects.create(
                    employeeDate=status,
                    timeStart=slots_sorted[-1][1],
                    timeEnd=datetime.time(hour=17, minute=0),
                )

                tsEntry = TimeSheetEntryNonProd.objects.create(
                    nonprod_task=blank_entry,
                    employee_date_time_slot=employee_date_time_slot,
                    description= "No Valid time entry"
                )
                tsEntry.save()
        else: 
            # As there is no entry present, mark day as absent
            status.is_absent = True     
            status.save()       
        status.committed = True            
        status.save()       


