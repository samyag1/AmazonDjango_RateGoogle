from django.http import Http404, HttpResponse
import datetime
from django.template import RequestContext
from django.shortcuts import render_to_response, render
import django
from django.utils import timezone
import json
from datetime import datetime, timedelta
import time
import random, string
from random import randint

from djangoProject import models
from djangoProject.settings import STATIC_URL
from djangoProject.models import Participant, Rating_Trial
import csv
import os
import json




##################################################
## Start a Task with  ##

# http://127.0.0.1:8000/instructions_GoogleFaces?MID=13231&assign_id=13231&hit_id=13231&ratingType=Basic&setType=Cropped


def test(request):

    firstOne = request.GET.get('firstOne')
    variables = {}    
    variables['instructions']="First there's: %s, then there's none" % (firstOne)
    return render_to_response('instructions.html',variables)


def instructionsGoogleFaces(request):

    # Get Amazon ID or Other ID from HTML request first time. (ex. A2GIYY77IUO78U)
    # if its not in the URL, get it from the session variable
    tempMID=request.GET.get('MID')
    if tempMID is not None:
       request.session['MID']=tempMID

    tempAID=request.GET.get('assign_id')
    if tempAID is not None:
       request.session['AID']=tempAID

    tempHID=request.GET.get('hit_id')
    if tempHID is not None:
       request.session['HID']=tempHID

    ratingType=request.GET.get('ratingType')
    if ratingType is not None:
       request.session['ratingType']=ratingType

    setType=request.GET.get('setType')
    if setType is not None:
       request.session['setType']=setType

    # if the participant doesn't already exist in the database, add them
    variables = {}    
    participant_exists = Participant.objects.filter(MID__exact=request.session['MID']).exists()
    if not participant_exists:
                
	# generate random completion code
        completion_code = ''.join([random.choice(string.ascii_letters + string.digits) for n in xrange(10)])

        # Sam - TODO
        # generate the randomized order for the current subject
        # for now just read in a csv file with the order
        stimOrder = generateStimOrder(setType)
        stimOrderString = ",".join(stimOrder)

	# generate new participant / save 
        curParticipant = Participant(MID=str(request.session['MID']), 
                                     AID=tempAID, 
                                     HID=tempHID, 
                                     start_date=datetime.now(), 
                                     start_time=time.mktime(datetime.now().timetuple()), 
                                     ratingType=ratingType, 
                                     setType=setType, 
                                     stimOrder=stimOrderString,
                                     numTrials=len(stimOrder), 
                                     curTrial=0, 
                                     completion_code=completion_code, 
                                     completed=False) # add new participant to RDS database
        curParticipant.save()

    # otherwise make sure that they are continuing the same task they already started,
    # as we are only allowing one worker per rating x set type
    else:
        # retrieve the current participant from the database
        curParticipant = list(Participant.objects.filter(MID=request.session['MID']))[0]

        # make sure they're doing the same rating and set task they've already started
        if ratingType != curParticipant.ratingType or setType != curParticipant.setType:
            variables["errorMessage"] = "You have already started another experiment with us and we currently only allow one experiment per worker. Please complete that other task."
            return render_to_response('errorPage.html',variables)
        
        # make sure this participant hasn't already finished
        if curParticipant.completed == True:
            variables["errorMessage"] = "You have already completed an experiment with us and we currently only allow one experiment per worker. Thank you for your interest."
            return render_to_response('errorPage.html',variables)
            
    # pass relevant parameters to the appropriate template
    # based on the rating type to be done and render it
    variables['instructions']=getFullInstructions(ratingType, setType)
    return render_to_response('instructions.html',variables)


########################################
########### Rating Page  ##############

