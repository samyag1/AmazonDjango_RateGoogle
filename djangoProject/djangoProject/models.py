from django.db import models
from django.db.models import DateTimeField, CharField, IntegerField, BigIntegerField, TextField

class Participant(models.Model):

    MID =CharField(max_length=200, primary_key=True)
    AID =CharField(max_length=200,default=None)
    HID =CharField(max_length=200,default=None)
    start_date = DateTimeField('start date')
    start_time = BigIntegerField() # in seconds

    completion_code = CharField(max_length=200)
    completed=IntegerField(default=0)
    curTrial=IntegerField(default=0)
    numTrials=IntegerField(default=0)

    ratingType = CharField(default='None',max_length=500)
    setType = CharField(default='None',max_length=500)

    stimOrder = TextField()

class Rating_Trial(models.Model):

    MID = CharField(max_length=200)
    AID =CharField(max_length=200,default=None)
    HID =CharField(max_length=200,default=None)

    # Timing Stuff
    start_date = DateTimeField('start date')
    trialstart  = BigIntegerField()

    ratingType = CharField(default='None',max_length=500)
    setType = CharField(default='None',max_length=500)

    trialNumber = IntegerField(default=-1)

    rating = CharField(default="",max_length=200)
    stimFilename = CharField(default="",max_length=200)

from django.contrib import admin

admin.site.register(Participant)
admin.site.register(Rating_Trial)
