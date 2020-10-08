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
    Employee, 
    OperatorSetup,
    NonProdTask,
     )

configure_logger()
logger = logging.getLogger(__name__)

def load(request):
    load_np_tasks(request)
    load_setups(request)
    load_machines(request)
    load_users(request)
    return redirect("home")

def load_np_tasks(request):
    with open('tmp/NPTasksList.csv', newline='') as csvfile:
        nptask_reader = csv.reader(csvfile, delimiter=',', quotechar='|')
        for row in nptask_reader:
            nptask_id = row[0]
            nptask_name = row[1]
            nptask_desc = row[2]

            try:
                with transaction.atomic():
                    new_nptask = NonProdTask.objects.filter(id_code = nptask_id)
                    if not new_nptask.exists():
                        new_nptask = NonProdTask.objects.create(id_code = nptask_id, 
                                                    name = nptask_name, 
                                                    desc = nptask_desc)
                        new_nptask.save()
                    else:
                        new_nptask = new_nptask[0]
            except Exception as e:
                messages.info(request, 'Upload Failed Id: ' + nptask_id)
                print('NPTask Failed Id: ' + nptask_id + 'name: ' + nptask_name, str(e))
                logger.debug('Upload-NPTask failed. Reason: ' + str(e))

def load_setups(request):
    # THIS PART LOADS PARTS AND SETUPS TOGETHER DUE TO THEIR DEPENDENCY
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
                messages.info(request, 'Upload Failed Id: ' + part_id)
                print('Part Failed Id: ' + part_id + 'name: ' + part_name, str(e))
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

def load_users(request):
    with open('tmp/OperatorsList.csv', newline='') as csvfile:
        operator_reader = csv.reader(csvfile, delimiter=',', quotechar='|')
        for row in operator_reader:
            operator_firstname = row[0]
            operator_lastname = row[1]
            username = operator_firstname.lower() + "." + operator_lastname.lower()
            while User.objects.filter(username = username).exists():
                username = username + "1"

            new_setups = []
            for setup_id in row[2:]:
                setups = Setup.objects.filter(id_code = setup_id)
                if setups.count() > 0:
                    setup = setups[0]
                else:
                    pass
                    setup = None
                    raise Exception("Setup not found: id [" + setup_id + "]")                            
                new_setups.append(setup)

            try:
                with transaction.atomic():
                    user = User.objects.create_user(username = username, 
                                                password = "electra1234", 
                                                email = "abc@nigasavi.com", 
                                                first_name = operator_firstname, 
                                                last_name = operator_lastname,
                                                is_superuser = False,
                                                is_staff = False
                                                )
                    newEmployee = Employee.objects.create(user = user)
                    newEmployee.save()
                    for new_setup in new_setups:
                        operator_setups = OperatorSetup.objects.filter(operator = newEmployee, setup = new_setup)
                        if operator_setups.count() > 0:
                            operator_setup = operator_setups[0]
                        else:
                            operator_setup = OperatorSetup.objects.create(
                                                    operator         = newEmployee,
                                                    setup           = new_setup,
                            )
                    operator_setup.save()
                    logger.info('User added: ' + user.username)
                        
            except Exception as e:
                messages.info(request, 'Upload-User ['+ username +'] Failed', str(e))
                logger.debug('Upload-User ['+ username +'] failed. Reason: ' + str(e))