def rateGoogleFaces(request):
    ## Get MTurk ID  based on Session Cookie, and get image ID to show
    # if they exist in the data base, grab their progress and completion code
    MTurkID = request.session['MID']
    curParticipant = list(Participant.objects.filter(MID=MTurkID))[0]

    # lookup the trial number in the database
    curTrial = curParticipant.curTrial
    nextTrial = int(request.GET.get('curTrialNo'))

    # when coming from the instructions page I set the current trial to -1
    # so look up the current trial in the database
    if nextTrial == -1:
        nextTrial = curParticipant.curTrial
    
    # if this is being called because the user refreshed,then redisplay the current page.
    variables = {}
    incrementStim = False
    # if the next trial has been increment, then the user has selected a valid rating,
    # so store that rating
    if curTrial != nextTrial: 
        rating = request.GET.get('rating')
        incrementStim = True

        # and add the current trial's value to the database
        T = Rating_Trial(trialstart=int(float(request.GET.get('trialStart'))),
                         start_date=datetime.now(),
                         rating = rating,
                         trialNumber = curTrial,
                         stimFilename=request.GET.get('stimFilename'),
                         setType=curParticipant.setType,
                         ratingType=curParticipant.ratingType,
                         MID=MTurkID,
                         AID=curParticipant.AID,
                         HID=curParticipant.HID)
        T.save()

    # get the number of trials this participant has to do
    numTrials = curParticipant.numTrials

    # if this is the last trial, then show the experiment complete page with the completion ID
    if curTrial == numTrials:

        # update the database saying the current subject has completed the rating
        curParticipant.completed = True 
	curParticipant.save()

        # store the completion code to be displayed on the rating complete page
        variables["completionCode"] = curParticipant.completion_code

        # show the rating complete page
        return(render_to_response('ratingComplete.html',variables))
    else:
        # don't increment the trial counter if this is just a refresh or coming from instructions
        if curTrial != nextTrial:
            # update the trial counter
            curParticipant.curTrial=nextTrial 
	    curParticipant.save()

        # lookup the next stimID for the current subject
        stimOrder = curParticipant.stimOrder.split(',')
        nextStimFilename = stimOrder[nextTrial]
        variables['stimFilename'] = os.path.join(STATIC_URL, 'images', nextStimFilename)

        # store the current and next trial number in the variables stored in the form
        # they start off the same, and javascript increments the next counter once the
        # user rates the image and clicks next
        variables['curTrialNo'] = nextTrial

        # store the current time as the start time of the trial - it's good enough, though client side javascript would be better
        variables["trialStart"] = time.mktime(datetime.now().timetuple())

        # determine the instructions to display below the image
        variables["instructions"] = getRatingInstructions(curParticipant.ratingType, curParticipant.setType)
        
        # display the next rating page
        if curParticipant.ratingType == 'Basic':
            ratingsFilename = 'rateGoogleFaces_Basic.html'
        elif curParticipant.ratingType == 'Extended':
            ratingsFilename = 'rateGoogleFaces_Extended.html'
        elif curParticipant.ratingType == 'Valence':
            variables['minScaleTag'] = 'Negative'
            variables['middleScaleTag'] = 'Neutral'
            variables['maxScaleTag'] = 'Positive'
            ratingsFilename = 'rateGoogleFaces_Scale.html'
        elif curParticipant.ratingType == 'Arousal':
            variables['minScaleTag'] = 'Not at all'
            variables['middleScaleTag'] = ''
            variables['maxScaleTag'] = 'Extremely'
            ratingsFilename = 'rateGoogleFaces_Scale.html'
        elif curParticipant.ratingType == 'Dominance':
            variables['minScaleTag'] = 'Submissive'
            variables['middleScaleTag'] = ''
            variables['maxScaleTag'] = 'Dominant'
            ratingsFilename = 'rateGoogleFaces_Scale.html'
        elif curParticipant.ratingType == 'Attractiveness':
            variables['minScaleTag'] = 'Unattractive'
            variables['middleScaleTag'] = ''
            variables['maxScaleTag'] = 'Attractive'
            ratingsFilename = 'rateGoogleFaces_Scale.html'
        elif curParticipant.ratingType == 'Trustworthiness':
            variables['minScaleTag'] = 'Not-trustworthy'
            variables['middleScaleTag'] = ''
            variables['maxScaleTag'] = 'Trustworthy'
            ratingsFilename = 'rateGoogleFaces_Scale.html'
        elif curParticipant.ratingType == 'Approachable': # SAM TODO - I think this is the same as trustworthiness, look at literature.
            variables['minScaleTag'] = 'Not-approachable'
            variables['middleScaleTag'] = ''
            variables['maxScaleTag'] = 'Approachable'
            ratingsFilename = 'rateGoogleFaces_Scale.html'
        else:
            raise ValueError('Invalid rating type')

        return(render_to_response(ratingsFilename,variables))

########################################
############## Helpers ####################

def generateStimOrder(setType):

    if setType == 'Cropped':
        filename = 'CroppedFileOrder.csv'
    elif setType == 'Uncropped':
        filename = 'UncroppedFileOrder.csv'
    elif setType == 'Whole':
        filename = 'WholeImageFileOrder.csv'
    setOrder = []
    with open('djangoProject/stimOrder/'+filename, 'rU') as f:
        reader = csv.reader(f)
        for row in reader:
            setOrder.append(row[0])

    return setOrder

