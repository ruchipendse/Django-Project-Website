from django.contrib.auth.models import User, auth
from django.contrib import messages
from django.shortcuts import render, redirect
from inprogress.models import Setup
from django.db import transaction

import json
import datetime
from datetime import datetime as dt
from datetime import timedelta, date
import logging

from inprogress.loggerConfig import configure_logger
from inprogress.subviews.views_report import allTimeSheetEntriesForUserDateDeep

from inprogress.models import (
     EmployeeDate, 
     EmployeeDateTimeSlot, 
     TimeSheetEntryProd, 
     TimeSheetEntryNonProd, 
     NonProdTask,
     Employee
     )

AUTO_COMMIT_EFFECTIVE_DATE = "2020-09-01"
OFFICE_START_TIME = datetime.time(hour=9, minute=0)

configure_logger()
logger = logging.getLogger(__name__)

def prepopulate(request):
    # FOR EACH PRESENT USER THERE SHOULD BE AN ENTRY STARTING FROM AUTOCOMMIT EFFECTIVE DATE

    end_date = dt.today()
    current_date = dt.strptime(AUTO_COMMIT_EFFECTIVE_DATE, "%Y-%m-%d")
    delta = datetime.timedelta(days=1)

    while current_date <= end_date:
        operators = Employee.objects.filter(is_active = True)
        # users = User.objects.filter(is_active = True)
        for operator in operators:
            user = operator.user
            emp_date = EmployeeDate.objects.filter(user__id = user.id, date= current_date.strftime("%Y-%m-%d"))
            if emp_date.count() == 0:
                emp_date = EmployeeDate.objects.create(user = user, date= current_date, committed = False, is_absent = False)
                emp_date.save()
        current_date += delta

def commit_timesheets_all_daterange(request):
    #TODO: CALL THIS METHOD FOR DATE RANGE AND USER RANGE
    
    testusername = "motiram.bhadange"
    testdate = "2020-09-05"
    emp_date = EmployeeDate.objects.filter(user__username = testusername, date= testdate)
    if (emp_date.count() > 0):
        commit_timesheet_for_user_date(request, emp_date[0])
    else:
        log_message = 'Employee-date entry not found for: ' + testusername + ", " + testdate 
        print (log_message)
        logger.debug(log_message)

"""
COMMITS TIMSHEET FOR GIVEN USER
"""
def commit_timesheet_for_user_date(request, status):
    try:
        with transaction.atomic():
            tslots = []
            # ----- COLLECT ALL PRODUCTION ENTRY SLOTS
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

            # ----- COLLECT ALL NON-PRODUCTION ENTRY SLOTS
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

            # SORT THESE SLOTS FOR START TIME
            slots_sorted = sorted(tslots, key=lambda tup: tup[0])
            slot_count = len(slots_sorted)

            blank_entry = getBlankNonProdTask()
            blank_time_slots = []
            if slot_count > 0:
                # THERE IS AT LEAST ONE ENTRY HENCE OPERATOR IS PRESENT
                if slots_sorted[0][0] >  OFFICE_START_TIME:
                    # FIRST TIMESHEET ENTRY IS MISSING, 
                    employee_date_time_slot = EmployeeDateTimeSlot.objects.create(
                        employeeDate=status,
                        timeStart=OFFICE_START_TIME,
                        timeEnd=slots_sorted[0][0],
                    )
                    blank_time_slots.append(employee_date_time_slot)

                # COLLECT ALL INTERMEDIATE BLANK TIMESLOTS
                for slot_index in range(1, slot_count):
                    if (slots_sorted[slot_index][0] != slots_sorted[slot_index - 1][1]):
                        employee_date_time_slot = EmployeeDateTimeSlot.objects.create(
                            employeeDate=status,
                            timeStart=slots_sorted[slot_index - 1][1],
                            timeEnd=slots_sorted[slot_index][0],
                        )
                        blank_time_slots.append(employee_date_time_slot)

                # CHECK IF 8 HOURS TIMESHEET ENTRIES ARE THERE ELSE MARK REQUIRED SLOT FOR BLANK ENTRY
                if slots_sorted[-1][1] <  datetime.time(hour=17, minute=0):
                    employee_date_time_slot = EmployeeDateTimeSlot.objects.create(
                        employeeDate=status,
                        timeStart=slots_sorted[-1][1],
                        timeEnd=datetime.time(hour=17, minute=0),
                    )
                    blank_time_slots.append(employee_date_time_slot)

                # ADD BLANK NON-PROD ENTRY AT BLANK SLOTS
                for blank_time_slot in blank_time_slots:
                    tsEntry = TimeSheetEntryNonProd.objects.create(
                        nonprod_task=blank_entry,
                        employee_date_time_slot=blank_time_slot,
                        description= "No Valid time entry"
                    )
                    blank_time_slot.save()
                    tsEntry.save()

            else: 
                # THERE IS NO TIMESHEET ENTRY HENCE MARK OPERATOR ABSENT
                status.is_absent = True     
                status.save()       
            status.committed = True            
            status.save()       
    except Exception as e:
        # messages.info(request, 'Forced commit Failed for ' + status.user + ", " + status.date)
        log_message = 'Force commit Failed:' + str(e)
        print (log_message)
        logger.debug(log_message)


def getBlankNonProdTask():
    # CHECK IF BLANK-NON-PROD-TASK ENTRY DOES NOT EXIST CREATE IT
    blankEntryTask = NonProdTask.objects.filter(id_code = 'NPBE')  # Dummy entry for blank timesheet entries
    blank_entry = None
    if blankEntryTask.count() == 0:
        blank_entry = NonProdTask.objects.create(id_code = "NPBE", name = "Blank Entry", desc = "NO Valid entry exists", is_active = False)
        blank_entry.save()
    else:
        blank_entry = blankEntryTask[0]
    return blank_entry


