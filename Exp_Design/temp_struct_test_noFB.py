"""
generic task using psychopy
"""

from psychopy import visual, core, event, logging, data, misc, sound
import sys,os
import yaml
import numpy as np
import datetime
import json

try:
    from save_data_to_db import *
except:
    pass

def np_to_list(d):
    d_fixed={}
    for k in d.iterkeys():
        if isinstance(d[k],np.ndarray) and d[k].ndim==1:
            d_fixed[k]=[x for x in d[k]]
            print 'converting %s from np array to list'%k
        else:
            #print 'copying %s'%k
            d_fixed[k]=d[k]
    return d_fixed


class tempStructTest:
    """ class defining a psychological experiment
    """
    
    def __init__(self,config_file,subject_code,verbose=True, fullscreen = False, bot = None):
        
        self.taskname=[]
        self.subject_code=subject_code
        self.win=[]
        self.window_dims=[800,600]
        self.textStim=[]
        self.quit_key=[]
        self.trigger_key=[]
        self.stimulusInfo=[]
        self.loadedStimulusFile=[]
        self.startTime=[]
        self.stimulusDuration=[]
        self.FBDuration=[]
        self.responseWindow=[]
        self.alldata=[]
        self.timestamp=datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        self.trigger_times=[]
        self.config_file=config_file
        self.trialnum = 0
        self.track_response = []
        self.action_keys = []
        self.fullscreen = fullscreen
        self.bot = bot
        self.bot_on = False
        if self.bot:
            self.bot_on = True
        try:
            self.loadStimulusFileYAML(config_file)
        except:
            print 'cannot load config file'
            sys.exit()
                                                        
        self.logfilename='%s_%s_Test_log_%s.log'%(self.taskname,self.subject_code,self.timestamp)

    def toJSON(self):
        """ log the initial conditions for the task 
        """
        init_dict = {k:self.__dict__[k] for k in self.__dict__.iterkeys() if k not in ('stimulusInfo', 'alldata', 'bot')}
        return json.dumps(init_dict)
    
    def writeToLog(self,msg,loc = '../Data/'):
        f=open(str(loc) + self.logfilename,'a')
        f.write(msg)
        f.write('\n')
        f.close()
         
    def writeDataToCouchdb(self):
        data={}
        data['taskinfo']=self.taskinfo
        data['configfile']=self.config_file
        data['subcode']=self.subject_code
        data['timestamp']=self.timestamp
        data['taskdata']=self.alldata
        save_data_to_db(data,'psychtask')

    def setupWindow(self,fullscr=False):
        """ set up the main window
        """
        self.win = visual.Window(self.window_dims,allowGUI=True, fullscr=self.fullscreen, monitor='testMonitor', units='deg')
        self.win.setColor('black')
        self.win.flip()
        self.win.flip()
        

    def presentTextToWindow(self,text):
        """ present a text message to the screen
        return:  time of completion
        """
        
        if not self.textStim:
            self.textStim=visual.TextStim(self.win, text=text,font='BiauKai',
                                height=1,color=u'white', colorSpace=u'rgb',
                                opacity=1,depth=0.0,
                                alignHoriz='center',wrapWidth=50)
            self.textStim.setAutoDraw(True) #automatically draw every frame
        else:
            self.textStim.setText(text)
        self.win.flip()
        return core.getTime()

    def defineStims(self):
        self.stims = [visual.Circle(self.win, radius = 3, fillColor = 'red'),
                      visual.Circle(self.win, radius = 3, fillColor = 'blue')]
        self.fixation = visual.ShapeStim(self.win, vertices=((0, -0.5), (0, 0.5), (0,0),
                                                        (-0.5,0), (0.5, 0)),
                                        lineWidth=5,
                                        closeShape=False,
                                        lineColor='white'
                                        )
    def clearWindow(self):
        """ clear the main window
        """
        if self.textStim:
            self.textStim.setText('')
            self.win.flip()
        else:
            self.presentTextToWindow('')


    def waitForKeypress(self,key=[]):
        """ wait for a keypress and return the pressed key
        - this is primarily for waiting to start a task
        - use getResponse to get responses on a task
        """

        start=False
        event.clearEvents()
        while start==False:
            key_response=event.getKeys()
            if len(key_response)>0:
                if key:
                    if key in key_response or self.quit_key in key_response:
                        start=True
                else:
                    start=True
        self.clearWindow()
        return key_response,core.getTime()

    def waitSeconds(self,duration):
        """ wait for some amount of time (in seconds)
        """
        core.wait(duration)
        
    def closeWindow(self):
        """ close the main window
        """
        
        if self.win:
            self.win.close()

    def checkRespForQuitKey(self,resp):
        if self.quit_key in resp:
            self.shutDownEarly()

    def shutDownEarly(self):
        self.closeWindow()
        sys.exit()

    def shutDownAndSave(self):
        """ shut down cleanly and save data
        """
        try:
            self.writeDataToCouchdb()
            print 'saved data to couchdb'
        except:
            print 'unable to save data to couchbd'
        
    def loadStimulusFileYAML(self,filename):
        """ load a stimulus file in YAML format
        """
        if not os.path.exists(filename):
            raise BaseException('Stimulus file not found')
        yaml_iterator=yaml.load_all(file(filename,'r'))
        for trial in yaml_iterator:
            if trial.has_key('taskname'):
                self.taskinfo=trial
                for k in self.taskinfo.iterkeys():
                    self.__dict__[k]=self.taskinfo[k]
            else:
                self.stimulusInfo.append(trial)
        if len(self.stimulusInfo)>0:
            self.loadedStimulusFile=filename
    
    def getPastAcc(self, time_win):
        """Returns the ratio of hits/trials in a predefined window
        """
        if time_win > self.trialnum:
            time_win = self.trialnum
        return sum(self.track_response[-time_win:])
        
        
        
    
    def presentTextTrialWithFB(self,trial):
        self.trialnum += 1
        self.stims[trial['stim']].draw()
        self.win.flip()
        onsetTime=core.getTime()
        event.clearEvents()
        trial['actualOnsetTime']=onsetTime - self.startTime
        trial['stimulusCleared']=0
        trial['response']=[]
        trial['rt']=[]
        trialDuration=np.max([self.stimulusDuration,self.responseWindow])
        trial['trial_duration']=trialDuration
        while core.getTime() < (onsetTime + trialDuration):
            key_response=event.getKeys(None,True)
            if self.bot:
                key_response = [(self.bot.choose(), core.getTime())]
            if len(key_response)==0:
                continue
            for key,response_time in key_response:
                if self.quit_key==key:
                    self.shutDownEarly()
                elif self.trigger_key==key:
                    self.trigger_times.append(response_time-self.startTime)
                    continue
                elif key in self.action_keys:
                    alreadyResponded=1
                    trial['response'].append(key)
                    trial['rt'].append(response_time-onsetTime)
                    if self.clearAfterResponse and trial['stimulusCleared']==0:
                        self.clearWindow()
                        trial['stimulusCleared']=core.getTime()-onsetTime
                        core.wait(trial['FBonset'])    
            if core.getTime() > (onsetTime+self.stimulusDuration) and trial['stimulusCleared']==0:
                self.clearWindow()
                trial['stimulusCleared']=core.getTime()-onsetTime
        if trial['stimulusCleared']==0:
            self.clearWindow()
            trial['stimulusCleared']=core.getTime()-onsetTime
        return trial
            
        



