def getFullInstructions(ratingType, setType):

    # determine what to is to be rated based on the set that is being used
    if setType == 'Cropped':
        facesString = "face";
        isString = 'it is'
    elif setType == 'Uncropped':
        facesString = "face in the red box";
        isString = 'it is'
    if setType == 'Whole':
        facesString = "face(s)";
        isString = 'they are'

    # determine the task based on the ratings type
    if ratingType == 'Basic' or ratingType == 'Extended':
        taskInstructions = 'to select the radio button with the emotional expression which best describes the expression of the %s. You may find that none of these terms perfectly describes the expression, in which case just pick the expression which is closest. ' % (facesString)
    else:
        # figure out what the labels for the buttons of the scale should say.
        if ratingType == 'Valence':
            leftLabel = '\'very negative\''
            middleString = 'the middle (4th) radio button \'neutral\', '
            rightLabel = '\'very positive\''
        elif ratingType == 'Arousal':
            leftLabel = '\'not at all emotionally intense\''
            middleString = ''
            rightLabel = '\'extremely emotionally intense\''
        elif ratingType == 'Dominance':
            leftLabel = '\'very submissive\''
            middleString = ''
            rightLabel = '\'very dominant\''
            
        taskInstructions = 'to judge the expression of the %s for how negative or positive %s. \n\n You will see a row of seven radio buttons, where the leftmost radio button represents %s, %sand the rightmost radio button %s. Simply select the radio button that best describes your judgment.' % (facesString, isString, leftLabel, middleString, rightLabel)

    # assemble the instructions
    ratingsInstructions = 'In this experiment you will see a series of faces.  \n\n Your task is %s \n\n These images are shown at the size they were presented in an another study. Some of them may be very small. If you feel you can\'t make out the expression, just do your best to pick the most appropriate selection. Once you have finished the task, click the continue button to move on to the next image. You may see duplicate images throughout the experiment. Just try to be as consistent as you can in your judgements. \n\nComplete each judgement as quickly as you can. We want your first impression, so don\'t overthink it. But also don\'t rush so you make mistakes and say something you didn\'t mean. This website will remember your progress, so if you need to take a break, simply close this browser and when you are ready to continue click the link in the HIT page on Mechanical Turk. You have a maximum of 24 hours to complete the task. \n\nPlease press the continue button at the bottom of this screen when you are ready to continue...' % (taskInstructions)
    
    return ratingsInstructions

def getRatingInstructions(ratingType, setType):

    if ratingType == 'Basic':
        ratingsInstructions = 'Judge which emotional term best describes the expression of the %s in this image using the radio buttons below.%s'
    elif ratingType == 'Extended':
        ratingsInstructions = 'Judge which emotional term best describes the expression of the %s in this image using the radio buttons below.%s'
    elif ratingType == 'Valence':
        ratingsInstructions = 'Judge how negative or positive the expression of the %s in this image %s using the radio buttons below.%s'
    elif ratingType == 'Arousal':
        ratingsInstructions = 'Judge how emotionaly intense the expression of the %s in this image %s using the radio buttons below.%s'
    elif ratingType == 'Dominance':
        ratingsInstructions = 'Judge how submissive or dominant the expression of the %s in this image %s using the radio buttons below.%s'
    else:
        raise ValueError('Invalid rating type')

    if setType == 'Cropped':
        facesString = "face"
        verbString = "is"
        multiInstruction = ''
    elif setType == 'Uncropped':
        facesString = "face in the red box"
        verbString = "is"
        multiInstruction = ''
    elif setType == 'Whole':
        facesString = "face(s)"
        verbString = "are"
        multiInstruction = ' If there is more than one face, give your overall impression.'

    if ratingType in ['Basic', 'Extended']:
        return ratingsInstructions % (facesString, multiInstruction)
    else:
        return ratingsInstructions % (facesString, verbString, multiInstruction)

########################################
#### CHECKING COMPLETION from AMT ######

# not working yet #

def json_response(func):
    """
    A decorator thats takes a view response and turns it
    into json. If a callback is added through GET or POST
    the response is JSONP. Apparently, you can't just return JSON object from a request. A jsonp which allows non-local requests. (Browsers prevent javascript from querying offsite). you need to return a function wrapper.
    """
    def decorator(request, *args, **kwargs):
        objects = func(request, *args, **kwargs)
        if isinstance(objects, HttpResponse):
            return objects
        try:
            data = json.dumps(objects)
            if request.GET.has_key('callback'):
                # a jsonp response!
                data = '%s(%s);' % (request.GET['callback'], data)
                return HttpResponse(data, "text/javascript")
        except:
            data = json.dumps(str(objects))
        return HttpResponse(data, "application/json")
    return decorator


@json_response
def completed(request):
    ## Get MTurk ID  based on Session Cookie, and get image ID to show
    # if they exist in the data base, grab their progress and completion code
    MTurkID = request.GET.get('MID')
    curParticipant = list(Participant.objects.filter(MID=MTurkID))[0]

    # get the completion code and hit ID
    completionCode = request.GET.get('completion_code')
    hitID = request.GET.get('hit_id')    

    # if this is a valid MTurk ID, then see if they've completed the HIT or not
    if curParticipant:
        completed = 'true' if curParticipant.completion_code == completionCode and curParticipant.HID == hitID and  curParticipant.completed == 1 else 'false'
    # otherwise it isn't a valid MTurk ID, so return false
    else:
        completed = 'false'

    return {'completed':completed}
