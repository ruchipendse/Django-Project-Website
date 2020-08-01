from django.contrib import messages
from django.shortcuts import render, redirect
from inprogress.models import Setup
import json

#------------------------------------------------------------------
#        SETUPS 
#------------------------------------------------------------------

"""
METHOD CALLED WHEN ADMIN CLICKS "SETUPS" LINK. 
RETURNS PARTS LIST
"""
def setups(request):
    #--- UPDATED METHOD ----
    setupQuerySet = Setup.objects.filter(is_active = True)
    setupsList = {}
    for setup in setupQuerySet:
        st = {
            "id_code": setup.id_code,
            "name": setup.name,
            "desc": setup.desc
        }
        setupsList[st['id_code']] =  st
    setupsListJson = json.dumps(setupsList)
    return render(request, 'setup/setups.html', 
                            {'setups': setupQuerySet, 
                            'setupsListJson': setupsListJson,
                            })

def processSetup(request):
    mode = request.POST['functionMode']
    returnPage = 'setups'
    if mode == "CANCEL":
        return redirect(returnPage)

    if mode == 'ADD':
        return render(request, 'setup/addSetup.html')

    elif mode == 'EDIT':
        setup = Setup.objects.get(id_code = request.POST['selectedSetup'])
        return render(request, 'setup/editSetup.html', {'selectedSetup': setup})

    elif mode == 'DELETE':
        deleteSetup(request)

    elif mode == "ADDED":
        addNewSetup(request)

    elif mode == "EDITED":
        updateSetupDetails(request)     

    return redirect(returnPage)

def updateSetupDetails(request):
    setup_code = request.POST['scode']
    setup_name = request.POST['sname']
    setup_desc = request.POST['sdesc']
    setup = Setup.objects.get(id_code = setup_code)
    setup.name = setup_name
    setup.desc = setup_desc
    setup.save()
    return redirect('setups')

def addNewSetup(request):
    setup_code = request.POST['scode']
    setup_name = request.POST['sname']
    setup_desc = request.POST['sdesc']

    if Setup.objects.filter(id_code = setup_code).exists():
        messages.info(request, 'Setup code already exists')
        return redirect('setups')
    else:
        try:
            setup = Setup.objects.create(id_code = setup_code, 
                                        name = setup_name, 
                                        desc = setup_desc)
            setup.save()
                
        except Exception as e:
            print ('--Exception while creating Setup ---', e)
    return redirect('setups')

def editSetup(request):
    return render(request, 'setup/editSetup.html')

def deleteSetup(request):
    setup = Setup.objects.get(id_code = request.POST['selectedSetup'])

    if setup is not None:
        setup.is_active = False
        setup.save()
    return redirect('setups')
