from django.contrib import messages
from django.shortcuts import render, redirect
from django.db.transaction import commit, rollback, set_autocommit
from django.db import transaction
import json
import logging

from inprogress.loggerConfig import configure_logger
from inprogress.models import Machine, MachineSetup, Setup

#------------------------------------------------------------------
#        MACHINES 
#------------------------------------------------------------------
configure_logger()
logger = logging.getLogger(__name__)
"""
METHOD CALLED WHEN ADMIN CLICKS "MACHINES" LINK. 
RETURNS PARTS LIST
"""
def machines(request):
    machineQuerySet = Machine.objects.filter(is_active = True).order_by('id_code')
    machinesList = {}

    for machine in machineQuerySet:
        machineSetups = MachineSetup.objects.select_related('setup').filter(machine_id = machine.id)
        setupsList = []
        for machineSetup in machineSetups:
            mSetup = {
                "id_code": machineSetup.setup.id_code,
                "name": machineSetup.setup.name,
                "desc": machineSetup.setup.desc,
                "cycle_time": machineSetup.cycle_time,
            }
            setupsList.append(mSetup)

        mc = {
            "id_code": machine.id_code,
            "name": machine.name,
            "desc": machine.desc,
            "setups": setupsList
        }
        machinesList[mc['id_code']] =  mc
    machinesListJson = json.dumps(machinesList)
    #------------- GENERATE TOTAL OPERATION LIST AS JSON -----------
    totalSetupList = {}
    setupQuerySet = Setup.objects.filter(is_active = True)
    for totSetups in setupQuerySet:
        setupObject = {
                "id_code": totSetups.id_code,
                "name": totSetups.name,
                "desc": totSetups.desc
        }
        totalSetupList [totSetups.id_code] = setupObject
    totalSetupListJson = json.dumps(totalSetupList)
    return render(request, 'machine/machines.html', 
                            {'machines': machineQuerySet, 
                            'machinesListJson': machinesListJson,
                            'totalSetupListJson': totalSetupListJson
                            })

def processMachine(request):
    mode = request.POST['functionMode']
    returnPage = 'machines'
    if mode == "CANCEL":
        return redirect(returnPage)

    #------------- GENERATE TOTAL OPERATION LIST AS JSON -----------
    totalSetupsList = []
    setupQuerySet = Setup.objects.filter(is_active = True)
    for totSetups in setupQuerySet:
        opObject = {
                "id_code": totSetups.id_code,
                "name": totSetups.name,
                "desc": totSetups.desc,
        }
        totalSetupsList.append(opObject)
    totalSetupsListJson = json.dumps(totalSetupsList)

    if mode == 'ADD':
        return render(request, 'machine/addMachine.html', {'allSetups':totalSetupsListJson})

    elif mode == 'EDIT':
        machine = Machine.objects.get(id_code = request.POST['selectedMachine'])
        setupsValues = MachineSetup.objects.select_related('setup').filter(machine_id = machine.id)
        setups = []
        for su in setupsValues:
            setups.append(
                {
                    'name' : su.setup.name,
                    'cycle_time': su.cycle_time
                }
            )
        setupsJSON = json.dumps(setups)    
        return render(request, 'machine/editMachine.html', 
                                {
                                    'allSetupsJSON':totalSetupsListJson, 
                                    'selectedMachine': machine, 
                                    'setupsJSON': setupsJSON
                                })

    elif mode == 'DELETE':
        deleteMachine(request)
    elif mode == "ADDED":
        addNewMachine(request)
    elif mode == "EDITED":
        updateMachineDetails(request)     

    return redirect(returnPage)

def addNewMachine(request):
    log_message = ''
    try:
        machine_code = request.POST['mcode']
        machine_name = request.POST['mname']
        machine_desc = request.POST['mdesc']

        setupSequenceJSON = request.POST['setUpSequence']
        setupSequence = json.loads(setupSequenceJSON)
        if Machine.objects.filter(id_code = machine_code).exists():
            messages.info(request, 'Machine code already exists')
            # return redirect('machines')
        else:
            with transaction.atomic():
                machine = Machine.objects.create(id_code = machine_code, 
                                            name = machine_name, 
                                            desc = machine_desc)
                machine.save()
                for setup in setupSequence:
                    setupToBeAdded = Setup.objects.get(name = setup['setup'])
                    machineSetup = MachineSetup.objects.create(machine_id = machine.id,
                                                                setup_id = setupToBeAdded.id, cycle_time = setup['cycle_time'])
                    machineSetup.save()
            log_message = 'Machine ' + str(machine.id) + ' added'
        logger.info(log_message)
    except Exception as e:
        messages.info(request, 'New-Machine Failed')
        log_message = 'New-Machine Failed:' + str(e)
        logger.debug(log_message)

        

