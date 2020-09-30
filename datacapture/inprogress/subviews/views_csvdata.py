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
    Machine,
    MachineSetup,
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
    load_machines(request)
    return redirect("home")

def load_setups(request):
    with open('tmp/PartsList.csv', newline='') as csvfile:
        part_reader = csv.reader(csvfile, delimiter=',', quotechar='|')
        for row in part_reader:
            part_id = row[0]
            part_name = row[1]
            part_desc = row[1]

            try:
                with transaction.atomic():
                    new_part = Part.objects.filter(id_code = part_id)
                    if not new_part.exists():
                        new_part = Part.objects.create(id_code = part_id, 
                                                    name = part_name, 
                                                    desc = part_desc)
                        new_part.save()
                    else:
                        new_part = new_part[0]
                    for index, setup_name in enumerate( row[2:]):
                        setup_id = part_id + '_' +  str(index).zfill(2)

                        new_setup = Setup.objects.filter(id_code = setup_id)
                        if not new_setup.exists():
                            new_setup = Setup.objects.create(id_code = setup_id,
                                                    name = part_name + "_" + setup_name,
                                                    desc = part_name + "_" + setup_name
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

def load_machines(request):
    with open('tmp/MachinesList.csv', newline='') as csvfile:
        machine_reader = csv.reader(csvfile, delimiter=',', quotechar='|')
        for row in machine_reader:
            machine_id = row[0]
            machine_name = row[1]
            machine_desc = row[1]

            try:
                with transaction.atomic():
                    new_machine = Machine.objects.filter(id_code = machine_id)
                    if not new_machine.exists():
                        new_machine = Machine.objects.create(id_code = machine_id, 
                                                    name = machine_name, 
                                                    desc = machine_desc)
                        new_machine.save()
                    else:
                        new_machine = new_machine[0]
                    for setup_str in row[2:]:
                        setup_id = setup_str.split('@')[0]
                        setup_cycle_time = setup_str.split('@')[1]
                        setups = Setup.objects.filter(id_code = setup_id)
                        if setups.count() > 0:
                            setup = setups[0]
                        else:
                            pass
                            setup = None
                            raise Exception("Setup not found: id [" + setup_id + "]")                            
                        machine_setup = MachineSetup.objects.filter(machine = new_machine, setup = setup)
                        if not machine_setup.exists():
                            machine_setup = MachineSetup.objects.create(
                                                    machine         = new_machine,
                                                    setup           = setup,
                                                    cycle_time      = int(float(setup_cycle_time))
                            )
                            machine_setup.save()
                        else:
                            machine_setup = machine_setup[0]
                        
            except Exception as e:
                messages.info(request, 'Upload-Machine Failed', str(e))
                logger.debug('Upload-Machine failed. Reason: ' + str(e))
