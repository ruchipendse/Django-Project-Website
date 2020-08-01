from django.contrib import messages
from django.shortcuts import render, redirect
from inprogress.models import NonProdTask
import json

#------------------------------------------------------------------
#        NON-PRODUCTION MASTER TASKS 
#------------------------------------------------------------------

"""
METHOD CALLED WHEN ADMIN CLICKS "SETUPS" LINK. 
RETURNS PARTS LIST
"""
def nonprodtasks(request):
    #--- UPDATED METHOD ----
    nonprodtaskQuerySet = NonProdTask.objects.filter(is_active = True)
    nonprodtasksList = {}
    for nonprodtask in nonprodtaskQuerySet:
        st = {
            "id_code": nonprodtask.id_code,
            "name": nonprodtask.name,
            "desc": nonprodtask.desc
        }
        nonprodtasksList[st['id_code']] =  st
    nonprodtasksListJson = json.dumps(nonprodtasksList)
    print ('\n--- nonprodtasksListJson --- \n', nonprodtasksListJson)
    return render(request, 'nonprodtask/nonprodtasks.html', 
                            {'nonprodtasks': nonprodtaskQuerySet, 
                            'nonprodtasksListJson': nonprodtasksListJson,
                            })

#TODO: nON pRODUCTION tASK FINCTIONALITY NOT WORKING
def processNonProdTask(request):
    mode = request.POST['functionMode']
    returnPage = 'nonprodtasks'
    if mode == "CANCEL":
        return redirect(returnPage)

    if mode == 'ADD':
        return render(request, 'nonprodtask/addNonProdTask.html')

    elif mode == 'EDIT':
        nonprodtask = NonProdTask.objects.get(id_code = request.POST['selectedNonProdTask'])
        return render(request, 'nonprodtask/editNonProdTask.html', {'selectedNonProdTask': nonprodtask})

    elif mode == 'DELETE':
        deleteNonProdTask(request)

    elif mode == "ADDED":
        addNewNonProdTask(request)

    elif mode == "EDITED":
        updateNonProdTaskDetails(request)     

    return redirect(returnPage)

def updateNonProdTaskDetails(request):
    nonprodtask_code = request.POST['scode']
    nonprodtask_name = request.POST['sname']
    nonprodtask_desc = request.POST['sdesc']
    nonprodtask = NonProdTask.objects.get(id_code = nonprodtask_code)
    nonprodtask.name = nonprodtask_name
    nonprodtask.desc = nonprodtask_desc
    nonprodtask.save()
    return redirect('nonprodtasks')

def addNewNonProdTask(request):
    nonprodtask_code = request.POST['scode']
    nonprodtask_name = request.POST['sname']
    nonprodtask_desc = request.POST['sdesc']

    if NonProdTask.objects.filter(id_code = nonprodtask_code).exists():
        messages.info(request, 'NonProdTask code already exists')
        return redirect('nonprodtasks')
    else:
        try:
            nonprodtask = NonProdTask.objects.create(id_code = nonprodtask_code, 
                                        name = nonprodtask_name, 
                                        desc = nonprodtask_desc)
            nonprodtask.save()
                
        except Exception as e:
            print ('--Exception while creating NonProdTask ---', e)
    return redirect('nonprodtasks')

def deleteNonProdTask(request):
    nonprodtask = NonProdTask.objects.get(id_code = request.POST['selectedNonProdTask'])

    if nonprodtask is not None:
        nonprodtask.is_active = False
        nonprodtask.save()
    return redirect('nonprodtasks')