def updateMachineDetails(request):
    log_message = ''
    try:
        machine_code = request.POST['mcode']
        machine_name = request.POST['mname']
        machine_desc = request.POST['mdesc']
        setupSequenceJSON = request.POST['setUpSequence']
        setupSequences = json.loads(setupSequenceJSON)   # SETUP SEQUENCE TO BE SET

        desiredSetupsAsSet = set()      # Set contains values to be set 
        for setupSequence in setupSequences:
            desiredSetupsAsSet.add(SetupEntry(setupSequence['setup'], setupSequence['cycle_time']))

        with transaction.atomic():
            machine = Machine.objects.get(id_code = machine_code)
            machine.name = machine_name
            machine.desc = machine_desc
            machine.save()

            machineSetups = MachineSetup.objects.filter(machine_id = machine.id)
            existingSetupsAsSet = set()
            for machineSetup in machineSetups:
                existingSetupsAsSet.add(SetupEntry(machineSetup.setup.name, machineSetup.cycle_time))
            setupsToBeRemoved = existingSetupsAsSet.difference(desiredSetupsAsSet)
            setupsToBeAdded = desiredSetupsAsSet.difference(existingSetupsAsSet)
            setupsToBeEdited = existingSetupsAsSet.intersection(desiredSetupsAsSet)

            # REMOVE REQUIRED SETUP ENTRIES
            for setupToBeRemoved in setupsToBeRemoved:
                removeMachineSetup = MachineSetup.objects.filter(machine_id = machine.id, setup__name = setupToBeRemoved.setup_name)
                removeMachineSetup.delete()

            # ADD REQUIRED SETUP ENTRIES
            for setupToBeAdded in setupsToBeAdded:
                reqdMachineSetup = MachineSetup.objects.create(machine_id = machine.id,                
                                                setup_id = Setup.objects.get(name = setupToBeAdded.setup_name).id,
                                                cycle_time = setupToBeAdded.cycle_time
                                            )
                reqdMachineSetup.save()

            # UPDATE CYCLE_TIME FOR REST OF THE SETUPS
            for setupToBeEdited in setupsToBeEdited:
                updateMachineSetup = MachineSetup.objects.filter(machine_id = machine.id, setup__name = setupToBeEdited.setup_name)[0]
                if (updateMachineSetup.cycle_time != setupToBeEdited.cycle_time):
                    updateMachineSetup.cycle_time = setupToBeEdited.cycle_time
                    updateMachineSetup.save()
            log_message = 'Machine updated'
        logger.info(log_message)
    except Exception as e:
        messages.info(request, 'Upate-Machine Failed')
        logger.debug('Upate-Machine Failed')

    # return redirect('machines')

def deleteMachine(request):
    log_message = ''
    try:
        with transaction.atomic():
            machine = Machine.objects.get(id_code = request.POST['selectedMachine'])
            machineSetups = MachineSetup.objects.filter(machine_id = machine.id)

            # UPDATE EXISTING LENGTH
            for machineSetup in machineSetups:
                machineSetup.is_active = False
                machineSetup.save()

            if machine is not None:
                machine.is_active = False
                machine.save()
        logger.info('Machine deleted')
    except  Exception as e:
        messages.info(request, 'Delete-Machine Failed')
        logger.debug('Delete-Machine Failed')

    # return redirect('machines')

class SetupEntry:
    def __init__(self, setup_name, cycle_time):
        self.setup_name = setup_name
        self.cycle_time = cycle_time
    
    def toJson(self):
        return json.dumps(self, default=lambda o: o.__dict__)

    def __hash__(self): 
        return hash(self.setup_name)

    def __eq__(self, other): 
        if other is None:
            return False
        if not isinstance(other, SetupEntry):
            # don't attempt to compare against unrelated types
            return NotImplemented
        return self.setup_name == other.setup_name

    def __repr__(self):  
        return "[" + str(self.setup_name) + ', ' + str(self.cycle_time) + "]" 

    def __str__(self):
        return "[" + str(self.setup_name) + ', ' + str(self.cycle_time) + "]" 

