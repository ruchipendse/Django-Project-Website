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
import csv

from inprogress.loggerConfig import configure_logger

from inprogress.models import (
    Part,
    PartSetupSequence,
    #  EmployeeDate, 
    #  EmployeeDateTimeSlot, 
    #  TimeSheetEntryProd, 
    #  TimeSheetEntryNonProd, 
    #  NonProdTask,
    #  Employee
     )

configure_logger()
logger = logging.getLogger(__name__)

def load(request):
    load_setups(request)
    return redirect("home")

def load_setups(request):
# TODO: THIS CODE IS NOT WORKING

    with open('tmp/PartsList.csv', newline='') as csvfile:
        part_reader = csv.reader(csvfile, delimiter=',', quotechar='|')
        for row in part_reader:
            part_id = row[0]
            part_name = row[1]
            part_desc = row[1]
            setups = []

            try:
                with transaction.atomic():
                    new_part = Part.objects.filter(id_code = row[0])
                    if not new_part.exists():
                        new_part = Part.objects.create(id_code = row[0], 
                                                    name = row[1], 
                                                    desc = row[1])
                        new_part.save()
                    else:
                        new_part = new_part[0]
                    for index, setup_name in enumerate( row[2:]):
                        setup_id = part_id + '_' +  str(index).zfill(2)

                        new_setup = Setup.objects.filter(id_code = setup_id)
                        if not new_setup.exists():
                            new_setup = Setup.objects.create(id_code = setup_id,
                                                    name = setup_name,
                                                    desc = setup_name
                                                )
                            new_setup.save()
                        else:
                            new_setup = new_setup[0]
                        part_setup = PartSetupSequence.objects.filter(part = new_part, setup = new_setup)
                        if not part_setup.exists():
                            part_setup = PartSetupSequence.objects.create(
                                                    part     = new_part,
                                                    setup   = new_setup,
                                                    sequence = index
                            )
                            part_setup.save()
                        else:
                            part_setup = part_setup[0]
                        
            except Exception as e:
                messages.info(request, 'Upload-Part Failed', str(e))
                logger.debug('Upload-Part failed. Reason: ' + str(e))

