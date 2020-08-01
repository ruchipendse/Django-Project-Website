from django.contrib import messages
from django.shortcuts import render, redirect
from django.db import transaction
import json
import logging

from inprogress.loggerConfig import configure_logger
from inprogress.models import Part, PartSetupSequence, Setup

configure_logger()
logger = logging.getLogger(__name__)

#------------------------------------------------------------------
#        PARTS 
#------------------------------------------------------------------

"""
METHOD CALLED WHEN ADMIN CLICKS "PARTS" LINK. 
RETURNS PARTS LIST
"""

def parts(request):
    partQuerySet = Part.objects.filter(is_active = True).order_by('id_code')
    partsList = {}

    for part in partQuerySet:
        partSetupSequences = PartSetupSequence.objects.select_related('setup').filter(part_id = part.id).order_by('sequence')
        setupsList = {}
        for setupSeq in partSetupSequences:
            pSetupSeq = {
                "id_code": setupSeq.setup.id_code,
                "name": setupSeq.setup.name,
                "desc": setupSeq.setup.desc,
                "sequence": setupSeq.sequence,
            }
            setupsList [pSetupSeq['sequence']] = pSetupSeq
        pt = {
            "id_code": part.id_code,
            "name": part.name,
            "desc": part.desc,
            "setups": setupsList
        }
        partsList[pt['id_code']] =  pt
    partsListJson = json.dumps(partsList)
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
    return render(request, 'part/parts.html', 
                            {'parts': partQuerySet, 
                            'partsListJson': partsListJson,
                            'totalSetupListJson': totalSetupListJson
                            })

def processPart(request):
    mode = request.POST['functionMode']
    returnPage = 'parts'
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
        return render(request, 'part/addPart.html', {'allSetups':totalSetupsListJson})

    elif mode == 'EDIT':
        part = Part.objects.get(id_code = request.POST['selectedPart'])
        setupsValues = PartSetupSequence.objects.select_related('setup').filter(part_id = part.id).order_by('sequence')
        setups = []
        for su in setupsValues:
            setups.append(su.setup.name)
        setupsJSON = json.dumps(setups)    
        return render(request, 'part/editPart.html', {'allSetups':totalSetupsListJson, 
                                                'selectedPart': part, 
                                                'setupSequenceJSON': setupsJSON})

    elif mode == 'DELETE':
        # delete part
        deletePart(request)
    elif mode == "ADDED":
        addNewPart(request)
    elif mode == "EDITED":
        updatePartDetails(request)     

    return redirect(returnPage)

def addNewPart(request):
    try:
        part_code = request.POST['pcode']
        part_name = request.POST['pname']
        part_desc = request.POST['pdesc']

        setupSequenceJSON = request.POST['setUpSequence']
        setupSequence = json.loads(setupSequenceJSON)
        if Part.objects.filter(id_code = part_code).exists():
            messages.info(request, 'Part code already exists')
            logger.debug('Part code already exists')
            # return redirect('parts')
        else:
            with transaction.atomic():
                part = Part.objects.create(id_code = part_code, 
                                            name = part_name, 
                                            desc = part_desc)
                for index, op in enumerate(setupSequence):
                    opToBeAdded = Setup.objects.get(name = op)

                    partSetupSeq = PartSetupSequence.objects.create(part_id = part.id,
                                                            setup_id = opToBeAdded.id,
                                                            sequence = index)
                    partSetupSeq.save()

                part.save()
            logger.info('Part added')
    except Exception as e:
        messages.info(request, 'Add-Part Failed')
        logger.debug('Add-Part failed. Reason: ' + str(e))
                
    # return redirect('parts')

def updatePartDetails(request):
    try:
        part_code = request.POST['pcode']
        part_name = request.POST['pname']
        part_desc = request.POST['pdesc']
        setupSequenceJSON = request.POST['setUpSequence']
        setupSequence = json.loads(setupSequenceJSON)   # SETUP SEQUENCE TO BE SET

        with transaction.atomic():
            part = Part.objects.get(id_code = part_code)
            part.name = part_name
            part.desc = part_desc
            part.save()
            partSetupSequences = PartSetupSequence.objects.filter(part_id = part.id).order_by('sequence')
            srcLen = len(setupSequence)
            dstLen = partSetupSequences.count()

            if srcLen > 0:
                if dstLen > 0:
                    if dstLen < srcLen: # FEW OPERATIONS HAVE BEEN ADDED
                        # UPDATE EXISTING LENGTH
                        for index, partOpSequence in enumerate(partSetupSequences):
                            if (partOpSequence.setup_id != Setup.objects.get(name = setupSequence[index]).id):
                                partOpSequence.setup_id = Setup.objects.get(name = setupSequence[index]).id
                                partOpSequence.save()
                        # ADD EXTRAS
                        for furtherindex, extra in enumerate(setupSequence[index + 1:], start = index + 1):
                            PartSetupSequence.objects.create(part_id = part.id,
                                                                        setup_id = Setup.objects.get(name = setupSequence[furtherindex]).id,
                                                                        sequence = furtherindex).save()

                    elif dstLen > srcLen:   # OPERATIONS HAVE BEEN REMOVED
                        # REMOVE EXTRA FROM DST
                        tobeRemoved = partSetupSequences[len(setupSequence):]
                        for tobe in tobeRemoved:
                            tobe.delete()

                        # UPDATE EXISTING LENGTH
                        for index, partOpSequence in enumerate(partSetupSequences):
                            if (partOpSequence.setup_id != Setup.objects.get(name = setupSequence[index]).id):
                                partOpSequence.setup_id = Setup.objects.get(name = setupSequence[index]).id
                                partOpSequence.save()

                    else:
                        # UPDATE EXISTING LENGTH
                        for index, partOpSequence in enumerate(partSetupSequences):
                            if (partOpSequence.setup_id != Setup.objects.get(name = setupSequence[index]).id):
                                partOpSequence.setup_id = Setup.objects.get(name = setupSequence[index]).id
                                partOpSequence.save()

                else: # ALL OPERATIONS HAVE BEEN NEWLY ADDED
                    # ADD EXTRAS
                    for furtherindex, extra in enumerate(setupSequence):
                        PartSetupSequence.objects.create(part_id = part.id,
                                                                    setup_id = Setup.objects.get(name = setupSequence[furtherindex]).id,
                                                                    sequence = furtherindex).save()

            else:   # EITHER THERE ARE NO OPERATIONS OR ALL OPERATIONS REMOVED
                for toBeRemoved in partSetupSequences:
                    toBeRemoved.delete()
        logger.info('Part Updated')
    except Exception as e:
        messages.info(request, 'Update-Part Failed')
        logger.debug('Update-Part failed. Reason: ' + str(e))

    # return redirect('parts')

def deletePart(request):
    try:
        with transaction.atomic():
            part = Part.objects.get(id_code = request.POST['selectedPart'])
            partSetupSequences = PartSetupSequence.objects.filter(part_id = part.id).order_by('sequence')

            # UPDATE EXISTING LENGTH
            for partOpSequence in partSetupSequences:
                partOpSequence.is_active = False
                partOpSequence.save()

            if part is not None:
                part.is_active = False
                part.save()
        logger.info('Part Deleted')
    except Exception as e:
        messages.info(request, 'Delete-Part Failed')
        logger.debug('Delete-Part failed. Reason: ' + str(e))
    # return redirect('parts')

