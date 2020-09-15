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

from inprogress.models import (
     EmployeeDate, 
     EmployeeDateTimeSlot, 
     TimeSheetEntryProd, 
     TimeSheetEntryNonProd, 
     NonProdTask,
     Employee
     )

AUTO_COMMIT_EFFECTIVE_DATE = "2020-08-31"
OFFICE_START_TIME = datetime.time(hour=9, minute=0)
OFFICE_CLOSE_TIME = datetime.time(hour=17, minute=30)

configure_logger()
logger = logging.getLogger(__name__)

def prepopulate(request):
    # FOR EACH PRESENT USER THERE SHOULD BE AN ENTRY STARTING FROM AUTOCOMMIT EFFECTIVE DATE

    end_date = dt.today()
    current_date = dt.strptime(AUTO_COMMIT_EFFECTIVE_DATE, "%Y-%m-%d")
    delta = datetime.timedelta(days=1)

    while current_date <= end_date:
        operators = Employee.objects.filter(is_active = True)
        for operator in operators:
            user = operator.user
            emp_date = EmployeeDate.objects.filter(user__id = user.id, date= current_date.strftime("%Y-%m-%d"))
            if emp_date.count() == 0:
                emp_date = EmployeeDate.objects.create(user = user, date= current_date, committed = False, is_absent = False)
                emp_date.save()
        current_date += delta

def force_commit(request, report_criteria = None, report_date = None):
    NUMBER_OF_PREV_DAYS = 6 # TODO: OBTAIN FROM GLOBAL PLACE

    operators = Employee.objects.all()
    users = []
    for operator in operators:
        users.append(operator.user_id)

    date_highbound = dt.strptime(report_date, "%Y-%m-%d")
    date_lowbound = date_highbound - timedelta(days=NUMBER_OF_PREV_DAYS)  # TO
    employeeDates               = EmployeeDate.objects.filter(user_id__in=users).filter(
                                        date__range=[
                                            date_lowbound.strftime("%Y-%m-%d"),
                                            date_highbound.strftime("%Y-%m-%d")
                                        ]
                                    )
    commit_sheets_selectusers_daterange(request, employeeDates)

def force_uncommit(request, report_criteria = None, report_date = None):
    # TODO: IMPLEMENT THIS METHOD TO FORCE_UNCOMMIT AND REMOVE FORCED ABSENT MARK
    print ('FORCE UNCOMMIT METHOD IN PROGRESS')

def commit_sheets_selectusers_daterange(request, user_dates):
    for user_date in user_dates:
        commit_timesheet_for_user_date(request, user_date)


"""
COMMITS TIMSHEET FOR GIVEN USER
"""
def commit_timesheet_for_user_date(request, user_date):
    try:
        with transaction.atomic():
            tslots = []
            # ----- COLLECT ALL PRODUCTION ENTRY SLOTS
            tsheetentries = (
                TimeSheetEntryProd.objects.select_related(
                    "employee_date_time_slot"
                )
                .filter(employee_date_time_slot__employeeDate__user_id = user_date.user.id)
                .filter(
                    employee_date_time_slot__employeeDate__date = user_date.date.strftime(
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
                .filter(employee_date_time_slot__employeeDate__user_id = user_date.user.id)
                .filter(
                    employee_date_time_slot__employeeDate__date = user_date.date.strftime(
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
                        employeeDate=user_date,
                        timeStart=OFFICE_START_TIME,
                        timeEnd=slots_sorted[0][0],
                    )
                    blank_time_slots.append(employee_date_time_slot)

                # COLLECT ALL INTERMEDIATE BLANK TIMESLOTS
                for slot_index in range(1, slot_count):
                    if (slots_sorted[slot_index][0] != slots_sorted[slot_index - 1][1]):
                        employee_date_time_slot = EmployeeDateTimeSlot.objects.create(
                            employeeDate=user_date,
                            timeStart=slots_sorted[slot_index - 1][1],
                            timeEnd=slots_sorted[slot_index][0],
                        )
                        blank_time_slots.append(employee_date_time_slot)

                # CHECK IF 8 HOURS TIMESHEET ENTRIES ARE THERE ELSE MARK REQUIRED SLOT FOR BLANK ENTRY
                if slots_sorted[-1][1] <  OFFICE_CLOSE_TIME:
                    employee_date_time_slot     = EmployeeDateTimeSlot.objects.create(
                                                        employeeDate    =user_date,
                                                        timeStart=slots_sorted[-1][1],
                                                        timeEnd=OFFICE_CLOSE_TIME,
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
                user_date.is_absent = True     
                user_date.save()       
            user_date.forceCommitted = True            
            user_date.save()       
    except Exception as e:
        # messages.info(request, 'Forced commit Failed for ' + user_date.user + ", " + user_date.date)
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


