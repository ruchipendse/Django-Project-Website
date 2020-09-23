from django.contrib.auth.models import User, auth
from django.contrib import messages
from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.db import transaction
import json
import logging

from inprogress.loggerConfig import configure_logger
from inprogress.models import Machine, Employee, Setup, OperatorSetup

#--------------------- USERS ----------
configure_logger()
logger = logging.getLogger(__name__)

def users(request):
    operatorQuerySet = Employee.objects.prefetch_related('setups').filter(is_active = True)
    operatorsList = {}
    for operator in operatorQuerySet:
        setupsList = {}
        for setup in operator.setups.values():
            st = {
                "id_code": setup['id_code'],
                "name": setup['name'],
                "desc": setup['desc'],
            }
            setupsList [setup['id_code']] = st
        opObj = {
            "username"      : operator.user.username,
            "first_name"    : operator.user.first_name,
            "last_name"     : operator.user.last_name,
            "email"         : operator.user.email,
            "setups"        : setupsList
        }
        operatorsList[operator.user.username] = opObj
    operatorsListJson = json.dumps(operatorsList)

    allSetups    = {}
    for setup in  Setup.objects.all():
        st = {
            "id_code": setup.id_code,
            "name": setup.name,
            "desc": setup.desc,
        }
        allSetups[setup.id_code] = st
    allSetupsListJson = json.dumps(allSetups)

    return render(request, 'user/users.html', {
                                    'operators'         : operatorQuerySet,
                                    'operatorsListJson' : operatorsListJson,
                                    'allSetupsListJson'         : allSetupsListJson
                                    })

def processUser(request):
    mode = request.POST['functionMode']
    returnPage = 'users'
    if mode == "CANCEL":
        return redirect(returnPage)

    #------------- GENERATE TOTAL OPERATION LIST AS JSON -----------
    totalSetupsList = []
    setupQuerySet = Setup.objects.filter(is_active = True)
    for totSetups in setupQuerySet:
        opObject = {
                "id_code": totSetups.id_code,
                "name": totSetups.name,
                "desc": totSetups.desc
        }
        totalSetupsList.append(opObject)
    totalSetupsListJson = json.dumps(totalSetupsList)


    if mode == 'ADD':
        return render(request, 'user/addUser.html', {'allSetups':totalSetupsListJson})

    elif mode == 'EDIT':
        operator = Employee.objects.get(user__username = request.POST['selectedUser'])
        setupsValues = OperatorSetup.objects.select_related('setup').filter(operator__user__username = operator.user.username)
        setups = []
        for su in setupsValues:
            setups.append(su.setup.name)
        setupsJSON = json.dumps(setups)    
        return render(request, 'user/editUser.html', {'allSetups':totalSetupsListJson, 
                                                'selectedUser': operator.user, 
                                                'setupSequenceJSON': setupsJSON})

    elif mode == 'DELETE':
        deleteUser(request)
    elif mode == "ADDED":
        addNewUser(request)
    elif mode == "EDITED":
        updateUserDetails(request)     

    return redirect(returnPage)


def addNewUser(request):
    try:
        firstname = request.POST['firstname']
        lastname = request.POST['lastname']
        username = request.POST['username']
        email = request.POST['email']
        password = request.POST['password']
        rpassword = request.POST['rpassword']
        setupSequenceJSON = request.POST['setUpSequence']
        setupSequence = json.loads(setupSequenceJSON)

        if (password == rpassword):
            with transaction.atomic():
                if User.objects.filter(username = username).exists():
                    messages.info(request, 'User name taken')
                    return redirect('users')
                elif User.objects.filter(email = email).exists():
                    messages.info(request, 'email taken')
                    return redirect('users')
                else:
                    user = User.objects.create_user(username = username, 
                                                password = password, 
                                                email = email, 
                                                first_name = firstname, 
                                                last_name = lastname,
                                                is_superuser = False,
                                                is_staff = False
                                                )
                    newEmployee = Employee.objects.create(user = user)

                    if (len(setupSequence) > 0):
                        # ADD SETUPS
                        for setup in setupSequence:
                            setupToBeAdded = Setup.objects.get(name = setup)
                            newEmployee.setups.add(setupToBeAdded)
                    newEmployee.save()
            logger.info('User added')
        else:
            messages.info(request, 'password does not match')
            logger.debug('password does not match ')
    except Exception as e:
        messages.info(request, 'Add-User Failed')
        logger.debug('Add-User Failed. reason: ' + str(e))

