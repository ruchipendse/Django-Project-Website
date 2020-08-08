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
    if (request.method == 'POST'):
        operation = request.POST['userOperation']
        if (operation == "UPDATE"):
            updateUserDetails(request)
        elif (operation == "NEW_USER"):
            addNewUser(request)
        else:
            print ("------------ ERROR")
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

    return render(request, 'users.html', {
                                    'operators'         : operatorQuerySet,
                                    'operatorsListJson' : operatorsListJson,
                                    'allSetupsListJson'         : allSetupsListJson
                                    })

def updateUserDetails(request):
    try:
        f_name = request.POST['firstName']
        l_name = request.POST['lastName']
        uname = request.POST['userName']
        em = request.POST['email']
        pword = request.POST['pword']
        cpword = request.POST['rpword']
        setupString = request.POST['setupSelection']

        with transaction.atomic():
            operator = Employee.objects.prefetch_related('setups').get(user__username = uname)
            user = operator.user
            if user is not None:
                if (user.first_name != f_name):
                    user.first_name = f_name
                if (user.last_name != l_name):
                    user.last_name = l_name
                if (user.username != uname):
                    user.username = uname
                if (user.email != em):
                    user.email = em

                if (pword != "" and pword == cpword):
                    user.set_password(pword)

                setupSelectionParts = setupString.split(";")
                # rightSideSetups = (setupSelectionParts[1][:-1]).split(",")
                rightPart = setupSelectionParts[1][:-1]
                rightSideSetups = set([])
                if len(rightPart) > 0:
                    rightSideSetups = set(rightPart.split(","))

                setupsForOperator =  operator.setups.values()
                existingOperatorSetups = set([])
                for setup in setupsForOperator:
                    existingOperatorSetups.add(setup['name'])
                setupsToBeAdded = set(rightSideSetups) - existingOperatorSetups
                setupsToBeRemoved = existingOperatorSetups - set(rightSideSetups)

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
        
                operator.save()
                logger.info('User saved')
            else:
                messages.info(request, 'User not found')
                logger.debug('User not found')
    except Exception as e:
        messages.info(request, 'Undate-User Failed')
        logger.debug('Undate-User Failed. reason: ' + str(e))

    return redirect('users')

def addNewUser(request):
    try:
        f_name = request.POST['firstName']
        l_name = request.POST['lastName']
        uname = request.POST['userName']
        em = request.POST['email']
        pword = request.POST['pword']
        cpword = request.POST['rpword']
        setupString = request.POST['setupSelection']

        if (pword == cpword):
            with transaction.atomic():
                if User.objects.filter(username = uname).exists():
                    messages.info(request, 'User name taken')
                    return redirect('users')
                elif User.objects.filter(email = em).exists():
                    messages.info(request, 'email taken')
                    return redirect('users')
                else:
                    user = User.objects.create_user(username = uname, 
                                                password = pword, 
                                                email = em, 
                                                first_name = f_name, 
                                                last_name = l_name)
                    newEmployee = Employee.objects.create(user = user)

                    setupSelectionParts = setupString.split(";")
                    rightSideSetups = (setupSelectionParts[1][:-1]).split(",")

                    setupsToBeAdded = set(rightSideSetups)

                    if (len(setupsToBeAdded) > 0):
                        # ADD SETUPS
                        for setup in setupsToBeAdded:
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
    
    return redirect('users')

def deleteUser(request):
    try:
        with transaction.atomic():
            employee = Employee.objects.select_related('user').get(user__username = request.POST['selectedUser'])
            operatorSetups = OperatorSetup.objects.filter(operator__id = employee.id)
            for operatorSetup in operatorSetups:
                operatorSetup.is_active = False
                operatorSetup.save()
            employee.user.is_active = False 
            employee.is_active = False 
            employee.user.save()
            employee.save()
        logger.info('User deleted')
    except Exception as e:
        messages.info(request, 'Delete-User Failed')
        logger.debug('Delete-User Failed. reason: ' + str(e))

    return redirect('users')