def updateUserDetails(request):
    try:
        firstname = request.POST['firstname']
        lastname = request.POST['lastname']
        username = request.POST['username']
        email = request.POST['email']
        password = request.POST['password']
        rpassword = request.POST['rpassword']
        setupSequenceJSON = request.POST['setUpSequence']
        setupSequence = json.loads(setupSequenceJSON)   # SETUP SEQUENCE TO BE SET

        with transaction.atomic():
            operator = Employee.objects.prefetch_related('setups').get(user__username = username)
            user = operator.user
            if user is not None:
                if (user.first_name != firstname):
                    user.first_name = firstname
                if (user.last_name != lastname):
                    user.last_name = lastname
                if (user.username != username):
                    user.username = username
                if (user.email != email):
                    user.email = email

                if (password != "" and password == rpassword):
                    user.set_password(password)

                setupsForOperator =  operator.setups.values()
                existingOperatorSetups = set([])
                for setup in setupsForOperator:
                    existingOperatorSetups.add(setup['name'])
                setupsToBeAdded = set(setupSequence) - existingOperatorSetups
                setupsToBeRemoved = existingOperatorSetups - set(setupSequence)
                if (len(setupsToBeAdded) > 0):
                    # ADD OPERATORS
                    for setupName in setupsToBeAdded:
                        setupToBeAdded = Setup.objects.get(name = setupName)
                        operator.setups.add(setupToBeAdded)

                if (len(setupsToBeRemoved) > 0):
                    # REMOVE OPERATORS
                    for setupName in setupsToBeRemoved:
                        setupToBeRemoved = Setup.objects.get(name = setupName)
                        operator.setups.remove(setupToBeRemoved)
        
                for su in operator.setups.values():
                    print ('Final Setup: ', su['name'])
                user.save()
                # operator.save()       # NOT SURE IF THIS IS REQUIRED
                logger.info('User ' + user.username+ ' saved')
            else:
                messages.info(request, 'User not found')
                logger.debug('User not found')
    except Exception as e:
        messages.info(request, 'Undate-User Failed')
        logger.debug('Undate-User Failed. reason: ' + str(e))
    return redirect('users')


def deleteUser(request):
    pass
    # try:
    #     with transaction.atomic():
    #         part = Part.objects.get(id_code = request.POST['selectedPart'])
    #         partSetupSequences = PartSetupSequence.objects.filter(part_id = part.id).order_by('sequence')

    #         # UPDATE EXISTING LENGTH
    #         for partOpSequence in partSetupSequences:
    #             partOpSequence.is_active = False
    #             partOpSequence.save()

    #         if part is not None:
    #             part.is_active = False
    #             part.save()
    #     logger.info('Part Deleted')
    # except Exception as e:
    #     messages.info(request, 'Delete-Part Failed')
    #     logger.debug('Delete-Part failed. Reason: ' + str(e))


# def deleteUser(request):
#     try:
#         with transaction.atomic():
#             employee = Employee.objects.select_related('user').get(user__username = request.POST['selectedUser'])
#             operatorSetups = OperatorSetup.objects.filter(operator__id = employee.id)
#             for operatorSetup in operatorSetups:
#                 operatorSetup.is_active = False
#                 operatorSetup.save()
#             employee.user.is_active = False 
#             employee.is_active = False 
#             employee.user.save()
#             employee.save()
#         logger.info('User deleted')
#     except Exception as e:
#         messages.info(request, 'Delete-User Failed')
#         logger.debug('Delete-User Failed. reason: ' + str(e))

#     return redirect('users')
