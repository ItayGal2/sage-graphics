#!/usr/bin/env python

############################################################################
#
# SAGE LAUNCHER - A GUI for launching SAGE and all related components
#
# Copyright (C) 2007 Electronic Visualization Laboratory,
# University of Illinois at Chicago
#
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# 
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above
#    copyright notice, this list of conditions and the following disclaimer
#    in the documentation and/or other materials provided with the distribution.
#  * Neither the name of the University of Illinois at Chicago nor
#    the names of its contributors may be used to endorse or promote
#    products derived from this software without specific prior written permission.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
# PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
# LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
# NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
# Direct questions, comments etc about SAGE UI to www.evl.uic.edu/cavern/forum
#
# Author: Ratko Jagodic
#        
############################################################################


import wx, cPickle, os, sys, os.path, stat, string, copy, time, cStringIO, zlib, pickle
import wx.lib.filebrowsebutton as fb
import wx.lib.buttons as buttons
import wx.lib.hyperlink as hl
import wx.lib.scrolledpanel as scrolled
from wx import BitmapFromImage, ImageFromStream
import traceback as tb
import subprocess as sp
from threading import Thread


# shortcut
opj = os.path.join
from sagePath import getUserPath, SAGE_DIR, getPath, getDefaultPath


# --------------------------------------------------------
#
#                   GLOBALS   
#
# --------------------------------------------------------

# component types and official names
APP_LAUNCHER = "Application Launcher"
FILE_SERVER  = "File Server"
SAGE_PROXY   = "SAGE Proxy"
SAGE_UI      = "SAGE UI"
SAGE         = "SAGE"     
componentNames = [SAGE, APP_LAUNCHER, SAGE_UI, FILE_SERVER, SAGE_PROXY]

# this is where all the information about the components is stored
components = {}   # key=componentType, value=Component()

# tileConfig file (structure of the cluster driving the display)
tileConfig = None

MAX_TEXT_LEN = 64000     # max characters in the output text ctrl
PREFS_FILE = getUserPath("sageLauncherSettings.pickle")   # store the settings in a pickle file
PY_EXEC = sys.executable    # platform dependent python executable

# quit if the SAGE_DIRECTORY env var is not set
if not "SAGE_DIRECTORY" in os.environ:
    print "SAGE_DIRECTORY environment variable not set."
    print "Please first set the SAGE_DIRECTORY environment variable to your sage directory."
    sys.exit(0)

# default frame background color on windows (screwed up otherwise)
global colour   





# --------------------------------------------------------
#
#               CONVENIENCE FUNCTIONS
#
# --------------------------------------------------------


def makeBoldFont(widget):
    f = widget.GetFont()
    f.SetWeight(wx.BOLD)
    widget.SetFont(f)

def makeBiggerFont(widget):
    f = widget.GetFont()
    ps = f.GetPointSize()
    f.SetPointSize(ps + ps*0.2)  # make it 20% bigger
    widget.SetFont(f)

def makeSmallerFont(widget):
    f = widget.GetFont()
    ps = f.GetPointSize()
    f.SetPointSize(ps - ps*0.2)  # make it 20% smaller
    widget.SetFont(f)

def makeBiggerBoldFont(widget):
    makeBoldFont(widget)
    makeBiggerFont(widget)    

def isWin():
    return "__WXMSW__" in wx.PlatformInfo



# if the loadSettings fails for some reason (other than first execution),
# do not save (since you will overwrite the previous good settings)
DO_SAVE = True   
def saveSettings():
    if DO_SAVE:
        # first assemble a dictionary of all the settings and then store it
        settings = {}
        for componentType, comp in components.iteritems():
            settings[componentType] = comp.settings

        # now try and save the dictionary
        try:
            f = open(PREFS_FILE, "wb")
            cPickle.Pickler(f, cPickle.HIGHEST_PROTOCOL).dump(settings)
            f.close()
        except:
            print " ***** Error occured while saving settings:"
            print "".join(tb.format_exception(sys.exc_info()[0], sys.exc_info()[1], sys.exc_info()[2]))
                        


def loadSettings():
    """ try loading the settings and if it fails just return the default
        if it succeeds, update the default with the saved settings """

    # default settings
    settings = {}
    settings[APP_LAUNCHER] = AppLauncherSettings(APP_LAUNCHER)
    settings[FILE_SERVER] = FileServerSettings(FILE_SERVER)
    settings[SAGE_PROXY] = SageProxySettings(SAGE_PROXY)
    settings[SAGE_UI] = SageUISettings(SAGE_UI)
    settings[SAGE] = SageSettings(SAGE)

    # try loading the saved ones
    try:
        if os.path.isfile(PREFS_FILE):
            f = open(PREFS_FILE, "rb")
            (d) = cPickle.Unpickler(f).load()
            f.close()
            settings.update(d)
    except:
        print " ***** Error occured while loading saved settings and the changes you make will not be saved after you quit sageLauncher:"
        print "".join(tb.format_exception(sys.exc_info()[0], sys.exc_info()[1], sys.exc_info()[2]))
        global DO_SAVE
        DO_SAVE = False
        
    return settings




def getTileConfig():
    """ returns the full path of the currently used tile
        config file as specifed in the fsManager.conf """
    
    f = open( getPath("fsManager.conf"), "r")
    for line in f:
        line = line.strip()
        if line.startswith('tileConfiguration'):
            config = line.split()[1].strip()
    f.close()
    return getPath(config)




# --------------------------------------------------------
#
#                      COMPONENTS
#
# --------------------------------------------------------


class Component:
    """ this is the class that contains all the information
        about each of the components:
         - settings, output field, process object
        There is one of these for each component and they are
        all stored in a global dictionary
    """
    def __init__(self, componentType):
        self.componentType = componentType
        self.settings = None
        self.output = None
        self.process = None





# --------------------------------------------------------
#
#             COMPONENT SETTINGS
#
# --------------------------------------------------------

# these are the objects that store all the information about
# a component and will be saved in a file
# they define how things are run and other specific settings


class ComponentSettings:
    """ this is the base class for all the settings """
    def __init__(self, t):
        self.inBG = False
        self.doRun = True
        self.cmd = ""
        self.componentType = t
        self.pid = -1  # pid from the started process


    def getStartCommand(self):
        """ this must be implemented by the subclasses
            it should return the final command that is used to run the component
        """
        raise NotImplemented


    def getCwd(self):
        """ this must be implemented by the subclasses
            returns the current working directory
        """
        raise NotImplemented
        

    def __getinitargs__(self):
        """ for pickling to work properly if we add some
            more settings to this class at a later time """
        return (self.componentType,)




class SageSettings(ComponentSettings):
    def __init__(self, componentType):
        ComponentSettings.__init__(self, componentType)
        self.doRun = True
        self.onStart = "xhost +local:\npython ../dim/dim.py\npython ../dim/hwcapture/localPointer.py localhost"  # a string of commands to be executed after shutdown (split by \n)
        self.onStop = "fuser -k 19010/tcp"

        # things to kill on each node
        self.toKill = "fsManager sageDisplayManager sageAudioManager svc imageviewer mplayer bplay bplay-noglut VNCViewer render atlantis atlantis-mpi checker pdfviewer sagepdf"
        

    def getStartCommand(self):
        """ commmand used to run this component """
        return ["fsManager"]


    def getCwd(self):
        """ returns the current working directory """
        return opj(SAGE_DIR, "bin")


    def getKillCmd(self):
        """ returns a list of kill commands to run for stopping sage
            On Windows just kill the stuff on the local machine for now
        """
        cmds = []   # this will be returned as a list of lists
        killString = self.toKill   # processes to be killed on each node

        # windows
        if isWin():
            # first append .exe to the processes
            killList = [proc + ".exe" for proc in killString.split()]
            
            # generate the commands to kill each process
            c = ["taskkill", "/F"]
            for proc in killList:
                c.extend(["/IM", proc])
            cmds.append(c)
            
        # Mac + Linux
        else:           
            # get the ip addresses of the nodes of the cluster
            # + the master node
            tileConfig.readConfigFile(getTileConfig())
            IPs = tileConfig.getAllIPs()  
            IPs.append("127.0.0.1")

            for node in IPs:
                c = []
                k = "/usr/bin/killall -9 %s" % killString
                c.extend( ["/usr/bin/ssh", "-fx", node, k] ) 
                cmds.append(c)

        return cmds
    
        
    def __getinitargs__(self):
        """ for pickling to work properly if we add some
            more settings to this class at a later time """
        return (self.componentType,)
    


class AppLauncherSettings(ComponentSettings):
    def __init__(self, componentType):
        ComponentSettings.__init__(self, componentType)
        self.doReport = False
        self.doRun = True
        self.server = "sage.sl.startap.net"
        self.port = 19010


    def getAppConfigFilename(self):
        return getPath("applications", "applications.conf")

    def getStartCommand(self):
        """ commmand used to run this component """
        cmd = [PY_EXEC, "-u", opj(self.getCwd(), "appLauncher.py"), "-v", "-p", str(self.port)]

        # report to sage server?
        if self.doReport: cmd.extend( ["-s", self.server] )
        else: rep = cmd.append("-n")

        # run in background?
        if self.inBG and not isWin(): cmd.append("&")
        
        return cmd


    def getKillCmd(self):
        """ returns the command to kill the appLauncher """
        return [PY_EXEC, "KILL_LAUNCHER.py", str(self.port)]
        
        
    def getCwd(self):
        """ returns the current working directory """
        return opj(SAGE_DIR, "bin", "appLauncher")

        
    def __getinitargs__(self):
        """ for pickling to work properly if we add some
            more settings to this class at a later time """
        return (self.componentType,)



class FileServerSettings(ComponentSettings):
    def __init__(self, componentType):
        ComponentSettings.__init__(self, componentType)


    def getConfigFilename(self):
        return getPath("fileServer", "fileServer.conf")


    def getStartCommand(self):
        """ commmand used to run this component """
        if self.inBG and not isWin(): bg = "&"
        else: bg = ""
        return [PY_EXEC, "-u", opj(self.getCwd(), "fileServer.py"), "-v", bg]


    def getCwd(self):
        """ returns the current working directory """
        return opj(SAGE_DIR, "bin", "fileServer")

        
    def __getinitargs__(self):
        """ for pickling to work properly if we add some
            more settings to this class at a later time """
        return (self.componentType,)




class SageProxySettings(ComponentSettings):
    def __init__(self, componentType):
        ComponentSettings.__init__(self, componentType)
        self.host = 'localhost'
        self.port = 20001
        self.password = "pass"


    def getStartCommand(self):
        """ commmand used to run this component """
        return [PY_EXEC, "-u", opj(self.getCwd(), "sageProxy.py"),
                "-s", self.host, "-p", str(self.port), "-x", self.password, "-v"]


    def getCwd(self):
        """ returns the current working directory """
        return opj(SAGE_DIR, "bin", "sageProxy")

        
    def __getinitargs__(self):
        """ for pickling to work properly if we add some
            more settings to this class at a later time """
        return (self.componentType,)



class SageUISettings(ComponentSettings):
    def __init__(self, componentType):
        ComponentSettings.__init__(self, componentType)
        self.host = 'sage.sl.startap.net'
        self.port = 15558
        self.doRun = True
        self.autologinMachine = ""
        self.loadState = ""


    def getStartCommand(self):
        """ commmand used to run this component """
        cmd = [PY_EXEC, "-u", opj(self.getCwd(),"sageui.py"), "-v", "-s", self.host, "-p", str(self.port), "-t"]
        if self.autologinMachine != "":
            cmd.extend( ["-a", self.autologinMachine] )
        if self.loadState != "":
            cmd.extend( ["-o", self.loadState] )
        return cmd


    def getCwd(self):
        """ returns the current working directory """
        return opj(SAGE_DIR, "ui")


    def __getinitargs__(self):
        """ for pickling to work properly if we add some
            more settings to this class at a later time """
        return (self.componentType,)

    





# --------------------------------------------------------
#
#                 UI STUFF 
#
# --------------------------------------------------------


###
### these are the specific frames for each component that let's you configure the component
###


class ComponentFrame(wx.Frame):
    def __init__(self, parent, componentType):
        s = wx.DEFAULT_FRAME_STYLE | wx.TAB_TRAVERSAL
        wx.Frame.__init__(self, parent, wx.ID_ANY, componentType+" Configuration", style=s)
        if isWin(): self.SetBackgroundColour(colour)
        self.settings = components[componentType].settings
        self.mainSizer = wx.BoxSizer(wx.VERTICAL)
        self.SetIcon(getSageIcon())
        self.Bind(wx.EVT_CLOSE, self.OnClose)


    def MakeWidgets(self):
        okBtn = wx.Button(self, wx.ID_ANY, "OK")
        okBtn.Bind(wx.EVT_BUTTON, self.DoClose)
        self.mainSizer.Add(okBtn, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.ALL, 15)
        self.SetSizerAndFit(self.mainSizer)


    def DoClose(self, evt=None):
        self.Close(True)
        

    def OnClose(self, evt):
        """ save everything here but let the subclasses do that
        since it's specific for each... therefore it must be implemented """
        raise NotImplemented


        


class AppLauncherFrame(ComponentFrame):
    def __init__(self, parent):
        ComponentFrame.__init__(self, parent, APP_LAUNCHER)
        self.configs = AppConfigurations(self.settings.getAppConfigFilename())
        self.currentConfig = None   #current config object being edited
        self.MakeWidgets()
        self.Show()


    def MakeWidgets(self):
        self.run = wx.CheckBox(self, wx.ID_ANY, "Run in background")
        self.run.SetToolTipString(HELP_INBG)
        self.run.SetValue(self.settings.inBG)

        self.mainSizer.Add(self.MakeConnectionBox(), 0, wx.EXPAND | wx.ALL, 10)
        self.mainSizer.Add(self.MakeAppConfigBox(), 0, wx.EXPAND | wx.ALL, 10)
        self.mainSizer.Add(self.run, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.ALIGN_BOTTOM | wx.ALL, 5)
        ComponentFrame.MakeWidgets(self)


    def MakeConnectionBox(self):
        # the box
        box = wx.StaticBox(self, wx.ID_ANY, "Public access:")
        box.SetForegroundColour(wx.BLUE)
        makeBiggerBoldFont( box )
        boxSizer = wx.StaticBoxSizer( box, wx.VERTICAL )

        # widgets
        hostLabel = wx.StaticText(self, wx.ID_ANY, "Hostname / IP:")
        self.hostText = wx.TextCtrl(self, wx.ID_ANY, self.settings.server)
        self.hostText.SetMinSize((150, -1))
        self.hostText.SetToolTipString(HELP_AL_PUBLIC_HOST)

        #portLabel = wx.StaticText(self, wx.ID_ANY, "Port:")
        #self.portText = wx.TextCtrl(self, wx.ID_ANY, str(self.settings.port))

        self.reportCheck = wx.CheckBox(self, wx.ID_ANY, "Allow public access?")
        self.reportCheck.SetToolTipString(HELP_AL_PUBLIC)
        self.reportCheck.SetValue(self.settings.doReport)
        self.reportCheck.Bind(wx.EVT_CHECKBOX, self.OnPublicCheck)
        self.OnPublicCheck(None)
        
        # add widgets to the boxSizer
        hSizer = wx.BoxSizer(wx.HORIZONTAL)
        hSizer.Add(hostLabel, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT | wx.ALL, 5)
        hSizer.Add(self.hostText, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT | wx.RIGHT | wx.BOTTOM | wx.TOP, 5)
        hSizer.Add((10,10))
        #hSizer.Add(portLabel, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT | wx.ALL, 5)
        #hSizer.Add(self.portText, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT | wx.RIGHT | wx.BOTTOM | wx.TOP, 5)

        boxSizer.Add(self.reportCheck, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT | wx.ALL, 5)
        boxSizer.Add(hSizer, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT | wx.ALL, 5)
        
        return boxSizer


    def MakeAppConfigBox(self):
        # the box
        box = wx.StaticBox(self, wx.ID_ANY, "SAGE Applications:")
        box.SetForegroundColour(wx.BLUE)
        makeBiggerBoldFont( box )
        boxSizer = wx.StaticBoxSizer( box, wx.HORIZONTAL )

        # apps label and list
        appsLabel = wx.StaticText(self, wx.ID_ANY, "Applications:")
        makeBoldFont(appsLabel)
        self.appsList = wx.ListBox(self, wx.ID_ANY, choices=self.configs.getAppList())
        self.appsList.Bind(wx.EVT_LISTBOX, self.OnAppList)
        self.appsList.SetToolTipString(HELP_AL_APPS)
        addBtn = wx.Button(self, wx.ID_ANY, "Add", style=wx.BU_EXACTFIT)
        addBtn.Bind(wx.EVT_BUTTON, self.OnAppAdd)
        delBtn = wx.Button(self, wx.ID_ANY, "Delete", style=wx.BU_EXACTFIT)
        delBtn.Bind(wx.EVT_BUTTON, self.OnAppDel)

        btnSizer = wx.BoxSizer(wx.HORIZONTAL)
        btnSizer.Add(addBtn, 1, wx.ALIGN_CENTER | wx.ALL, 4)
        btnSizer.Add(delBtn, 1, wx.ALIGN_CENTER | wx.RIGHT | wx.TOP | wx.BOTTOM, 4)
                     
        appsSizer = wx.BoxSizer(wx.VERTICAL)
        appsSizer.Add(appsLabel, 0, wx.EXPAND | wx.ALIGN_LEFT | wx.ALL, 5)
        appsSizer.Add(self.appsList, 1, wx.EXPAND | wx.ALIGN_LEFT | wx.ALL, 5)
        appsSizer.Add(btnSizer, 0, wx.EXPAND | wx.ALIGN_CENTER_HORIZONTAL | wx.ALL, 1)
              
        # add widgets to the boxSizer
        self.confSizer = self.MakeConfigBox()
        boxSizer.Add(appsSizer, 0, wx.EXPAND | wx.ALIGN_LEFT | wx.ALL, 5)
        boxSizer.Add(wx.StaticLine(self, wx.ID_ANY, style=wx.VERTICAL), 0, wx.EXPAND | wx.ALIGN_LEFT | wx.ALL, 5)
        boxSizer.Add(self.confSizer, 1, wx.EXPAND | wx.ALIGN_LEFT | wx.ALL, 5)

        return boxSizer


    def MakeConfigBox(self):
        self.configSizers = {}
        
        # configuration list
        configLabel = wx.StaticText(self, wx.ID_ANY, "Configurations:")
        makeBoldFont(configLabel)
        self.configCombo = wx.ComboBox(self, wx.ID_ANY, choices=[])
        self.configCombo.SetMinSize((180, -1))
        self.configCombo.Bind(wx.EVT_COMBOBOX, self.OnConfigCombo)
        self.configCombo.SetToolTipString(HELP_AL_CFG)
        newBtn = wx.Button(self, wx.ID_ANY, " Add ", style=wx.BU_EXACTFIT)
        newBtn.Bind(wx.EVT_BUTTON, self.OnAddConfig)
        delBtn = wx.Button(self, wx.ID_ANY, " Delete ", style=wx.BU_EXACTFIT)
        delBtn.Bind(wx.EVT_BUTTON, self.OnDelConfig)
        copyBtn = wx.Button(self, wx.ID_ANY, " Make Copy ", style=wx.BU_EXACTFIT)
        copyBtn.Bind(wx.EVT_BUTTON, self.OnCopyConfig)
        copyBtn.SetToolTipString(HELP_AL_CFG_COPY)

        self.comboSizer = wx.BoxSizer(wx.HORIZONTAL)
        self.comboSizer.Add(configLabel, 0, wx.ALIGN_CENTER | wx.ALL, 5)
        self.comboSizer.Add(self.configCombo, 0, wx.ALIGN_CENTER | wx.ALL, 5)
        self.comboSizer.Add(newBtn, 0, wx.ALIGN_CENTER | wx.ALL, 5)
        self.comboSizer.Add(delBtn, 0, wx.ALIGN_CENTER | wx.ALL, 5)
        self.comboSizer.Add(copyBtn, 0, wx.ALIGN_CENTER | wx.ALL, 5)

        # add all to the main config sizer
        vSizer = wx.BoxSizer(wx.VERTICAL)
        vSizer.Add(self.comboSizer, 1, wx.EXPAND | wx.ALIGN_CENTER_HORIZONTAL | wx.ALIGN_TOP | wx.ALL, 9)
        l = wx.StaticLine(self, wx.ID_ANY);  l.Disable()
        vSizer.Add(l, 0, wx.EXPAND | wx.ALIGN_LEFT | wx.ALL, 5)

        # static app
        self.staticCheck = wx.CheckBox(self, wx.ID_ANY, "Static application")#, style=wx.ALIGN_RIGHT)
        self.staticCheck.SetValue(True)
        self.staticCheck.Bind(wx.EVT_KILL_FOCUS, self.OnStaticFocus)
        self.staticCheck.SetToolTipString(HELP_AL_CFG_STATIC)
        vSizer.Add(self.staticCheck, 0, wx.EXPAND | wx.ALIGN_TOP | wx.ALIGN_LEFT | wx.ALL, 10)

        # execution
        execFoldBar = FoldBar(self, 101, "Execution", self.OnFoldBtn)
        self.configSizers[101] = self.MakeExecutionSection()
        vSizer.Add(execFoldBar, 0, wx.EXPAND | wx.ALIGN_TOP | wx.ALIGN_LEFT | wx.ALL, 5)
        vSizer.Add(self.configSizers[101], 0, wx.EXPAND | wx.ALIGN_TOP | wx.ALIGN_LEFT | wx.LEFT | wx.BOTTOM | wx.RIGHT, 15)
        vSizer.Show(self.configSizers[101], False, True)
        
        # size and pos
        sizePosFoldBar = FoldBar(self, 100, "Size and position", self.OnFoldBtn)
        self.configSizers[100] = self.MakeSizePosSection()
        vSizer.Add(sizePosFoldBar, 0, wx.EXPAND | wx.ALIGN_TOP | wx.ALIGN_LEFT | wx.ALL, 5)
        vSizer.Add(self.configSizers[100], 0, wx.EXPAND | wx.ALIGN_TOP | wx.ALIGN_LEFT | wx.LEFT | wx.BOTTOM | wx.RIGHT, 15)
        vSizer.Show(self.configSizers[100], False, True)
        
        # parallel application stuff
        parallelFoldBar = FoldBar(self, 102, "Parallel Applications", self.OnFoldBtn)
        self.configSizers[102] = self.MakeParallelSection()
        vSizer.Add(parallelFoldBar, 0, wx.EXPAND | wx.ALIGN_TOP | wx.ALIGN_LEFT | wx.ALL, 5)
        vSizer.Add(self.configSizers[102], 0, wx.EXPAND | wx.ALIGN_TOP | wx.ALIGN_LEFT | wx.LEFT | wx.BOTTOM | wx.RIGHT, 15)
        vSizer.Show(self.configSizers[102], False, True)
        
        # advanced stuff...
        advFoldBar = FoldBar(self, 103, "Advanced", self.OnFoldBtn)
        self.configSizers[103] = self.MakeAdvancedSection()
        vSizer.Add(advFoldBar, 0, wx.EXPAND | wx.ALIGN_TOP | wx.ALIGN_LEFT | wx.ALL, 5)
        vSizer.Add(self.configSizers[103], 0, wx.EXPAND | wx.ALIGN_TOP | wx.ALIGN_LEFT | wx.LEFT | wx.BOTTOM | wx.RIGHT, 15)
        vSizer.Show(self.configSizers[103], False, True)
        
        return vSizer


    def MakeParallelSection(self):
        # parallel checkbox
        self.parallelCheck = wx.CheckBox(self, wx.ID_ANY, "This is a parallel application", style=wx.ALIGN_RIGHT)
        self.parallelCheck.Bind(wx.EVT_CHECKBOX, self.OnParallelCheck)
        
        # number of nodes
        nodeNumLabel = wx.StaticText(self, wx.ID_ANY, "Number of nodes:")
        self.nodeNumSpin = wx.SpinCtrl(self, wx.ID_ANY, min=1, initial=1)
        self.nodeNumSpin.SetToolTipString(HELP_AL_CFG_NUM_NODES)
        self.nodeNumSpin.Disable()
        self.nodeNumSpin.Bind(wx.EVT_KILL_FOCUS, self.OnNodeNumFocus)

        # master ip
        masterIPLabel = wx.StaticText(self, wx.ID_ANY, "Master node:")
        self.masterIPText = wx.TextCtrl(self, wx.ID_ANY)
        self.masterIPText.SetToolTipString(HELP_AL_CFG_MASTER)
        self.masterIPText.SetMinSize((120, -1))
        self.masterIPText.Disable()
        self.masterIPText.Bind(wx.EVT_KILL_FOCUS, self.OnMasterIPFocus)

        # sizer stuff
        pSizer = wx.FlexGridSizer(2,2,5,5)
        pSizer.Add(nodeNumLabel, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT | wx.LEFT | wx.RIGHT, 5)
        pSizer.Add(self.nodeNumSpin, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT | wx.RIGHT, 5)
        pSizer.Add(masterIPLabel, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT | wx.LEFT | wx.RIGHT, 5)
        pSizer.Add(self.masterIPText, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT | wx.RIGHT, 5)
        
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.parallelCheck, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.ALL, 5)
        sizer.Add(pSizer, 0, wx.ALIGN_LEFT | wx.ALL, 5)

        return sizer
    

    def MakeExecutionSection(self):
        appLabel = wx.StaticText(self, wx.ID_ANY, "Run application")
        appLabel.SetMinSize((100, -1))
        self.appText = wx.TextCtrl(self, wx.ID_ANY)
        self.appText.SetToolTipString(HELP_AL_CFG_APP)
        self.appText.Bind(wx.EVT_KILL_FOCUS, self.OnAppTextFocus)

        dirLabel = wx.StaticText(self, wx.ID_ANY, "from directory")
        dirLabel.SetMinSize((100, -1))
        self.dirText = wx.TextCtrl(self, wx.ID_ANY)
        self.dirText.SetToolTipString(HELP_AL_CFG_DIR)
        self.dirText.Bind(wx.EVT_KILL_FOCUS, self.OnDirTextFocus)
            
        machineLabel = wx.StaticText(self, wx.ID_ANY, "on host")
        self.machineText = wx.TextCtrl(self, wx.ID_ANY)
        self.machineText.SetToolTipString(HELP_AL_CFG_MACHINE)
        self.machineText.SetMinSize((140, -1))
        self.machineText.Bind(wx.EVT_KILL_FOCUS, self.OnMachineTextFocus)
        
        sizer = wx.FlexGridSizer(3,2, 3,10)
        sizer.Add(appLabel, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT | wx.ALL, 5)
        sizer.Add(self.appText, 0, wx.EXPAND | wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT)
        sizer.Add(dirLabel, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT | wx.ALL, 5)
        sizer.Add(self.dirText, 0, wx.EXPAND | wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT)
        sizer.Add(machineLabel, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT | wx.ALL, 5)
        sizer.Add(self.machineText, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT)
        sizer.AddGrowableCol(1)
        
        return sizer


    def MakeSizePosSection(self):
        # sage window size
        szLabel = wx.StaticText(self, wx.ID_ANY, "Initial SAGE window size")
        szLabel.SetMinSize((180, -1))
        wLabel = wx.StaticText(self, wx.ID_ANY, "W")
        self.wText = wx.TextCtrl(self, wx.ID_ANY, "1000")
        self.wText.Bind(wx.EVT_KILL_FOCUS, self.OnSizeTextFocus)
        self.wText.SetToolTipString(HELP_AL_CFG_SIZE)
        hLabel = wx.StaticText(self, wx.ID_ANY, "H")
        self.hText = wx.TextCtrl(self, wx.ID_ANY, "1000")
        self.hText.SetToolTipString(HELP_AL_CFG_SIZE)
        self.hText.Bind(wx.EVT_KILL_FOCUS, self.OnSizeTextFocus)
        
        # sage window position
        posLabel = wx.StaticText(self, wx.ID_ANY, "Initial SAGE window position")
        posLabel.SetMinSize((180, -1))
        xLabel = wx.StaticText(self, wx.ID_ANY, "X")
        self.xText = wx.TextCtrl(self, wx.ID_ANY, "100")
        self.xText.Bind(wx.EVT_KILL_FOCUS, self.OnPosTextFocus)
        yLabel = wx.StaticText(self, wx.ID_ANY, "Y")
        self.yText = wx.TextCtrl(self, wx.ID_ANY, "100")
        self.yText.Bind(wx.EVT_KILL_FOCUS, self.OnPosTextFocus)

        # add to sizer
        sizer = wx.FlexGridSizer(2,5, 5,0)
        sizer.Add(szLabel, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT | wx.ALL, border=5)
        sizer.Add(wLabel, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT | wx.ALL, border=5)
        sizer.Add(self.wText, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT | wx.ALL, border=5)
        sizer.Add(hLabel, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT | wx.ALL, border=5)
        sizer.Add(self.hText, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT | wx.ALL, border=5)

        sizer.Add(posLabel, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT | wx.ALL, border=5)
        sizer.Add(xLabel, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT | wx.ALL, border=5)
        sizer.Add(self.xText, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT | wx.ALL, border=5)
        sizer.Add(yLabel, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT | wx.ALL, border=5)
        sizer.Add(self.yText, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT | wx.ALL, border=5)
        
        return sizer


    def MakeAdvancedSection(self):
        pbLabel = wx.StaticText(self, wx.ID_ANY, "Pixel block size")
        pbLabel.SetMinSize((130, -1))
        self.pbSpin = wx.SpinCtrl(self, wx.ID_ANY, min=1, max=512, initial=64)
        self.pbSpin.Bind(wx.EVT_KILL_FOCUS, self.OnPBSpinFocus)
        self.pbSpin.SetToolTipString(HELP_AL_CFG_BP)

        #protoLabel = wx.StaticText(self, wx.ID_ANY, "Streaming protocol")
        #protoLabel.SetMinSize((130, -1))
        #self.protoCombo = wx.ComboBox(self, wx.ID_ANY, choices=["TCP"])

        bridgeIPLabel = wx.StaticText(self, wx.ID_ANY, "SAGE Bridge host")
        bridgeIPLabel.SetMinSize((130, -1))
        self.bridgeIPText = wx.TextCtrl(self, wx.ID_ANY)
        self.bridgeIPText.SetMinSize((150, -1))
        self.bridgeIPText.Bind(wx.EVT_KILL_FOCUS, self.OnBridgeIPTextFocus)
        self.bridgeIPText.SetToolTipString(HELP_AL_CFG_BHOST)

        bridgePortLabel = wx.StaticText(self, wx.ID_ANY, "SAGE Bridge port")
        bridgePortLabel.SetMinSize((130, -1))
        self.bridgePortText = wx.TextCtrl(self, wx.ID_ANY)
        self.bridgePortText.SetMinSize((150, -1))
        self.bridgePortText.Bind(wx.EVT_KILL_FOCUS, self.OnBridgePortTextFocus)
        self.bridgePortText.SetToolTipString(HELP_AL_CFG_BPORT)
        
        sizer = wx.FlexGridSizer(3,2, 3,10)
        #sizer.Add(protoLabel, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT | wx.ALL, 5)
        #sizer.Add(self.protoCombo, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT | wx.ALL, 5)
        sizer.Add(pbLabel, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT | wx.ALL, 5)
        sizer.Add(self.pbSpin, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT | wx.ALL, 5)
        sizer.Add(bridgeIPLabel, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT | wx.ALL, 5)
        sizer.Add(self.bridgeIPText, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT)
        sizer.Add(bridgePortLabel, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT | wx.ALL, 5)
        sizer.Add(self.bridgePortText, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT)
        sizer.AddGrowableCol(1)
        
        return sizer


    def OnFoldBtn(self, sectionId, collapse):
        self.confSizer.Show(self.configSizers[sectionId], not collapse, True)
        self.Fit()
        

    def OnParallelCheck(self, evt):
        self.nodeNumSpin.Enable( self.parallelCheck.IsChecked() )
        self.masterIPText.Enable( self.parallelCheck.IsChecked() )
        if not self.parallelCheck.IsChecked():
            self.nodeNumSpin.SetValue(1)
            self.currentConfig.setNodeNum(1)


    def OnAddConfig(self, evt):
        """ add a new configuration for the currently selected app """

        # an app must be selected first
        appName = self.appsList.GetStringSelection()
        if appName == "":
            wx.MessageBox("Please select an application first", "Error", parent=self)
            return
        app = self.configs.getApp(appName)

        # get the config name, do nothing if cancel pressed
        configName = wx.GetTextFromUser("Enter new configuration name", "Config Name", parent=self)
        if configName == "":  return
        if configName in app.getAllConfigNames():
            wx.MessageBox("Configuration with that name already exists", "Error", parent=self)
            return

        # add the new config and clear the config fields
        conf = OneConfig(configName, appName)
        app.addConfig(conf)
        self.ClearConfig()
        self.currentConfig = conf
        self.configCombo.Append(configName)
        self.configCombo.SetStringSelection(configName)


    def OnDelConfig(self, evt):
        # an app must be selected first
        appName = self.appsList.GetStringSelection()
        if appName == "":
            wx.MessageBox("Please select an application first", "Error", parent=self)
            return
        app = self.configs.getApp(appName)

        # get the config name, do nothing if cancel pressed
        configName = self.configCombo.GetValue()
        if configName == "":  return

        # there must be at least one config per app
        if len(app.getAllConfigNames()) < 2:
            wx.MessageBox("Cannot delete the last configuration. There must be at least one configuration per application.", "Cannot Delete", parent=self)
            return

        # add the new config and clear the config fields
        app.delConfig(configName)
        self.configCombo.Delete(self.configCombo.FindString(configName))
        self.configCombo.SetValue("")
        self.ClearConfig()
        self.currentConfig = None


    def OnCopyConfig(self, evt):
        # an app must be selected first
        appName = self.appsList.GetStringSelection()
        if appName == "":
            wx.MessageBox("Please select an application first", "Error", parent=self)
            return
        app = self.configs.getApp(appName)

        # get the config name, do nothing if cancel pressed
        configName = self.configCombo.GetValue()
        if configName == "":  return

        # get the new config name, do nothing if cancel pressed
        newConfigName = wx.GetTextFromUser("Enter new configuration name", "Config Name", parent=self)
        if newConfigName == "":  return
        if newConfigName in app.getAllConfigNames():
            wx.MessageBox("Configuration with that name already exists", "Error", parent=self)
            return

        # copy the old config, change its name and add it to the app
        conf = copy.deepcopy( app.getConfig(configName) )
        conf.setName(newConfigName)
        app.addConfig(conf)

        # select the new config
        self.configCombo.Append(newConfigName)
        self.configCombo.SetStringSelection(newConfigName)
        self.__SetConfig(conf)
        
    
    def OnAppList(self, evt):
        """ refill configCombo, select the first one and fill the fields for it"""
        a = evt.GetString()
        if not a: return
        self.configCombo.Clear()
        for c in self.configs.getApp(a).getAllConfigNames():
            self.configCombo.Append(c)
        self.configCombo.SetSelection(0)
        conf = self.configs.getConfig(a, self.configCombo.GetString(0))
        self.__SetConfig(conf)


    def OnConfigCombo(self, evt):
        configName = self.configCombo.GetValue()
        appName = self.appsList.GetStringSelection()
        c = self.configs.getConfig(appName, configName)
        self.__SetConfig(c)


    def __SetConfig(self, conf):
        """ fill all the widgets with correct values for this configuration """
        self.currentConfig = conf
        
        self.staticCheck.SetValue( conf.getStaticApp() )

        # execution
        self.dirText.SetValue( conf.getBinDir() )
        self.machineText.SetValue( conf.getTargetMachine() )
        self.appText.SetValue( conf.getCommand() )

        # size and pos
        self.wText.SetValue( str(conf.getSize()[0]) )
        self.hText.SetValue( str(conf.getSize()[1]) )
        self.yText.SetValue( str(conf.getPosition()[1]) )
        self.xText.SetValue( str(conf.getPosition()[0]) )

        # parallel section
        if conf.getNodeNum() == 1:
            self.parallelCheck.SetValue(False)
            self.nodeNumSpin.SetValue(1)
            self.nodeNumSpin.Enable(False)
            self.masterIPText.Enable(False)
        else:
            self.parallelCheck.SetValue(True)
            self.nodeNumSpin.SetValue( conf.getNodeNum() )
            if conf.getMasterIP():  # could be none
                self.masterIPText.SetValue( conf.getMasterIP() )        
            self.nodeNumSpin.Enable(True)
            self.masterIPText.Enable(True)


        # advanced
        self.pbSpin.SetValue( conf.getBlockSize()[0] )
        self.bridgeIPText.SetValue( conf.getBridgeIP() )
        self.bridgePortText.SetValue( conf.getBridgePort() )


    def OnAppAdd(self, evt):
        appName = wx.GetTextFromUser("Enter new application name.\nHas to be the same as the sage app configuration file the application\nis trying to load (e.g. \"atlantis\" is trying to load \"atlantis.conf\")", "App Name", parent=self)
        if appName == "":  return
        if appName in self.configs.getAppList():
            wx.MessageBox("Application already exists", "Error", parent=self)
            return
        
        configName = wx.GetTextFromUser("Enter first configuration name", "Config Name", parent=self)
        if configName == "":  return
        self.ClearConfig(clearConfigNames=True)

        # add to the list of apps
        self.appsList.Append(appName)
        self.appsList.SetStringSelection(appName)

        # add to the list of configs
        self.configCombo.Append(configName)
        self.configCombo.SetStringSelection(configName)

        # change the actual datastructure
        self.configs.addNewApp(appName)
        conf = OneConfig(configName, appName)
        self.currentConfig = conf
        self.configs.getApp(appName).addConfig(conf)


    def OnAppDel(self, evt):
        appName = self.appsList.GetStringSelection()
        if appName == "":  return  #nothing selected
        self.configs.delApp(appName)
        self.ClearConfig(clearConfigNames=True)
        self.currentConfig = None
        self.appsList.Delete( self.appsList.FindString(appName) )
        

    def ClearConfig(self, clearConfigNames=False):
        """ clears all the config fields to their default values """
        self.pbSpin.SetValue(64)
        self.bridgeIPText.SetValue("")
        self.bridgePortText.SetValue("")
        self.masterIPText.SetValue("")
        self.nodeNumSpin.SetValue(1)
        self.parallelCheck.SetValue(False)
        self.nodeNumSpin.Enable(False)
        self.masterIPText.Enable(False)
        self.xText.SetValue("100")
        self.yText.SetValue("100")
        self.hText.SetValue("1000")
        self.wText.SetValue("1000")
        self.staticCheck.SetValue(True)
        self.dirText.SetValue("$SAGE_DIRECTORY/bin")
        self.machineText.SetValue("127.0.0.1")
        self.appText.SetValue("")
        if clearConfigNames:
            self.configCombo.Clear()
            self.configCombo.SetValue("")


    def OnPublicCheck(self, evt):
        if self.reportCheck.IsChecked():
            self.hostText.Enable()
            #self.portText.Enable()
        else:
            self.hostText.Disable()
            #self.portText.Disable()


    ####  KILL FOCUS EVENT HANDLERS (for saving config data right away)

    def OnStaticFocus(self, evt):
        if self.currentConfig:
            self.currentConfig.setStaticApp(self.staticCheck.IsChecked())

    def OnNodeNumFocus(self, evt):
        if self.currentConfig:
            self.currentConfig.setNodeNum(self.nodeNumSpin.GetValue())

    def OnMasterIPFocus(self, evt):
        if self.currentConfig:
            self.currentConfig.setMasterIP(self.masterIPText.GetValue())

    def OnAppTextFocus(self, evt):
        if self.currentConfig:
            self.currentConfig.setCommand(self.appText.GetValue())

    def OnDirTextFocus(self, evt):
        if self.currentConfig:
            self.currentConfig.setBinDir(self.dirText.GetValue())

    def OnMachineTextFocus(self, evt):
        if self.currentConfig:
            self.currentConfig.setTargetMachine(self.machineText.GetValue())

    def OnSizeTextFocus(self, evt):
        if self.currentConfig:
            self.currentConfig.setSize((int(self.wText.GetValue()),
                                       int(self.hText.GetValue())))

    def OnPosTextFocus(self, evt):
        if self.currentConfig:
            self.currentConfig.setPosition((int(self.xText.GetValue()),
                                           int(self.yText.GetValue())))

    def OnPBSpinFocus(self, evt):
        if self.currentConfig:
            sz = self.pbSpin.GetValue()
            self.currentConfig.setBlockSize((sz,sz))

    def OnBridgePortTextFocus(self, evt):
        if self.currentConfig:
            self.currentConfig.setBridgePort(self.bridgePortText.GetValue())
            
    def OnBridgeIPTextFocus(self, evt):
        if self.currentConfig:
            self.currentConfig.setBridgeIP(self.bridgeIPText.GetValue())

    
    def OnClose(self, evt):
        """ save stuff here """
        self.settings.doReport = self.reportCheck.IsChecked()
        self.settings.server = self.hostText.GetValue()
        #self.settings.port = self.portText.GetValue()
        self.settings.inBG = self.run.GetValue()
        saveSettings()
        self.configs.writeConfig()
        evt.Skip()






class FileServerFrame(ComponentFrame):
    def __init__(self, parent):
        ComponentFrame.__init__(self, parent, FILE_SERVER)

        # for reading the config file
        self.types ={}
        self.viewers = {}
        self.filesDir = ""
        self.ReadConfigFile()
        
        self.MakeWidgets()
        self.Show()


    def MakeWidgets(self):
        self.run = wx.CheckBox(self, wx.ID_ANY, "Run in background")
        self.run.SetToolTipString(HELP_INBG)
        self.run.SetValue(self.settings.inBG)

        self.mainSizer.Add(self.MakeConfigBox(), 1, wx.EXPAND | wx.ALL, 10)
        self.mainSizer.Add(self.run, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.ALIGN_BOTTOM | wx.ALL, 10)
        ComponentFrame.MakeWidgets(self)



    def MakeConfigBox(self):
        # the box
        box = wx.StaticBox(self, wx.ID_ANY, "File Server Configuration:")
        box.SetForegroundColour(wx.BLUE)
        makeBiggerBoldFont( box )
        boxSizer = wx.StaticBoxSizer( box, wx.VERTICAL )

        # widgets
        self.fbb = fb.DirBrowseButton(self, wx.ID_ANY, labelText='Library Root:',
                                      dialogTitle="Choose Library Root",
                                      startDirectory=opj(SAGE_DIR,"bin"),
                                      toolTip=HELP_FS_ROOT)
        self.fbb.SetValue(self.filesDir)
        self.fbb.label.SetMinSize((80, -1))
        self.fbb.SetMinSize((600,-1))

        # types label and list
        typesLabel = wx.StaticText(self, wx.ID_ANY, "File types:")
        self.typesList = wx.ListBox(self, wx.ID_ANY, choices=self.types.keys())
        self.typesList.Bind(wx.EVT_LISTBOX, self.OnList)
        self.typesList.SetToolTipString(HELP_FS_TYPES)
        
        addBtn = wx.Button(self, wx.ID_ANY, "Add", style=wx.BU_EXACTFIT)
        addBtn.Bind(wx.EVT_BUTTON, self.OnAdd)
        delBtn = wx.Button(self, wx.ID_ANY, "Delete", style=wx.BU_EXACTFIT)
        delBtn.Bind(wx.EVT_BUTTON, self.OnDel)

        btnSizer = wx.BoxSizer(wx.HORIZONTAL)
        btnSizer.Add(addBtn, 1, wx.ALIGN_CENTER | wx.ALL, 4)
        btnSizer.Add(delBtn, 1, wx.ALIGN_CENTER | wx.RIGHT | wx.TOP | wx.BOTTOM, 4)
                     
        typesSizer = wx.BoxSizer(wx.VERTICAL)
        typesSizer.Add(typesLabel, 0, wx.EXPAND | wx.ALIGN_LEFT | wx.ALL, 5)
        typesSizer.Add(self.typesList, 1, wx.EXPAND | wx.ALIGN_LEFT | wx.ALL, 5)
        typesSizer.Add(btnSizer, 0, wx.EXPAND | wx.ALIGN_CENTER_HORIZONTAL | wx.ALL, 1)
        

        # details (extensions and application)
        extLabel = wx.StaticText(self, wx.ID_ANY, "File extensions:")
        self.extText = wx.TextCtrl(self, wx.ID_ANY)
        self.extText.Bind(wx.EVT_KILL_FOCUS, self.OnExtText)
        self.extText.SetToolTipString(HELP_FS_EXT)
        
        appLabel = wx.StaticText(self, wx.ID_ANY, "Run with application (and any optional arguments):")
        self.appText = wx.TextCtrl(self, wx.ID_ANY)
        self.appText.Bind(wx.EVT_KILL_FOCUS, self.OnAppText)
        self.appText.SetToolTipString(HELP_FS_APP)

        detailSizer = wx.BoxSizer(wx.VERTICAL)
        detailSizer.Add(extLabel, 0, wx.EXPAND | wx.ALIGN_LEFT | wx.ALL, 5)
        detailSizer.Add(self.extText, 0, wx.ALIGN_LEFT | wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 5)
        detailSizer.Add(appLabel, 0, wx.EXPAND | wx.ALIGN_LEFT | wx.ALL, 5)
        detailSizer.Add(self.appText, 0, wx.ALIGN_LEFT | wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 5)

        # add the above two to the horizontal sizer
        horSizer = wx.BoxSizer(wx.HORIZONTAL)
        horSizer.Add(typesSizer, 0, wx.EXPAND | wx.ALIGN_LEFT | wx.ALIGN_TOP | wx.ALL, 10)
        horSizer.Add(detailSizer, 1, wx.EXPAND | wx.ALIGN_LEFT | wx.ALIGN_TOP | wx.ALL, 10)
        
        # add widgets to the boxSizer
        boxSizer.Add(self.fbb, 0, wx.EXPAND | wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT | wx.ALL, 10)
        boxSizer.Add(horSizer, 1, wx.EXPAND | wx.ALIGN_LEFT | wx.ALL, 5)

        return boxSizer



    def ReadConfigFile(self):
        # reinitialize everything
        self.types = {}
        self.viewers = {}

        # read the config file
        try:
            f = open(self.settings.getConfigFilename(), "r")
        except:
            m = """
            File Server configuration file doesn't exist yet which usually means
            that it hasn't been compiled yet. Please compile it first by running "make install" from
            %s.""" % opj(SAGE_DIR,"app","FileViewer")
            wx.MessageBox(m, "No FileServer")
            self.Destroy()
            return
                
        for line in f:
            line = line.strip()

            # read root library directory
            if line.startswith("FILES_DIR"):
                self.filesDir = line.split("=")[1].strip()

            # read types
            elif line.startswith("type:"):
                line = line.split(":",1)[1]
                (type, extensions) = line.split("=")
                self.types[type.strip()] = extensions.strip().split(" ")

            # read apps for types
            elif line.startswith("app:"):
                line = line.split(":", 1)[1].strip()
                (type, app) = line.split("=")
                tpl = app.strip().split(" ", 1)
                if len(tpl) == 1:  params = ""
                else:  params = tpl[1].strip()
                app = tpl[0].strip()
                self.viewers[type.strip()] = (app, params)
        f.close()
        

    def WriteConfigFile(self):
        try:
            self.filesDir = self.fbb.GetValue()
            
            f = open(getUserPath("fileServer", "fileServer.conf"), "w")
            f.write("FILES_DIR = "+ self.filesDir+"\n")

            f.write("\n#"+"----"*12+"\n\n")  # separator
            
            # write types out and their extensions
            for t, ext in self.types.iteritems():
                f.write("type:" + t + " = " + " ".join(ext) + "\n")

            f.write("\n#"+"----"*12+"\n\n")  # separator
            
            # write apps out and their parameters
            for t, appTuple in self.viewers.iteritems():
                f.write("app:"+ t + " = " + " ".join(appTuple) + "\n")
            
            f.close()
        except:
            print " ***** Error while writing file server config file"
            print "".join(tb.format_exception(sys.exc_info()[0], sys.exc_info()[1], sys.exc_info()[2]))
            return False


    def OnAdd(self, evt):
        newType = wx.GetTextFromUser("Enter new file type to the file library:", "New Type", parent=self)
        if newType != "":
            if newType in self.types:
                wx.MessageBox("File type already exists", "Error", parent=self)
                return
            self.extText.Clear()
            self.appText.Clear()
            self.types[newType] = []
            self.viewers[newType] = ()
            self.typesList.AppendAndEnsureVisible(newType)
            self.typesList.SetStringSelection(newType)


    def OnDel(self, evt):
        t = self.typesList.GetStringSelection()
        if t != "":
            self.extText.Clear()
            self.appText.Clear()
            del self.types[t]
            del self.viewers[t]
            self.typesList.Delete( self.typesList.FindString(t) )
            

    def OnList(self, evt):
        t = evt.GetString()
        self.extText.SetValue(" ".join(self.types[t]))
        self.appText.SetValue(" ".join(self.viewers[t]))


    def OnAppText(self, evt):
        """ gets called when the text ctrl loses focus so we save the data """
        t = self.typesList.GetStringSelection()
        tpl = self.appText.GetValue().strip().split(" ", 1)
        if len(tpl) == 1:  params = ""
        else:  params = tpl[1].strip()
        app = tpl[0].strip()
        self.viewers[t] = (app, params)
        

    def OnExtText(self, evt):
        """ gets called when the text ctrl loses focus so we save the data """
        t = self.typesList.GetStringSelection()
        self.types[t] = self.extText.GetValue().strip().split(' ')


    def OnClose(self, evt):
        """ save stuff here """
        self.settings.inBG = self.run.GetValue()
        self.WriteConfigFile()
        saveSettings()
        evt.Skip()




        

class SageProxyFrame(ComponentFrame):
    def __init__(self, parent):
        ComponentFrame.__init__(self, parent, SAGE_PROXY)
        self.MakeWidgets()
        self.Show()


    def MakeWidgets(self):
        # add the boxes to the main sizer
        self.mainSizer.Add(self.MakeConnectionBox(), 0, wx.EXPAND | wx.ALL, 10)
        self.mainSizer.Add(self.MakePasswordBox(), 0, wx.EXPAND | wx.ALL, 10)
        ComponentFrame.MakeWidgets(self)


    def MakeConnectionBox(self):
        # sage connection box
        box = wx.StaticBox(self, wx.ID_ANY, "Run Proxy for SAGE on:")
        box.SetForegroundColour(wx.BLUE)
        makeBiggerBoldFont( box )
        boxSizer = wx.StaticBoxSizer( box, wx.HORIZONTAL )

        # widgets
        hostLabel = wx.StaticText(self, wx.ID_ANY, "Hostname / IP:")
        self.hostText = wx.TextCtrl(self, wx.ID_ANY, self.settings.host)
        self.hostText.SetToolTipString(HELP_SP_HOST)
        self.hostText.SetMinSize((150, -1))

        portLabel = wx.StaticText(self, wx.ID_ANY, "Port:")
        self.portText = wx.TextCtrl(self, wx.ID_ANY, str(self.settings.port))
        self.portText.SetToolTipString(HELP_SP_PORT)
        
        # add widgets to the boxSizer
        boxSizer.Add(hostLabel, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT | wx.ALL, 5)
        boxSizer.Add(self.hostText, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT | wx.RIGHT | wx.BOTTOM | wx.TOP, 5)
        boxSizer.Add((10,10))
        boxSizer.Add(portLabel, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT | wx.ALL, 5)
        boxSizer.Add(self.portText, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT | wx.RIGHT | wx.BOTTOM | wx.TOP, 5)

        return boxSizer


    def MakePasswordBox(self):
        # password box
        box = wx.StaticBox(self, wx.ID_ANY, "Password for SAGE Web UI access:")
        box.SetForegroundColour(wx.BLUE)
        makeBiggerBoldFont( box )
        boxSizer = wx.StaticBoxSizer( box, wx.HORIZONTAL )

        # widgets
        passLabel = wx.StaticText(self, wx.ID_ANY, "Password:")
        self.passText = wx.TextCtrl(self, wx.ID_ANY, self.settings.password)
        self.passText.SetToolTipString(HELP_SP_PASS)
        self.passText.SetMinSize((150, -1))

        # add widgets to the boxSizer
        boxSizer.Add(passLabel, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT | wx.ALL, 5)
        boxSizer.Add(self.passText, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT | wx.RIGHT | wx.BOTTOM | wx.TOP, 5)

        return boxSizer


    def OnClose(self, evt):
        """ save stuff here """
        self.settings.host = self.hostText.GetValue()
        self.settings.port = int(self.portText.GetValue())
        self.settings.password = self.passText.GetValue()
        saveSettings()
        evt.Skip()
        



class SageUIFrame(ComponentFrame):
    def __init__(self, parent):
        ComponentFrame.__init__(self, parent, SAGE_UI)
        self.MakeWidgets()
        self.Show()

        
    def MakeWidgets(self):
        # make the box first (this is REQUIRED since the box is a
        # sibling of the widgets inside it and not their parent)
        
        box = wx.StaticBox(self, wx.ID_ANY, "Connection Manager")
        box.SetForegroundColour(wx.BLUE)
        makeBiggerBoldFont( box )
        boxSizer = wx.StaticBoxSizer( box, wx.HORIZONTAL )

        # widgets
        hostLabel = wx.StaticText(self, wx.ID_ANY, "Hostname / IP:")
        self.hostText = wx.TextCtrl(self, wx.ID_ANY, self.settings.host)
        self.hostText.SetToolTipString(HELP_SU_HOST)
        self.hostText.SetMinSize((150, -1))

        portLabel = wx.StaticText(self, wx.ID_ANY, "Port:")
        self.portText = wx.TextCtrl(self, wx.ID_ANY, str(self.settings.port))
        self.portText.SetToolTipString(HELP_SU_HOST)

        autologinLabel = wx.StaticText(self, wx.ID_ANY, "Autologin to (enter sage session name):")
        self.autologinText = wx.TextCtrl(self, wx.ID_ANY, self.settings.autologinMachine)
        self.autologinText.SetToolTipString(HELP_SU_AUTOLOGIN)
        self.autologinText.SetMinSize((150, -1))
        
        # add widgets to the boxSizer
        boxSizer.Add(hostLabel, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT | wx.ALL, 5)
        boxSizer.Add(self.hostText, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT | wx.RIGHT | wx.BOTTOM | wx.TOP, 5)
        boxSizer.Add((10,10))
        boxSizer.Add(portLabel, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT | wx.ALL, 5)
        boxSizer.Add(self.portText, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT | wx.RIGHT | wx.BOTTOM | wx.TOP, 5)

        # autologin sizer
        loginSizer = wx.BoxSizer(wx.HORIZONTAL)
        loginSizer.Add(autologinLabel, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT | wx.ALL, 5)
        loginSizer.Add(self.autologinText, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT | wx.ALL, 5)
        
        # add the box to the main sizer
        self.mainSizer.Add(boxSizer, 0, wx.EXPAND | wx.ALL, 10)
        self.mainSizer.Add(loginSizer, 0, wx.EXPAND | wx.ALL, 10)
        ComponentFrame.MakeWidgets(self)   # call this last


    def OnClose(self, evt):
        """ save stuff here """
        self.settings.host = self.hostText.GetValue()
        self.settings.port = int(self.portText.GetValue())
        self.settings.autologinMachine = self.autologinText.GetValue()
        saveSettings()
        evt.Skip()



class SageFrame(ComponentFrame):
    def __init__(self, parent):
        ComponentFrame.__init__(self, parent, SAGE)
        self.MakeWidgets()
        self.Show()

        
    def MakeWidgets(self):
        box1 = wx.StaticBox(self, wx.ID_ANY, "ON SAGE STARTUP")
        box1.SetForegroundColour(wx.BLUE)
        makeBiggerBoldFont( box1 )
        box1Sizer = wx.StaticBoxSizer( box1, wx.VERTICAL )

        box2 = wx.StaticBox(self, wx.ID_ANY, "ON SAGE SHUTDOWN")
        box2.SetForegroundColour(wx.BLUE)
        makeBiggerBoldFont( box2 )
        box2Sizer = wx.StaticBoxSizer( box2, wx.VERTICAL )

        # start stuff
        startLabel = wx.StaticText(self, wx.ID_ANY, "Specify any additional commands to be executed before SAGE starts")
        self.start = wx.TextCtrl(self, wx.ID_ANY, self.settings.onStart, style=wx.TE_MULTILINE)
        self.start.SetToolTipString(HELP_S_START)
        box1Sizer.AddSpacer((10,10)) 
        box1Sizer.Add(startLabel, 0, wx.EXPAND | wx.ALIGN_LEFT | wx.ALL, 5)
        box1Sizer.Add(self.start, 1, wx.EXPAND | wx.ALIGN_LEFT | wx.ALL, 5)

        # stop stuff
        stopLabel = wx.StaticText(self, wx.ID_ANY, "Specify any additional commands to be executed after SAGE is stopped")
        self.stop = wx.TextCtrl(self, wx.ID_ANY, self.settings.onStop, style=wx.TE_MULTILINE)
        self.stop.SetToolTipString(HELP_S_STOP)
        procLabel = wx.StaticText(self, wx.ID_ANY, "List all processes to be killed on the nodes and the master during SAGE shutdown")
        self.proc = wx.TextCtrl(self, wx.ID_ANY, self.settings.toKill)
        self.proc.SetToolTipString(HELP_S_PROC)
                
        box2Sizer.AddSpacer((10,10)) 
        box2Sizer.Add(stopLabel, 0, wx.EXPAND | wx.ALIGN_LEFT | wx.ALL, 5)
        box2Sizer.Add(self.stop, 1, wx.EXPAND | wx.ALIGN_LEFT | wx.ALL, 5)
        box2Sizer.AddSpacer((20,20)) 
        box2Sizer.Add(procLabel, 0, wx.EXPAND | wx.ALIGN_LEFT | wx.ALL, 5)
        box2Sizer.Add(self.proc, 0, wx.EXPAND | wx.ALIGN_LEFT | wx.ALL, 5)

        self.mainSizer.Add(box1Sizer, 1, wx.EXPAND | wx.ALL, 15)
        self.mainSizer.Add(box2Sizer, 1, wx.EXPAND | wx.ALL, 15)
        ComponentFrame.MakeWidgets(self)   # call this last


    def OnClose(self, evt):
        """ save stuff here """
        self.settings.onStop = self.stop.GetValue().strip()
        self.settings.onStart = self.start.GetValue().strip()
        self.settings.toKill = self.proc.GetValue().strip()
        saveSettings()
        evt.Skip()



        

###
### the following are the main frame UI components
###
        
class ComponentSummary(wx.Panel):
    """ this is the container for one SAGE component...
        it has 3 widgets: name, run checkbox and edit button
    """
    def __init__(self, parent, componentType):
        wx.Panel.__init__(self, parent, wx.ID_ANY, style=wx.SIMPLE_BORDER)
        self.color = wx.Colour(252,172,130)
        self.componentType = componentType
        self.SetMinSize((250,70))
        self.SetMaxSize((250,70))
        self.settings = components[componentType].settings
        self.MakeWidgets()
        
        # for selecting the component on click
        self.Bind(wx.EVT_LEFT_DOWN, self.OnRunCheck)
        self.name.Bind(wx.EVT_LEFT_DOWN, self.OnRunCheck)
        self.SetBackgroundColour(self.color)
        
        # where the console output will be printed
        # it's a child of the whole ComponentsPanel
        # since it's placed inside a sizer there
        self.output = wx.TextCtrl(self.GetParent().outputNotebook, wx.ID_ANY, style=wx.TE_MULTILINE | wx.TE_READONLY)
        self.output.SetMinSize((800, 300))
        self.output.SetMaxLength(MAX_TEXT_LEN)
        components[componentType].output = self.output

        # the process tied with the component
        components[componentType].process = Process(componentType)


    def ChangeColor(self, newColor):
        self.color = newColor
        self.SetBackgroundColour(self.color)
        self.run.faceDnClr = self.color
        self.Refresh()
        

    def MakeWidgets(self):    
        # make all the widgets
        self.MakeName()
        self.MakeRun()
        self.MakeEdit()
        self.MakeStopBtn()
        
        # add the widgets to the sizers
        vSizer = wx.BoxSizer(wx.VERTICAL)
        hSizer = wx.BoxSizer(wx.HORIZONTAL)
        hSizer2 = wx.BoxSizer(wx.HORIZONTAL)

        hSizer.Add(self.run, 0, wx.ALIGN_LEFT | wx.ALL, 0)
        hSizer.Add(self.name, 1, wx.ALIGN_LEFT | wx.ALL, 5)

        hSizer2.Add(self.stopBtn, 0, wx.ALIGN_RIGHT | wx.RIGHT, 20)
        hSizer2.Add(self.editBtn, 0, wx.ALIGN_RIGHT | wx.RIGHT, 3)
        
        vSizer.Add(hSizer, 1, wx.ALIGN_TOP | wx.ALIGN_LEFT | wx.ALL, 3)
        vSizer.Add(hSizer2, 0, wx.ALIGN_BOTTOM | wx.ALIGN_RIGHT | wx.BOTTOM, 1)

        self.SetSizer(vSizer)


    def MakeStopBtn(self):
        self.stopBtn = buttons.GenBitmapButton(self, wx.ID_ANY, getStopBitmap(), style=wx.BORDER_NONE)
        self.stopBtn.faceDnClr = self.color
        self.stopBtn.SetBestSize((24,24))
        self.stopBtn.Bind(wx.EVT_BUTTON, self.OnStopBtn)
        self.stopBtn.SetToolTipString(HELP_COMP_STOP)
           
    def MakeName(self):
        self.name = wx.StaticText(self, wx.ID_ANY, self.componentType)
        makeBoldFont(self.name)
        try: self.name.Wrap(150)  # wrap the text if longer than 150 pixels
        except: pass
        help = ""
        if self.componentType == APP_LAUNCHER:
            help = HELP_AL
        elif self.componentType == FILE_SERVER:
            help = HELP_FS
        elif self.componentType == SAGE_UI:
            help = HELP_SU
        elif self.componentType == SAGE_PROXY:
            help = HELP_SP
        elif self.componentType == SAGE:
            help = HELP_S
        self.name.SetToolTipString(help)
        self.SetToolTipString(help)


    def MakeRun(self):
        bmp = getRunBitmap(self.settings.doRun)
        self.run = buttons.GenBitmapButton(self, wx.ID_ANY, bmp, style=wx.BORDER_NONE)
        self.run.SetBitmapSelected(bmp)
        self.run.Bind(wx.EVT_BUTTON, self.OnRunCheck)
        self.run.SetToolTipString(HELP_RUN)
        self.run.faceDnClr = self.color
        
                
    def MakeEdit(self):
        self.editBtn = wx.Button(self, wx.ID_ANY, "Settings")
        self.editBtn.Bind(wx.EVT_BUTTON, self.OnEdit)
        self.editBtn.SetToolTipString(HELP_EDIT)


    def OnEdit(self, evt):
        if self.componentType == APP_LAUNCHER:
            frame = AppLauncherFrame(self)
        elif self.componentType == FILE_SERVER:
            frame = FileServerFrame(self)
        elif self.componentType == SAGE_PROXY:
            frame = SageProxyFrame(self)
        elif self.componentType == SAGE_UI:
            frame = SageUIFrame(self)
        elif self.componentType == SAGE:
            frame = SageFrame(self)


    def OnRunCheck(self, evt):
        self.settings.doRun = not self.settings.doRun # reverse the value 
        bmp = getRunBitmap(self.settings.doRun)
        self.run.SetBitmapLabel(bmp, False)
        self.run.SetBitmapSelected(bmp)
        self.run.Refresh()


    def OnStopBtn(self, evt):
        components[self.componentType].process.stop()






class ComponentsPanel(scrolled.ScrolledPanel):
    """ this holds the summaries for each component on the main frame """

    def __init__(self, parent):
        scrolled.ScrolledPanel.__init__(self, parent, wx.ID_ANY)
        self.MakeWidgets()


    def ChangeAllColors(self, newColor):
        for c in self.compSummary.itervalues():
            c.ChangeColor(newColor)


    def MakeWidgets(self):
        mainSizer = wx.BoxSizer( wx.HORIZONTAL )
        compSizer = wx.BoxSizer( wx.VERTICAL )

        # notebook
        self.outputNotebook = wx.Notebook(self, wx.ID_ANY, style=wx.NO_BORDER)

        # component objects
        self.compSummary = {}
        for componentType, c in components.iteritems():
            self.compSummary[componentType] = ComponentSummary(self, componentType)

        # add components to the compSizer
        label = wx.StaticText(self, wx.ID_ANY, "Components to Start:")
        makeBoldFont(label)
        compSizer.Add(label, 0, wx.EXPAND | wx.TOP | wx.LEFT, 10)
        for cName in componentNames:
            c = self.compSummary[cName]
            compSizer.Add(c, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.ALIGN_TOP | wx.ALL, 10)
            self.outputNotebook.AddPage(c.output, cName)  # add the notebook pages
            
        # run controls
        self.runPanel = RunPanel(self)
        compSizer.Add(self.runPanel, 1, wx.EXPAND | wx.ALIGN_CENTER_HORIZONTAL | wx.ALIGN_TOP | wx.ALL, 5)

        # create the output label and sizer
        self.outLabel = wx.StaticText(self, wx.ID_ANY, "Output from:")
        makeBoldFont(self.outLabel)
        self.outSizer = wx.BoxSizer(wx.VERTICAL)
        self.outSizer.Add(self.outLabel, 0, wx.EXPAND | wx.TOP | wx.LEFT, 15)
        self.outSizer.Add(self.outputNotebook, 1, wx.EXPAND | wx.TOP | wx.LEFT | wx.BOTTOM, 5)

        # add the stuff to the main sizer
        mainSizer.Add(compSizer, 0, wx.EXPAND | wx.ALIGN_LEFT | wx.ALL, 5)
        mainSizer.Add(self.outSizer, 1, wx.EXPAND | wx.LEFT | wx.BOTTOM, 15)

        # select the default component
        self.SetSizerAndFit(mainSizer)
        self.SetAutoLayout(1)
        self.SetupScrolling()




class RunPanel(wx.Panel):
    """ the run panel on the main frame for starting and stopping sage """

    def __init__(self, parent):
        wx.Panel.__init__(self, parent, wx.ID_ANY)
        self.MakeWidgets()

        
    def MakeWidgets(self):
        mainSizer = wx.BoxSizer( wx.VERTICAL )
        boxSizer = wx.BoxSizer( wx.HORIZONTAL )

        # add components to the boxSizer
        self.runBtn = wx.Button(self, 1, "START")
        self.runBtn.Bind(wx.EVT_BUTTON, self.OnRun)
        self.runBtn.Bind(wx.EVT_ENTER_WINDOW, self.OnMouseEnterWindow)
        self.runBtn.Bind(wx.EVT_LEAVE_WINDOW, self.OnMouseLeaveWindow)
        makeBiggerBoldFont(self.runBtn)
        makeBiggerFont(self.runBtn)

        self.stopBtn = wx.Button(self, 2, "STOP")
        self.stopBtn.Bind(wx.EVT_BUTTON, self.OnStop)
        self.stopBtn.Bind(wx.EVT_ENTER_WINDOW, self.OnMouseEnterWindow)
        self.stopBtn.Bind(wx.EVT_LEAVE_WINDOW, self.OnMouseLeaveWindow)
        makeBiggerBoldFont(self.stopBtn)
        makeBiggerFont(self.stopBtn)

        self.helpNote = wx.StaticText(self, wx.ID_ANY, "\n", style=wx.ALIGN_CENTRE)
        self.helpNote.SetMinSize((-1, 30))

        self.simpleBtn = hl.HyperLinkCtrl(self, wx.ID_ANY, "<- Simple Mode")
        self.simpleBtn.SetBackgroundColour(self.GetBackgroundColour())
        self.simpleBtn.AutoBrowse(False)
        self.simpleBtn.Bind(hl.EVT_HYPERLINK_LEFT, self.OnSimple)

        boxSizer.Add(self.runBtn, 0, wx.ALIGN_CENTER | wx.TOP | wx.RIGHT, 15)
        boxSizer.Add(self.stopBtn, 0, wx.ALIGN_CENTER | wx.TOP | wx.LEFT, 15)

        mainSizer.Add(boxSizer, 0, wx.ALIGN_CENTER)
        mainSizer.Add(self.helpNote, 0, wx.EXPAND | wx.ALIGN_CENTER_HORIZONTAL | wx.ALIGN_TOP | wx.ALL, 5)
        mainSizer.AddSpacer((10,10), 1)
        mainSizer.Add(self.simpleBtn, 0, wx.ALIGN_BOTTOM | wx.ALIGN_LEFT | wx.ALL, 10)
    
        self.SetSizerAndFit(mainSizer)


    def OnSimple(self, evt):
        wx.GetApp().GetTopWindow().advancedFrame.Hide()
        wx.GetApp().GetTopWindow().Show()


    def OnMouseEnterWindow(self, evt):
        if evt.GetId() == 1:
            self.helpNote.SetLabel("Start all the checked components\nthat are not already running.")
        else:
            self.helpNote.SetLabel("Stop all the components that are\nnot running in the background.")
        evt.Skip()
        

    def OnMouseLeaveWindow(self, evt):
        self.helpNote.SetLabel("")
        self.GetSizer().Layout()
        evt.Skip()
            

    def OnRun(self, evt):
        """ start all the checked processes... but start sage before everything else
            because some components need sage running already
        """

        # first start sage and then sleep for a few seconds
        sage = components[SAGE]
        if sage.settings.doRun:
            sage.process.start()
            time.sleep(2)

        # now start the rest of the components
        for c in components.itervalues():
            if c.componentType != SAGE and c.settings.doRun:
                c.process.start()
        saveSettings()  # to save the changed PIDs
        

    def OnStop(self, evt):
        for c in components.itervalues():
            if not c.settings.inBG:
                c.process.stop()
        saveSettings()  # to save the changed PIDs
        




class QuickFrame(wx.Frame):
    def __init__(self):
        wx.Frame.__init__(self, None, wx.ID_ANY, "SAGE Launcher",
                          style=wx.SYSTEM_MENU | wx.CAPTION | wx.CLOSE_BOX | wx.CLIP_CHILDREN)
        self.SetBackgroundColour(wx.Colour(14,51,51))
        #self.SetClientSize((373, 315))
        self.SetMinSize((377, 315))
        self.MakeWidgets()
        self.SetThemeEnabled(False)
        self.SetIcon(getSageIcon())
        self.Bind(wx.EVT_CLOSE, self.OnClose)
        self.Centre()
        self.Show()
        

    def MakeWidgets(self):
        ms = wx.BoxSizer(wx.VERTICAL)
        self.panel = wx.Panel(self, wx.ID_ANY)
        self.panel.SetBackgroundColour(self.GetBackgroundColour())
        self.panel.Bind(wx.EVT_PAINT, self.OnPaint)
        ms.Add(self.panel, 1, wx.EXPAND)
        
        self.runBtn = buttons.GenBitmapButton(self.panel, 1, getSageStartUpBitmap(), style=wx.BORDER_NONE)
        self.runBtn.SetBitmapSelected(getSageStartDownBitmap())
        self.runBtn.faceDnClr = self.GetBackgroundColour()
        self.runBtn.Bind(wx.EVT_BUTTON, self.OnRun)
            
        self.stopBtn = buttons.GenBitmapButton(self.panel, 2, getSageStopUpBitmap(), style=wx.BORDER_NONE)
        self.stopBtn.SetBitmapSelected(getSageStopDownBitmap())
        self.stopBtn.faceDnClr = self.GetBackgroundColour()
        self.stopBtn.Bind(wx.EVT_BUTTON, self.OnStop)

        self.advancedBtn = hl.HyperLinkCtrl(self.panel, wx.ID_ANY, "Advanced Mode ->")
        self.advancedBtn.SetBackgroundColour(self.GetBackgroundColour())
        self.advancedBtn.SetForegroundColour(wx.Colour(103,153,102))
        self.advancedBtn.AutoBrowse(False)
        self.advancedBtn.Bind(hl.EVT_HYPERLINK_LEFT, self.OnAdvanced)
        
        btnSizer = wx.BoxSizer(wx.HORIZONTAL)
        btnSizer.Add(self.runBtn, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.ALIGN_BOTTOM | wx.TOP | wx.RIGHT, 15)
        btnSizer.Add(self.stopBtn, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.ALIGN_BOTTOM | wx.TOP | wx.LEFT, 15)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add((150,150))
        sizer.Add(self.MakeStatesPanel(self.panel), 0, wx.ALIGN_CENTER_HORIZONTAL | wx.ALIGN_BOTTOM | wx.ALL, 10)
        sizer.Add(btnSizer, 1, wx.ALIGN_CENTER_HORIZONTAL | wx.ALIGN_BOTTOM | wx.ALL, 10)
        sizer.Add(self.advancedBtn, 0, wx.ALIGN_BOTTOM | wx.ALIGN_RIGHT | wx.ALL, 10)

        self.panel.SetSizer(sizer)
        self.SetSizer(ms)
        self.Fit()


    def MakeStatesPanel(self, parent):
        def OnSelectedRadioButton(evt):
            session = evt.GetEventObject().GetLabel()
            if session == "New session":
                session = ""
            components[SAGE_UI].settings.loadState = session

        stateHash = self.GetStateList()
        
        statesPanel = scrolled.ScrolledPanel(parent, wx.ID_ANY, size=(200,200))
        statesPanel.SetBackgroundColour(wx.Colour(14,51,51))
        statesPanel.SetForegroundColour(wx.Colour(200,200,200))
        sizer = wx.BoxSizer(wx.VERTICAL)

        # add the default radio button
        choices = {}
        states = stateHash.keys()
        states.sort()
        defaultBtn = wx.RadioButton(statesPanel, -1, "New session", style=wx.RB_GROUP)
        defaultBtn.Bind(wx.EVT_RADIOBUTTON, OnSelectedRadioButton, defaultBtn)
        #defaultBtn.SetBackgroundColour(wx.Colour(14,51,51))
        #defaultBtn.SetForegroundColour(wx.Colour(200,200,200))
        defaultBtn.SetToolTipString("Empty display wall with nothing running")
        choices["new"] = defaultBtn
        sizer.Add(defaultBtn, 0, wx.ALIGN_LEFT | wx.ALIGN_TOP | wx.TOP, border=5)
        sizer.Add(wx.StaticLine(statesPanel, -1), 0, wx.EXPAND | wx.ALL, border=5)

        # add the rest of them
        if len(stateHash) == 0:
            t = wx.StaticText(statesPanel, wx.ID_ANY, "Any sessions you save through SAGE UI will show up here.")
            try: t.Wrap(200)
            except: pass
            sizer.Add(t, 0, wx.ALIGN_LEFT | wx.ALIGN_TOP | wx.BOTTOM | wx.TOP, border=2)
            
        for stateName in states:
            btn = wx.RadioButton(statesPanel, wx.ID_ANY, stateName)
            btn.SetToolTipString(stateHash[stateName])
            #btn.SetBackgroundColour(wx.Colour(14,51,51))
            #btn.SetForegroundColour(wx.Colour(200,200,200))
            choices[stateName] = btn
            btn.Bind(wx.EVT_RADIOBUTTON, OnSelectedRadioButton, btn)
            sizer.Add(btn, 0, wx.ALIGN_LEFT | wx.ALIGN_TOP | wx.BOTTOM | wx.TOP, border=2)

        choices["new"].SetValue(True)
        components[SAGE_UI].settings.loadState = ""

        statesPanel.SetSizer(sizer)
        statesPanel.SetAutoLayout(1)
        statesPanel.SetupScrolling(scroll_x = False)
        
        return statesPanel


    def GetStateList(self):
        """ returns a hash of key=stateName, value=description """
        savedStatesDir = getUserPath("saved-states")
        stateHash = {}
        appList = []
        description = ""

        if not os.path.isdir(savedStatesDir):
            return {}
        
        # load all the states and read descriptions from them
        for fileName in os.listdir(savedStatesDir):
            filePath = opj(savedStatesDir, fileName)
            if os.path.isfile(filePath) and os.path.splitext(filePath)[1] == ".state":
                try:
                    stateName = os.path.splitext( os.path.split(filePath)[1] )[0]
                    f = open(filePath, "rb")
                    (description, appList) = pickle.Unpickler(f).load()
                    f.close()
                    stateHash[stateName] = description
                except:
                    print "\nUnable to read saved state file: "+filePath
                    continue

        return stateHash
        

    def OnPaint(self, evt):
        dc = wx.PaintDC(self.panel)
        self.Redraw(dc)


    def Redraw(self, dc=None):
        if not dc:
            dc = wx.ClientDC(self.panel)
        dc.DrawBitmap(getSageBitmap(), 0, 0, False)
        
        
    def OnClose(self, evt):
        saveSettings()

        # stop all the read threads from the executed processes
        for c in components.itervalues():
            c.process.stopRead()
        
        evt.Skip()


    def OnAdvanced(self, evt):
        self.Hide()
        self.advancedFrame.Show()


    def OnRun(self, evt):
        """ start all the checked processes... but start sage before everything else
            because some components need sage running already
        """

        # first start sage and then sleep for a few seconds
        sage = components[SAGE]
        if sage.settings.doRun:
            sage.process.start()
            time.sleep(2)

        # now start the rest of the components
        for c in components.itervalues():
            if c.componentType != SAGE and c.settings.doRun:
                c.process.start()
        saveSettings()  # to save the changed PIDs
        

    def OnStop(self, evt):
        for c in components.itervalues():
            if not c.settings.inBG:
                c.process.stop()
        saveSettings()  # to save the changed PIDs
        





class AdvancedFrame(wx.Frame):
    def __init__(self, parent):
        wx.Frame.__init__(self, parent, wx.ID_ANY, "SAGE Launcher - Advanced Settings")
        self.MakeWidgets()
        self.SetThemeEnabled(False)
        self.SetIcon(getSageIcon())
        self.Bind(wx.EVT_CLOSE, self.OnClose)
            
        # a hack to get correct frame colour on Windows
        if isWin():
            global colour
            colour = self.componentsPanel.GetBackgroundColour()
            self.SetBackgroundColour(colour)


    def MakeWidgets(self):
        sizer = wx.BoxSizer(wx.VERTICAL)
        
        # set up tooltips globally
        tt = wx.ToolTip("")
        tt.SetDelay(500)
        tt.Enable(True)
        
        t = HELP_INTRO
        introText = wx.StaticText(self, wx.ID_ANY, t)
        
        self.componentsPanel = ComponentsPanel(self)
        sizer.Add(introText, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 20)
        sizer.Add(self.componentsPanel, 1, wx.EXPAND | wx.ALL, 10)
        self.SetSizerAndFit(sizer)


    def OnClose(self, evt):
        self.GetParent().Close()



 
# --------------------------------------------------------
#
#                  MAIN ENTRY POINT 
#
# --------------------------------------------------------


def main():
    """ main called at the bottom of this file """

    # load the settings before everything else
    settings = loadSettings()  # a hash comes back

    # read the tile config
    global tileConfig
    tileConfig = TileConfig(getTileConfig())

    # create the Component objects and set their settings
    global components
    for componentType in componentNames:
        c = Component(componentType)
        c.settings = settings[componentType]
        components[componentType] = c
        
    # create our GUI
    app = wx.App(redirect = False)
    quickFrame = QuickFrame()
    advancedFrame = AdvancedFrame(quickFrame)
    quickFrame.advancedFrame = advancedFrame
    app.SetTopWindow( quickFrame )

    # start the app
    app.MainLoop()












# --------------------------------------------------------
#
#            MISCELLANEOUS HELPER CLASSES
#
# --------------------------------------------------------




class Process:
    """ there is one instance of this class for each component
        that is running (or needs to run). It starts the process
        itself and creates a thread to read data from that
        process.
    """
    def __init__(self, componentType):
        self.componentType = componentType
        self.settings = components[componentType].settings
        self.output = components[componentType].output
        self.running = False
        self.p = None    # Popen process object
        self.t = None    # thread reading the output from the process
        self._extraProcesses = []  # pids of extra processes started before SAGE


    def start(self):
        """ if the process is already running do nothing...
            otherwise launch the new process and 
        """
        if self.isAlive():
            self.output.SetInsertionPointEnd()
            self.output.WriteText("\n\n**** Already running ****\n\n")
        else:
            cmd = self.settings.getStartCommand()
            cwdir = self.settings.getCwd()

            try:
                # execute any extra commands first
                self.__startExtra()
                
                self.p = sp.Popen(cmd, stdout=sp.PIPE, stderr=sp.STDOUT, bufsize=1, cwd=cwdir)
                self.t = Thread(target=self.__readOutput)
                self.t.setDaemon(True)
                self.doRead = True
                self.t.start()
                self.running = True
                self.settings.pid = self.p.pid  # save the pid for later
                
            except:
                print " ***** Error while starting", self.componentType
                print "".join(tb.format_exception(sys.exc_info()[0], sys.exc_info()[1], sys.exc_info()[2]))
                self.running = False
                self.doRead = False
                self.t = None
                self.p = None


    def __startExtra(self):
        """ if the component has any extra commands to execute
            before startup, this will start them """
        if hasattr(self.settings, 'onStart'):
            if self.settings.onStart != "":
                for cmd in self.settings.onStart.splitlines():
                    if not cmd.strip().startswith("#"):
                        proc = sp.Popen(cmd.split())
                        self._extraProcesses.append(proc.pid)  # save the pid for later killing
        

    def stop(self):
        """ stops the read thread and the process """
        try:
            # kill SAGE unconditionally
            if self.componentType == SAGE:
                for c in self.settings.getKillCmd():
                    sp.Popen(c)

                # kill extra stuff started before sage
                for pid in self._extraProcesses:
                    self.__killProcess(pid)
                self._extraProcesses = []
                

            # kill appLauncher unconditionally (because we can)
            elif self.componentType == APP_LAUNCHER:
                sp.Popen(self.settings.getKillCmd(), cwd=self.settings.getCwd())

            # kill the other processes depending on whether they are running or not
            elif self.isAlive():

                # get the pid from the current object or from the saved settings
                if self.p:    pid = self.p.pid
                else:         pid = self.settings.pid

                # execute a kill command
                self.__killProcess(pid)

            # execute any extra commands
            self.__stopExtra()
            
        except:
            print " ***** Error while stopping",self.componentType
            print "".join(tb.format_exception(sys.exc_info()[0], sys.exc_info()[1], sys.exc_info()[2]))
            
        self.settings.pid = -1
        self.running = False
        self.doRead = False
        self.p = None
        self.t = None


    def __stopExtra(self):
        """ if the component has any extra commands to execute
            after stopping, this will execute them """
        if hasattr(self.settings, 'onStop'):
            if self.settings.onStop != "":
                for cmd in self.settings.onStop.splitlines():
                    sp.Popen(cmd.split())


    def isAlive(self):
        """ return true if the process is currently running, false otherwise """
        if self.running or  \
           (self.p and (self.p.poll() is None)) or \
           self.settings.pid != -1:

            # if it's presumably running but its process object is dead,
            # it's a zombie so report it as dead and close it's read thread
            if self.p and not (self.p.poll() is None):
                self.stopRead()
                if self.t: self.t.join(1) # wait for the old read thread to die
                return False
            
            return True

        else:
            return False


    def __killProcess(self, pid):
        """ execute a kill command depending on the OS
            the Windows version will only work on XP
        """
        if isWin():
            sp.Popen(["taskkill", "/F", "/PID", str(pid)])
        else:
            sp.Popen(["/bin/kill", "-9", str(pid)])
                

    def stopRead(self):
        self.doRead = False
        
    
    def __readOutput(self):
        """ this runs in a thread and it checks for the output
            from the executed process. Once the output comes in,
            it tells the main wx thread to add the text that was
            just read.
        """
        while self.doRead:
            txt = os.read(self.p.stdout.fileno(), 2048)
            wx.CallAfter(self.fillText, txt)
            time.sleep(0.3)   # read at most twice / sec


    def fillText(self, txt):
        """ first check whether the text we are about to insert
            will overflow the control or not. If it would, remove
            some text from the beginning and then append the
            new text. If not, just append the new text.
        """
        if len(txt) + self.output.GetLastPosition() > MAX_TEXT_LEN:
            self.output.Remove(0, 2048)
        self.output.SetInsertionPointEnd()
        self.output.WriteText(txt)






class FoldBar(wx.Panel):
    """ This class represents the fold bar title for the individual
        application configuration in the app launcher frame.
        When clicked it expands/collapses the sizer that's holding the actual controls
        for this section. It does that through the callback that's passed to this panel
    """
    
    def __init__(self, parent, btnId, title, callback):
        wx.Panel.__init__(self, parent, wx.ID_ANY, style = wx.NO_BORDER)
        label = wx.StaticText(self, wx.ID_ANY, title)
        label.Bind(wx.EVT_LEFT_DOWN, self.OnBtn)
        makeBoldFont(label)
        self.btn = buttons.GenBitmapButton(self, btnId, GetCollapsedIconBitmap(), style=wx.BORDER_NONE)
        self.btn.Bind(wx.EVT_BUTTON, self.OnBtn)

        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(label, 0, wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL)
        sizer.Add(self.btn, 0, wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL)
        self.SetSizer(sizer)
        self.Fit()

        self.callback = callback
        self.collapsed = True
        
        
    def OnBtn(self, evt):
        if self.collapsed:
            self.collapsed = False
            self.btn.SetBitmapLabel(GetExpandedIconBitmap())
            self.btn.Refresh()
            self.callback(self.btn.GetId(), False)
        else:
            self.collapsed = True
            self.btn.SetBitmapLabel(GetCollapsedIconBitmap())
            self.btn.Refresh()
            self.callback(self.btn.GetId(), True)





####                                        #####  
####       TILE CONFIGURATION CLASSES       #####
####                                        #####

class Tile:
    """ describes one tile """

    def __init__(self):
        self.name = "node"
        self.ip = "127.0.0.1"
        self.numMonitors = 0
        self.monitors = []  # a list of positions for each monitor (tuples)


    def addMonitor(self, pos):
        if pos in self.monitors:
            return
        self.monitors.append(pos)
        self.numMonitors += 1


    def delMonitor(self, pos):
        if pos in self.monitors:
            self.monitors.remove(pos)
            self.numMonitors -= 1


    def toString(self):
        s = "\n\nDisplayNode\n"
        s += "\tName %s\n" % self.name
        s += "\tIP %s\n" % self.ip
        s += "\tMonitors %s " %self.numMonitors
        for m in self.monitors:
            s += str(m) + " "

        return s



        

class TileConfig:
    """ describes the whole tiled display configuration """

    def __init__(self, configName):
        self.dim = [1,1]                # dimensions of the display (xTiles, yTiles)
        self.mullions = ["0.75", "0.75", "0.75", "0.75"]  # mullions on top, down, left, right
        self.resolution = [800, 600]    # of each tile in pixels
        self.ppi = 72                   # pixels-per-inch of each tile
        self.numMachines = 1            # total number of machines in the display
        self.tiles = {}                 # key=IP, value=Tile object
        self.readConfigFile(configName)


    def getAllIPs(self):
        return self.tiles.keys()
        

    def readConfigFile(self, filename):
        f = open(filename, "r")
        lines = f.readlines()
        f.close()

        # reinitialize variables
        self.tiles = {}
        currentTile = None

        # read the file line by line
        for line in lines:

            if '#' in line:     # allow comments with # anywhere in the line
                line = line.split('#')[0].strip()
            line = line.strip()

            if 'Dimensions' in line:
                d = line.lstrip('Dimensions').strip().split(' ',1)
                self.dim = [int(d[0]), int(d[1])]

            elif 'Mullions' in line:
                m = line.lstrip('Mullions').strip().split(' ',3)
                self.mullions = [m[0], m[1], m[2], m[3]]

            elif 'Resolution' in line:
                r = line.lstrip('Resolution').strip().split(' ',1)
                self.resolution = [int(r[0]), int(r[1])]

            elif 'PPI' in line:
                self.ppi = int( float ( line.lstrip('PPI').strip() ) )
            
            elif 'Machines' in line:
                self.numMachines = int( line.lstrip('Machines').strip() )


            # reading the tiles
            elif 'DisplayNode' in line:
                if currentTile:  # store the previous Tile if exists
                    self.tiles[ currentTile.ip ] = currentTile
                currentTile = Tile()

            elif 'Name' in line:
                currentTile.name = line.lstrip('Name').strip()

            elif 'IP' in line:
                currentTile.ip = line.lstrip('IP').split(":")[0].strip()

            elif 'Monitors' in line:
                (num, positions) = line.lstrip('Monitors').strip().split(' ', 1)
                nums = positions.replace('(', ' ').replace(')', ' ').replace(',', ' ').split()
                for i in range(0, len(nums)-1, 2):
                    currentTile.addMonitor( (int(nums[i]),int(nums[i+1])) )

        # add the last one
        self.tiles[ currentTile.ip ] = currentTile

        

    def writeConfigFile(self):
        # first the global stuff
        s = "TileDisplay\n"
        s += "\tDimensions %d %d\n" % (self.dim[0], self.dim[1])
        s += "\tMullions %s %s %s %s\n" % (self.mullions[0], self.mullions[1],
                                           self.mullions[2], self.mullions[3])
        s += "\tResolution %d %d\n" % (self.resolution[0], self.resolution[1])
        s += "\tPPI %d\n" % self.ppi
        s += "\tMachines %d\n" % self.numMachines

        # now each node
        for t in self.tiles.itervalues():
            s += t.toString()

        return s
    
        
    
        

####                                        #####  
####   APP LAUNCHER CONFIGURATION CLASSES   #####
####                                        #####
class OneConfig:
    ''' describes one configuration for an app '''
    
    def __init__(self, name, appName, dynamic=False):
        self._configName = name
        self._dynamic = dynamic     # dynamic config???
        self._appName = appName
        self._configFilename = appName+".conf"
        self._launcherId = ""

        self._binDir = "$SAGE_DIRECTORY/bin/"  # where the binary resides - this is where the config is copied to
        self._nodeNum = 1
        self._position = (100, 100)        # initial position of the window on SAGE
        self._size = (1000, 1000)          # initial size of the window on SAGE
        self._command = ""                 # the actual command used to start the application
        self._targetMachine = "127.0.0.1"           # the render machine where the app will be started
        self._protocol = "TCP"
        self._masterIP = None              # the master machine of a parallel application
        self._fsIP = None                  # which SAGE will the app connect to (if not using sageBridge)
        self._fsPort = None                # which SAGE will the app connect to (if not using sageBridge)
        self._useBridge = False            # if True the app will connect to sageBridge instead of fsManager
        self._bridgeIP = ""                # the machine for sage bridge
        self._bridgePort = ""              # the machine for sage bridge

        self._additionalParams = ""        # any additional parameters you want to specify... used for testing

        # audio stuff
        self._audioFile = ""
             
        self._nwID = 1
        self._msgPort = 23010
        self._syncPort = 13010
        self._nodeNum = 1
        self._appId = 0                    # the port number for the app on the render machine
        self._blockSize = (64,64)
        self._blockThreshold = 0
        self._streamType = "SAGE_BLOCK_HARD_SYNC"    # sync mode
        self._staticApp = False             # static applications dont refresh their windows so sage needs to keep the last frame
        self._runOnNodes = False    # if an app has to connect to the outside world or requires
                                    #an SDL/GLUT window for rendering then it can't run on the nodes
        

    def getName(self): return self._configName
    def getAppName(self): return self._appName
    def isDynamic(self): return self._dynamic
    def getConfigFilename(self): return self._configFilename

    # audio stuff
    def setAudioFile(self, f):
        self._audioFile = f
    def getAudioFile(self):
        return self._audioFile

  
    def getLauncherId(self):
        return self._launcherId
    def setLauncherId(self, launcherId):
        self._launcherId = launcherId

    def setBinDir(self, d):
        self._binDir = d
    def getBinDir(self):
        return self._binDir

    def setNodeNum(self, num): self._nodeNum = num
    def getNodeNum(self): return self._nodeNum

    def setPosition(self, pos): self._position = pos
    def getPosition(self): return self._position

    def setSize(self, size): self._size = size
    def getSize(self): return self._size

    def setCommand(self, command): self._command = command
    def getCommand(self): return self._command

    def setTargetMachine(self, target): self._targetMachine = target
    def getTargetMachine(self): return self._targetMachine

    def setProtocol(self, protocol):
        if protocol == "tvTcpModule.so" or protocol=="TCP":
            self._protocol = "TCP"
        else:
            self._protocol = "UDP"
    def getProtocol(self): return self._protocol

    def setMasterIP(self, ip):
        self._masterIP = ip
    def getMasterIP(self):
        return self._masterIP

    def setFSIP(self, ip):
        self._fsIP = ip
    def getFSIP(self):
        return self._fsIP
    
    def setFSPort(self, port):
        self._fsPort = port
    def getFSPort(self):
        return self._fsPort

    def setBridgeIP(self, ip):
        self._bridgeIP = ip
    def getBridgeIP(self):
        return self._bridgeIP

    def setBridgePort(self, port):
        self._bridgePort = port
    def getBridgePort(self):
        return self._bridgePort

    def setUseBridge(self, doUse):
        self._useBridge = doUse
    def getUseBridge(self):
        return self._useBridge

    def setNWId(self, id):
        self._nwID = id
    def getNWId(self):
        return self._nwID

    def setMsgPort(self, port):
        self._msgPort = port
    def getMsgPort(self):
        return self._msgPort

    def setSyncPort(self, port):
        self._syncPort = port
    def getSyncPort(self):
        return self._syncPort

    def setAppId(self, id):
        self._appId = id
    def getAppId(self):
        return self._appId

    def setBlockSize(self, size):
        self._blockSize = size
    def getBlockSize(self):
        return self._blockSize

    def setBlockThreshold(self, threshold):
        self._blockThreshold = threshold
    def getBlockThreshold(self):
        return self._blockThreshold

    def setStreamType(self, mode):
        self._streamType = mode
    def getStreamType(self):
        return self._streamType

    def setStaticApp(self, do):
        self._staticApp = do
    def getStaticApp(self):
        return self._staticApp

    def setRunOnNodes(self, run):
        self._runOnNodes = run
    def getRunOnNodes(self):
        return self._runOnNodes

    def setAdditionalParams(self, param):
        self._additionalParams += param + "\n"
    def getAdditionalParams(self):
        return self._additionalParams

    def writeToFile(self):
        s = ""

        # sage bridge stuff
        if self.getUseBridge():      # using sageBridge
            s += 'bridgeOn true\n'
            s += 'bridgeIP %s\n'% self.getBridgeIP()
            s += 'bridgePort %s\n'% self.getBridgePort()
        else:                        # not using sageBridge
            s += 'bridgeOn false\n'
            
        s += 'fsIP %s\n'% self.getFSIP()
        s += 'fsPort %s\n'% self.getFSPort()
        s += 'masterIP %s\n'% self.getMasterIP()
        s += 'nwID %d\n' % self.getNWId()
        s += 'msgPort %d\n' % self.getMsgPort()
        s += 'syncPort %d\n' % self.getSyncPort()
        s += 'nodeNum %d\n' % self.getNodeNum()
        s += 'appID %d\n' % self.getAppId()
        s += 'launcherID %s\n' % self.getLauncherId()
        s += 'pixelBlockSize %d %d\n' % (self.getBlockSize()[0], self.getBlockSize()[1])
        s += 'blockThreshold %d\n' % self.getBlockThreshold()
        s += 'winX %d\n' % self.getPosition()[0]
        s += 'winY %d\n' % self.getPosition()[1]
        s += 'winWidth %d\n' % self.getSize()[0]
        s += 'winHeight %d\n' % self.getSize()[1]
        s += 'streamType %s\n' % self.getStreamType()
        s += 'nwProtocol %s\n' % self.getProtocol()

        # audio
        if self.getAudioFile():
            s += 'audioOn true\n'
            s += 'audioFile %s\n' % self.getAudioFile()
            s += 'audioType read\ndeviceNum -1\n'
            s += 'framePerBuffer 512\n'
            
        # static app
        if self.getStaticApp():
            s += 'asyncUpdate true\n'
        else:
            s += 'asyncUpdate false\n'

        # additional params
        s += self.getAdditionalParams()
            
        f = open(self._configFilename, "w")
        f.write(s)
        f.close()


    def getConfigString(self):
        """ returns a tuple of strings: (configName, optionalArgs that the app was started with) """
        return (self.getName(), self.getCommand().split(" ", 1)[1].strip())

    
    def getAppLauncherConfig(self):
        """ this returns the appLauncher config format (for applications.conf)"""

        s = ""

        # common parameters
        s += 'configName %s\n' % self.getName()
        s += 'Init %d %d %d %d\n' % (self.getPosition()[0],
                                     self.getPosition()[1],
                                     self.getSize()[0],
                                     self.getSize()[1])
        s += 'exec %s %s\n' % (self.getTargetMachine(), self.getCommand())

        # now the optional parameters
        if self.getNodeNum() != 1:
            s += 'nodeNum %d\n' % self.getNodeNum()
        
        if self.getStaticApp():
            s += 'staticApp\n'

        if self.getProtocol() != "TCP":
            s += 'nwProtocol %s\n' % self.getProtocol()
            
        if self.getBinDir() != "$SAGE_DIRECTORY/bin/":
            s += 'binDir %s\n' % self.getBinDir()
            
        if self.getBridgeIP() != "":
            s += 'bridgeIP %s\n' % self.getBridgeIP()
            s += 'bridgePort %s\n' % self.getBridgePort()

        if self.getBlockSize() != (64,64):
            s += 'pixelBlockSize %s %s\n' % (self.getBlockSize()[0],
                                             self.getBlockSize()[1])
            
        if self.getMasterIP():
            s += 'masterIP %s\n' % self.getMasterIP()

        if self.getRunOnNodes():
            s += 'runOnNodes\n'
            
        if self.getStreamType() != "SAGE_BLOCK_HARD_SYNC":
            s += 'sync %s\n' % self.getStreamType()

        if self.getAudioFile():
            s += 'audioFile %s\n' % self.getAudioFile()

        s += self.getAdditionalParams()

        return s




class AppConfig:
    ''' a collection of all the configurations for an app '''
    
    def __init__(self, appName):
        self._configs = {}   #key=configName, value=OneConfig object
        self._appName = appName

    def getAppName(self):
        return self._appName

    def addConfig(self, oneConfig):
        self._configs[oneConfig.getName()] = oneConfig

    def addNewConfig(self, configName):
        cfg = OneConfig(configName, self._appName)
        self._configs[configName] = cfg

    def delConfig(self, configName):
        if configName in self._configs:
            del self._configs[configName]
        
    def getConfig(self, configName):
        return self._configs[configName]
    
    def getDefaultConfig(self):
        return self._configs.values()[0]  #return an arbitrary config file

    def getAllConfigs(self):
        return self._configs
    
    def getAllConfigNames(self):
        return self._configs.keys()
    
    def makeConfigFile(self, configName):
        config = self.getConfig(configName)
        config.writeToFile()



    

class AppConfigurations:
    ''' a collection of all applications and their configurations '''
    
    def __init__(self, configFile):
        self._configFile = configFile
        self._lastModTime = None  #last modification time to the config file
        # sageBridge stuff
        self._bridgeIP = None
        self._bridgePort = None

        self._appConfigs = {}   #key=appName, value=AppConfig object
        self._readConfig()
        #self._printConfig()


        # so that we can change the config file without restarting the appLauncher
        # checks the last modification time so that we don't reload unnecessarily
    def reloadConfigFile(self):
        try:
            lastModTime = os.path.getmtime(self._configFile)
            if lastModTime != self._lastModTime:
                self._appConfigs = {}  #empty out the hash
                self._readConfig()
                self._lastModTime = lastModTime
        except:
            WriteLog( "".join(tb.format_exception(sys.exc_info()[0], sys.exc_info()[1], sys.exc_info()[2])) )

    def addNewApp(self, appName):
        self._appConfigs[appName] = AppConfig(appName)

    def delApp(self, appName):
        if appName in self._appConfigs:
            del self._appConfigs[appName]
          
    def getConfig(self, appName, configName):   #returns a copy so that it can be safely modified without the destroying what's in the config file
        return self._appConfigs[appName].getConfig(configName)

    def getDefaultConfig(self, appName):   #returns a copy so that it can be safely modified without destroying what's in the config file
        return self._appConfigs[appName].getDefaultConfig()

    def getApp(self, appName):
        return self._appConfigs[appName]

    def getAppList(self):   # returns just the names of the apps
        return self._appConfigs.keys()

    def getBridgeIP(self):
        return self._bridgeIP

    def getBridgePort(self):
        return self._bridgePort

    def _printConfig(self):
        for name, app in self._appConfigs.iteritems():
            print "\n----------------------------------------"
            print "Config For: ", name
            for name, config in app.getAllConfigs().iteritems():
                print "Config: ", name
                print "nodeNum = ", config.getNodeNum()
                print "pos = ", config.getPosition()
                print "size = ", config.getSize()
                print "command = ", config.getCommand()
                print "target = ", config.getTargetMachine()
                print "protocol = ", config.getProtocol()
                print "runOnNodes = ", config.getRunOnNodes()

        print "\n----------------------------------------"
        print "bridgePort = ", self._bridgePort
        print "bridgeIP = ", self._bridgeIP


    def getConfigHash(self):
        """ returns a hash of all the configurations without the objects... just tuples of strings and ints """
        strHash = {}   #keyed by appName, value = a list of configNames
        for appName, app in self._appConfigs.iteritems():
            strHash[appName] = app.getAllConfigNames()
        return strHash
    
                
    def _readConfig(self):
        f = open(self._configFile, "r")
        lines = f.readlines()
        f.close()

        self.appconfig = None
        self.oneconfig = None
        self.lineCounter = 0
        
        for line in lines:
            self.lineCounter += 1

            # allow comments with #
            if '#' in line:
                line = line.split('#')[0].strip()
                
                
            if '{' in line:
                appName = line.replace('{', ' ').strip()
                self.appconfig = AppConfig(appName)
                
            elif 'configName' in line:
                if self.oneconfig:
                    self.appconfig.addConfig(self.oneconfig)
                self.oneconfig = OneConfig(line.lstrip('configName').strip(), self.appconfig.getAppName())

            elif 'nodeNum' in line:
                self.oneconfig.setNodeNum(int(line.lstrip('nodeNum').strip()))

            elif 'Init' in line:
                lineTokens = line.split()
                pos = (int(lineTokens[1]), int(lineTokens[2]))
                size = (int(lineTokens[3]), int(lineTokens[4]))
                self.oneconfig.setPosition(pos)
                self.oneconfig.setSize(size)

            elif 'exec' in line:
                bla, target, command = line.split(' ', 2)
                self.oneconfig.setTargetMachine(target.strip())
                if not self.oneconfig.getMasterIP():   #if it has been set, dont overwrite it
                    self.oneconfig.setMasterIP(target.strip())
                self.oneconfig.setCommand(command.strip())

            elif 'nwProtocol' in line:
                self.oneconfig.setProtocol(line.lstrip('nwProtocol').strip())

            elif 'bridgeIP' in line:
                self.oneconfig.setBridgeIP(line.split()[1].strip())

            elif 'bridgePort' in line:
                self.oneconfig.setBridgePort(line.split()[1].strip())

            elif 'runOnNodes' in line:
                self.oneconfig.setRunOnNodes(True)

            elif 'staticApp' in line:
                self.oneconfig.setStaticApp(True)

            elif 'pixelBlockSize' in line:
                s = line.split()
                self.oneconfig.setBlockSize( (int(s[1].strip()), int(s[2].strip()))  )

            elif 'binDir' in line:
                p = line.split()[1].strip()
                if not p.endswith("/"):
                    p += "/"
                self.oneconfig.setBinDir(p)

            elif 'masterIP' in line:
                self.oneconfig.setMasterIP(line.split()[1].strip())

            elif 'audioFile' in line:
                self.oneconfig.setAudioFile(line.split()[1].strip())

            elif 'sync' in line:
                mode = line.split()[1].strip()
                if not mode.startswith("SAGE_BLOCK_"):
                    mode = "SAGE_BLOCK_" + mode
                    
                if mode == "SAGE_BLOCK_NO_SYNC" or \
                   mode == "SAGE_BLOCK_SOFT_SYNC" or \
                   mode == "SAGE_BLOCK_HARD_SYNC":
                    self.oneconfig.setStreamType(mode)
                else:
                    WriteLog("\n*** Invalid streamType mode on line: "+str(self.lineCounter)+". Defaulting to NO_SYNC")

            elif '}' in line:
                self.appconfig.addConfig(self.oneconfig)   #save the last config
                self._appConfigs[self.appconfig.getAppName()] = self.appconfig   #save the appConfig
                self.appconfig = None   #reinitialize everything
                self.oneconfig = None


            elif 'defaultBridgeIP' in line:
                self._bridgeIP = line.split()[1].strip()

            elif 'defaultBridgePort' in line:
                self._bridgePort = line.split()[1].strip()


            elif line in string.whitespace:
                pass
            
            else:    # if line is not recognized
                self.oneconfig.setAdditionalParams(line.strip())
             

    def writeConfig(self):
        """ write applications.conf based on the current configuration """
        self._configFile = getUserPath("applications", "applications.conf")
        f = open(self._configFile, "w")

        # loop through all the apps and write their configs to a file
        for appName, app in self._appConfigs.iteritems():
            f.write("\n"+appName+" {\n")

            # write all the configs
            for configName, conf in app.getAllConfigs().iteritems():
                f.write("\n")
                f.write(conf.getAppLauncherConfig())
                f.write("\n")
                
            f.write("}\n\n#"+"-"*30+"\n")   # finish the app

        if self._bridgeIP: f.write("\ndefaultBridgeIP "+self._bridgeIP)
        if self._bridgePort: f.write("\ndefaultBridgePort "+self._bridgePort+"\n")
            
        f.close()


        






# --------------------------------------------------------
#
#                    HELP STRINGS
#
# --------------------------------------------------------

HELP_INTRO = \
"""
This SAGE Launcher helps you run SAGE and all the related components listed below. Check the components you wish to run with SAGE and click START.
For more information hover your mouse over any area. """

HELP_FS = "File Server allows you to easily show and organize\n"\
          "common multimedia files in a SAGE environment from\n"\
          "SAGE UI. Showing files is as easy as drag-and-drop\n"\
          "of files onto the UI."

HELP_AL = "Application Launcher takes care of starting SAGE applications\n"\
          "either on a local machine or any node of a rendering cluster.\n"\
          "Applications are started through SAGE UI."

HELP_SU = "SAGE UI is the main interface for controlling your SAGE display."

HELP_SP = "SAGE Proxy allows interaction with SAGE through XML-RPC as opposed\n"\
          "to regular sockets. Primarily used by the SAGE Web UI."

HELP_S = "SAGE itself (i.e. fsManager)"

HELP_RUN = "If checked this component will run when START is pressed."

HELP_EDIT = "Configure component specific settings."

HELP_COMP_STOP = "Kills the component now.\n"\
                 "To restart it, make sure that it's checked and then press START below."

HELP_INBG = "If run in background, the component will keep running\n"\
            "even after STOP is pressed and they need not be restarted.\n"\
            "Usually you want to do this if the components are used\n"\
            "independently of your local SAGE session."


### SAGE help stuff

HELP_S_START = "These are just shell commands\n(each line is executed as a separate command)"

HELP_S_STOP = "These are just shell commands\n(each line is executed as a separate command)"

HELP_S_PROC = "Typically these are SAGE applications and SAGE itself.\n"\
              "This should not include components as they are killed separately."


### AppLauncher help stuff

HELP_AL_PUBLIC = "Makes the appLauncher visible to other SAGE UIs connected to\n"\
                 "remote SAGE displays. This appLauncher can then be used by\n"\
                 "remote SAGE UIs to start applications and stream to their SAGE display."

HELP_AL_PUBLIC_HOST = "Which connection manager/SAGE server to report to?"

HELP_AL_APPS = "List of applications currently configured with this appLauncher\n"\
               "and available for running from the SAGE UI."

HELP_AL_CFG = "Different configurations for a particular application.\n"\
                  "Configurations usually specify different running scenarios\n"\
                  "of an application. All will show up in the SAGE UI."

HELP_AL_CFG_COPY = "Makes a copy of the current configuration with\n"\
                      "a different name but same parameters."

HELP_AL_CFG_STATIC = "This should be checked for applications that are not animated\n"\
                        "(i.e. do not refresh on a regular basis)" 

HELP_AL_CFG_APP = "This is the actual command executed (could also be a script)\n"\
                  "Full paths and/or parameters can be specified as well."

HELP_AL_CFG_DIR = "The directory where the app configuration file will be copied to.\n"\
                  "This must be in the same directory as the executable that's\n"\
                  "initializing SAIL and connecting to SAGE (basically your app).\n"\
                  "If empty it defaults to $SAGE_DIRECTORY/bin."

HELP_AL_CFG_MACHINE = "This is the remote machine that the application will be started\n"\
                      "on. SSH and SCP need to be set up for this to work.\n"\
                      "If left empty it defaults to the local machine."

HELP_AL_CFG_SIZE = "This is just the initial SAGE window size. Sometimes it is\n"\
                   "overwritten at startup by the application (such as imageviewer\n"\
                   "or mplayer) to get the correct aspect ratio for the data being displayed."

HELP_AL_CFG_NUM_NODES = "Specify the number of nodes of this application that are\n"\
                        "streaming pixels to SAGE (this may or may not include the\n"\
                        "master node depending on whether it's doing any rendering)"

HELP_AL_CFG_MASTER = "This is the IP address of the master node for your parallel\n"\
                     "application."

HELP_AL_CFG_BP = "Block size that SAGE splits the image into and streams."

HELP_AL_CFG_BHOST = "Used in visualcasting for sharing applications between displays.\n"\
                    "Specify the address of the SAGE Bridge that's handling this."

HELP_AL_CFG_BPORT = "Used in visualcasting for sharing applications between displays.\n"\
                    "Specify the port of the SAGE Bridge that's handling this."


### SAGE UI help stuff

HELP_SU_HOST = "Specify the connection manager/SAGE server to connect to\n"\
               "in order to find the running SAGE sessions. This should be\n"\
               "the same as for SAGE and the appLauncher."

HELP_SU_AUTOLOGIN = "To automatically log in to a sage session specify its name here\n"\
                    "(the name should be exactly the same as the one that fsManager reports"\
                    "to the connection manager... from the first line of fsManager.conf)"

### FileServer help

HELP_FS_ROOT = "All the multimedia files will be organized under this directory.\n"\
               "Either specify a relative path to $SAGE_DIRECTORY/bin or a full path."

HELP_FS_TYPES = "These are all the file types supported by the File Server.\n"\
                "All types have file extensions associated with them and all\n"\
                "the files are checked against that and matched to the correct\n"\
                "application for opening the files."

HELP_FS_EXT = "List all the file extensions that match this file type\n"\
              "and can be opened by the specified application."

HELP_FS_APP = "Specify the application for opening this file type.\n"\
              "When the application is started by the appLauncher,\n"\
              "the filename to open will always be the last argument."


### SageProxy help

HELP_SP_HOST = "Specify the SAGE machine to connect to"

HELP_SP_PORT = "Specify port on which SAGE is accepting UI connections."

HELP_SP_PASS = "This password is only used by the SAGE Web UI to restrict\n"\
               "access to this SAGE session. Since no encryption is used,\n"\
               "this is more of a determent."



#----------------------------------------------------------------------
#
#                           IMAGES
#
#----------------------------------------------------------------------


def GetCollapsedIconData():
    return \
'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x10\x00\x00\x00\x10\x08\x06\
\x00\x00\x00\x1f\xf3\xffa\x00\x00\x00\x04sBIT\x08\x08\x08\x08|\x08d\x88\x00\
\x00\x01\x8eIDAT8\x8d\xa5\x93-n\xe4@\x10\x85?g\x03\n6lh)\xc4\xd2\x12\xc3\x81\
\xd6\xa2I\x90\x154\xb9\x81\x8f1G\xc8\x11\x16\x86\xcd\xa0\x99F\xb3A\x91\xa1\
\xc9J&\x96L"5lX\xcc\x0bl\xf7v\xb2\x7fZ\xa5\x98\xebU\xbdz\xf5\\\x9deW\x9f\xf8\
H\\\xbfO|{y\x9dT\x15P\x04\x01\x01UPUD\x84\xdb/7YZ\x9f\xa5\n\xce\x97aRU\x8a\
\xdc`\xacA\x00\x04P\xf0!0\xf6\x81\xa0\xf0p\xff9\xfb\x85\xe0|\x19&T)K\x8b\x18\
\xf9\xa3\xe4\xbe\xf3\x8c^#\xc9\xd5\n\xa8*\xc5?\x9a\x01\x8a\xd2b\r\x1cN\xc3\
\x14\t\xce\x97a\xb2F0Ks\xd58\xaa\xc6\xc5\xa6\xf7\xdfya\xe7\xbdR\x13M2\xf9\
\xf9qKQ\x1fi\xf6-\x00~T\xfac\x1dq#\x82,\xe5q\x05\x91D\xba@\xefj\xba1\xf0\xdc\
zzW\xcff&\xb8,\x89\xa8@Q\xd6\xaaf\xdfRm,\xee\xb1BDxr#\xae\xf5|\xddo\xd6\xe2H\
\x18\x15\x84\xa0q@]\xe54\x8d\xa3\xedf\x05M\xe3\xd8Uy\xc4\x15\x8d\xf5\xd7\x8b\
~\x82\x0fh\x0e"\xb0\xad,\xee\xb8c\xbb\x18\xe7\x8e;6\xa5\x89\x04\xde\xff\x1c\
\x16\xef\xe0p\xfa>\x19\x11\xca\x8d\x8d\xe0\x93\x1b\x01\xd8m\xf3(;x\xa5\xef=\
\xb7w\xf3\x1d$\x7f\xc1\xe0\xbd\xa7\xeb\xa0(,"Kc\x12\xc1+\xfd\xe8\tI\xee\xed)\
\xbf\xbcN\xc1{D\x04k\x05#\x12\xfd\xf2a\xde[\x81\x87\xbb\xdf\x9cr\x1a\x87\xd3\
0)\xba>\x83\xd5\xb97o\xe0\xaf\x04\xff\x13?\x00\xd2\xfb\xa9`z\xac\x80w\x00\
\x00\x00\x00IEND\xaeB`\x82' 

def GetCollapsedIconBitmap():
    return BitmapFromImage(GetCollapsedIconImage())

def GetCollapsedIconImage():
    stream = cStringIO.StringIO(GetCollapsedIconData())
    return ImageFromStream(stream)

#----------------------------------------------------------------------
def GetExpandedIconData():
    return \
'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x10\x00\x00\x00\x10\x08\x06\
\x00\x00\x00\x1f\xf3\xffa\x00\x00\x00\x04sBIT\x08\x08\x08\x08|\x08d\x88\x00\
\x00\x01\x9fIDAT8\x8d\x95\x93\xa1\x8e\xdc0\x14EO\xb2\xc4\xd0\xd2\x12\xb7(mI\
\xa4%V\xd1lQT4[4-\x9a\xfe\xc1\xc2|\xc6\xc2~BY\x83:A3E\xd3\xa0*\xa4\xd2\x90H!\
\x95\x0c\r\r\x1fK\x81g\xb2\x99\x84\xb4\x0fY\xd6\xbb\xc7\xf7>=\'Iz\xc3\xbcv\
\xfbn\xb8\x9c\x15 \xe7\xf3\xc7\x0fw\xc9\xbc7\x99\x03\x0e\xfbn0\x99F+\x85R\
\x80RH\x10\x82\x08\xde\x05\x1ef\x90+\xc0\xe1\xd8\ryn\xd0Z-\\A\xb4\xd2\xf7\
\x9e\xfbwoF\xc8\x088\x1c\xbbae\xb3\xe8y&\x9a\xdf\xf5\xbd\xe7\xfem\x84\xa4\
\x97\xccYf\x16\x8d\xdb\xb2a]\xfeX\x18\xc9s\xc3\xe1\x18\xe7\x94\x12cb\xcc\xb5\
\xfa\xb1l8\xf5\x01\xe7\x84\xc7\xb2Y@\xb2\xcc0\x02\xb4\x9a\x88%\xbe\xdc\xb4\
\x9e\xb6Zs\xaa74\xadg[6\x88<\xb7]\xc6\x14\x1dL\x86\xe6\x83\xa0\x81\xba\xda\
\x10\x02x/\xd4\xd5\x06\r\x840!\x9c\x1fM\x92\xf4\x86\x9f\xbf\xfe\x0c\xd6\x9ae\
\xd6u\x8d \xf4\xf5\x165\x9b\x8f\x04\xe1\xc5\xcb\xdb$\x05\x90\xa97@\x04lQas\
\xcd*7\x14\xdb\x9aY\xcb\xb8\\\xe9E\x10|\xbc\xf2^\xb0E\x85\xc95_\x9f\n\xaa/\
\x05\x10\x81\xce\xc9\xa8\xf6><G\xd8\xed\xbbA)X\xd9\x0c\x01\x9a\xc6Q\x14\xd9h\
[\x04\xda\xd6c\xadFkE\xf0\xc2\xab\xd7\xb7\xc9\x08\x00\xf8\xf6\xbd\x1b\x8cQ\
\xd8|\xb9\x0f\xd3\x9a\x8a\xc7\x08\x00\x9f?\xdd%\xde\x07\xda\x93\xc3{\x19C\
\x8a\x9c\x03\x0b8\x17\xe8\x9d\xbf\x02.>\x13\xc0n\xff{PJ\xc5\xfdP\x11""<\xbc\
\xff\x87\xdf\xf8\xbf\xf5\x17FF\xaf\x8f\x8b\xd3\xe6K\x00\x00\x00\x00IEND\xaeB\
`\x82' 

def GetExpandedIconBitmap():
    return BitmapFromImage(GetExpandedIconImage())

def GetExpandedIconImage():
    stream = cStringIO.StringIO(GetExpandedIconData())
    return ImageFromStream(stream)

#----------------------------------------------------------------------
def getCheckedData():
    return zlib.decompress(
'x\xda\x01\xaf\x01P\xfe\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x17\
\x00\x00\x00\x16\x08\x06\x00\x00\x00+v\x07\x05\x00\x00\x00\x04sBIT\x08\x08\
\x08\x08|\x08d\x88\x00\x00\x01fIDAT8\x8d\xc5\x95Mj\xc2P\x14\x85\xbf\x17\xad\
\xd6\x1fp\t\x82#\xc76\x11\x91B\xad\xa3\x16\xa4\xa8\x9d\xb8\x10\xe9*\xa4\xd3"\
\xddA\xd1\x06;\x97\x96\x8eK7\xe3@1!\xb7\x03m\x88&\x9a\xa8)\xbd!\x83\xf3\xee\
\xe1{\x87\x97\xfb\x08JK\x10\xd7kL\x0c\xf1\xea$1T\xdd\xac\xc9\x92\xa5o]\x8b\
\x03\x1e\x04\x06NK^5uqp\\]\xa4\xc8\x17\xdf\xae>)\xb9\x17\x8c\x03\xe3\x8e\xa9\
\xbc\xfd\xa3\x92\xebfE\xbc\xba\xa0\nL\xef\xdf\xd5\xb6\xcfM~\xf9Z\x97\xbaY\
\x93mCh\tL\xdb~\xb0\x0b\xd7\xcd\x8a,\xd4\x82%K\xc260\xcc\x8b\x8d\xbef\xef>\
\xd9d\xcd\xac\x8a\x8d\xed.\xa4%\xbd\x13*\xac\x9e\xdf\xeaez\xf4;\x0f\x81\xa9W\
\x1b{\xc0\x00\xb6\xd8\x81F/\x14\xc0\xb1\x1c\xfa7\xbb\xc1\x10\xf0A\xe7j\xbe\
\xa1\xb7\xc7\r\xa0q\xde`\xd0y\xdc\x0b\x86\x1d\xa3\xd8}k\x0b@{t\xe7\x03;\x96\
\xc3\xe06\x1c\x0c\xa0\x8c\x89\x11mB\x04J\x94x\xe9\x8e"\x81\x01\xb4\x9c\x95\
\x8bd,\xaa\xe2A`\x00\xad\xac\x95\xf7\x1a\xc4\x12\x8c3\xc3w\xfb"\xc1\xc3\x0cz\
V\xe7\xa95<\x18\x0c\xa0\x94\x96\xf0]gX%\xd6\xb3:\xc3\xd6\xf3Q`X\'O\x91\xf25\
\x9a\x99\xe6I`X\'\x07\xb8\x1e_\xc9L\x9b\x01\x90\'\xcfG\xe7\xf3$\xf0\x06\xfc/\
*\x96?\xd1\xbf\xc0\x7f\x00\x07#sW\xd1Zw\x10\x00\x00\x00\x00IEND\xaeB`\x82\
\x03\t\xb8>' )

def getCheckedBitmap():
    return BitmapFromImage(getCheckedImage())

def getCheckedImage():
    stream = cStringIO.StringIO(getCheckedData())
    return ImageFromStream(stream)

#----------------------------------------------------------------------
def getUncheckedData():
    return zlib.decompress(
'x\xda\x01\xe4\x01\x1b\xfe\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\
\x13\x00\x00\x00\x16\x08\x06\x00\x00\x00"\x9d\xa7\x7f\x00\x00\x00\x04sBIT\
\x08\x08\x08\x08|\x08d\x88\x00\x00\x01\x9bIDAT8\x8d\xb5U;O\xc30\x10\xbe\xb3\
\xa9H\x93\x896\xc9\xd6f\xec\xd0\xb1]`\xe8\x06##\xfc\x84\xfe\x1d\xf8;\xb0C\'\
\xd8*\xb1u)\x12Q\x1f\x03mB\x1f\xc91D6\x8e\xed\x14\x89\xc7\'EQ\xee\xce\x9f\
\xbf{\xd8Ad\x1c\xfe\nL7\xe4\x94S\x1a\xb5\xe9\xd0\xa24jS\x1a\xb5i_w\xe8\xf5\
\xfaJ\xc6\x96\xc8\x84c\xddl\x1eTP\x8bc`\xab\x15d\xae\x0b\xcer)\xed(\xd2\xdc4\
\x1b\x04\x00\xc0\x93\x04X\x92\x14;!C\x95d_wH\xf8\x00\x00v\xbe\x0f<I\xe0(\xfd\
\xc0\x92\xb2\xe3\xf9\x02\xb9\x12h\x03\xb3\xf8\xe3\xcb\xcb\xaf\x0fd\\>\x84H\
\xfa\xb3\xeev)\xf3<\xc3\xbe\r\x02R\xd7"\xe3\xe5\x9a\xe5\xaek\xec\xec\x8e\xc7\
\x86\xa2\x9d\xef\xc3\xba\xd73\x95\x97\x82\xc2\xd0J\xa8\xe3=\x8a\xa0qw\x8f\
\x86C\x97\x8a\x8c\xc36\x08\x8c\xb4\x08\x912\xcf\xa3y\xbfo\xa4gMSUXe\xf7\x9f\
\x9eME\xb64\x05jql\r\xce\xbe)\x81A\xb6i6\xa86\x9bY\x83\x9d\xc9\x04\xd4\x89\
\xd7\x81\xea\xd9\xd4\x87\x12\xa0\xe8\xb0n\xd3\x87\xd9\xaa\xccF\xa4\xbe\x05\
\xaa\xd41\x80"\xb5\x9cr#\xe0e8\x94\xcdP\tOF#X\\\x9c\x1b\xf1\x0c\xa08\x8f6ton\
K\xe9\x08\xc2\xaaF 2\x0ei\xd4&\xb5\x83,IJuY\x9f\x9d\x12\x9bN%\xd1\xb6\xd5\
\xb2\x0e-\x13\x01\x99\xeb\xc2.\x0c\xad\xbbz\x0f\x8f\x08P\\MUD\x92l\xdbj\xc9\
\xdapM\x95@\xda\xe9\xc0\xdb`PI$\xd3\x14\xd8\xd7\x1d\x12w\xd3O\x80\xff\xfa\
\x0f\xf8\r>\x01lo\xba\\\x08x\xd9{\x00\x00\x00\x00IEND\xaeB`\x82\xd6d\xd4\xb4\
' )

def getUncheckedBitmap():
    return BitmapFromImage(getUncheckedImage())

def getUncheckedImage():
    stream = cStringIO.StringIO(getUncheckedData())
    return ImageFromStream(stream)


def getRunBitmap(checked=False):
    if checked:
        bmp = getCheckedBitmap()
    else:
        bmp = getUncheckedBitmap()
    return bmp


#----------------------------------------------------------------------
def getStopData():
    return \
'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x18\x00\x00\x00\x18\x08\x06\
\x00\x00\x00\xe0w=\xf8\x00\x00\x00\x04sBIT\x08\x08\x08\x08|\x08d\x88\x00\x00\
\x038IDATH\x89\xa5\x95]o\x1bE\x14\x86\x9f\xfd\xb0\xd7\x1fk\xc7\x9441m#\x12(T\
\x14\x81PDS\xae\xe0"w\xdcrU\xa9\xff\xaf?\x01n\xb8\xa7v\x89T\x90\xa8\x84R@\
\x04Gi\x9a\xb8q\xfc\x91\xf5\xec\xcc\x1c.v\xd7\xd9\x8d\x137\x88W\xb2\xb4\xda3\
\xf3\xbcg\x8e\xcf\x9eq\x1c\xd7\xe3:\xeav\xb4\x008\x0e\x88\xc0\x83-\xdf\xb9\
\xce>g\x91A\xb7\xa3\xe5/{\x82\t4\x81x\x94+\xe71\x15\x81V\x0e\xebnk\xa1\xd9\
\x9c\xc1\xde\x9b\xb1\xbc\xda\r\xf8m\xda\xa7\\\xb7l\xdc\x08x\xbf\x15P/{TK\x1e\
\x0e`E\x88\xb4\xe5$\xd2\xec\x9f*\xf6\x8f5k\xe6\x1d\xbe|0o4g\xd0\xedh\xf9\xc5\
\x1e\xb2\xd5.\xb1\xbe\xda\xa4^^\\B+p\x1aiv\xf6\xc6\xb4FKs&\x05\x83g]-\xcf\
\xcd!_\xaf\xd7\xf8`9L\x17,\xe4\xcf$\x02\xcfzC\xbc\xc3F\xc1df\x90\x87\x7fx3\
\xbc\x1e\xf5\x12u\xff)\x9a\xb8Y\xe0\xb99\xe4\x8b\x15\xff\x7f\xc1\x016o\x85\
\x9c\x84\x03:;S\x01\xf0!\xa9\xfb\xcb\xd2\x11\x1b+\xcd\xc2b}t\x8c\xff\xea`!P\
\xaf\xb6\xf1\x97\xdf\x05\xc0X\xc1\x08\xdc\xbd\x19\xf0\xfa\x0f\x8f\xfe(\x12\
\x1f\xe0\x85\xeaso5\xa0U\xf5\x0b\x9b\xbd\x1f\xbe\x87\'O\xe6\xa9\x9e\x07\xc6$\
\x8f\x8f\x1e\xc1\xe3\xc7(#\x00\xc4\xc6\xd2\xac\xf8\xbc\xb4Sv\x7f\xf7\x93\x12\
\xc5\xbe\xe6V\xb3|\xbd\x1a\xe4\xe0\x00N\x18"\x92\x80\x93_b$K\x11\x00n\xb7\
\xa3\xa5\x1e\xb8\xb4*\xfe\xa5\xbc\x194S\x0e\x0e \xa3\x11\xc4\x8a\xd8\x08\xb1\
\x11\x94\xb1(cy\xaf\xe12T\x1a7k\xc3\x8a\xefr\xa5.@/J\xa6S\x00\x94\xb1\xc4V\
\x88\xadP\xf6\x1dFg\x86Y\xda\x9e{\xcd\x86\xcf+w\xb2\x0cn\xd2\x12\xa9dt\xe1\
\x8a\xa4IZ\xf9\xef\x06\xe9\xc9\xecT\xcd\xe0\xb1\xd6\xc4Z32\x10V\xbd\xe4OVc\
\x97H\xdb\xb7fyY\xcc\x99L\x00\x88\xa61\xb1\xd6\xb3\xec\x87\x13KX\xb7\xb8\xd9\
$<\x1e\xc7I6\x92\x9cF\x94Zl\x92v\x93\xd4j\xa8\xd4$\x83[\xady3H*\xe2\x03\xdc\
\x0fn\xb0\xfbz\xc0\xed\xa5\x00\x93\xb6\\\x8d\xa4\x05\xcd\'\xf7\x17V\xc9\x05\
\x94["\x8a\xe2\xe2\xfb\xbe\xe6\xe1W\xcb\x8e\x0f\xc9\xa0\xda?6\x1c\xb4\x15\
\xad\x8aOl\x84\x01.\xcd\xedm\x9c\xedm\xecT\x156\xab\xc9\x04\xe5\x96(\xdb\x04\
\xda\x93\xe0<f\x85\xbfO\x1c\xee\xac\xd5\x81\xdc\xb0\xeb\xecL\xa5\xc7)\xdf|\
\xdcH\x16\xa6]\x91)\xeb\x0e\xa0Pk\x9b=\xa7k\xe3\xa9\xa1\xf7\xa7\xc3w\xdf\xb6\
\x8b\xc3nk3p\x9a\xaa\xc6\xce\xde\x18el\x01\x9c\xef\x8eXk\x94\x16\xa2(\xc6j\
\x8d\xb22\x07\xff|\xf3\xfc\xea+|\xbe\x8d\xb2\xcfpP\xe1g\x19\xf3\xe9Ju.\xdbL\
\x198\xaf\x0c~{C\xf8\xa8\xdd\x9a\xbf\x0f\xf2\xfa\xf1\xa7\xb1\xf4\xf4\x98{k%\
\xc24<\xba\xf01\xfb&\x9e\x81\xf7\x06%\xdc\xbe\xe6\xceZ\x9d\x87\x9f5\xae\xbe\
\xd1\xf2z\xfa\xebP\x0e\x8e\x84A)\xa2QshT]\x1a\xb5\xa4\xa2\xc3\x89exf\x19N\
\x84\xfa\xa9\xbd\x14\xfcV\x83\xbc\xd1h\xec2:3\xe8\xb3\t\xe3\xa6\xcbR\\!\xacz\
\x84u{%8\xd3\xbf\x07\xf8\xd8d\xb6\xf93\n\x00\x00\x00\x00IEND\xaeB`\x82'

def getStopBitmap():
    return BitmapFromImage(getStopImage())

def getStopImage():
    stream = cStringIO.StringIO(getStopData())
    return ImageFromStream(stream)


#----------------------------------------------------------------------

def getSageIconData():
    return zlib.decompress(
'x\xda\x01s\x06\x8c\xf9\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00 \x00\
\x00\x00 \x08\x02\x00\x00\x00\xfc\x18\xed\xa3\x00\x00\x00\x03sBIT\x08\x08\
\x08\xdb\xe1O\xe0\x00\x00\x06+IDATH\x89\xb5V[oU\xc7\x15^k\xcd\xec\xbd\xcf\
\xdd\xe7\xd8.6\x17\x03\xe6j\x0c\xae0\xd4Ih\xa0\t)A\xa8IT\xd4(/\x95\xfa\x90\
\xa8?\xa8}\xe8[[\xa9J\x1b\xb5\xaa\xa0JS\xf5!j\xa9Dn$\x90\x00\xa1\\\xe2\x10HC\
\x08\x81\xe3\xdb\xf1\xf1\xb9\xec=3\xeb\xeb\xc3\x01\x83\xaa \x15J\xd7\xd3\xd6\
\xec\xf5}\xeb2#}\x1f\xef<\xfc\xc3\x85\xc5E\x80\x0103=\x8a\xe8Q1\xa3\xaf\\\
\xb6\xf5\xd9\xd9f\xab\ra\xc1#!\xbf\x1d\xca\xc4\n\xe7\x9c5&"#L\xa4 \xe2GT\xa4\
\xb7\x0b\xc3\xc6D\xc2\xcc\xacPU\x00\xcbC\x88>\xf0\xae\x96!\x02\x02\xa0\xaa\
\xac`f\xdb;ef\xb9\xf3\x9b\x88\x88\xf1\xc0\x1b\xbb\x07b\x98\x94\x99@Dd\x97\
\x13\x94I@\xbd>\x96?\x1e`\x82\xfb`\xe5\x1b\xb3\x1f|C\xf7\x85\xd8\xe5\xa7)\
\xca\xbd1{\xa3<D,\x03EY\xefPXU\xcd\xb2,\x80X\x19\xc2\xacP\xa3y\x9bx\n>c1\nR(\
\x91\xd1|R\x88HR\xcd\xd2,\x18\xcf\x1c\x8b@\x88T\x95l\x12G\x1c\x1a\x9d\xae\
\x10\x1bc,1\x14\x1d\xc7\xc5\xa2\xb7\n\xfa\xf6\xb6M\xc3\xab\xfbE\x08\x81D\x08\
dO\xbc\x7f\xbeT\x88\x1f{|w1F1.\xe5\xe2|\xa5R\xbat\xf9\xf3#o\x1e\x13\xe2\xa9\
\x9d;\xd6\x8d\x0e\xda\xd8\xb3\x18\x0b\x13\xe7\xe3k\x9f\xd5?<s\xf5\xe5\x1f\
\x1cZ\xbfj0sh\xb4\x17\x9a\xdaqi\xe7\xd2\xf9\xaf\xed\xf8\xd8\xc8\xd43#Jj\x94\
\x85\xa2\x8c;L\xf6\xe2\xf9\xca\xe4\x13\xeb7\xee\xe8\x8b\x9a\xc5\x88L_\xb9rp\
\xcf\xde\xf7\xce]|\xf5\xf57\x0e~o\xcf\xae\xef\xaf\x0c.\xa3n\xc1S\xd0\x94:iV\
\xac\x16\x96\x16\x9b?:\xf4tl\xf5\xe4\xb9K\xca1[\xca\xd7dh\xc5\xb8]72\x08\xf8\
so\xcd\x9d97mH\x9e}~\xe7\xc8\xe6\x1c3\x95+9M\xc3/~y\xa4\x99v\xb6\xac]\xfd\
\xc5\x17\xf5\xa3\xc7\x8e\xe5l\x92\x14\xc0\xd0O?\x9a;~\xfc\x12\xc7v\xb86\xf0\
\xe2\xe1}\x0b7\xafv\x83{\xef\xd4\xc7\xcdf\xf3g\xbf\xf9C)_0l\x7f\xf2\xd3\xef\
\x96\x8ay\x0b1b\xf9\xe6\xd7\x0b7\xeau\x11\xb9\xf0\xd1\xf5\xfa\x8d\xf2B\xb3\
\xf9\xee\xf1O\xca\x85|\xa3\xd5.\x98h\xdb\xe6\xedo\xbf\x7fz\xfa\xf2\xd5|\xb1\
\xf4\xce\x07\xd3&\xe1\xe9K33\x8d\x19k\xa3\xe6\xfc\xdc\xc9S\xfd\x93c\xdb\x0b\
\xb9w\xcf~2\xbdfx\xd8\x10\x03!(\x03\x89\x04\xb6\xce)\x14{\x0fn\x98zr\x84-\
\xa7i\xb8rqv\xa1\xd1\x18\x1e\xac\x8e\x8d\r\x8fO\xad\xc9\x1b\xfa\xce\xd8\xc4\
\xc7g\n\'.\x9c\xb5\xaa\xc5\\T\x1b\xccW\xfaK\xcf\x1d\xd8[\xae\x19\x0f\xef\x1d\
\xb5}\x8b\xc4$69\xf0\xc4\xee\\\x91S\xb4<\xfb\\\x9f\x0f\x99\xb7gNMG\xf1\xa6\
\xd2\x80$U\x03p\xae\xea\x9e\x1cY\xdbl\xa5\xbb\xf7\x8d\x14k\xc1\xb5\x12\x84\
\xee\xec\xd2\xc2\xee\x89\x89\\\xf2z\xd6u\xb5\x95\xa55\xa3\xfd\x17N\xd6GG\x87\
\xca\xab\xad\xcbP.\x13\xb9\xd8{mv\x97\n\xe5R\xb5Th8\x9f\x89v\x9b!\x0eb\x17\
\x96\xdao\xfc\xe9\x84\xc9\x19\x86\xf1]=ph\xd7\xda\xed\xe9\xd0`\x1f\xb1K\xeb\
\xf1\x1f_{;\r\xd9\x96u_\xbd\xf2\xd2K\xc5b\xf1V\xeb\x16\xbcs!\x03\xeb\xef~\
\xff\xb7|>\'0/\xbf\xf2,\x8b\xf3\xdd\xf6\xd6\xb5\xeb\xff\xfa\xe6[\xbf:r4\xc9\
\x17\x0c\xc8{_-W\xed\xfe\xa7v\x8el\xa8\xfc\xf6\xd7\xc7\xaf~u\x9d\x9c.-\xb6\
\xd8TI\xc9\xb2\xb4:Y\xbd\xb1H\xc6\xa7\x99k,\xce\x97\xf3\xc9\xc0\xfa\x8d\x99k\
\x82-\xac4\xe6\x1a\x8b\xb9\x0e{\xb26:}\xfab\x9ae\xe3\x9b\xd7\xbf\xf3\xe1\xd9\
\xa5F\xb3\xeb2\xf5\xe6\xc7/\xee\xcf\x15c\x1bG\xe4\x93\xf6\x9e\xa7\xc6\xc7n\
\x8e\x90\t\xabF\xfb\xbc\xf76\xc7.\xa0\\\x8b\xf7=\xbe]A\x93[v\xd4\xe7\xe7\xb6\
n\xdc\xb4n\xc5\xd0\x07\x9f\x9d\xd5\xd0\x99\x9cZ\xb5\xa2V\xf4\xc4B\xbe\xd6_\
\x99\x99\xef\xd4\xaa\xb54M\'\xb6n\xde\xb7w\x8a\x89l,\xab\xb6\x95b\x9fX\xcb\
\x11A6\x8c\x95\xedx\xd5\x91\x0b\x81\x96f\xa2sg\xff900\xd1\xbf!y\xe6\x85\x89\
\x1c\x15\x1f\xdb\xb4\xeb\xe8\x9f\xff^-\x15\'\xb6o\xf9\xcb\xb1\x7f\xb4g\xc7j\
\x03\x18ZYVE\xce$\x85bd\xc0CC+>\xbdv\xfd\x85\xfd\xfb\x922\xcda\x0e\x94:\xe7\
\xae\\\x9c\xe3\x89\xc3\xcfC\x19\xc1\x89X x\xefgg\x96Zi;_.\x0c\rT\xe0a\xa2d\
\xcf\xe4\xe4\xf4\x95\xab\x95B~\xdb\xe8\xa6\x9f\xbf\xf6j\xb5\xd4W\xab\xf6\x19\
\x06\x04\xd6\xc4I\x92\xa8\xd3\\\x12\xb9\xe0\xab\x95\xf2\x97\xd7o\x92U\xf8\
\xe0\x95\xd2\xd4\xd9\xf9\x85\xa5\xb9\xd9\xf9 \xc4\x10""\x811b\x12\xe9v\xbb\
\xff\xfa\xbc\x1d\x98XH\x9df!4\n\xc9|\xb3].\xe4;\xddv\xf3Z\x13\x86\x00\x108\
\x12\xb3rE\xed\xd6\xac:\xd7\xbd\x8c\xd0Z\xea\x1a&\x02\x8b\xc8`\xb5j\r\x8b\
\x8d\xd8\x08\x1b\x15\x00j\x84\xc0\x02\x80\x83\x89"\x16\xb1\x1an\xdc\xba\x01k\
\xeb\rJ\xf8V\x08\x81\x19\x12Y\x16\xe2@\xccL\x1cn\xd4\xe7\x8cae\x81\x0f\xb9(\
\x860\x00V\xa8\t\x16\xc4L\x96\x01\x05\x89\x11V\xcfdU\x94aY\xc8 \x80)0\xc4;O\
\x1c\xc8\x0b\x1b%0\x1b(D<\xb3\x81\x1a\x12\n\x04\t\xc2\x02(X\t\xe2`,\x91\xb5D\
D\x1c\x88D\r\x03$l\x94!j\x08\x80\x90\xb2\x12\x89h\xc4\xa4\xc2d@\x81\x95\x99\
\x05\x8e\x85\x03\x0c\x81\x8c\xa8\x80\x03\x91\xb0:\x82\x11\x10\x0c!\x12\x90\
\x04X\xe1\xdbbc\xf4\x1eW\xc1\xa0\xdb\xfa\'\xbd\x0e@$D\xb8\xabE\x02\x90\x10\
\x88\x08`"2 \xcf0`\xea!{TF,p\x1b\xa1\x82e9}\x08\xc9\xbcW\xd4\x96\xe5\x0c\xc0\
7k\xf2CH\xe6\xfd \xf6?2\xeeZ\xa3\xff\xa1\xc6\xbd\xc6\xe2v\x01\x00\x01l\xf8\
\x8e\xf5\xb8G\xb5\xff[\xf6;\x10\x01\x05\x10\x11z\x97a\x01@X\x88\xa1\xa4|\xf7\
>\x1e\xb4\xfde\x88211\x0b\x83\x08\x80\r\xc1QP\x08K\xaf\xea\xa3\t(\x88\x15!8\
\xfb\xad\x81\x81(\x8a\xfeO\xf6\xbdZ\xa9\xfc\x1b\'\x9f`y\x8c\\\xb8\xf0\x00\
\x00\x00\x00IEND\xaeB`\x82e\xd2)\xef' )

def getSageIconBitmap():
    return BitmapFromImage(getSageIconImage())

def getSageIconImage():
    stream = cStringIO.StringIO(getSageIconData())
    return ImageFromStream(stream)

def getSageIcon():
    icon = wx.EmptyIcon()
    icon.CopyFromBitmap(getSageIconBitmap())
    return icon


#----------------------------------------------------------------------
def getSageData():
    return \
'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x01u\x00\x00\x01;\x08\x06\x00\
\x00\x00"\xaf\x11\xd4\x00\x00\x00\x04sBIT\x08\x08\x08\x08|\x08d\x88\x00\x00 \
\x00IDATx\x9c\xec\xbd{x\x1c\xe5y6~\xcfaO\xda\x83v\xad\xf5J\xb2\x0e\x16\xb21\
\x08[\x8aA\x96c\x08\xf6U\x88\x82\x81\x12N\r\x816!?\xd2\x03Iq\x93&_RZ\xda\x92\
4\x906m\x9a4|I\xe0KH\x9a\xf2\x85\xf0\x05Jj\x08%\t6\x0e\xa6\xb6\x03\xc4\xb6\
\xc0\xf8$\x03\x96,\xeb`I\xeb\x95w\xb5\x07\xedi\x0e\xbf?F\xef\xec\xcc\xec\xec\
jw\xb5+\xad\x94\xb9\xafK\xd7\xca\xab\xdd\xf5\xec\xcc;\xf7\xfb\xbc\xf7\xfb<\
\xf7C\xb9\xba\xbbE\x180`\xc0\x80\x81e\x01z\xb1\x0f\xc0\x80\x01\x03\x06\x0c\
\x94\x0f\x06\xa9\x1b0`\xc0\xc02\x82A\xea\x06\x0c\x180\xb0\x8c`\x90\xba\x01\
\x03\x06\x0c,#\x18\xa4n\xc0\x80\x01\x03\xcb\x08\x06\xa9\x1b0`\xc0\xc02\x82A\
\xea\x06\x0c\x180\xb0\x8c`\x90\xba\x01\x03\x06\x0c,#\x18\xa4n\xc0\x80\x01\
\x03\xcb\x08\x06\xa9\x1b0`\xc0\xc02\x82A\xea\x06\x0c\x180\xb0\x8c`\x90\xba\
\x01\x03\x06\x0c,#\x18\xa4n\xc0\x80\x01\x03\xcb\x08\x06\xa9\x1b0`\xc0\xc02\
\x82A\xea\x06\x0c\x180\xb0\x8c`\x90\xba\x01\x03\x06\x0c,#\x18\xa4n\xc0\x80\
\x01\x03\xcb\x08\x06\xa9\x1b0`\xc0\xc02\x82A\xea\x06\x0c\x180\xb0\x8c`\x90\
\xba\x01\x03\x06\x0c,#\x18\xa4n\xc0\x80\x01\x03\xcb\x08\x06\xa9\x1b0`\xc0\
\xc02\x82A\xea\x06\x0c\x180\xb0\x8c`\x90\xba\x01\x03\x06\x0c,#\x18\xa4n\xc0\
\x80\x01\x03\xcb\x08\x06\xa9\x1b0`\xc0\xc02\x02\xbb\xd8\x07`\xc0\x00\x01MQe\
\xf9\x1cA\x14\xcb\xf29\x06\x0c,E\x18\xa4n`Q\xa1%r\x96a\xe6\xf5y\x1c\xcf\xab>\
\xd3 \xf8\xfc(t"5\xce\xe3\xd2\x81A\xea\x06\x16\rz\x84\xce\xf1\xbcL\xec\xac\
\xc9\x94\xf3\xbd\\:\r\xd6d\x02\x97Ng\x9eS\xbc\x97\xe3y\xf9\xff0\x08)\x1b\xc5\
\xae\x8a\xc8\xeb\x8dsY\xfd0H\xdd\xc0\xa2@I*\xca\xe8\x9ce\x98\xbcd.\xbfn\xf65\
\x85\xbc\xd6 v\tzD^\xcc\xca\xc8X\x05-\r\x18\xa4n`\xc1A\x88AK(Z\x82\xb6\x9a\
\xcds~V"\x95R\xbd\x9fD\xeeF\xc4\x9e\x81\xf2|+W3z \xd7@\xb9\x02\x92\xff\xa68\
\xa7\xe4\xb3\x94\xf8]=\xbf\xd5\x06\x83\xd4\r,(r-\xfb\t\x99h\x89\xdcf\xb5\xe8\
\xbe>\x9eHf\xbd>\x91J\xa9H)\x17\xf9\xfc. \xd7^E!\xd2V\xbe\xbfs\xe9\xb4\xea\
\xb3\x94\xe7\xf6wy\xe2\xac&\x18\xa4n`Q\xa0G.J\x82\xd6\x92\xb9\xddfC,\x1e\x97\
\x1f\xbd\x1e7b\xf1\xb8\xfc\xf7x")\xbf_I\xee\xe4\xff"\xd2\xc1r%\x9d\x9c\x93e\
\x9e\xd5P!+!\x02\xb2"\xd2\xeec\x142i\x96+\xab\xa9\x14,\xd7\xeb\x9d\x0f\x94\
\xab\xbb\xfbw\xef[\xff\x0e#\xdf\r\xa6\xbd\x01\xc42\xde\x10\x14E\xa9H\x95\xa6\
(\x95~N\x08FI\xe6v\x9bm\xce\xcf\x8d\xc5\xe3r\xd4\xae\x94b\x08\x08\x01\x11\
\xe2)\xf7M\xae\xfcN\xa2(B\x10\x04\x08\x82 \xff\x9d\x17*\x7f{14\x854\xc7I\xc7\
C3\xaa\xe7\xa5\xe72\xe5(&\x96\xcd\xda\xb7\xb0\x9a\xcd9WD@fU\x04\xa8\xcf\xb1\
\x9eD\x93\xe28\xd5y \xdf_\x10xp\xb3\xc7\xb8P`Y\x164\xcd\xa8\xce\x03M\xd3\xf2\
X\x04\x96\'\xe9\x1b\x91\xfa\xef\x00\x04Q\x84(\x08Hs<\x04!\x13U\x91\x9b\x8ce\
\xb3\x87\x81\xf2f\xa8\x148\x86\x01\x95N\x83\xa2(9\x9b\x05\x90\x88]I\xe8.\xa7\
3\xeb\xbd\xe1H\x04\xa3\x93~Yf\x11D\x11\xa2(\xca7lV\x84Z\x86h]\x10E@\x14\xc1\
\xf3<xA\x94\x89\x8aeY\x98X\x16&\x9a\x81\xd3\xe1\x98\x93$\x17\n\xb9&E\xe5\xf9\
t;\x9c\x08E#\x08G"\x00\xd4\x93$ ]\x0b\xbd\xef\xa2\x95\xba\xa4\xf7%\xc0\xb2,\
\xac\x16\x0b\x9c\x0e\x07<.\xa7|\x1c\xe4\xfft;\xb2\xafe%\x10\x8aJ\xdf\'\x1c\
\x89\xc8\xdf)\x91J!63\x83\x99x\\\xben4\xcd\xc0lbAQ\x14\xa8E\\Q\x94\x13\xcb\
\x8e\xd4i\x8a\x02/\x08\xe08N\xbe\xf1\x96"L,\x0b\x8b\xd9\\2\x01\xd1\x14\x85d*\
\x854\xc7\xc1\xc4\xb2\xa8u\xb9\xd0\\\xefCk\xe3*\xb4\xaej\xc4\nW-\x00\xa0\xde\
d\x82\xbd\xc1\'\xbf\xcf\xdb\xe8@`<\no\xa3\xa3,\xdfC\x0b\xf2\xd9\x81\xf1\xa8\
\xfc\\l\xc2\x8f\xc9\xd9\xa8opt\x14\xe1hT\xbe)\x95 \x84\xf0\xe6\xc9\x93\x08\
\x04\x83\x00 \xdf\x88\xca\x9bR\x10E\xa48N\x97\xdc\x8bE:\x9d\x96\xa3`\x13\xcb\
\xc2n\xb3ae\xdd\n4\xfa|\xe8Z\xb7\x0e+\\\xb5hoi\x82\xb7\xd1\x01/\xed\x81\xb5\
\xae\x06\xde\xda:\xf9\xfd\xf5\x1e\x1f&\x83\xfeE{\x9c\xeb8\x00\xe0o\xbe\xfe-<\
\x7f\xfc\x84\xfcZ\xe5\xca\xa3\xce\xed\x86\xd7\xe3\x96\xaeS<\x0e\x9b\xd5"K]\
\x89T\n\x91h\x14&\x96\xc5\xfa\x8b\xd7\xe2\xea\xeenlZ\x7f\x19\xbc\x8d\x0e4\
\xafl\x9a\xf3<T\x02\xda\xcfV\x9e\x03\x00\x18\x1d\x1cA@\x08\xe2\xec[\x83x\xfd\
\xcc\x19\x1c\x7f\xef]\x9c>;\x8c\xe8\xcc\x0ch\x9a\x81\xc5lZ\xf2\xe4\xbel\xe4\
\x17\x9a\xa2\xc0\xf1<\xa2\xb1\x18\x00\xc0\xe9p\xc8\x03\xd2\xe5t\xc2\xedp\xc2\
\xe5\xa8\x0cQU\x02\xc7\xdf{\x17\xfd\x03\x83`J$\xa5\x99x\x1c&\x96\xc5\r\xdb\
\xb6\xe1\xf6\x0f}\x10\x1b\xbb.\xc1\xfa\xb6\x8e\x9c\xaf\xd7#\x82B\xa0|O1\x843\
\x17&\x83~\x8c\x0e\x8e\xe0\xd4\xd8\x08\x06G\xc6p\xe4\xd4)\x00\xc0\xf0\xf8\
\xb9\xa2\xce\x8b\x92\xd8\x95\xdao\xbe\xc9\x92\xa6(\xcc$\x92H\xa5\x92\xb0\xd7\
\xd4\xa0uU#\xde\xdf\xf5>\\y\xd1E\xf8\xc0u[u\xcf\xa3\xf2\xbc\x05\xa6\xa7\xe4\
\xdf\x13S3\xb0\xd6\xd5`\xf4\xfc\x18\xbc\xb4\x07\x01!\xb8`\x8f\xcd+\x9b\x90\
\x98\x9a\x91\x8f\xc5ZW#\x1f\x0f\x00\xfcf\xf7~<\xf2\xf3\xe71|n\x1c\x14M\x83\
\x02\xb2\x08M\x10\x04\\\xda~\x11\\NgV4\x1f\x8d\xc5\xb0\xad\xa7\x07\xf7~\xe2\
\x16l\xef\xe9\xcdy>\x94\xe7Dy<\xcac\xd5C0>\x05\x8f\xad\x0e\x81\xf1(\x18wR\
\xf75Zxlu\xaa\x7f\x93\x89\x16@\xd6$C\xd0\xd7\xd7\x87\x9f\xec\xde\x85]\x07\
\x0e\xa0\xff\xf4\x00lV\xeb\xbc\x02\xaa\xc5\xc6\xb2!\xf5\x99\xd9M\xb3m\x9b{\
\xd0\xb5n\x1d\xae\xef\xdd,G\x0b\x95\x8a\n*\x89\x87\x1f}\x14_\xfa\xf6\xb7\xe1\
v\xb9\x8a\x1a\\4E!:3\x83\xe6\x86\x06|\xf5/?\x83\x8f\xdd|+\x80\x0cI\xbe\x17;\
\r\x00\x08\xc5B\x88Fc\xba\x9f\x11\r%\xe0p[u\xff\xe6\n: \xb4\x88\xa0G(\x84=Q\
\xf9\xdf\x00@\x8fP\xf2\xef\x00\xe0L\xd7\xab\xde\xcb\xb8\x93\xe0C\x16\xf9\x06\
%7\xa0\xf2\xc6\x0327\x9f\xf2\xba\x9d\x18\xea\xc7\x91\xa3\xef\xe0\x1f\xbf\xff\
8\x86F\xc7`* ?\x9d\xc0\xac\x90\x97\xe6\xd2\xd6\x05A@4\x16\x83\xd7\xe3\xc1M\
\xd7\\\x83\xde+\xdf\x8f\xde\xadW\xc9\xc7B\xcec@\x08\xe2L`\x00\xd1h\x0c\x11q\
\x1a\xb1d\x0c\xf1d\x12\x9c i\xceI.\x05\x8e\xd7K\x0b4\xa9\x9e/\xf4\xdf\xca\
\xc7|`g5u\x86f\xc0\x0b<\x18\x9a\x01K+6\xa0-\x16\xd8-v\x1c\xf8\xd5Y\xbc\xf2\
\xda\xeb0\x9b-\xb0Zro\x98\n\xa2\x08GM\r.[\xbb\x06@F\xce\x00\x80\xbf\xfb\xd4\
\xbd\xaa\xf1\x15\x98\x9eBbjFE\xd2\xc1\xb8D\xe6\xe4\xba\x87b!\xd5\xe7k\xc7`4\
\x94\xc8y,!!\n\xea\x82\x03\xe2\ni\x95\x17N\x85u_\x97BH>O\xe4\\\xb2\x8c\t,\
\xcd\xc0\xc2\xda`\xb3X\xd0`]\x85\xe6\xfa&\\l_\x8b\xe6\xf6\x16\xd4{|81\xd4\
\x8f\x1f\xfe\xf49\xfc\xf0\xd9\x9f!\x95\xe6Pc\xb5,Ib_\xf2\xa4\x9eN\xa7\x11O$p\
\xedUW\xe2\x8fo\xbb5\xe7\rH\x06W5#\x14\x0b\xe1"\xef\x1al\xef\xe9-\x89\xd4\t\
\xa1_\xdc\xb6\x1aO>\xf40\xba\xbb\xbbqb\xa8\x1f\xbf:\xf4+\x9c\x9c\x18\x84\xc0\
\xc4@\xf3\xf6\xbc\x9f\xe12\xbb\xe4\xdf\xc9\rD]p\xa0\xd6\x9b\xfdZ&U\x0b\x9bO"\
\xe8\xb8\xdf"\xff\xae$~%\xc9\x03\x12\xd1k\xa3.\xbd\xe8\n\x80*\xc2"\xd7\xb4\
\xe7#\x7f\x80\x13\xef\x9d.;\xa9\x8b\xa2\x88x"\x81\x1a\xb3\x05\xb7_\xbf\x1d\
\x7f\xf1\x91\x8f\xa0\xbb\xbb\x1b\x804\xa1\x1c\x1b>\x8a\xfe\x89\x93\x08\x84/ \
\x96\x8af\x11\xb6\x92l\xf5\x88\xb5R`i38!\xa5"n@"o%\xec\x16\xe9\xba;\xa9Z\x8c\
^\x08\xe0\xa9\xffx\x05\x89t\x1a,M\xcf=\xbe\x04\n\xeb\xda[\xd1\xda\xb8\n\xc3\
\xe3\xe7\xe0r:q\xff}\x1f\xc7\xf6\x9e^\x99\xccG\xcf\x8fe\xbd\x8dD\xda\xda{\
\x8f\x0fY\x101M\xc2\x99\xaeG\xc44)\x8f\x13e\xa0\x10\xf6D\x11\xf7[\xc0\x9b\
\xa7u\x0f)$Du\x9f\x0f\xa7\xc2\xb0\xd9(\xc4\xe3"L\x96\xcc5\xe2geXN\xe0\xb3&M\
\xaf\xb3\x0e\x9bV\xf7\xe0\xaemw\x02\x00\x9ez\xe1y|\xf1_\xbf\x89\xc0\x85\x0b\
\xa8)`\xb3\xbe\xda\xb0\xa45\xf5\x99x\x1c\xde\x15+\xf0\xc8\x8e\x1d\xb8\xf7\
\xde{\x01H7\xe0\xdec{q\xf8\xec!\x04"S\xba\xd1R5\xe3t\xe0=\xd5R\xb6\x98H\x81D\
\xe8\x84\xd0w\x1d\xda\x83\x9f\x1ez\n\x1c\x9f\x86\x19n\x15\xa1\xdbl\x14L\xbcz\
\xd3\xcaM;\x10\x12\xa2p\xd3\xb32\x95\x17\x00\x1c\xb3\x8f\x12\x08\x91kI\x1c\
\xbe(\x1c\x0e\xbb\x8a\xc8\xc9#!re\x94\x0e\xe4&s\x00\xaa\xc8\x9d,\xdd\x03\xd3\
S\x08\x04\xd5\x91^\xa1 \xa9x\xda\rS\xb2\x07\x13\x89F\xb1\xa9s\x03\xbe\xfa\
\xd7\x7f.\x9f\xff]\x87\xf6\xe0\xb53\xfb1\x11\x9a@,\x19\x93\x89\x9b\xa5\x19\
\x15q\xe7C9\t]K\xdc\xb9\x9e\xcfG\xe8\x0e\x87\x1d\xbfy\xe67\x88\xc5\xe3`Y\xa6\
\xa0\xf1\xc5\x8b\x9c\x1c\x9d\xbb\x9cN\xfc\xf1m\xb7\xaa\x08=15\xa3+\xa3h\t]{\
\xfd#\xa6I\x00P\x11:\x00\x99\xd0m\xbe$\xa2:\x97;\x1f\xa1\xbb\xcc.\xa4\x11\
\x81\xcdF\x01PNx\xd2\n\x8a\xa1\x19XX\xe9|\xf1\x02\x0fN\xe0\x11\x88L\xe1\xc5\
\xb7\xff\x1b\x87\xcf\x1e\xc2\'\xb7\xfe\t>v\xf3\xad\xf06:\xf0\xf1\xcf\xfc=\
\xc2\xb1\x99\xbc+\x99j\xc4\x92%\xf5p$\x82\x8e\xb5kT\x11\xe9\xfe\xfe}x\xe3\
\xcc\x1b\xf22\x95U\\\xc0\xa5\x80X2&\xdf\x80\x04\x85fk\xa4\xd3i\x98X\x16_\xfd\
\xcb\xcf\xc8\x84\xfe\xe4\x1bO\xc0\x0c7jm\x92N\xaa"q\x9d\xfd\xe3\\7\x8b\x12JB\
\'\x11\x95,\xc38D\xe9\xf7\x11)R\'\x91\x18A\xc44\t7\xa4M7>d\x01t\x82 \xa2\xfb\
\xe6\x832Eo.\x98Y6+\xb7Z\tN\x10\x10\x8dFq\xfbu\xd7\xe1\xb1\x87\x1eD\xbd\xc7\
\x87\xbe\xbe>\xfc\xf4\xe4O1\x11\x9a\x90\xc7\x91\xf6\xba,$r\x919\x81\xcdbA<\
\x99\xcc"s\x00\xaa\xe3v8\xec8\x1dx\x0f\xa3\x93\x92\xdeMQ\x85\x9dG\x8a\xa2\
\x10\x0cKz\xfa\x9dW^%K.\x84\xd0\xb5{\x06\x04\xdaH\x9dL\xeczQ\xba\xd0"\xc25\
\xe2\x90\x89\x9d\x8c3\x98\xb3\xe5\x18e\xf0\xa1\x1c\xb36\x1b\x854"\x88\xc7EE\
\xb4\x0eY\x12\xd3\x82\xa1\x19y\xd2\xb5\xb0fL\x84&\xf0\xb5\xff\xfeG\xdc\xbd\
\xe5\x1el\xef\xe9\xc5#\x7f\x1b\xc5\x9f=\xf8e\x08\x82P\xd4\x98[l,\x9d#U`&\x1e\
\xc7\xa6\xce\rx\xf6\xd1o\xca\x04\xf6\xed\xdd\x8f\xe0\xc0\xe9\xfd\xf2\rha\xcd\
\x15]\xf6V\x1b\xe2\x89\x04\xee\xbc\xf1F|\xec\xe6[qb\xa8\x1f?=\xf4\x14\xccpg\
\x067\xefD\x9a\x89\xe4\xd4!It.G\xe9:p\xb8\xad\xaa\x08\x9d\x909\x90\x89\xb6\
\x1c\x0e\xbb\x9cM\xa3\xbcy\x81\x8c\xc6\xee\xb1\xd5eI0\x84\x10\x94\x1by\x80zs\
\xcb[[\x87\xf6\xd6\x16\xa4\xb9\xe22\x9a\xacf\xb3n\x85\xa4(\x8a\x88F\xa3\xb8\
\xe7\xf6\xdb\xf1\xd8C\x0f\x02\x00\xbe\xf7\xab\xef\xe3;\xbf\xfd.\x02\x91\xa9\
\xaa\x18G\xf9\x08\xddf\xb1\xc8D\xae\x17\x9d+\t\xddI\xd5\x82\xf6Q\xe0f\xcc\
\xe0\xd2\xe9\xa2H\x8a\xa6i\x04.\\\x00\x00\xdcr\x87D\xe8\'\x86\xfa\x01($2\xc5\
*\x8b@\xb9\x12\xe3C\xd2\xf11\xee\xa4<&\x9c\xe9z\xd5~\x0c!tW\xd0!\x8f3&U\x9b\
\xf3\xb8\xb4A\x88\x89w\xc2\xc4;e\t\xd1f\xa3\xe6\x9c\x10\x95\xb0[\xec`\x19\
\x13\x9e\xed{\x1a\'\x86\xfa\xf1\xb1\x9bo\xc5\r\xdb\xb6!\x91L.j\x01U\xb1Xr\
\xa4\x1e\x8eD\xb0\xb1\xe3R<\xf1\x8d\xafb}[\x07\x9e\xde\xf7\x0c\x9e|\xe3\t9\
\xca\xfd]"r\x82t:\r\x9b\xd5\x8a\xbbn\xff \x00\xe0?\x0f>\r\x00\xb3K\xd0\xcc#\
\xa0\xd6\xcc\x95P\xc9.:\xd0\xbb\xb9H\xa4\xae\x95]\x94$\xce\xb8\x93p\xdb\xdd\
\xaa\xa57\x89\xe0\xb4\xd0n\x98\x02R4\xa8$\xf6\xaeu\xeb\x8aNSM\xa4R\xba\x91z<\
\x91\xc0\xa6\xce\r\xf8\xe7\xfb?\x8fz\x8f\x0fO\xee\xf9\x89\x1c\x18,\xe6\n\x8f\
\x10\x91\x1e!\x11"\xcf\x17\x95kW\x15Dv\x11\xfc"\x9aWx\xe1\xb0\xdbU\x05R\x85\
\x80\xd44h3\xa4\xc8\xaaJ/\x83E)\xbd\x90k\xaf\x8d\xd4\x81\x0c\xa1;\x1cvyLi%>-\
r\x8d\xd5p*\x8c4#E\xeb\x00\xe4\xc7B\xc9\xdd\xc2\x9a\x91H\'\xf0\x1f\xfb\xff\
\x1d\x00\xf0\xd0\x17\xee\x83\xa3\xa6fIYM,)RO$S\xf0z<\xf8\xea_\xff\xb9L\xe8/\
\xbe\xfd\xdf\xb0\x9a\xac\x8b\xba<\xae$\n\xd2<\x05\x11m\xcdM\xd8\xb8\xb6\x0b\
\'\x86\xfa129%\xeb\xe7$z!\xbfk\xe1\xa6\x1d\xf2\x8f\x1e\x98T-\x1cnk\x96\xec\
\x02@\x97\xd0\x9d\xe9z\xd0#\x94|\xd3\xf2!K\xc1Z\xba\x9e\xf4B\x08\x9d\xe8\xea\
\xd7\xf7n\x86\xcdj-\x88\x94h\x8a\x82\xc3.\x9d\x07m\xa4\xce\xf1<\x1c55\xf8\
\xde\x03\x7f\x8bz\x8f\x0f\xdfx\xf6\xdfpd\xe2MXM\xd6\xaa\x08\x0c\xf4tr%\x91\
\x93H\x9c\xfc\\\x08%\x10\x08_\xc8\x8a\xce\t\xa1G\xa31\xd0>\n\xcd\xf5M\xb8\
\xe2\xb2\xcb\xe4\xdc\xfb\x82\x8f\x87e1<~.+%U\x19\xa9\xe7\xd2\xd4\x95\xd7[\
\x19\xa9\x03\x90\xa3u2\x8e\x94\xd1\xba,\xc1\xe8\x80D\xe9\xdaq\xeb2\xbb\xe4h\
\x9d\xc80d3\xb9P\xd8-vL\x84&\xd0\xd7\xd7\x87\xf5m\x1d\xb8b\xc3\xfa%\x15\xad/\
)RO\xa5\x92\xf8\xec\xddwc{O/v\x1d\xda#\x13z5\xdc\x84\x95B!\x03I\x10xt\xb4\
\xafA\xbd\xc7\x87c\xc3G!0R\x9a\x98\x89w\xca\x91K.\x90\x9b#\x97\x9e\xce\x9b\
\xa7\x11\r%dB\x8f\xfb-\xaa\x1b/\x1a\x8d\xc9\xd2\x0b E\xe9B\x8b\xa8\x8a\xc6\
\xb4R\x8b6\x1bBI\x06Z\xe9\x85\x909!\xf7\x8dk\xbb\xf0\xa1\xab\xaeB4\x16\x9b\
\xf3\xdc\x90\xfct\xad\xc7\t\xcb0\x88\xc6b\xb8\xe7\xf6\xdbd\xf9\xaeZ\x08}.2\
\x07$\xd2\x89%c\x18\x99\x9cB ,\xc9"g\xdf\x8cb\xefs\x03\x002d\xae\x84\xc3a\
\x87+&=w\xc7\x1dW\xa3\xb9\xa1\x01|\x11\xd1\xa7\xc5lF\xff\xc0 \xfe\xf9{?\xc4\
\x89\xa1~\xd5\xea\t\x90\xae[\xf3\xca\xa6\xac\xf7)5u"\xc1\x90\xb1\x01H\x85g\
\xd1h\x0c\xd1hL\x1eWq\xbf\x05\xe7\xa8\x00\xa2\xa1\x84*\xfbe: \x8dS\xe5X\x1dN\
\x9c\x03 E\xe8\xda\x1f@\x8a\xd4\xe3q\xb1(\x19\x86`\xef\xe0\xff\x00\x90\xf6\
\x11\xa4b\xc6\xe2V7\x8b\x85%\xb1QJ\x8aA6un\xc0\xbd\x7ft\x07&\x83~\xbc\xf0\
\xf6\xcf\xc12\xa6E\xbf\t\xab\x014\xcd\xa0uU#\x00)-\x92\xe3\xd3\xa8\xb5Q\x08\
\xc73\xe9]\xb0IKR=\xf9e8q\x0e.\xb3+\x8b\xd8\x95Q\x90D\xee\x00\xcc\x89LF\x82\
\x07\xb3\x91T\x0c\xf0@\xde\xe8")\x8d$\x1a\x0b\xc5BY\x190\xca\x08N.\x9a\x99\
\xd2\xcfzQ\xa2\xde\xe3\x93\xbfk\xbeU\x8c(\x8a`M&\xd8\xac\x16y\x93\x8f@2\x04\
\xf3\xe0O\xff\xf06\x00\xc0\xcb\xa7^\x02P\xdeL\x15 \x93]\x01 o\x16\x962\x1d2\
\t\x85\x950\xcd\xc8\x11&!%\x9b\xc5\x82@\xf8\x02~\xf9\xd3\x93\x08\x85\xc3\xb0\
Z\xad\xf0\xb8\x9c\x88\'\x92\x18\x1a\x1d\xc5\xf1\xfdk\xf0\xa1\x1bW\xc9\xf9\
\xdf\x0e\x87\x14\xb9\xd3>\n\x98M\t\xf7\xd8\xeap\xcbG\xdf\x8f\xff\xf3\xdd\x17\
ab\xd9\x82V\x83\x0c#e\xca|\xf7\'O\xe1@_\x1f\xbe\xf0\xd9\x8f\xe2\x9a\xcekT\
\x9b\xa5\x85f\xc1\xb8\xedn\x00I\\d[#gV\x91J\xe3`|\n\xa8\x07\xc8\x1f\xc8x\xe1\
C\x160\x97\xa87Z\x01\xa86\xe2\x01u\xde{D\x9c\xc6t0\x8dp*<+\xc3\x98d)r\xae\
\xc8\x9deL\x98\x98\x9d0\xba\xbb\xbb\xe1v\xb9\x90L\xa5\x8aJ\xa5],,\tR\x17D\
\xa9\xdc\xffs\x9f\xb8\x1b\xf5\x1e\x1f\xbe\xf7\xab\xefc:\x1e\\\xb6\x92K)\xe8\
\xa8\x93n\x82\xf1\x884\x109!\x05\x93\x05\x00\xcc2\xb1\x93\xec\x00 \x13\xc5\
\x03\xc0\xe6\xb5\x9dp\xdb\xdd\xb8\xd8\xbe6K\xd3\xce\x05\x12Ek\xa3i\xad\x06\
\xae\x07eua@\x08\xca\x95\x85\xda\xff{\xae\xcf\xc9\x07\x11\x90\xbdGHI;\x01\
\xd9T^\xdf\xd6\x81]\x87\xf6`"4Q\x96\xb1DH\x9cd_\xd9\xcd\x0e\xb8g\x8b}\x00dE\
\xcfJD\xc4\xe9\xbc\x7fW\x92\xf3\xb97\x03\xb80\xfd\xbala0\x1d\x0e\x83\xa6i\
\x98\xcd\x16\x0c\x8f\x9f\x03\xb0\x01\xaev\x07\x04\xbf(\xbf\x87D\xe9d"\xbd\
\xe1\x8ak\xb1\xbb\xf5\x08\x06\x86G\x0bN\xd9\xa3)\nV\xab\x15\x87\x8f\x1d\xc77\
\xbf\rt~\xa3\x0b@f"&\xd7Q\t2yw\xb6v\xc1\xdb\xb9\xb0\x85\x80D\xfb\x0fLO\xe1\
\xd8\xf0Q\xec\x7f\xf7\x80\xac\xb1\xdbl\xd2w\xceE\xee\x16\xd6\x8c@d\n\x93A?\
\xacu5p\xbb\\\x18\x9d\x980H\xbd\\\x98\x89\xc7qq\xdbj\xf4n\xbd\n\x93A?\x0e\
\x9f=4ge\x9d\x1e\x947\xddBb>\x84QP\x14ES*\xff\x16\xe5\xb9!y\xbaJb\x8f\xc7E\
\xc4\x11FK}\x1d>\xba\xf9.\xb9\xec\xbdX\x8b\x00B\xba\xda\x0c\x15\x82\\\x04/\
\x97\xd9\xb7I\x0f\'\x86\xfau\xb5t\xbd\xf7O\x06\xfd\x18>7\x0e w\xba\xa7 \x08\
\xf0z\xb2\xb31X\x93\t\x89D\x02f\xb3\x05\xbdW\xbe\x1f\x00\xf0\xda\x99\xfd%\
\x8d%%H\xf5h\xad\xcd\x83Kk/Bg[WE\xab\x99\'\xdb\xfd\xf8\xc5\xae>\x1c}\xe7=0,\
\r\x13\xc3@\x14\x05X\xcc,\x86F\xc7p\xf0\xf41lFg\x86\xccu\n\x87\x9bW6\xe1\xa3\
\xb7^\x8d\x7f|\xe4)9_\xbf\x10\xd0\x14\x05\xb3\xd9\x82\xd1I?\x12S3hno\x91\'ib\
K\xa0\x8c\xd6/\xb6\xaf\x95\x8b\xb8&\x83~\xf4\xf5\xf5\xe1\xd4\xd8\x88\xec\xf7\
s!,\xc9++\\\xb5\xb8\x10\x9e\xce\xf9\xa8\xf7\x9a\\\xef\x03 \xfb\xf1\x90\xebp\
\xd7\xb6;\xd1\xd9\xda\x85\xff<\xf84F&\xa5\xe3%)\x8f\xf9@\xc6\xa0\xd7\xe3\xc6\
\xd0\xe8hA\xe7h\xb1\xb1$H\x9d\xe38l\xbf\xfaj\xd4{|xz\xdf3H\xa4\x13E\x13%\xb9\
\xf1\x1a\xdc\rh\xb0\xae\x92#\x1fi)X9\x84b!\x1c\x1b;\x8e$\x17/iy_H\x9e:\xb17%\
\xa4\xcc\xf1iU\xf6\x06\x89F\xa4\x9c]\x80,C\t\xa1?\xf5\xc2\xf3\xd8\xf3\xfao1<\
1\x8eq\xbf_eeK\xa2\\\xed\xa3\x16\xca\xbf\xeb\x818/\xba\x9cN\xb464\xa2\xbd\
\xb9\x19\xed-M\xe8\xddz\x15\xd6\xb7u\xe0\x04\xfaU\xe9\x8cz\x84^\xef\xf1I\x05\
AG\x8e\xc0^S\xa3{^x\x9e\x87\x89eU&T\xca\xe3Ks\x1cV\xf9Vbc\xd7%\x98\x0c\xfa1\
\x11\x9a(9\xd3\x85\x17x$\xd2\t\xd4\xda<\xd8\xba\xeej\\\xd3yMV5\xf3\x11\xe1(\
\xce\xbe58\xe7g\xd9\x1b|\x88M\xf8U\xbf+\'j-\xae\xee\xeeF \x18B(\x1cF\x9a\xe3\
T\x0e\x9cO\xffp?\x8e]<\x8e\xdf\xdf\xde\r\xd7%\xb5\xba\x99F\x00p\xc7\x87n\xc3\
/v\xf5\xe1\xf0\xb1\xe3EU.34\x85D"!\xf9\xcb\xa0E\xf57\xe5f\xb7\x97\xf6\xa0\
\xbb\xbb\x1b\x93A?\xfe\xf9{?\xc4\xae\x03\x0700,\x11\xe3BX\xf1\x9a\xcd\x16\
\xb8\xec5hkn\xc2\x9f]\xb7\x1d\xf7\xde{/\xee\xab\xdd\x81\x87\xfe\xeba\xb9\xe2\
4\xdf&*\xc7\xa7\xa5\xfc\xfb\xda:\xd9er)x\xf2W=\xa9\xa7\xd3i\x98\xcd\x16\\\
\xdf\xbb\x19\x00\xd0?q\xb2\xe8\xc8*\x96\x8caM\xfd\x1a\\u\xd1Vl\\\xdb\xb5\xe0\
K\xc0\xf1\x97\xcf\xe1l`\xb8b\xfa?CS\xb2\xab\xa2\xb2\xf21\x17\x04&\x86\xce\
\xa6-X\xdf\xd6\x81\xc7\x1f\x7f\x1c\x9f\xf9\xcew\x91J%u-x\xf5@\xcfYEI\xc1D3\
\x00\xc5\x80f\xa4\x8d\xc9D*\x85`8\x02k0\x84\xc1\xe1\x11\xfc\xf6\xe8\xdb\xb0\
\xdbl\x18\x1c\x19\xc3\x83;vH\x91\xb9\xe23\xf4"\xf5\xa7^x\x1e\x7f\xff\xbf\xbf\
\x83\x0b\xa1\xe9\x9c\x92\x01\xb1|U\x1aP\xa9\xbe\xbb \xa0\xbd\xb5E\x96^\x92\\\
\xaa$R\'\x84~\xf5\xda\xad\xb8m\xcbm\xb2w\xc8\xcf\x9f}\x1e\xbb\x8e\x1dC\xff\
\xe0\x00\xceO]@8\x96]H%\x08<h\x9a\x91\x1fS)i\x12U\x9e\x7f\x9af`b\x19\x95\xff\
9\xb1\xf4%\x93c{\xabD\xa8\xe3~\xbf\xdc<\xe4\xbd\xa1\xb3\xb0Z\xad8\xd2\x7f\n\
\xa7\xcf\x0e\xe3\xda-[\xd0\xb2A"\xa4\xe6\x15^t\xb6u\xc1\xdb\xe3\x01\x86\xa4\
\x15\xd3\xe7>q7\xfe\xe2\xe1\x7fD\x9a\xe3\x8a2\x8f\x13xIZ\xa9\xf7\xf8\xb2\xf6\
>\xacu5\xc0\xf9 \x9a\xdb\xa5\xe3\xfb\x9b\xaf\x7f\x0bO\xec\xdc\xa9\xf2\x99QV\
\xf4\x02s\x1b\xaci_\x93\xf5\x9c@\x01t\xc6\xab_\x10E@\xa0\x10O&q\xf8\xd8q\x1c\
>v\x1c\x00p\xef\xbd\xf7\xa2\xb3i\x03\xde8\xf3\x06H\xc5\xe9\\P\xf2E\xb5\x13:\
\xb0\x14H\x9d\xe3\xd0\xdc\xd0\x80\xe6\x95M\x98\x0c\xfa1vaL.\xd1.\x04\xb1d\
\x0c\x1b\x1b\xae\xc0\xdd\xbd\x1fW\xddx\xfdS\x01\x84\xc2\x11\x84\xa3sWQ\x96\n\
=\xf7\xbaJ\xa0\x98F\x0c\xc4\x03ck\xc76L\x06\xfd\xf8\xc1\xee]H\xa5\x92p\xd9]\
\xaa\x9b"\x17\xb4\x83:g\x03\xe9\x1cM\x18\x88\xc77\x89|^=|\x08\x9b\x0f\xed\
\xc1\xf6\x9e\xde,r \xf2\xc5\x89\xa1~|\xe3\xfb?\xc6\xb3/\xbd\x84d*\x95\xd7\
\x8f\xc3\xe3r\xa2\xd1\xa7\x9e\xb4\x95v\xb1\x11\x9aF\xd7\xbau\x002Y8\xc5\xa6\
\xbc\x11\x19\xef\xa6\xf7}\x18wm\xbb\x13\x93A?>\xff\xb5\x7f\xc2\xf3{~\x8d\xd1\
\x89\t\x95W\xb7\x89e@e\x15\xfa\x98T\x8ff\xb3IER4E\xc9\xdfQ\xd9<D\xeb\x8fN\
\xac\x88\xdd\x0e\'6^z)\xee\xfd\xa3;p\xdf\x97\x1e\xc6\xce\xdd\xbba6[\x90L\xa5\
\xf0\xab}\xfb`z\xdd\x84D2\x85\x1a\xab\x05n\xd7/p\xc5e\x97\xa1\xb3\xab\x11G\
\xea\xdf\x81\xb7\xd1\x81\xb5\xab[q\xe2\xbd\xd3\x05\x93\xba\x94B\xbb\x12\x9d\
\xad]\x98\x0c\xfaU\xfb*\x80\xb4W\xd2\xbc\xb2I\xae\xce}q\xef^\xb8].U\x97$2\
\x8e\n!I]\x89M\xfb\x1c-f\xff\x8d\x16\xc1\x08,\xdc.\x17B\xe10~\xb0{\x17n\xb9\
\xe3Vl\xed\xd86K\xeasc)xFiQ\xf5\xa4\xceq\x1c\xda[[\xe0\xad\xad\xc3\xe8\xe0HQ\
\xd2K\x92K\xa1\xd6\xe6\x91\t\xfd\xf3_\xfb\'\xfc\xf0g\xff\x85T*\xa3\xa9W\xc2o\
\x9d,+\xb7wv\x02=\xd2\xc4R*\x8a\x8d\x0c\xe2\xc9\xb9-J-\xacY>\x9f\xa3\x93~\
\x98\xcd\x16\xfd\x9b\xa2\xc0\xe3\xcb7\t(\xe5\x18-\xa1\x13R"\xde\xeaz\xd1\xf9\
?\xfc\xe0\x9f\xf0\xfd\x1f\xff\n\x81\x0b\x17`b\xd99\r\x96F&&\x11\x0cG\xd0\\\
\xefS\xfd\x9f\x80\xd4\xc1\x87\xa2iySytR2\xa1Rf\x98\x14B\xee\x89tB&\xf4\x13C\
\xfd\xf8\xecW\xfeEv<\xb4\x98\xcdE\x9b@\xe5j\xc4M\xa0mRA\xce_(\x1a\x91\x9b\\\
\x00RD\xf9\xd0\x17\xee\x83\xcb\xe1\xc0\x8b{\xf7"\x14\x89H\x16\xb2\x82\x00\
\xb3\x89E\x9a\xe30\x19\x08\xe0\x85W^\xc1\x8b\xaff\xfe/\x97\xbd\xa6\xe0\r@Q\
\x14\xc1\xd0\x14>w\xcb\xadX\xdf\xd6!\xfb\xbfh\x89\x9d\xa0\xaf\xaf\x0f\x89tZ*\
\xe0\xc9a\xd5PQ\xd0"\x04\x11p\xd8\xed\x18\x1a\x95\xae\xb7\xb7\xb6\x0e\x16\
\xd6\\\xd4*m\xa1\x9a{\x94\x03UO\xea\x80tB\xeb=>\xec\x8d\xed-\xea}\x1c\x9f\
\xc6\xd6u\x92\x16\xff\xf0\xa3\x8f\xe2\x91\'\xfe/lVk\xc5\rz\x04A\x00\xcf\xf3\
\xb07H\xd5w\xa4\x98\xa1\x94e~%4<\xa7M:\x9fG\x84\xa3\xf3\xbe\xd1\x94\x84N\x1a\
=\xe7kQ\xa7$t\xe2oO\xb4d \xb3\xd1\xbag\xffkx\xe4\xc7O\xe2\xf0\xb1\xe3\xb0Y\
\xad\x05\x13%q\xaa\xec\x1f\x18\x84\xcdb\x91\x8b\x8fH\x07\x1fGMM\xc6\xc6@\x9c\
\x86\x855\xcb\xe9\x82dS9\x1f\xb1\x93\x95\x1f\x89\xd0\xef\xd8\xf1\x05\xf4\x9f\
\x1eP\xadtJ\x85\xf6\xfc\x11\xc4\x13I\xd8\xac\x16\xb9Gk8\x12\xd1\xed\x06Ep\
\xe5G.\xc2\xfa+V\xe2\x99g~#m\xa6\xd2\x94L\xda\x0c\xc3\xc0d2A\x14E\x88\x00(H-\
\xe8\x8a\x01/\x88\xe8\x9f\xca\x88eZB\x97\xb4vio\xa4\x7f*\x00V\xb1RY\xacF\xe0\
\x14E!\x95Latp\x04\xcd\xed-`i\xb3*}t9aI\x90\xba2\x07\xbb\x18\xb0\x8cI^"\xfe\
\xf4\x97\xbf\x90\xda\x8e-@J\x12EQ\xb2$B\xf4\xb8\xf9fX\xe4\x84P\\\x95\x1b\xa7\
Y\x99$R\xa9\xb2\xb4\xad\xcb\xd5\xa5^)\xbb\xe8\x11\xba\xdb\xe5\x94\xbb\x1e\
\x91\x8d\xd0\xc7\x7f\xfcs\xec:p\x00\xb1\x99\x99\xbc\xe4\x95\x0b4E\x01\x0c\
\x83d:\x8d\xc4l\x87$2\xc1\xb0&\x13.mj\xd1\xcd\xf4\xd1+\xcfW\x12</\xf0\xb0\
\x9a\xac\xb8\xa1\xe7\x06\x00\xc0\x1f\xfd\xaf\xfb\xd1\x7fz\xa0h\xcf\xfb\xb9\
\xa0l\xed\x97\x0b\x84\xd8\xf5:D\t~\x11\xcd\xf5M\xf8\xc2g?\x8a]\xbf:\x82\x17\
\xf7\xeeE<\x99T\xc9+\x14E\xa1\x94\xabNQ\x14\x18\x9a\xc2\xf7\x9f~\x06\x9b\xd6\
_&{\riA&\xe7P8\xa2\x1a\x1b$\x88X\xe8\rG\x8a\xa2\x10\x9e\x89\xca\x9b\xbb6\x8b\
\x05\xb1T\xe5\xa4\xd7\xc5\xc4\x92\xa8(%iJ@\xe1\xe4\xc8\x0b<\xecf\x07\xd6\xb7\
u\xe0\xc8\xe9\xa3\x18;7\x01S\x81\x1b\x81\xe5\x00!\xca\xc9\xa0\x1f\xb1d\xac*-\
\x80\x03\xe3Q\xa9\xfc\xb9D\x07\xba\xb9d\x17\xad\x8e\x0e\xa8\x97\xb1\xee\xd9<\
\xf2\xfaY\x02{\xfc\xf1\xc7q\xd7}\x0f`\xe7\xee\xdd\x10\x04\x01n\x97\xbeOM\xa1\
\xa0(Jn6\x9cL\xa7\x11O&1\x1d\x0e\xe3\x97od\xf4T\x966\xeb\xfa\xa8(AH>\x91N`\
\xd3\xea\x1e9c\xe8\x95\xd7^\x87\xab\xc6>or\xd2{?!?\x92iD2\x92H6O.\x90\xcc\
\x93\xb0]J\xf9\xbb\xeb\xf6\x0fb\xc7\x9f\xdc\x0c\x8a\xa2\x90H\xa6\xc0\xf3\xfc\
\xbc\x1b\x8a\x9bL&\xa49\x0e\x7f\xff\xbf\xbf\x93U]*\xa74\xceF\xee\x95\xdc\xb3\
*\x064E\x81eYU\x1b\xc5\xe5\x8a\xaa\'ueF\x00)\xac)\x04\x9c\xc0\xc3\xebZ\x01\
\x008\xfb\xd6 \x12\x1c\xb7(\xf6\x99\xf5\x1e\x9f\xec\xfeV\n\xe6$\x8cy.\xf9\
\x01\x14m\xee\xa4\x85V\x0b\xce\xa5\xa3\x13Bw9\x1c2\xa1\xafp\xd5\xc2\xde m\
\x86~\xf9\xc9\'\x11\n\x87\xe1r:a2\x99\xca\x1a\xc9Q\x14\x05\x86a\xc0\x0b"\xbe\
\xf1\xefO\xe0\xf1\xff\xf7\xac\xaa\xd8G\x8f\xd8\xb5r\x8c\xd5dE\x8fo\x13\x00\
\xe0\x91\x1f?)\xbd\x88)\xcf\x98"\xdfUO\x9a\xd0\xa6\x90\x12b\'\xd9=\xe1HD\xce\
\xdb\x06\xa4\xaaJRx\x14\x8cO\xe1\xd2K\xd6\xe0\xba\x0f|\x00kZ\x9ba\xb3X\x90L\
\xa51\x13\x8fc&\x1eG8\x12\xc1L<^\xf4\x18p\xd4\xd4`ht\x14\x9f\xfd\xca\xbfd\
\xed\x83\x04\x84 \xbc\xb5u\xf2jH\xbb\xea\x98o\xdf\xd8\xc5\x80\xde\x8a\xa8Z\
\xb1$\xe4\x17\x82|\x15w\xf9^?\x99N#\x95J\xc2lZ\xf8\n\xd4\\\xb9\xe3\x85b!\x96\
\xa9\xe5\x9a\xec\x947\xaf\x9e\x8e\x0ed\x13: 5\xbb\xfe\xe1O\x9f\xc3\x84\xdf\
\x0fg\x85\xfb\xc8Z-f\xa4\xd3)\xfch\xe7N\xfc\xc1=\x97\xc3\xebZ!od\x13b\'\x9b\
\xcdJ9&\xc9\xc5\xe1\xb6\xbb\xd1\xdc\xde\x82\xbe\xbe>\x0c\x8d\x8e\xc1f\xd5o\
\xf9W.he\x18\x12\xadk\xf5u\xd5\xf7\xab\xab\x01f\xd3\xe2\xc3\xf6i\xb9\x92\xf4\
\xdeO\xdc\x82`|\n\xa3\x93c\x18;\x9d\xc0\xd1w\xdfU\xbdopx\x04S\xa1P\xc1M\x97\
\x05Q\x84\xcb\xe9\xc4\xbe\x83\x87p\xe4\xe8;\xe8\xddzU\xa6\xce\xe0|\xc6&\x80\
\x90\xa1^}\xc3b\xe5|\x97\x92\xd2ll\x94V\x08\x11Q\xbf\xb5\x95\x1e8>-\x17\x18\
\x91(f!#\xf5j\xd5\xd4\xcb\x85\\\x19\x1bzQ:\x80\xac\xc6\xdf\xca\xca\xbf\xb3o\
\r\xe2\xf9=\xbf\x86\xd9l\x01SH{\xb5y\xc2d2atb\x02g\x0e&\xb1ak\xf6D\xaf%w\x82\
\x06\xeb*\xd4{|x\xfc\x8dg\x11\x08\x06\xe5M\xd8r\x83l\x98\x02\x19b\'\x84h5\
\x9b\xb36N\x95\x92\xcc\xe8\xf91\xe9>\x89\x02\x0e\xd8\x11BH\xf6}\xf1\xd8\xea\
\xe0i\xab\xc3\r=M2\x01\xafo\xeb\x903x&\x03\x81\xa2\xf6\x9ch\x8a\x02\xc7q\xd8\
\xf3\xfao\xb1\xb1\xeb\x12]\x97M-\x19j;P-$H}\xc5|\x93\x17\xaa\x1dU/\xbf(Ql\
\xa4\xbe\x98X0M]G~\xe1\xf84x\x81\xd7\xfdY\x08h\xa3t\xad\x8eN\x08\x9dh\xe9\
\xfdS\x01\x9c\xf3\x9f\x87\xd5\xb2p\x1d\xdcmV\x0b^;r\x04@vC\t\xd5\xebf7\xd4\
\x12\xe9\x04\x9a\xeb%\x17\xc2\xc1\xd9r\xf1r\xcb\x08\xca\xef\xce\xf1\xbcLz\
\xca\x0c%=\x8d=\x9eH"4kZ\xa6\xd7\xacB\xf0\x8b\x08\xdb\xa7\x11\x8cOI\xd1\xfa\
\xf91\x95\xe9\x96\xb7\xb6\x0e\xe3\xfe\xe2,"\xc8\xf1\xda\xacV\xfc\xf6\xe8\xdb\
\xf2sz\xbe\xea\xb9\xaa\x8c\x17\x1a$}y)6\xa2/\x06K\x8a\xd4\x8b\x89\xd4u\xc1/\
\xbcu\xa62R\xcfE\xb4\xf9\xc8\xb6X\x92#\xfa/G|n\xb4?|\xba\xa0\\\xf6B\xa0\x8c\
\xb6\xb4\xba\xa9\xb6P\xc6\xa5\x91U\xeaM&9\xb5\xf0@__Y\x8e\xa7\x18P\x14\x8dH4\
\x8a\x81\xc9\x019X\xd0\x12\xbb\xd7\xb5\x02\x13\xa1\t\xfc\xe2\xc7\xfd\x18\x7f\
\x93\x95\xcb\xed\x87\'\xc6+v\\\xda\xeb\x9d\x8b\xd8\x13\xa9\x14\xe2\x89$\xe2\
\x89\xa4J\xd6\x08\x08A\xc4\x921D\xc4i\x8cG\xce\xc9\xae\x85\x82_\x94\xb3\xc7\
\x08\xb9\x13\x8c\x0e\x8e \x18\x8e\x80)!\x91\x80a\x18\x04\xc3\x11\xb9\xf1\xb4\
\xde\xa4BP-\xe4\x0e\xcc\xafv\xa4\xda\xb1\xa4\xe4\x97yG\xeae\xda\xd4*\x06JM\
\xbd\x90h];\xd8\x8a\xd1\x1d\xeb=>|\xf6\xba\xcf\x15\x7f\x90%B)\x13\x00\xd97\
\xad6\x1dQ\x19\xa5+14:\x06\x13\xbb\xf0\x9bg\x82 \xe0\xcd\x97.`\xe3=\x99\xe7\
\x88W9\x00\x04\xc2\x17\xf0\x9b\xe7\xc7\xd1\xd6\xdc\x84\xcb\xaf\xf5\xe2\xc97\
\x9e\xc0\xc1\x83\xef \x1c\x89\x14l\xa9PN\x10b\'\x13(\xf1\xda\xd1\xd6\x1a\xd8\
-v\xb99\x86\x12\xc4\xe7H\xeb\x05\x13\x10\x82\x98\x89%PJ\x0f\x08\x8a\xa20\x1d\
\x0e\xe3L`\x00\x1b\xd7vat\x8e\xfe\xb2\xd5\x00"\xbf,W,)R\x9fw\xa4\xbe\x08\xa8\
\xf7\xf8\xf0\xc9\xad\x7f"G2\x80\xbaK\x8c\xd6\x7fZ\xaf\xd1@>\x08\xa2\x08\xab\
\xc9\x82\xb3o\r\xe2\xc4\xca\xec|\xe1\\81\xd4\x8f\xc1\x911\xd04S\xf0\xe6\x98\
\x16z\xb9\xe9\xdarv\xad\x96\x0ed\xa2to\xa3\x03/\xed9\x88X<\xbe(\x96\xa64M#\
\x18\x8e\xc8\xb6\xb7d|\x11b\xdf\xfb\xdc\x00F\'&P\xb7v\x1a\xbf|:\x8e\xfe\xd3\
\x03\xb8\xe7\xf6\x16\xd5dU\x89\xcd>\xad\xc7\x89\xbc\x1aR\xe8\xec\x00d\xad=\
\x91J\xc9\xa9\x83\xdb{z\xb1qmW\xce\xcfV\xb6\xa3#\xab\xc8\xb3o\r"\x91N\x96T\
\x94GQ\x14\xe2\x89\x04\xce\x0fr\x08t\xe4.\xa9\'V\r\xe4\xb8\x17\xa5\xbat\x16\
\xcb]~YR\xa4\xbe\x944u\x9a\xa6\xe5JIom]\xc6n\xb6\x00\x14c\x81KS\x14@\x89\xf8\
\xf2\x93O\xc2\xfa\xcc3E\x1dc"\x95\x82\xc5l*\x99\xd4\xf5\x10O$\xb3\xa4\x17 w\
\x94>|n\x1c\xbc b\xe1)=\x83X2\x86F\xef*D"\x99\xa0\xe1\xcc\xc1\xa4\x9c\xe1\
\xf2\xde!\n\x89\xf4(\\v\x17\xee\xba\xfd\x83\xf8\xfac?\xa9\xb8\xc3 \x81Vg\x07\
\xb2\xc9\x1d\x90\xb2L\xfatd,\xbd\x9e\xaf\x804&I\x8ey\xffT`\xdev\x19q\xc1\x83\
\xb5\x00\x00 \x00IDAT\x83\xa3\xa3\x19S\xb6\xf3\xd9\xbaz.\x14b\xe8Un\x14k1\
\xbd\xd4\xb0\xa4H\xbd,\x9a\xfa\x02H0$\'\xfa\x91\x9f?\x8f\x1f\xec\xde\x05 \
\x93[\xac\xcdV P>o\xb7\xd9\x10\x08\x86\xa4\x06\xc1\x05\x0e\xf6H4\x8a\x0b\x9c\
tc2\xb4T\xd1\xaa\xf7\xa8\x04M\xd3E9\xf3\x15\x02\xb2I\x9a\xaf\x12\x94h\xe9\
\x81\xf1(\xfa\x07\x07\xcaR\xd1Z\nh\x9a\xc6t8\x8c\xb7^\t`\xedG/VE\xebR\xb3\t\
\xe9Z\x82\x92\xaeA\xef\x07\xb6\xa0ye\xd3\xa2\xc9/\xc4gGK\xee,\xc3\xe0\xcd\
\xe3\'\xd0\xfb\xe9Og9:\x12\x90\x8a^\xb2r"i\xa5\x1du^\x1c}\xf7]X\xe6\xa1w\x9b\
\xcd\x16\xb8]N]\xef\x17 \xdb\xbbf\xb1QJ\xa4n\xe4\xa9W\x08\xf3\x8d\xd4E\xba\
\xb4\xd2\xe8R14:\x864\xc7\xc9\xae}\x00T\xbf+\xa1}\xdeb6\x17E\xb8\x0c\xc3\xa8\
^o\xca\xf18_h\xabH\xb5>/s\xa1^#\xb3\x9c\x9f\xba\xb0(Ea@f\xf2=\xda\x7f\n\x9d\
\xc3\xabpi\xebj \x9a\x1d<\x90^\x9e\xf7~\xe2\x96yuc*\x07\xc8$\xafG\xee\x80Zo\
\x07\xf4\xdd\x1d\x89T\xd3\xde\xdc\x0c@\x92\xc8\x04A(i\x82\'\xd5\xa9+\\\xb5\
\xb2I\\\xb5\xa3\x94H\xdd\xc8S\xaf\x10\xe6\x1b\xa9\x97Sf(\x04&\x93I7\x02R\xde\
\x98\xb9\xb0\x14|\x9b\x01u\x81\x8c6"\xd3\xd3\xd3\'\xd3i\xb4\x03\xb2\x9e\x9eH\
\xa7u\xaci\x17\x0e4M#\x14\x89\xe07/\xbf\x83\xe6;\xbdp8\xec\xf8\xd5\x7f\x1eE\
\xff\xc0 X\x96A:\x9dF\xad\xcb\x85\xcb\xd6\xae)z\xbf\xa3\x92P\xbac\xea\xe5\
\xb5\x13\x10\x1d\x9b\x10;qv\x04f\xeb7f%\xb1R2_\x00\xa9m`\x8d\xd5\x82\xf6\x96\
&\x04\xa6\xa7\xb2\x8a\x8f\xaa\x11\x86\xa6^E(5R\x0f\x85\x17o\xe9\x94\x8f\x9c\
\x97\nq\xe7\x83\x96@\xb4\xc4\x1e\x8eFeC6@\x1d\xa9\x87\xc2\x11\xf09V.\x0b\x89\
\x1a\x9b\r\'\xde;\x8d#\x136\x8c\xbf\xc9\xe2\xf57\xdf\x02\xcb2H\xa68\xacim\
\xc6U\x1f^U\xf1\x0eY\xa5 W\xd4\xae,X"+("\xed\xe9\xc9b\xca\xebS,x\x8eCKs\x13.\
mjY\xd6\x91\xfaR\xc2\x92"\xf5b"u\x961\xc99\xbaD?\x14Eq\xc1\xa3\xf5\xdf%h\t=\
\x14\x8d\xa0\xb5\xa1\x11\xa1pD^\xea\x13\x04\xc6\xa3\x18\x9e\x18G\x9a\xe3\xaa\
\xa2\x99/\xcb\xb2x\xe1\x89~\x00"\xd8\xd9\xf4J\xb3\xd9\x84+\xae_\x01\xb7\xdd\
\x8dH|\xe9h\xaaZ\xe4\x9al\x81Le/MQ%\xdd\x1f\xbc \xa2\xd1\xe7\x83\xb5\xaeFWS\
\xd7\xae\xd4\xaa\x01\xcb=R_R\xc5G\xa5F\xea\x1du^\xb0,\x0b\xbd\xb8\x98\xa6\
\xa8\x8a\xfe,W\x90\xc2\xa3|\xa9iJ\x1d\x92X5\x08-\x99\xabp\xf2\xf4\xc0\x9c\
\xad\xf1\x16\n\x14E\xcd\xfeH\xb7\x84 \x88\xf0\xba\xddhp7\x00\x90\x1a\xae\xe8\
\xa1\x1aV[z\x192\x04\x89TJw\xb2\xd5Z64\xd5\xfb\x8a\xce\xe8\xa1)\n\x82\xc0\
\xa3\xb5\xa11\xe7^C\xb5\xb84*aD\xeaU\x84b5\xf5\x89\x84\x94\xc1\xb0\xfa\xf2v\
\x98X\x16\xd1h\x146\xab\x15\xbc V\xa4\xe3Q.\xc8m\xcdd\xe2X<\xb2\'\xcd\x110K\
\x04\xa2(\x16\xe5\xd0G<mH\xc6J\x9a\xa6\xc1$S\x80C"\x10\x8f\xcb\x99\x95\xdd\
\xa3$\x90\xf3\x83\x1c\x9c\xb3\xbd\x8a\x9b\xeb}\x98\xf0\xfbUM\x1c\xaa\x03\x12\
Y}\xe0VI\x96\x88\'\x93Y-\x14\x17*\xa5\xb1P\xe8J1\xb3\xe7T\x19\xa9\x87#\x11\
\xb46\xaeB8\x1a\x85\xcb\xe1\xc0\x85\xf04:\xea\xbc\xf8\xc3\x1b\x7f\x1f?\xda\
\xb9\xb3(\xff\x17\xf2\x7f\xaen\xcf\xbf\x89\xa8ld\xce\xa5\xd3\xe0x\x1e\x82("\
\xad\x08\x08*\xbdY\xce#s\xcd\x96{\xa4\xbe\xa4H\xbd\x98H\xdd\xc2\x9a\x11\x88L\
\xa1\xaf\xaf\x0f\xdb{z\xf1\xc0\xbd\xf7\xe2\xa7\xbf\xfc\x85\xbca\xd4\xda\xb8J\
\x95\xdaU\t\x90\x1e\xa8\xc3\xe3\xe7\x10\x08\x860\x19\x08 =;\xb0L\x0b\xd4\xb0\
C\x10\x04\xa4\xd2\x9cj\x12#\xff\xb7(\x8ap\xd8\xedY\xe9o\xc5B\x99]\x91\xcfb\
\x17\x90\x0c\xbc\x00i\xa3\xf4\xab\x7f\xfd\xe78x\xf0\x1d\xfch\xe7N\x04\x82\
\xc1\x05\xcd\x82\x11\x04Aw\x82\x15D\x11<\xc7\xe1\xca+.G\x83\xdb;\xaf\xffc\
\xbe\xbe\xe5\xa5@@\x86\xd89\x9e\x87U\xe1$\x19\x8b\xc7\xd1\xe8\xf3\xa96K\x01\
\xc8MJ\x80\xd2\xc8u:\x90\xfbo.\x87\x03^Of?\x82L\xf8\x84\xe8\x17\x126\x8b\x05\
\xdeF\x87\x11\xa9W\x03\xc8\xd2\xdd\xe1\xb0\x83\x9b(\xce\xc2\xf6\x85\x81\x17\
\xd0\xdc\xde\x82\x07w\xec\xc0\x83;vT\xea\x10\xe7\xc4d\xd0\x8f#\xa7\x8f\xe2\
\xe0\xc1w\xf0\xea\xe1Cx\xf3\xf8\t\x84\xc2a\xd8\xacV\xa9\x8fd\x19\t\x80\xdc\
\xd4\xd1X\x0c,\xcb\xc2\xbbb\x05\x9a\xeb}\xd8p\xf1:\xb477\xa3\xbdE\xda\xd8\
\x02 w|\x072\xd5\x86\xf3}\xd4~V>l\xef\xe9\xc5\x8d[\xb6\xe0#\xf7\xdf/\x9bzU\
\x1a\xa2(\xe2\xd2\xf6\x8b04:\x86D:-\xcbd\xa2("\x95J\xe3\xeaMW\xe0\xf2k%B/\
\xc5\'\x87\xa6(\xa49\x0e\xb1\x99\xc5/\x997\'\x92\xa8\xb1Z\x10\x8d1p\xd8\xed\
\x18\xf7\xfb3\x1e\xf7\x8a\x15\xd4\xe0\xe8(\xce_\xb8PRZ#IDP:4\x06\xa6\xa7\xb0\
\xbe\xad\x03\xff|\xff\xe7\xe7\xf9\r\xca\x8bR\xa3t#O\xbd\x8c\xe08N\x1e4\xc5f \
XX3\x06&\x07\xf0\xaf/~\x1d\x9bV\xf7\xc0c\xabS\x95\xe5\x07\xe3SE\xb7\xc8+\x06\
\xe4x/\xb6\xaf\x85\xb5\xae\x06\x1b\xd7va{O/\x1e\x04\xb0\xeb\xd0\x1e<\xbd\xf3\
\xd7x\xf6\xa5\x97\xe4\xc6\x10\xe5\x00\xe9\xd1\t\x00\xd7^u%~oS\x0fn\xdc\xb2\
\x05\xcd\xed-\xaa\x01M\xc8W\xb9\xb95:8\x02k]M\xc9\x8f\xaa>\x95\xb3\xbf+\x9f\
\xd3\xd3]\xeb=>4\xb7\xb7\xc0\xebqcht\x145VKEujQ\x14\x91L\xa5\xb1\xe1\xe2uhm\
\\\x85\x17_\xfd\x1f\xd4X-Hs\x1c\xd2\x1c\x8f\xaeK.\x96\t]\tm\x1b\xc0|Hs\x1cZW\
5b\xfb\xd5W\x97\xf3\xd0K\x86\xb6\x92Wi\xa6\x06\x00\x976\xb5\xe0\xbb?\xfb\x19\
\xd2\x1c_\x14\xa9\xd3\x14\x05\x9afd\xdd\\k\xbd\x9b+"\xce\xd7\xa8\xba\xd2\x08\
LO!15\x83X2V\x94\x1d\xb6\x91\xa7^f\x0cO\x8cc2\xe8\xcf2"*\x04v\x8b\x1d\x81\
\xc8\x14^|\xfb\xbf\xc12\xa6Ek+g\xb7\xd8\xe1\xb49\xb1\xd6{1z|\x9b\xb0\xbd\xa7\
\x17\xdb{zq\xd7\xed\x1f\xc4\xdf\xff\xcb\xff\xc1\xe1c\xc7\xe1p8\xe6\xbd\xb9\
\x1a\x9d\x99\xc1\xc5m\xab\xf1w\x9f\xba\x17\xbd[\xaf\x92\x89\xbc\xaf\xaf\x0f{\
c{1:9&\xef5\x90\x8c\x0e\xe2\x12I\\\x1c\xf3A\xefFP\xae\x9c\x9c6\xa7\xfc}\x01\
\xc8\xc6RZ3)/\xedQM\x04\xe5\x9a\xd4\xe6\x025\xbb\xb9\x17\x8eF\xf1\xa1\x1b7\
\xe0\xcd\x93\'1:1\x01\xb7\xd3\x89\xf7o\xbc\x14W\xdf\xb0\x1a\x80d\x1d@\xa2\
\xf4|\x8d\xa8\xb5\xa0)\n\xe1\x99\x19t\xb4\xaf\xc1\xb7\x1e\xf8\xdb\x8a|\x87\
\x8a\xe0g?C*\x95,jR%\xaf\x0bE#Y\x04=z~\x0c\xc7\x86\x8f\x82\x0fI\xb2^\xc44\tz\
\x84B\xd8\x13E\xdco\x01o\xce\xde\x1f\x0b\t\x99M\xd54\x13\x81\x89w"\xcdd"\xe4\
b\xaeC!X\x8e^\xea\xc0\x12 u\xb3\xd9\x82\x93\xa7\x07\x10\x98\x9e\xc2\xf6\x9e^\
\xbc\xf0\xf6\xcf\x91\xe4\xe2`\x8a\xc8\x9a\x90:\xc6\xcf\x96T\xeb\xbc\xaf\x98\
\xcf*\x05\xc4^7\x10\x99\xc2Dh\x02\x07N\xef\xc7\x9a\x815\xb8y\xcd\xcd\x92\x01\
\xd3\x0f\xba\xf07_\xff\x16\x9e\xd8\xb9\x13\xf6\x9a\x1a\x98X\xb6\xe8hU\x10ED\
\xa3Q\xdc~\xddux\xec\xa1\x07Q\xef\x91Z\xc4=\xf7\xc6s86v\x1c\xd3\xf1LA\x88\
\x96\x98Y\x9a\x01\'\xf0`iF\xf7\xfc\xe4\x82\xf2\xbc)\x9b5\x13(\xf7@B\xb1P\xd6\
J\x8b4j\xf0\xd6\xd6\xa1k\xdd:\xbc\xf2\xda\xeb\xe0g\xb5\xeeJ#\x14\x8d\x80\xf6\
Q\xf8\x83{.\xc7\x85P\x026\x1b\xa5\xea\x82\xa4\x94]\xe6\xd3y\xfe\xc4P?\xf6\
\xf7\xef+\xcb1\x17\x03\xb7\xdd\xad{\xce\x01\xb5Kc\xf3\xca&\xaco\xeb\xc0\xf0\
\xc48\xcc\xe6\xe2WI\x0cMey\xb1kM\xea\x94\x84\x0e \x8b\xd0\x95dN\x10\x8f\x8b\
\x88#,\xff[`b\xf28\x9d/X\x9a\xa9\xf8=\xbf\x98\xa8zR\xb7\x98M\x98\xf0\xfb\xf1\
\x9b\xdd\xfb\xb1\xfe\xde\x0et6m\xc0\x81\xd3\xfb\x8b\xb6\xce\\\xcc\x8bH\xfeo\
\x86f\xe4\xe8``r\x00\xdf\x9a\xfc\x16\xae\xf6o\xc5m[n\xc3\x7f|\xedkhon\xc6\
\x97\xbe\xfdm\xd8\xac\xd6\xa26QE\x1dB\xff\xde\xaf\xbe\x8f\xc3g\x0f!\x91N\xc0\
j\xb2\xc2j\xb2\xe6=\x07\xa5\x9e\x1f%\x99k\xfb|\x12\xf7C@_:S\x9aM]\xdf\xbb\
\x19?\xf9\xf9\x0b\x08\xc7f\x16DW\x07$\x8f\xf1\x06\xeb*\xd8\xeb%\x92\xd1#\xf4\
\xf9F\x87\xc7\x86\x8f\xe2\xc0\xe9\xfd\x00*\xd8\xfd*\x0f\xc8x#\r\xb6\xb5+\xa8\
\xe6\x95M\x98\x0c\xfa18<R\xb2\xfd1\xd9\xf4$\x86^\xa4\xf94l\x00l\x00\x13O\x82\
o\xb0@0\x89\xa0G(`\xd6r=\x1aJ\x00\x00\xdc\xb4#\x8b\xd8m6J\x15\xa9s\x82\xf4=\
\x963\x19\x97\x0bU\x9f\xa7\xce\xd04X\x96\xc5\x0fv\xef\xc2d\xd0\x8f\xdb\xb6\
\xdc\x06\xbb\xc5\x9e3ox\xa9\xc0n\xb1\xc3j\xb2\xe2\xc0\xe9\xfdx\xec\xe5G1\x19\
\xf4\xe3\xc1\x1d;\xf0\xb9{\xfe?\xc4\x13\x89\xa2\xd2\x0c\xe3\x89\x046un\xc0c\
\x0f=\x08\x00\xf8\xc6\xb3\xff&\x13\x89\xddb\x07S\xc1\xc8\xa4P\xd2S6h\x00\xd4\
\x1dr\x02\xd3S\xd8\xb8\xb6\x0b7]s\r\x04a\xfe\xdd\xee\x0b\xc5x\xe4\x9c\x9c&[L\
\xd3\x04=C\xb6\\ Q\xb1\xd5d\x85\x855/\xc8\x8f\xdd\xec\x90\x7f\x9c6\'\x9c6\
\xa7L\xe8N\xaa6\xcbk\xfd\xc8\xe9\xa3\xb8p\xa1\xb4\xec#\x86a\x90H\xa5T\xd6\
\xd2\xd6\xba\x1a\xd5\xf5\xf5\xd8\xea\xc0\xb8\x93p\xa6\xebao\xf0\xc1\xe1\xb0\
\xc3\x15t\xc0\xe1\xb6\xc2\xe1\xb6\x82I\xd5\xc2M;\xe4\x1f\x000\xf1\x199.\x1e\
\x17uW\x82\x06\xf4Q\xf5\xa4.\x88"jl6\x1c\xe9?\x85\xc7\xff\xdf\xb3\xa8\xf7\
\xf8p\xfb\xe5w\x80\xe3\xd3K\x9e\xd8\x19\x9a\x81\xddb\x977s\'\x83~|\xeb\x81\
\xbf\xc5\xb5W]\x89h\xac0\x92\x11E\x11&\x96\xc5W\xff\xfa\xcfQ\xef\xf1\xe1\xb9\
7\x9e\xc3\x91\x897e2\xaf$\xc8\x8dF\x88\xbd\xd8L\x11m?\xcb\xbbn\xff \xdcNg\
\xd1\x9d\xedKA8\x12\x91W\x11\xb9\x08\x9d\x13R\x99\xef\xa8\xd8k\xd0\xb3\x16\
\x9e\x0b\x0b\x19a\xeaM\xb4$B\xd7\xab\xf58\xfb\xd6 \x12\x1cW\x9a\xecEQ\x98\
\x89f\x9f?e\x07$2\x913\xee\xcc\xf8\x10ZD\x99\xdcm\xbe\xa4L\xf0\x00T\x04\xbfR\
l\x84\xcb\xec\x82\x89w\xc2&\xd6\x81\xa5\xcd\x06\xc1\xcf\x81\xaa\'u\x02\x13\
\xcb\xe2\xdbO>)\xe7\x9d\xdf\xf4\xbe\x0f/\x0bb\x07\xa4(n"4\x81\'\xf7\xfc\x04\
\x00\xf0\xf5\xbf\xf8\x0c\xbc\x1e\x8f\xec\x0e\x98\x0f\xf1D\x02W^q9\xb6\xf7\
\xf4\xa2\xaf\xaf\x0fo\x9cyc\xc1\x96\xf9\xf9\xa2t%QFunz\x02%\xb17\xafl\xaaX3g\
%H\x15\xab\x96\xe0\xe2\xc9d\xd6\xe6(y\\\x0c\xe9\xa4\x9cP^\x0f\x12\xa5\xd3\
\xbe\xd9>\xba\xf3hXA\x01Hp\x1c\x02\xe3\x19\xf9D;Y\x93\xd5\n\xd94%P\xea\xec\
\x00\x10\xf7[\xc0\xa4\xb2kQH\xf4\x0eH\x11\xbc\x89wJr\x92A\xf2\xbaX:\xa4n2!\
\x14\x89\xe0\xee/=\x88\x13C\xfd\xb8k\xdb\x9d\xb8{\xcb=\x00\x96~\xbfA\x86f`5Y\
qd\xe2M\xec:\xb4\x07\xdd\xdd\xdd\xf8\xf8-7#63\x937\x1b\x86ts\xff\xe3\xdbn\
\x05\x00\xec\x1d\xfc\x1fp|qy\xfc\xe5\x80\xdeMU\xe8\x9e\x07\xd1\xd5I\x9a\x9b\
\xd7\xe3\xaex\xa4\xae\xf4o\xd7\x1b;\xca\x08]\x0f\xc5\xc8/\x04\x0b\xd5\xf4;\
\x17\x94Z:\x99d]1\x89@_=|h^\x15\xd6\x82\xc0cpdL\xf5\x9cR~Q\xf6C\x8d\x98&\x01\
H\x84N,#\\A\x07\xe2~\x0bl\xbe\xe4\x9cY1\x04Do\x8f\xc7\xa5\xcfH\'M\x15%\xf7\
\xa5\x94\xa7\xbedH\x1d\x90\xdc\xf4\xfaO\x0f\xe0\x8e\x1d_\x90#\xf6\xbf\xba\
\xf1~4\xb8\x1b\x10K\xc6\x16\xfd\xc6\x99\x0f\xc8\xf2\xfc\xe5S/a2\xe8\xc7\x9f\
\xfe\xe1mh\xf0\xf9\xe4\nT=$S)4\xf8|\xd8\xd8u\t&\x83~\x9c\x99>\xb3(\x11%\'\
\xa4\xb2$\x18B\x96\xcahX[\x13\xa0\xd7y\xbe\xb5q\x95lEPI\xc4\xe2q\x15\xa1k\
\xa5\xa3|\xab\x90R\xe4\x97\x85\x84\x1e\xb9\xe9E\xea\x80\xb4\x91;\xee\xf7\x97\
\xec\xc1C\xcd\x06\x16J2\xb6\xd6\xd5\xa8\xe4\x17\x8f\xad\x0e|\xc8"\xeb\xea\
\x80$\xbf\xd0#\xd2\xe4\x1a\xf6Da\xf3%\x11\xf7gW5\x87\x84\xa8*R\' )\x8f\x046\
\x1bU\xf6\x94G%\x96R\x9e\xfa\x92"u@\xcag\xee?=\x80\x8f\xdc\x7f?\x9ez\xe1y\
\xaco\xeb\xc0_\xddt?nz\xdf\x87\x01`I\x93\xbb\xddb\xc7Dh\x02GN\x1f\xc5\xfa\
\xb6\x0e\\\xb5qc\xceh\x9d\x9e\xed\ry\xd9\xda5X\xdf\xd6\x81\xd1\xc1\x11L\xc7\
\x83\x0b\x16\xa5\xe7;\xc7\xf1d\x12\xdcL\xee\xe3 \x91\x9b\x97\xf6d-\xd5[W5.\
\xa8/\x0fP\xd8^\x00\xc7\xa7\xb3\x8e\xb5\x18T\x93\xa6N"u\x8f\xad\x0eo\xf4\xbf\
\x8d\xd1\x89I\x98M%\xfa\xa9\x8b"X\x96UY\x05h\xcfS0>\x05\xc6\x9d\x94\xe5\x17%\
\x99\xbb\x82\x12a\x93H]\x0b\xbd\xcc\x18@\x8a\xd4\xc3\xa90l\xb6YO\xf99VW\xbfK\
\xa8\xfa\x94F=\xb8\x9cN\x8cNL\xe0\xcf\x1e\xfc2\x0e\x9f8\x89\xbf\xf9\xf4\x9f\
\xe2\xaemw\xa2\xb3\xb5\x0b\xfb\xfb\xf7\xcd\x99\x97]n(s\xbb\xcbq\xf3\x1e\x1b:\
*\x15\'uvb\xe7\xee\xddys\xb7[\x1b$\xd3\xa9>d\xf7\xa7,\x04\xbc\xc0#\x91N\xe4\
\xfc{\xbe\x82-\xe5yei\x06\xbc \xd5\x0f\xb0\xb4\x19lM\n\xd3A\xe9\xa6\x8c\xd4N\
\x03Q)B$\x11\x1b E\xea\x84\xd8\x89\x0c\xa3\xd7\xc7\xb4\xdc\xa0iZ\xd7{$_\xa4\
\xc72\xa6\xac~\x9f\x85\x80L`\x0b\xb5\xf7#\xd5d\xe4&7\x92\xf9B\xfb(\x04cS\x18\
9\x1eA$\x1a\x85s\x1e\x16\xb9V\x8bEu\xdd\xacu5r6\x0c\xf9\xfe|\xc8"K/QO\x0c\
\x88JD\x0e_TJm4\'\x10\rI>2\xb5^\xb5\xe4\x12N\x85\xe12\xbb\x10N\x85\xa1\x05\
\x91_R\x88\x01X\xda2l\xb9\xb0$I\x1d\x90\xa4\x18\x9e\xe7\xf1\xc8\x13\xff\x17\
\xbb\x0e\x1c\x90+(?}\xc3\xa7d\x9f\x953\x81\x01D\xa31L$\xce\x95\xe4\xe1Q\x088\
!\x05^\xe0\xe5\xa2\x08B\x90,c*)j\xb6\x9a\xac83}\x06\x00\xd0\xdd\xdd\r\xaf\
\xc7\xa3\x9b\xbb\xcd\xcf\xea\xce\xc4\xa7<<X\x9c\xc5)!s\xab\xc9\x8a5\xf5k\xe0\
\xa4j\xd1\\/\x99m\x95R\xb9K@\nOH\xc5h\xce\xd7\xe5\xb0\x0choi\xaa\xb8\x1d/\
\xd1\xec\xe3\xc9\xa4*\xb7\x9e\xa5\xcdr\xc4\x97w\x13\xb8\x84\x94\xc6\xb9\xc8\
\xb6\x9c($j\x15\xfc"`\x07\xee\xb8\xe3j\x0c\x8f\x9f\xc3\x89\xf7N\x97l0\'\x8a\
\xa2l\xd4\x06d\xf2\xd4\xadu5hF\x93\x14\xb9\xdb\x01\xa0E\x92\xdc\x88\x0bC[\
\xe63\x02\xe3Qx\x1b\x1d\x08\xc6\xa7\xe4\x89_\xfb\x08dKx\x95D4\x1a\xc3\xc5\
\xf6\xb5\xaa\xe7\x96BO\x86%K\xea\x80\x94#\xebv\xb9\xf0\xde\xd0Y\xdc\xf3\xc0\
\xdfac\xc7\xa5\xb8\xf9\x9akq\xfb\xef_\x8b\xed=\xbd\x00z\x01\xa8}N\x88\xe7D\
\xb9\x1e\x95HL\xcd  \x04ql\xe8(\xceL\x9f\xc1t<XR\x91T,\x15\xc5\x89\xa1~4\xb7\
\xb7`e\xdd\n\x84"\xd9\x9b4\x82 \xc0f\xb5\xca7SD\x9c.xEB&\xa1\xab\xd7n\xc5\
\xd6\x8em\xf0\xd6\xd6U\xc4\x8eTk\xf6U\x08\xbc\x8d\x0e\xd4X-\xe0x\xbeb\xae\
\x8dz\x9f\xab$\xf1\xb9\xb4\xd9b4\xf5\x8dk\xbb\xd0\xbc\xf2\xef\xca>\xeer=\x1e\
\x1b>\x8a\x97\x8e\xbf\x04\xd6l\xce*\x06S\x9d\x03\x1f\x05\xc4\x80\xce\xd6.|\
\xef\x81\xb5\xb8~\xc7\x0e$R\xa9\xa2\xcf\xb9\x08\x80\xa2iU\xba"\x00\xb5\xd7P[\
Q\x1fY\xd5\xa8vB\x07\x968\xa9\x03\x99<vA\x10p\xa4\xff\x14\x8e\xf4\x9f\xc2cO?\
\x8d\xcb\xd6\xaeA\xd7\xbau\xe8\xa8\xf3b\xf5\xe5\xedY^#\xe5z$\xf0\xd6\xd6\xa1\
\xbe\xad\x03\x80\xe4<8\x19\xf4\xe3\xb97\x9e\x93R\x0c\x8b,\xfe\xe1\xf84F\xcf\
\x8f\xc1[[\x87F\x9f\x0f\xfd\xa7\x07r\xbe\xd6\xdb(-\x9b\x03\xe1\x0b\x05\x97\
\xf8s\x02\x8f\xeb7\\\x8f\xbb\xb6\xdd\t@2\x17;x\xf0\x1d\x0c\x8e\x8e"\x1c\x8d"\
\x14\x8d \x1c\x89\xa8"R\xbb\xcd\x86X<\xae\xfb\xa8\x07\xe2\xe5\xa2\xb4\xe1\
\x05\xa4.Td\xa9N\x8c\xa5\xbc\x8d\x8e\xd9IX\x8a\xf4\xdd.\x17&\x03\x81\x8a\x91\
\xba^vM\xbe\xe8\x9c/\xc0\x13G\xfe\xecY\x8d\x19\x90\xfcv\x94\xd9=\x95|\x04 \
\xed\xad(\x8a\x80\xb4+\x11\xd5q\xceF\xea\x80D\xc0\x0e\xbb\xbd\xa4\xd5\xac(\
\x08p:\x1c\xb8\xd8\xbe6sLB\x10\xcd\x90\xdc?\x1f~\xf4Q\xd9e\x15X\xdc\xd6\x92\
\xa5"\x1c\x8d\xe2\xcd\x93\'aS\xd8\x18W3\x96<\xa9\x13\xd04-\x93\xfb\x85\xd04^\
y\xedu\xec;x\x084\xcd\x80\xa1)X\xccf\xb99/k2\xc9}\x1c\xe7\xfbH`5\x9b\xe1\xf5\
\xb8\xd1\xda\xb8\n\xdb;;q\xcb\x1d\xb7\xe2\xd37|\n\xee}n\xbc\xf8\xf6\x7f\xcfY\
\xa6\xafE0>\x85z\x8fO\xd6\xcc\xb5\x10\x04\x01&\xc6\xac\xca2(\x04I.\x85\r+;q\
\xd7\xb6;qb\xa8\x1f\xf7|\xf1\xefq\xf4\x9d\xf7 \x08<8\x9d~\xa1D\n)d\xf3Rn\x06\
B\xd3\xb0\x9aL`M&\xd9\xab\xddn\xb3\xc1\xe5tJ\x93F8"\xf9\xac\xbbj\x81\x911\
\x00Mr4o\xad\xab\x81\xd7\xe3\xc69\xffyTj\'\x84aY\xa9a\x83\x90\x02`\x99S\xae(\
v\x9f\xa4\xc6f\xc3+o\xbc\x81}\x87\x0e\xc9c\xa4\\\xe3M\xef1\x95L\xa1\xf7\xea\
\x0f\xe0\xbf\xbe\xf3\x1d\xd5q\x10B\xd7Z\x03\x00\xc5;\x9e\xe6\x82 \x08\xf0\
\xb8\x9c*\xa9\x8d\x8c\xc9\xc9\xa0\x1f\xaf\x1e>\x84\xa3\xfd\xa7\x00HM2DQD\x9a\
\xe3\xe5\xf1\xb6\x14\xc0\xb2,\xac\x16K\x955r\xc9\x8deC\xea\x044M\xc3j1\xcb\
\x1a\xb4 \x8a\xa0\x00p\x82\x00n6B\x13\x93IP\x14U\x96G\x82iA\xc0d \x80#\xfd\
\xa7\xb0s\xf7n<\xf2\xf3\xe7\xf1\xec\xa3\xdf\xc4]\xdb\xeeD\xff\xc4I\x9c\r\x0c\
\x17E\x0eD;\xcc\xd5\xc4\x83\x17D\xd4\xba\xa4\xc8a2\xe8/*\x9d\xeb\x86\x9e\x1b\
\x00\x00\x9f\xfd\xca\xbf\xe0\xf0\xb1\xe3\xb0\xd7\xd4\x80\xa1,\x80\xad\xb4TB\
\x92\x9d\xa3\x9c4I\xc3c%\xa1\xeb\xa5\x85\xd5\x9bL\xf06:d\x99\xc6[[\x87\xd6\
\xc6U8\xd2\x7fJj\x97V\t\xcb\x001\x93\xdb\x8c\x02\x95\x14\xa5\xb4U\x88\xa6.\
\x88"\x12\xa9\x140Kd\xe5\x1aoY\x8f4\x8d\xe8L\xac\xe0<\xeah4\x06W\xbbC\xdeS\
\xf4\xd6\xd6a\xcf\xfe\xd7JnRBz\x94*\xe5He\xa4\xeev8\xe5\x822\x87\xdd.\x9d\
\x13 \xd3\x01\x89\x07 \x16\x90\xedD\xcd\xde;\xf4\xe2\xb7\x0f\xacv,\xb9\x94\
\xc6bA\xcfv\xb7Q\xf6\re\x18\x064M\x97\xe5\x91\xfc\x98L&\x98L&\xd4\xcc\x12X\
\xff\xe9\x01|\xe3\xfb?\x06\x00t4\\V\xd41g\xb9(\xb2lN?\x94b22\x92\\\n^g\x1d\
\xbc\xb5u\xe8\xeb\xeb\xc3\xe1#Ga6[$\x0f\xed\x05\xb8Y\xb4\xbd1\tH5"\xd1`[W5\
\x82\xe3\xb8\xca\xf9\xaaS\x94\xaa\xb7\xea\\\x1b\xa3Z\x14\xaa\xa9\xd34]\xb6q\
\x96\xeb\x91\x9d%\xe2B\xf3\xa8\x1d\x0e\xbb$\xbd\xcc"0=\x85=\xaf\xff\x16\x89\
\xd9\x89\xa2\x18\x90\x1e\xa5]\xeb\xd6\xc9\xcf\xc9f^:\xd0\x12\xba\xf4!"\xc0\
\xd0s\xff\xd0\xa2A\xe8\x05b\xd9\x93\xfa\xa2@\xa0\xc0\xb2,^=x\x10\x93A?:[\xbb\
fS\xfe\n\xcf\xbf\x1e\x8fH\x9e\xe7+\\\xb5\xba\xcb\xd4Rr\xb99>\r\xbb\xc5\x8ez\
\x8f\x0f\xa7\xc6F\x10\x9e\x89U\xcc\x11\x91\xdc\xc0Zh\x1b\x11+K\xd4\xc9\x86\
\xf6B\xa45\x02\x92\x9dk\xa1\x98o\x9ez\xa5\xa1\x8c\xd4\xe7\xda[!\xf6\x00\x1e[\
\x1dF\xcf\x8f\xe1\xd5\x83\x07ab\x8b_\xb4\x0b\xa2\x08\x9af\xb2\xd2\x19\x95EeK\
\xa9\x12s\xb9\xc0 \xf5J\x80\x96L\xb6\xa2\xb1\x18F\x07G\xe0\xad\xad\x83\x85-\
\xae\n\xb1\x98~\xac\xa5|\xae\xb6\xac{\xa1\xa0\x8d\xd4\xeb\x15:%\x89\xd4\xdb[\
\x9a`\xb3Z+g\x17 \x8aH%\x0b\x8f\xccy\x81/9O}\xa1\xa0\x8c\xd49\x81\xcf\xab\
\xa7\x13{\x00\x00xi\xcfA\x8cNL\x94\xd4\xc6N\x10\x04X-fl\xde|\x89,\xbdh\'>\
\xb7\xc3\xa9\x9a\xe0\xb9y\xf8\xcc\x18(\x0c\x06\xa9W\x10\xb1x\x1c\xa7\xc6FP\
\xef\xf1\xc1f\xb1\x14e\xf0\xaf5\x9b*\x97\x1d-\xb9\xb1IF\xc2|;-)\xc1\xe51 \
\x0b\xcf\xa6e\x16\x12\xa9\xc7&\xfc\x92=B\x05\xd2\xc7DQ\x84(\x8a\xd8\xb4\xb1\
\x0b^g]A\x19\x1f\xda\xbd\x90R\xbc_\x16\x12\x85dA\x91\xfc\xf9\xa3\xef\xbe\x0b\
\xa0\xb4\x86\xd3\x89d\x12\xeb\xdaV\xa3yeS\xce\xd7\x18\x91\xfa\xc2\xc3 \xf5\n\
\x81\xa6i\x95\x87I\xb1\xf9\xea\xcb\x016k&\x9d.W\xbb:\xbdH\xfd\xf53R\xf1\x15[\
\x81\x94FQ\x14\xc1P,:\xb7\xac\xca\xba&\x85\x16\x07U\x9b\xf7\x8b6cI\x0b\xe5\
\xaa\x8fH/\x00p&0\x80\xa3\xfd\xa7`1\x97&\xc1q\x1c\x87\xab\xbb\xbbu\x0b\xc9\
\xb4PE\xeb\xb3\x93\x7f%{\xd1\xfe.\xc3 \xf5\nB\x10x\xc4&\xa4\xe8\xb3RrJ\xa9X\
\x88|ae)~8\x12\xd1\xdd\xcc#\x91\xba\xb6Iq\xa5\xd2\xddh\x9aF\x9aOa\xe4\xb8\
\xfa\xfb\x97+O}1\xa0=Wde\xa1\xe7\xa1\xee\x8a\xd5\xcaQ\xfa;G\xa6\x10\x8aDJ\
\x92^x\x9e\x87\xd9l\xc1\xa6\xf5\xea$\x00=\x93\xb6\\(\xe7*\xd1@\x06K\x86\xd4i\
M\x06K\xa1?\x8b\x05\x92I\xa0\x94\x17\xaa\x99\x18\xca\r\xab&\xfas9\x9d\xbaKq\
\x12\xa9++N{\xaf|?\x1cv{^9g>Hs\x1cB\xd1H\xc1\x96\xcd\xd5\xdcB\x8d-\x80\x90\
\x95~/@\xc6\x8f\xe5@_i~A\x80\xe4\x10\xba\xca\xb7\x12\x976\xb5\xc8\xcf\xe5\
\xca|\xc9\xa5\xa3\x1b\x91ze\xb0$\xf2\xd4y\x9eGb\xb6`\xa1\x18\x90b\x98R"\x91r\
\xa3\x982\xfeJBYt2\xd7\xb2\xbdX(\t&\x91Je\x11\xbb\x1e&\xd3i\xb4\x93\xdf\x15\
\xd1z%=6L,;\xab\xf1{a\xb3X$W\xc99R\x1a\x8b\xcdS_H\x14z\x1dI\x15\xa9\xc7V\x87\
3\x81\x01\xbcs\xe6\x8cJ"+\x06\x1c\xc7\xe1\xf76oFs{\x8b\xaa\xaa\x95D\xea\xc4\
\xba\xc0\xc0\xc2cI\x90\xba\xcdb\x81\xd3Q\x1a!r\xe94R\x8bX\xb9F"\xd1j\x91_\
\x94\x86H\x95\xac\xe8\xcbE\xe8se\xbfL\x06\xfd\xd8\xf3\xfao\x11\x9b\x99\x81\
\xdb\xe5\xaaX4\x17\x08*\xceC\x01&^JT\x8b\xa6\x9ek%\xaa\xdc\x1b\xc8UE\xfa\xdb\
}C\x88\'\x92\xa8)\xe1\xbb\xa4\xd3ix=\x1e\xdcu\xfb\x07\xe5\xe7d\xa7\xcd\xf3\
\x12\xa9+\t\x9d\xe3y\xb9\xfa\x95\xc0\x88\xd2+\x87\xaa\'\xf5t:\x8d/~\xf2\x93\
\xb8\xf7\x8f\xee\xc8\xf2[)\x04\xbf\xd9\xbd\x1f\x9f{\xf4Q\xb9`c\xa11\x9fVa\
\xcb\rn\x87d\x13\xa0W\x80\xa44\xfd\x1a\x9e\x18/j\x15!\xccZ\x13\x17\x1a\xd9\
\x93q\x10\x89G\xe0\xb49\x0b\xda \x95\xf3\xd4\x97H\xf4\xa9\xd4\xd3\x1d\xc8l\
\x08\x13=\xfd\xb7G\xdf.y\x834\xcdq\xd8\xd6\xd3\x83\x8dk\xbb\xe4{\xd2ZW\xa3Jg\
\xcc\x15\xa9WJR+\x14\xe9t\xba\xe8&,\x0cM-\x19\x8b\x00`)\x90:\xc7\xa1\xbd\xa5\
\xa9$\x17\xc1z\x8f\x0f\xa3\x97\x8f\x81\x17DT\x81\x02\xb3(\xad\xe6\xf2\xa1\
\xdc\xf2\x8b\x12\x89T\n\x9e\x1c\x16\x07J\xeb\x03"\xbf\x90\xeb\x1b\x98\x9e\
\xc2\xb8\xdf\x0f\x13\xcb\x16\x1c\xcd\xd14-\xa7*\x16B\xec4M!\x1a\x8b\xc96\x01\
sy\xbfT{\x9ez>\xabb\xb2B$\xae\x8c\x80\xe4\xd7?21\t\x9a.M\xde2\xb1,\xde<y\x12\
GN\x1f\x95\x89]\x9b\x9f\x9eKza\x19fQ\x89\xbd\xd6\xe5*\xe9}\x89D"o_\x83jB\xd5\
\x93\xba\x12\x8f\xbd\xfc(\xce\x06\x86\xe7$F^\xe0\xe1\xb6\xbb\xf1\x8d\xbb\xbf\
\xa1j\x88\xbb\x18 \xf2B5j\xea@\xe5\x96\xc1V\xb3\x19\xf1DR\xa5\xd9\x86\xa2\
\x11\xb464f\x0c\xbd\xa0\x96_\x00`\xf4\xfc\x18\xceO](h\x1fD\x10\x04X\xcdf|\
\xfc\x96\x9bq\xa0\xaf\x0fG\xfaO\x15$\'Hn@\xa4\xa2\xd4:\xa7\xf4\xc2\xd0\x0c\
\x12\xe9\x84\x1c\xa9W\x83\xa6\x9e/\t\x80\x14\x1e)%?e\xc1\xd1\xeb\xfb\xce \
\x95J\xc3l6\xa1\x14\x8a\xa2i\x1a\x81`P\xba\xb7f\xed\xc6\x95\x8d1\x00u\xa4\
\xae\xdc\n#\x84^1_\x9f<H$S\xf8\xe2\'?\x89\xdb\x7f\xff\xda\xa2\xdew\xe4\xe8;\
\xf8\xe2\xbf~\x13\xd3\xe1\xf0\x92\x88\xd8\x97\x14\xa9\xc7\x92\xb193H\xd8\xd9\
\x1b\x90\x80X\xd3.\x16\x88\xfcR\xad\x9a\xfa|o.-\xb9(\x9d+\xb5\x9bpD~i]\xa5\
\xef<\tH>0zMA\xf4\x90Js\xd8\xfc\xbe.|\xeb\x81\xbf\xc5\xc3\x8f>\x8aw\x87\xce\
\x82\xe7\xf99\'\x04\n\x12\xb9\xd0\xbc$K\x14\xaa\xa9\x13\xa3\xaaj\xd1\xd4\t\
\x18M\xc4\x1dO&e\xf9\x85\xe8\xe9a\xfb4V\x0b\xed\x08\xc6\xa7\xd0?(Y9\x97\x9a\
\x1d\x96\xe6x\xacim\xc6\xc6\xaeK\xe4\xe7H\xe6\x8bnJc!\x86]\x15\x06\xf1\xa9io\
i\xc2\xfa\xb6\x8e\xac\x14\xda\\P*\x04\xbc V\xcc9\xb4\x9c\xa8zRWn\xe6\xd9-\
\xf6\x82,l\x95\x11\xf1bF\xea\xcae\xb1\xb6Bt\xb9BkI\xac%@\xad\x9eN\xe4\x17\
\xa2\xa9\xc7&\xfc\x10\x04~\xce\xc9\x86\xa6(\xa4RI\xfc\xf1m\xb7\x02\x00n\xdc\
\xb2\x05\xaf\x1e>\x84\xd7\xdf|kNR\'\x9f\xaa\x8c\xd4\x0bE\xbd\xc7\x87\xd6\xc6\
U8|\xecx\xd5n\xf6\x91H]\xa9\xa7\xbbb\xb5\x80\r\x18\x9d\x1c\xc3\xd8\xa4\x1f&v\
~z\xa4\xd6\x99Q\xa9\xa9\x07\xe3S\xd8X\xdb%\xbfV,Q\xe6\xa9$\xe6Z\xf5\xf3\x02\
\x0f\x86f\xf0\xd0\x1d\x0f/\xf0\x91\xcd\x1fK&O\x1d\x98\x8d\xd4\x8bLk\\\xecH\
\x9d`\xbe\x91z%\xb4\xbcrj\xeaJ\xdb\xdd\xb9\x10\nGT\x8d2\x80LD4\x99N\x83\xa6\
\x999\t}&\x91\xc4\xa6\xce\r\xe8\xddz\x15&\x83\xfe\xa2\x8a^\xc8\xf1\x92H\xbdP\
\x9c\tH\x11n\xbe\x95F5A\xa5\xa7\xcf\xe2\xf5}g0\x13\x8f\xcf+i@\x10\xf8\xacB2\
\xd2\xf5\x0b\x906c\x95I\r\xe5\xb2\xb8(\x17&\x83~y\xd5\xcf\x0b\xbc\xee\x0f\'\
\xf0\x0b\xd6W\xb6\xdc\xa8zRW\x12O)\xa5\xf6\x81\xf1h\xd6\xf2t\xa1 \x08\xbcJ3.\
\xb5\xf8\xa8\x92\x1b\x9a\xe5\x8a6sm~\xe9\xe9\xcfn\x97S\xf6\x9e\xd1f\x07]\x08\
O\xcfY\x8f \x88"\x04\x81\xc7\x9f]\xb7\x1d\xf5\x1e\x1f\xea=>\x04\xc6\xa3\x18\
\xf7\x17\xb6\xa4\x86(\xaa&\x1fNH\x15\x94\xa7N\x9c37\xad\xbf\x0c,\xcb\x82_\
\xa4\r\xbfbe\x13b\xb5\x1b\x8cOax\\\xfa\x0e\xf3\r\x12\xf42\x98\x8am\xd8\xb2X\
\xa8\xf7\xf8d.af\xbb\x92i\x7fX\x9a\x91\xa3\xf8jv\xe7\xd4C\xd5\x93\xba\x12\
\xb1d\xac\xe0\x96m\x04\xdeF\x87d\x0e\xb5\xc0\xd0F\'\xa5n\x94\xb6\xb74I\xde\
\xe2er,Tn\x94\x12M\xbd\x1c\xc8U\xd9H\x1adh\xa1\x8d\xd4\t\x86\xcf\x8d\x03\xc8\
O\\3\xf18.n[\x8d\x0f\\\xb7U\xf5\xbc\xd2\x96 \x1f\xc8\xb51Y\xa4\t\x85\xc8/\
\xf9d\x18\x96f0\x11\x9a\xc0d\xd0\x8f\x8d]\x97\xa0\xb9\xa1\x01in\xf1\xb5b`n3.\
\xb7\xdd\r\x8f\xad\x0e\xa1X\x08C\xa3c%\xd9\xecf}\xa6&\xb3Ik\xb9\xab:>TA\xea\
\x99\x02\x85\xea\xe9\x04\xd5\x9a\xf5\x94\x0bUO\xeaZM\xbdX\xf9%0\x1e\xadxwz=\
\x08\x82\x00\xab\xd5\n{\x83$+\x14Z\x92\xae\x07\x96e+gC[\x01\x14RI\xaa\x85\
\xf6F\xcb\xb5\x82\x10E\x11\x1c\xc7\xe1\x0fo\xfc}\xac\x9f\xed\t\x0bH\xce\x8e\
\xd1X\xe1\xe7\xd8j6\xc3is\xaa\\\x1a\xe7\xca\x80\x89%c8r\xfa(\xd6\xb7u\xe0\
\xf76oF*U|O\xcf\x85\x82R\xee\x0b\xdb\xa5UQ4\x1a\x9bwCoQ\xc7C\x1d\xd0\xb7\x08\
\xa8\xf7\xf8$\x99\xa6J\x9a[p\x1c\'\xcb\xb1\xb1d\xac*\xb2\xd1*\x81\xaa\'\xf5\
\xf9\xc2\xdb\xe8X4\xf9\xc5QS\x83K\x9bZ0\x19\xf4#\x9eL\x16\xb5\xca\x88%cR{\
\xb7FGY"+\x02e\xf6\xcb|e\x9db\xa2|\xb7\xc3\xa9_t4+\xbf\x90j\xd2\xe1\xf1sy\'\
\xe1d*\x8d\xb6\xe6f\xdc\xb8eK\xd6\xdf\n\xcd\x7fNs<\xbc\x1ew\xd1r\x1e\xcb\x98\
\xf0\xf2\xa9\x97\x00\x00_\xfc\xd4\'\xd0\xe0\xf3I\xfa\xf4"\xe5.\xb3\x0c\x03\
\xd6d\xd2\x95R"\xe2\xb4\xae\x7fz\xa5\xa0\x8cf\x89\xb7L\xb5\x81e\xd9EOq^\x08T\
=\xa9+\x89\xa7\x94h70\x1e-\xba\x82\xac\x1cHs\x1c\x9a\xeb}\xe8\xee\xee\xc6\
\xe8\xe0\x08b\xa9h\xc1\xc6P,\xcd\xc8\x11\xa4\x97\xf6\x94\\\xf9\x97\x0fn\x97\
\xb3\xa26\x01\xdat\xc6P4\x92\xe5\xa5\x0ed\xcb/\x81`(\xef$,\x08<\xae\xb8\xec2\
4\xb7\xb7\xc8\xd1=y\xb4\x16\xd8\xed=\x95J\xa2\xb5qU\xd6\xe6\xf5\\Y0D\x82yz\
\xdf3X\xdf\xd6\x81\'\xfe\xed\xcb\xa8\xb1\xd4 \x14\x0e/\x9a\x81\x9c\x9eYV\xae\
\xc9*\x1aJ\xc8}z\xf5 \x8a\xe2\x9c\xfb\x04\xd4lj\xe0\xe0\xe8\xa8\xeay\xedF)\
\x81\xdeD\xbe\x18 ]\x9aJM\x9c\xb0\x9a\xcd%u\x1b[\x0cT=\xa9+Q\xcaF\xa9\xb7\
\xd1\xb1`\x17\x83T5&f\xbb\xea|\xee\x13w\x03\x00\x0e\xf9\x0f\x17\xbdI\x9a\xe4\
\xe2\x08LO\xa1\xb9\xbd\x05n\x97\xabl\x13S4*M\x8c\xe5l\x19\x97+\xf3E\x99\xceH\
"\xf5\\\x8d\xb4\x01\xe0\xe7\xcf>\x8f\xf3\x17.\x80\xc9\xb1\x82\x10\x04\x01&\
\x96\xc5\xf6\xceNU\xfep\xbd\xc7\'\xcb\\sI\x0b\x84x]\x0e\x07\x9a\xeb\x9bT\x92\
\xcb\\\x9b\xa5\x0c\xcd\xc0j\xb2b\xcf\xc9\x97\xd1\xd7\xd7\x87\xed=\xbd\xf8\
\xcf\xef\x7f\r\x9b:7 \x14\x0e#:3\x03\x9e\xe7!\x08\x82<\x16\xca\re\xaa\'\xf1T\
\xa1(*\x8b<\x9dT-\xa2\xd1\x98*\xf3\x85@/\xb2\xe7y\x1e\xf6\x9a\x1at\xaci\x87y\
\x8ej^\x9af0<!\xed}\x90\x02#k]\x8d,\xbf\x04\xe3\x99\n\xd3\xf6\xe6f\xd5{\xc9X\
Y\xe8tPA\x14Qc\xb5\xc8\r=\ni\x8e\xb2T\xb1\xa4\xf2\xd4KA`<\n\x8e\xe3\x10\xe5\
\xb8\x8af\x91(\xd1\xdc\xd0\x80\x07\xee\xbc\x13\x1f\xbb\xf9V\x9c\x18\xea\xc7\
\xe1\xb3\x87`5\x15\x16E\x12p\x02/W0\xea9\xe9\x11\x89\xa2\x18?\x12\x961a"!e?\
\xdc\xb8e\x0b\x1ez\xec1Dgf`\xb3ZU7\xfa\\\x11\'\xb9!\x05Q\x9c\xf3\xb5\xb9\x9a\
c\x00\xd9Q\xfa\xaec\xc7\x10\x9b\x99\xc9\xf9\x1eQ\x14Q\xebr\xa1\xbb\xbb[\xa5\
\xc1\x93\xdf=.\'\xa6\xc3\xe1\xbcy\xea\x1c\xcf\x83eY\xf4^\xf9~xl\x19",\xd4\
\xd0\x8b\xa1\x19$\xb9\x14\x1e\xef{\x1c\xb7\x0bw`{O/6\xfe\xa0\x0b{\xf6\xbf\
\x86\x1f=\xf7<N\x9e\x1e@$\x1aEb\x81H\x83\x13\x04D\xa3\xd1\xacUPD\x9cF\xa3s\
\x95\xec\xccH@*I\xb5Hs<\xacf3n\xbe\xe6Z\xfch\xe7N\xc4\x02\x01\xd09\xd2S\x19\
\x9a\xc2\xb8\xdf\xafJ[Tf\x88xlur\xd4~\xe3\x96-\xf8\xf6\x93O":3\x03\xab\xc9\
\xb4\xa0\x16\x01dR\x15\x04\x01\xb1\x99\x19l\xea\xdc\x80\xf5m\x1d81\xd4\x8fX*\
Zt\xd2\xc5RA\xd5\x93\xba\x12\xa5\xc8/\x976\xb5`S\xe7\x86\xbc\xe42\x1f\x90|]\
\x97\xc3\x81\xf6\xe6f\xb4\xb74\xa1w\xebU\xa8\xf7\xf8pb\xa8\x1f\xff\xb1\xff\
\xdf\x91H\'\xaa\xa2\xf3\x91\x855#\x10\x99\xc2\x89\xa1~tww\xe3\xe37\xdf\x8c\
\x9f\xbc\xf0\x02":\xb2H\xb1\xe9\x9d<w\x00\x00\x1a1IDAT`YV\xb6:\xe6,\x16$R)\
\xc4\x13I\xc4\xe2\xf1\xac\x02$\x12\xad\x13=}s\xa3\x03\'\x86\xfa\xd1?8\x90w\
\xe2\x15\x04\x01\xcd\xf5>4\xb7\xb7\xe8\xfe\xbd\xd1\xe7\xc3\xd0h\xfe\xde\xab\
\xa94\x07\xef\x8a\x15\xd8\xd8u\t\xbc\xb5u\xd8\xf9\xd6\xb3\x00\xe6\x8e\xd2\
\x95\xb0\xb0f$\xb9\x14~z\xe8)\x9c\t\x0c\xe0\xb6-\xb7\xe1c7\xdf*O\xe2\xa3\xe7\
\xc7p\xf0\xe0;\xb8\x10\x9e\x96\xb3y*\xd5\xd6\xcd\xed\x90|\xea7^z\xa9\xeay=\
\xcf\x17\x19\xa2\xa8\xdb*0\x1a\x8ba\xf3\xe6Kp\xe4\xd4ex\xf1\xd5\xff\xc9Y=\
\xa9\\5\x92\x02$\xad\xa1W0\x9e\x19g\x9f\xbd\xfbn<\xf6\xf4\xd3\xb8\x10\x9a^\
\x94\xcde\x96e\xd1\xe0\xf3\xc9+\xe7\xfd\xfd\xfb\x8a\xf6aJ\xa4R\x8b\x92pQ\n\
\xaa\x9e\xd4\xb5y\xea\x81Hq\x9b0\xdd\xdd\xdd8\xf4\xb3\xff*\xf7a\xe5\xc5\x89\
\xa1~\xec=\xb6\x17\xfb\xdf=\x80X*Z2\xa1\x17\x93J\xc5\xd2f\xf0Ba\x9e$\xffy\
\xf0i\xdcW\xbb\x03\xff\xf1\xb5\xaf\xe1\xae\xdb?\x88\x83\x07\xdf\x915\xd2p4Z\
\x10\x01\x91\xc9\x8c\xbcV[\x8cB\xe4\x00B\xe0\xca\x14F"\x95\x104\xaflBbj\x06\
\xc1p$\xef\x8d\x93\xe6\xb8\x9c\x93\xf3\xa5M-\xe8Z\xb7\x0e\xbf=\xf2v\xde\xe3f\
h\n\\Zr\\\xaco\xeb\x80\xd3\xe6D$\x1e)\xcaz\x17\x90\x88\x9d\x17x\x1c8\xbd\x1f\
\x87\xcf\x1e\xc2\xa6\xd5=\xb8\xc8\xbb\x06\x1b\xd7v\xc1[[\x87\xed=\xbd\x05\
\x7fV%\xa1\x8c\xd4C\x824y\xe7\xcbQ\xf7\xd2\x1e\xb4\xaej,Z\xb2$\x9a\xba\xd2*`\
\xf4\xfc\x18\xbc\xb5uxp\xc7\x0e\xdc\xb8e\x0bN\x8d\x8d\xe0\xf0\x89\x93\xd2\
\xb1,@\xe7-2\xf6:\xea\xbc\xf8\xc0u[\xe5(\xbd\xd0\x953\xd9cIL\xcd\x80K\xa7\
\x17-\xe1\xa2XT=\xa9+Qh\x9e:\xd9h|z\xdf3\x002\x1b7\xc1\xf8TE~\x072Y%\xe3\x91\
s\x98\x08M\xc8)S\xa5\xba2\x92\xef\x19\x98\x9eBP\xe7\x06`h\n\x89\x84\xe4qS\
\xef\xf1\x15LH\x16\xd6\x8c\x81\xc9\x01<\xf6\xf2\xa3\xf8\xe8\xe6\xbb\xb0\xbd\
\xa77\x8b\x80H\xc9~\xbeG\xf2\xff\x92\xd7\x93\x7fk_\xabE\xae\xe7\x9f:\xfa\xbc\
$\x9d\xe4\xb8q\xf4d\x9e\xc0\xf4\x94\\|T\xdf-}\xe6\x13;\x9f\xcb\x9b\xb6\xc7\
\xb2,B\x91\x08~\xf9\xc6\x1b\xe8\xee\xee\xc6\xa6\xd5=x\xe9\xf8K\x00[\xb8\x04C\
\xc0\xd0\x0c\xec\x16;\x92\\\n\x07N\xef\xc7\x81\xd3\xfb\xb1\xf3-;\x1a\xdc\r\
\xb2\x8f9\xa9\x0b\xf0\xd8\xea\xca6\xe6\xf2\x81\x8cG=\x0fu7M\xf6\x97\xb2cp-\
\x89\xe7\x9b\\\x19\x9a\xc2\xf9\xa9\x0b8r\xf4\x1d\xf4n\xbd\n\xc0\xac\xa6>\x05\
uU\xe9x\x14{\xe3{\xd1\xd9\xda\x85\xee\xeentww\xe3c7\xdf:\xe7w\xa8\x04&\x83~\
\xec:\xb4\x07\xcf\xf6=\rN\xe0\xe7\xbc/9\x81\x87\xdbbA\xbd\xc7\x87#\xc2Q\x84c\
3\x06\xa9\x97\x0b\xda<\xf5@dj\xce,\x12I\xf7\x8cK7+2\x95\x9c,c*\xfb\xefZ\x90\
\xdc\xd7\xf9\xc8-\x9c\xc0c\xb5\xb7\x15\xeb\xdb:\xf0\xd4\x0b\xcf#\x12\xcd\xae\
\x8a\xa5i\x1a3\x89\xa4|\x13\x15\x13\xa9\xdb-v\x9c\r\x0c\xe3[/}\x13n\xbb\x1b\
\r\xd6Uh\xae\xcft\x84W\x12P\xa1d\xa2\x04\xd90\x1b\xc5\x88\xfc\x1cYuxk\xebpb\
\xa8_\xfe\x9d`pd\x0c\xf1D\x02\xce<\xd9\x12\xda\xfd\x15om\x9dJ[onoA\xa3o\xa5,\
y\xe8\x81\xa2(\xd04\x83W\x0f\x1f\xc2\x83\x00:[\xbb\xb0\xf7\xd4+\xe0\x05\x1e@\
ie\xe1\x16\xd6,G\xeeI.\x85\x81\xc9\x01\xdd\xd7\x95:\xb6\xc8\x98R\xbe\x06\x90\
&~\xa9\xfa\xd1,\xfb\xbd\xd8-\xf6\xac\x1c\xf5\xd5\x82\xd4[j:\x909\x07\xba\xc7\
7\xab\xa1_\xdf\xbb\x19?\xf9\xf9\x0bH\xa6\xd3\xba\xaf5\x99L\x08\x04\x83\xd8\
\xf9\xf2\xafeR\xd7"\x18\x9f\x02\xe3\x06\xf8\x90\x05\xfbc\xfb\xb0\xbf\x7f\x1f\
\x9c\xe9z0\xee\xa4j<i\xc7Y9\xd3!\x95\x81V |\x01\xd3\xf1 \xac&kA\x81\x16\xc7\
\xa7\xd1`]\x05\x008\xfb\xd6 R\xa9$\x1cU\x92\xc93\x17\xaa\x9e\xd4K\x05)\xf7\
\x05\xa0\xba\x88\x95\xf8\xbd\xdc\xe0\xf84\xae\xbaH\xaa\x96$]\x80r\x91\x1d\
\xc9\xbb\xf5\xbaV\xe0l`\xb8\xe0\xb4Ir\xfc\x81\xc8\x14&B\x1382\xf1&\x80\x0c\
\xa9\x10\xe2\xa0y;\x04&\x96\xd3\'\xc5e\x96\xfc\xa9\xdd\xb4\xfa\xf8\x1cniyK\
\xa2U~\xcc\x02o\xa3CZ\x92\x13\xd2\'\xddr\x00Y\xfe)\xa6|]\xaf\x11C\xa3\xcf\
\x87\x81\xe1\xd1\xbc\x9b\xa55V\x0b\x8e\xf6\x9f\xc2S/<\x8f\x8f\xdd|+.o\xb9\
\x02\x07N\xefG\xad\xcdST\xa4\xae\x05\x19s\xf9\xc6\xc6|\xc6\x16y^\x99z\xa9$s=\
\xb8b\xb5\x08b\n\x17\xdb\xd7b\xdaq\xae\x80o\x01l\\\xdb\x85\xb6\xe6&\x1c}\xe7\
\xbd\xbcn\x99\xc3\xe3\xe7r6\xae\xd1\x124=Ba\xdc3\x08L\x02\xa7B\xdaIo\x00\xd3\
\x01@\\\xa1\x96\xce\xc2\xa9p\xd6\xe7J&l\xc5Yn\xb0\x8c\t\xec\xec\xaa\xaa\x18\
\x90@\xa7\x7fJ\x9a\rY\x9a\xaeZ\x137%\xaa>\xa5q\xbey\xeaK\r\xb1d\x0ck\xea\xd7\
`{O/\xfa\xfa\xfa\xf0\xea\xc1\x830\x9b-YdG\xd34R\xa9$\x06G\xa4\x8dA\'U[\x92\
\xb7\x8c\x855\xc3n\xb1\xcb?\x16\xd6\x8cZ\x9bGz\xde,\x11\xb5\xdd\xec\x80\xcdF\
\xc1f\xa3\xe02\xbbT?zd\xeep[\xe1\n:\xe0p\xd8\xe1L\xd7\x83\x0fY\xc0\xb8\xb37\
\xc8\x94{\x06$E._6\r\x19\x0b\x84H\xf4\x1a1t\xad[\x87T*\x99\xf3sDQ\x94\xd3\
\xea~\xf4\xdc\xf3\x00\x80\xad\x1d\xdbPk\xf3 \x96\xaa\xee\xc2\x14\x966\xeb\
\x12\xba\x12\xca\xf6u$\x9dQ\x99\x8d\x02\x00\x10\xf4\xcf\x8d\xb2\x12\xd8\xe5t\
\xcan\x99s\xc1[[\x97\xd7\x1f\xc5\x99\xae\x87\xd0"\xc2\xe1\xb0K\xe3\xc2m\xc5*\
\xd1\xabzM\xadW\n\x0c\x94\xe3I9\xce\xc8\xf8\xa3y;\xecf\x87j\xcc\xce\xf5ca\
\xcdE5\x0f\xe7g\xa5\xa8\xce\xd6.L\x06\xfd8\xd0\xd7\'Uu/\x01B\x07\x96\x00\xa9\
+Q\r\x19$\x95D,\x19C\xad\xcd\x83\xfb>\xb4\x03\x00\xf0OO<\x81\xa1\xd1Q\xddh\
\x89\x90<1\xc6R\xca\'\xf3\x852Z\xb5\xd9(\xc4\xe3"L\xbc\x13\xf1\xb8\x884\xa3\
\xd6\xf7CB4\x8b\xd8\xb5\xd0.\xb9\xb5HL\xcd\x14n\xc6\x05\xa8,_\xb5\x91\xe2\
\xc7\xaf\xdb\x8e\xb6\xe6f$S\xf9#n\x87\xdd\x8e\xd7\xdf|\x0b\x8f?\xfe8\xd6\xb7\
u\xe0\xe6\xf7\xdd\x02 sCW\x1b\xb4\x85QJB\'\xf7\x85\xb6\x98JYI\xda\xbc\xb2\t\
\xe2\xb9\xd9\x82\xb3\x1ce\xfb\xc54\xa1V\x06[$\xfbE\x0f\x8c;\x89\x88i\x12\xce\
t\xbd\\#\x01\x00aO\x14L*\xbbVBo<\xa5\x99\x88<\xfel\xb6\xca\xeb\xda\x89t\x02\
\r\xee\x06\xaco\xeb\xc0\xe8\xe0\x08N\x9d\x19\x82\xad\xc0\xc2\xb6j@\xd5\x93z%\
\xab\x1e\xab\t2\xa1\xf7\xde\x87z\x8f\x0f\x0f?\xfa(^x\xe5\x95\x9c\xb2\x0b\x89\
\xa0\x8e\xbe\xfb.&\x83~t\xb6J\xfe\xd5\xe5 %B \x9c\x90\x92o\xa44\x13\x81\xcb\
\xec\x82\x89Wg\x9f\xb8i\x87\x9cU\xe1p[\x11\xf7g\x13\x03\x1f\xcaO\x16\x01!\
\x88`8\x02\x9b\xd5\x9a7\x1a"c\x81\xc8.\xcaG\x82\xee\xeen\xdc\xda\xfbA\xc4\
\x13\t\xdd\xcf\xa0(\n\x1c\xcf#\x91J\xc1n\xb3\xe1\xcbO>\x89]\x87\xf6`{O/\xae\
\xdfp=\x12\xe9D\xd5Z\xae\xce%\r\xe5\xf3\xec\']\x89\n\xad\xd5p;\n\xaf8V\xae\
\x98\xb4\xfe/|\xc8\x02g\xba\x1e\x11\xd3$\x1c\x0e;\xc2\x1ei\xac\xc4\xfd\x16\
\xd8|\xfa\xe9\x8dd<\x11\xc4\xe3\xd2\x98 \x84\x1e\x8f\x8bEy\xe0\x17\x03r\xff|\
\xe8\xd2\xeb\x01\x00\xdf\xfd\xd9\xcf\x10\x8dF\xc1,B\x7f\xe3R\xb1t\x8e\x14\
\xcbS~Ir)Yr\xb9\xaf\xf7>ys\xf4_~\xf8CX\xcc\xe6\x9c\x1a\xb3 \x8ap\xd8\xed8t\
\xf4\x18F\x07G\xb0\xbe\xad\x03\r\xee\x06U\xd7\xa7RA\xc8\x83\xa5\xcd\xaa\x1b)\
\xcdD\xb2tNed\x15\r%`\xf3%\xe1\n: \xb4d\xc8\x99q\'e}\x95\xa4\xbc)\xf3\x9a\
\x03\xe3Q\xcc\xc4\xe3yupA\x14\xc1\xb2,Z\x1b\x1a\xb3d\x17\xe5\xbf\'\x83~t\xd4\
y\xf3\x9a\xa0\xf1\xb3\xcf;\xecvDgf\xf0\xf9\x7f\xf87\xf4\xf5\xf5\xe1\xaemw\
\xe2\xee-\xf7\x80\x9d5\xef\xaa\x16h]$\xf5\xa2t@_zQB\xcf\xa6\x81@\x99\xedB&\
\xc9\xb9&\x80X<._\xc3\xc4\xec\xfe\x88\x9eSc\xc44)\xfd\x1f#\xb3\xd5\xbcA\x07l\
\xbe\xa4n\x00\xa0\xb7\xeaSF\xe7$\xc8\x98\xcf\xdeG>$\xd2\tll\xb8B\x96?_\xdc\
\xbb\x17\x0e\xbb}\xc9H/\xc0\x12 \xf5\xf9\xfa\xa9W+\x08\x99[X3nz\xdf\x87q\xdf\
\x87v`}[\x07\x1e~\xf4Q\xfc\xd9\x83_F\x9a\x9b\xbb-\x1b\xcb0\x88D\xa3\xf8\xc9\
\xee]\x002\xd1E\xb9"Mr\xe3\xc4\xe3\xa2\x1c\xa5\x93\x8d\xd1|\x08{\xa2\xa0G(8\
\xd3\xf5\xf2sD~!\xb9\xcc\t\xc5&il\xc2_P\xe3\x06\x9afp\xe5E\x17I\x9f\xa3\x88\
\xce\xb5\x12\x8c\xec\xd1\x9eG\x0f&\x9e)\x8e\x9a\x1a\x0c\x0c\x8f\xe2\xee/=(\
\x97\xfe\x7f\xfe\xfa/`M\xfd\x1a\xc4\x92\xb1\xaa\x8d\xdas\x81H\x1c\xc4C]\t\
\x97\xc3\x913\xfa\x16\x04^U$F\xea\x0c\xf8\x1c\x13#M3\x88+\xb2\xaf\xb4\xc5G\
\x00\xe4\xbd\x14\xe58 \xd1z\xdco\x01o\xce^Yh\xa3t\x000\xf1N9\x98\xa8\x94\xfc\
\xc2\x0b<b\xc9\x1866\\\x81\xbb{?\x8e\xc9\xa0\x1f\xf7\x7f\xf7;\x08E"\xf3r\xb5\
\\\x0c,\xa9\xa3-\xc5O}1\xa1\xed\xa6B\x88<\xc9\xa5\xe0u\xd6\xe1\xa6\xf7}\x18\
\x0f\xdd\xf10\xee\xdav\'\x00\xe0\x93\x0f<\x80\x87\x1e{\x0c\xbc \xf9T\xcc\x05\
A\x14a\xaf\xa9\xc1\x8f\xfek\xa7,!\xdc\xbd\xe5\x1ep|\x1a\xb1dL\xfe\x7fK\x85\
\x1c\x19\xda(\x84Sa\xddH]\t\xa5\xfc"\xb4\x88r\x84\xa6\x84^#\x05m\xa3\x0c=\
\xf0<\x8fU\xbe\x95X}y{\xe6\xb3\x14\x12\x0cA\xbd\xc7\x87\x0b\xe1\xe9\xa2\xbc\
\xe2]\xf6\x1a\xbc7t\x167}\xeesx\xea\x85\xe7\xb1\xbe\xad\x03_\xf9\xe8Wp\xf7\
\x96{\xe0u\xd6!\x96\x8c\xc9\xd7m\xbe\xe7\xb4T\xcc\x15\x99\x12=}\xaeH}\xae\
\xe8\x9b\x90t8*YV\xe7\xcbFJ\xe8\xec[(\xaf/\xe3N\x82\x0fYdM\x9dL\xf6\x00`\xf3\
%u5u ;Z\x0f\xa7\xc2p\x99]\xb2\x0cC\x1e\xe7\x03\xed=\xc9\xd0\x0cnz\xdf\x87\
\xf1\xc5;\xfe\x17\xea=>\xfc\xcd\xd7\xbf\x85W^{}Ii\xe9\x04U\x9f\xd2\xa8\x8d,\
\xca!/,\x14H*\x15C3p\xda\x9cr>xgk\x97\xec\x05>\x19\xf4\xe3\xf1\xc7\x1f\xc7\
\xd7\x9ey\x06C\xa3\xa3\xb0\xd7\xd4\xc0T\xc4N;\xc30H$S\xf8\xfc?\xfc\x1b\x9e|\
\xc8\x83\xed=\xbdh^\xd9\x84\xfd\xfd\xfbpl\xec8b\xa9\xe8<\xceY\xc6s\x9a\x86]\
\xbe\x99\x94\xc4\xee2\xbb2\xd1U\x08\x809\x01\xc0\nz\x84B\xd8\x13\x85\xd3"El\
\x81P\x14\xdeF\x87L\x1a\xcah\x9d\x90p.\xd0\x14\x85\xf0\xcc\x0c\xb6_}5\x9aW6\
\xe9n\x92\x12r\x9f\x0c\xfa\x8b\xaaV\xb4\x9a\xcdH\x00p;%\xdf\x98\x8f\xff\xd5_\
c\xe7\xcb\xbf\xc6C_\xb8O.\xcc:1\xd4\x8f\xfd\xfd\xfbp:\xf0\x1e"\xf1\x08\x92\\\
jA\xc7!\xcbH\xe4\x99D\n,\xcd\xc8\x8d\xb2U\x98\x8d\x01"\x91iI\x86\x81\x1d!\
\x84\xe0\xb6\xbbq\x96\x1e\xc4j\xa1\xbd\xacV\x05\x0cMa&\x96)~#\x9b\xa5D\xbb\
\xd7\xe6\x9b\xc7&\xfc\x80GZ\xc5EC\xb3\xe7\xce,=J\xe9\x8c\x99\x08=$D\xb3\x82\
\x07\xf2\xefx\\\x84\xc0\xc4\x10K\x96\xd6E\x8c\x80\x14\x06\xba\xednlZ\xdd\x83\
k:\xaf\x91\x8b\xe6\xee\xfb\xd2\xc3\xd8\xb9{7\x1cv{E\xdaHV\x1aUO\xeaJlZ\xdd\
\x83Q\xeb\x98\x1c\x8dT+H\xa7\x19@\xca:\xf0\xd6\xd6\xa9\xaa(\'\x83~\xf4\xf5\
\xf5\xe1\'\xbbwa\xd7\x81\x03\xe8?=\x00\xb3\xd9"\x97\xc0\x17\xab\xdfY-f\xf4\
\x9f\x1e\xc0G\xee\xbf\x1f_\xfd\xcb\xcf\xa0w\xebU\xf8\xf4\r\x9f\xc2d\xd0\x8f\
\xd1\xc1\x11i#2>\xa5\xf2R/7Ha\t \x91\xb8\xf7\xf2L\xb4E\xa27\xbd\x0c\te\x94\
\x9d\xab\xd94/\x080\x9b-\xd8\xde\xd9\xa9\x9b\xc6\xa8\xfc\x9cz\x8f/\xaf\x13$\
\x81\x9e\xb1\x94\xddf\x83\xc9d\xc2\xce\xdd\xbb\xb1\xef\xd0!\xdct\xcd5\xf8\
\x8b\x8f|\x04\xcd\xed-\xf8\xf4\r\x9f\x02 ]\xbb\xc0\xf4\x14F\xcf\x8feU\x13/\
\x06\x94\x15\xa3\x04\xdaL\xa3\xce\xba.\x8c\x9e\x1f\xc3\xb8\xdf\x9f\xd7\xc6\
\x99\x8c\xbf\xc4\xd4\x0c\\\x8e\xfc\xee\xa6\x0c\xc3`&9#\xd7I\x90 \x85\\\x87\
\xc0\xf4\xacS\xa3\x1d\x08\x08\x0e@\x91\xc1\x18\x18\x8f\xcaQ<\x000\x97d~\xd7[\
\xdd\xcd\x07\xda\xf3C\xce\x8d\x97\xf6\xc0ZW\x933\xb8\xaa\x94W\xd4B\xa0\xeaI]\
\xb9\\$2\xc5R\x02!\xd6=c\xaf!6\xe1\xc7\xebg\xce\xe0\xf8{\xef\xa2\x7f`\x10\
\xb1\x99\x19\x98\xcd\x16\xb8]\xaeyo\xc4\xb8].\x8cNL\xe0\x8f\xff\xeeK\xb8z\
\xd3\x15\xb8\xf3\xca\xab\xd0\xdd\xdd\x8d\xe6\xf6\x16t{\xba\xcb\xf4m*\x03\xe2\
\x0b\xa3w\x0eh\x8aBt\xb6}\xdd-w\xdc\xaak1\xa0EG\x9d\xc4 \xa2(\xeaFZT\x8e\xc9\
\x03\x00\xcc,\x0b\xaf\xc7\x83X<\x8e\'v\xee\xc4\xf3{\xf6\xe0\x8a\r\xeb\xf1{\
\x9bz\xd0\xde\xd2\x84K\x9bZ\xd0\xdc\xde\xa2\xea\xba\xb4\x14\xf0\x8d\xef\xff\
\x18\xfd\xa7\x07\xf2\x92U8\x92\x89\xe4\xdd.g\xde\xe6,4M\xc3\xc4\xb2\xd8\xf9\
\xf2\xaf\x01H\xde;\xd6\xba\x1a9\x80\xa9\xf7\xf8\x80\xb6\xb2\x1d~\xd9A&\xe7\
\xa7^x\x1e\x87O\x9c\xc4\x81\xbe>\x1c>v\xbcl\xf7\xe3b\xa2\xeaI\xddb6c\xe7\xcb\
\xbf\x96\x8bl\xaa\x19\x17\xc2\xd3\x08\x85#\xb2)V8\x12A \x18B"\x95Btf\x06\x89\
DB\x96\x19lVk\xc9\x91\xb9\x1e\x04Q\x84\xa3\xa6\x06i\x8e\xc3+\xaf\xbd\x8e\x03\
\x87\xdf\xc4\nw-\x9a\xeb}p9\x9dhmh\x04 \xdd\xac\xe5\xf4R\xd7Bi\xa7\xab5\xeeR\
6( Y0^\xda\x83#\xa7N\xc1l\xd6\xdfC \xe7\xc6n\xb3a\xcf\xfe\xd7\xb2\x9a\x1c\
\xe4jv\xecp8 \x08B\xce\xcdfQ\x14\x91H\xa5\xb2Z\xef\x91\x08\xde\xf2\xff\xb7ww\
\xbfm[w\x1c\xc6\xbf\x14E\xd9\x8ad\xcf\xdd\xda4\xe9\x1b\x06\xf7\xaa\xd7\xf9\
\x97w\xbb\x9b\xdd\xec\x05E.z\xd1`\xc3\x80\r\x05\xd6\x15\xd9\x16\xb4i\x1b\'\
\xee\xe6\xda\x92\x15\xd9\xa6D\xeeB:\xf4\xe11)Q\xb6\x93H\xbf<\x1f h\x91\xc4\
\x8aM&\x8f\x8e\x0f\x0f\x0f;\x1dmu::\xbf\xb8\xd0\xc3/\x1f\xe9\xe1\x97\x8f\xd4\
\xef\xf7\xf5\xee\xde\x9e\xba\xdb[\xba\x7f\xf7\xee\x95\xa79\xbd\xeac\xeb{?I\
\xf4"M\x17\x1eoiv\xcc\xff\xf0\xf9_\xf4\xdb?\xfdQ\xfd^\xfdw\xb8\xadV\xac\x1f^\
\x1c\xea\xbb\xbf=\xd1\xbb\x0f\x1e\x14_G\xdd\x1b\xa3t\xb9[\xe3\xe8\xf9\xa1~3\
\xdf\xa8\xab\x89Wu\x8c\xc2\x07w\xf8\xfc\x95?\xfe\xbf\xcd\xe3\xc1@\xc7\x83\
\xd9\xd4N\xbf\xdf\xaf\xfdnq\x93\xac}\xd4\xe38\xd6\xef\xbf\xf8B\xbf{\xf8\xf0M\
\x7f*\x0b\xb5Z\xb1\xe2V\xa4\xf1\xd9Y\xb1\rm\x96M\x8b\xa5bq+\xd2\xf6\xd6\x96Z\
\xc16\xb4\xb7)\xcbs\xc5q\xac\xdd\x9d\x1dM\xa7S\x1d\x1d\x9f\xe8\xe8\xf8DY6-\
\xcdY\xdft_y\xf7Z\xee\xeb\x8c[\x91\x92$Q\xa7\xddV;I\xb4\xdd\xe9\xa8\xbb\xbdU\
<t\xda\x8f_\xb8k\xa34\xbb\xdd\xbcn\xb3\xa4,\xcfu\xa7\xdb\xd5\'\xf7?\xd0\xe7\
\x8f\xfe\\\xfc|\xd5\xeb\xf8>\xbe\xf7\xfe\xc2\xed\x02\xc2P\xb5\x93D\x934U;\
\x8e\x8b\xb0gy\xae$I\x94$I\xf1l\xd4g\x87?I\x92\xfe\xf5\xedwW\xae\x03\xdc\xe6\
~\xfd\xe1\xf9r\xc79\x8e\xe3bUO\xff\xcel:\xcb\x1d\xef\xf1\xd9\xb9NG\xa3\xd29\
\x90\xa4\x83\xc3\x9f\x94e\xf9\xc2\xd5T\x9d\xa4\xad\x97\xa3\xb3\xcb\xc7\x0b&\
\x89z\xdd\xae\xc6\xe7\xe7\xb5\x1f\x97e\xd3b\x9e\xfe\x97\xbb\xbf(\x065O\x9f\
\x1f\x14\xa3~7\xa8y9\x1e+MSM\xb3\xbc\x98\xd6\x99\xdc\xf23\x0eZ\xadx\xe1\xd6\
\xbe\xedv\xbb\xf83\xdd\xf1\x94\xa4\x9d~\x7f#\xe7\xce\xeb\xac}\xd4\xa5\xd9\
\x06B\xaf\xeb\x01\x177\x11E\xb3\xb8\xad\x838\x8e\x97\xae\xfb\xbe\x8e\xf0\xb1\
m\xee9\x99\x92J1\x97T\x04\xdd\xa9\x0b\xf1h\xbc`#\xb2<W\xc7;\xa6u\xaf\xe1\xb6\
\xf4\x1d=?T\xef\xde]}\xb6\xff\xa9\x9e>;X8\xd2\x9c\xa4\xa9\xd4\xf0Q\x81\xee\
\xdc.;\xbb\xb7\xf5\xb4#\xf79\x87\xc7\xba\xf8\xffy\xb8%\x15A?:9\x99\xad\xcdO\
\xd3b\x8f\xfc\xa8\xd5R+\x8a\x96.\x8f\xcd\xf3\\\xad\xf9?\xb1\xfff?\xabw\xef\
\xae\xfa\xbd\x9eF\x0b\xee\x1fp\x03\x16\xf7F\xe0.P\xbbs>\x18\x0e\xd5\xdd\xdeR\
w{kvAz\xbeZf\x92\xa6\xa57\xce\xf0\x98U\x9d\xaf\xf0\xefk\xf8;\xdc\xc7\xf8w_\
\xe7y6\xff\xb5\x8dZ\xe4wc\x1b\xf3\xd5FQ\xb4\xf6?6\x89\x8b\xf3\xaa?\x9aX\x18\
\xe9\n\xe3\xb3\xfa\xd1`\xc8\x85\xc3m\x8f ]N\xf9\xb8)\xbaa\xf2B\x9f|p_I\xbb\
\xbd0\xb2.,\xe1\x14\xccM\xbc\xaa\xbfKa\xd0\xa5\xf2\x92\xc2\xb3\x8b\x8b\xd9\
\xd7\x1aE\x8at\xf9\xa6\xde\xf4\x9c\xa5\x93\xa9\xee\xdf}O\xef\'\xc9\xe5&q\xef\
\xec)]\xb0*)nEW\xe6\xe1C\xbdnW\xe3\xb3\xcb\xd1s\xd53U\x9b\xfc;\n\xff\x1e6\
\xf9\x98(j\xbduA\x976(\xea\xd8\x1c\xfeM,U\xcb\xe8\xfc \x1f\rN*\xd7;\xfb\xc2g\
\x9f\x86\xdcH\xf1\xbd\xfd\xb6^\xa4\xa9Z\xdfG\xfa\xea\xf1c\xa5\x93I\xa3\x1bG\
\xc2?\xbf\xdd\xf0\r\xe6u\xf2W\xeb\xf8atO\x98\xda\xeet\xf4\xab\xbd=\xbd\xbb\
\xb7\xa7\xde\x9d;\x951wA\xcc\xb2\xac\xf81\x9dN5\x9dN\x95\xb4c}\xb6\xffii^\
\xbe\xc9\n\x10\xf7\x06\x1e^O\n\x7f\x1d\xaf\xcf\xfa\xcfi`\xa3\xb8Q\x99\x0b\
\xbb?\xfdr<\x18\x16\xa39?\xec\xdb\x9d\x8eNG\xd5\xb7\xe5\xe7y\xaew\xe6\x1f38=\
\xd5n\xbf_\xbc\xce\xd1\xe0\xa4\x98\x86y\x91\xa6\xd2\x13i\xff\xe3\x0f\xf5\xd7\
\x7f|\xad\xaf\xfe\xf9\xcd\xd2\xcf\xd5\xc5\xdb\x9f\x1a\x90.\x03\xba\x0e\x17\
\xcd\xfc\xe7\xc0N\xa6\xd3\xe2s\x9e\xa4ii\xc4\xeeO\xc5t\xb7\xb7\xa4`\xd4\xec\
\xaeoH\xd2\xc1\xe1aq\x9e\xdcE\xdfO\xee\xdd\xd7\xfeG\x1f\xe9\xc9\xf7?V>\x9d\
\xaaJ\xab\xd5\xd2\xcf\x83a\xe9\\\xe2\xcd#\xea\xb8U\xe1N\x7f\xc7\xa7C\xed\xf5\
w\x8a \xd7}L\xd54I\x9e\xe7J\xdam\xdd\xbf\xbb<0\xd2l\x1a\xe6\xc9\xf7?\xea\xe9\
\xb3\x03\rF/\x17\xee\x05\xbe\xa9\x16\x85\xdd\xe7\xceC\xf8|XI\xfal\xffSI\xe5G\
\x0e\xfa\xd7(^\xa4\xa9\xf6U^\xe2X%\x9a\x7f\x17Tu\xb3\xd7`8,\x8d\xd2\x97}7\
\x86\xdb\xc3\xf4\x0bn\x95?\x7fZ\xe5x0,E\xe0x0\x9c?\x9b\xf4\xea_E7W\xea\xc7\
\xc5-M\xab\x9a[wK\xfcv\xfb}u:\x89\xa6K\x9e\\\xefvk\x0c\xbfKX\xb7\xe9\x97,\
\xcfK\xdf1\x84S1\xe1t\x8c\x9b\x92q\x0f\xfevqu\xc7\xd1M\x8f\xf8\xc7\xf2hpR:\
\x96\xee\xfa\xc4\xa2\xc7\xda\xb5\xa2\xd9#\x15\xdd\xeb4}\xbe\xad\x7f\x91\x14\
\xb7\x8f\xa8\xe3\xc6\xaa.~I\xf5\x11\x91.\xe3\xfe\xf4\xf9\x81^\x8e\xc7\xf5+T\
\xe6\x01X\x14\x8b0\xec{\xbb;\xdan\xb0\n)\xcbs\x9d\xbe|\xa9\xf34-\x9e\xf7\xba\
\xce\xfc\xb8O\xa6\xd3\xa5q\x97.\xdfd\x9b\x84]\xd2\xcaS)n\xc3/\xff\xdc\xfao\
\xc2\x8b\xde\xe4\x9b^\xc4\xc5j\x88:\xae\xed:#\xdap\xfb\xd7\xc1pX\xbbEn\x96e\
\xa5\x95)u!\x92te\xa4\xd9\xef\xf5j_\xd7\xe7VR\xd4\x8d\x84\xd7\xd1\xb2\xb8;~\
\xd8\xdd\xa8]*\x87\xfd\xf8tX\x19\xf6\xbf\x7f\xf3\x8d\xbe\xfd\xe1Gu:\x8b\xdf\
\x1c\xf3<\xd7\xd3\x83g\xc5\xeb\xb9\xd7\xae\x9az\t\xdf\xfc\x19\xa9\xbf\x1aD\
\x1d\xb7\xc6\x9f7\xad\x1b\x19J\xb3(\xbb\x1fu\xab#\\\xd0\x7f\xfd\xd1\x87\xa5U\
\x18Ua\x0f\xe3.\xad\xf6\x14\x9f\xdc\xbb\x18Y\xfa\x1c\xd6<:\xe1\x1b\x91\x8b{U\
\xd8\x9d\xf0\xbc8\xee|<}v\xa0\xaf\x1e?\xd6\xe7\x8f\x1e\xe9,M\x1b\x8f\xa6\xab\
V\xbc,\x1a\xa5\xaf\xfb\xb1\xddd\\(\xc5\xca\xdc\x8a\x0c\xff\xa2\x9do|v^\x19U\
\xf7\x0f\xdf_\x11\xd3\xebv\xafL\xbd\xe4y^\x04]*\x07hwg\xa7\xf2\xe2kx\xb1n\
\xd9\xdc\xbe/\x8a\xa2\xcb\x8b\x8fk>J\x0f\xb98\x86+d\\\xd8\xdbIR\xac\x8eq\xe7\
e4\x1e\xab\xd7\xed\x16\xc7\xd5\xad\x869\xbb\xb8\xd0$M5\x9a\xefm\xdf\xe4\xde\
\x81(\x8a4\x1a\x8f\xb5\xbb\xb3S\xba8\xea\x8e\x7f8J\xdf\xb4\xe3\xbb\x89\x88:n\
$\x0c\xbb\x1f\x10I\xa5x\xb8\x11w8?\x9e\xab|\x87`\x96e\xc5\xaa\x0e\x17\xa0\
\x90\x1fvI\xa5\x955\xee\xe7\xaa.\xbeV\xdda\xda\xf1\xeeV\xf6\xb7\t\xd8$\xcb\
\x96>V\x85\xfd\xa7\xff\x1d\xe9l\x1e\xdb<sw_\xae~W\xf4\xcf\x83\xa1z\xdd\xee\
\xd2\xa0\xe3\xf5 \xea\xb8\x91\xaa\xe5u>?\xca~\xdc\x07\xc3\xa1vwv4\x1a\x8f\
\xb5\x9d$\xba\xf0\xee\\\xecn\xcdn+w\x91p\xff\r\xdf \xfc\x91\x7f\xb8a\xd3\xd9\
\xc5\xc5\x95x\xbb)\x9db\x9f\x17\xef\xf3\rG\x92\x9b8=P\x17v\'|\xc3\xbd\x98L\
\x14i\xbe\xca\xe8\x9a+~\xdcQj\x12\xf4\xc9t\xba\x91\xc7u\xd3D\xbb\x0f\x1ep\
\x94\xb1\xb2\xaa=I\xfcH\xfa7\xc38U#ni\x16\x84p\xba\xc4}\\8\x95\x13\xbeF\xdd]\
\x8f_\xff\xfb?\xb3\xa5\x8a\xde\x1e*w\xba\xdd\xe2F&7\xdd ]\r\x8f\xb4\x99Qw\
\x9a\x9e\x9b\xd3\xd1H\xe7i\xdax\x8b\x8b\xf0^\x82\xb8\xd5R;\x8eK\xbb?\x96n\
\xe2\xaa8\xae\xd2f\x1f\xdbM@\xd4qmM\xe3!\xadv\xe1\xb2n>\xbci\xdc\xfd\x15\x18\
\xfek\xb9\x8d\xaf\xa4\xea\xf8X\x08\xba\xb3h#0\xc7\xddI\xdbt9gx\x8e\xfd\xf3\
\x1b^\x90\xad\x9bC\xb7pl\xd7\x1dQ\xc7\xb55\r\x87\xaf*\xeeU\x11w\x91X\xf6\xf1\
u\xa3\x7f_\xdd\xd4\x80T\x1d\x1f+\xe1\xa9;?R\xfd~:\xabnnV\x17s\x89\xa0\xbf)D\
\x1d7\xd2$\xecR\xb3X4\xb9\x95|\x95\xd1\xbf\x9b\xba\xf1\xdf4\x96M\x0fX\nO\xd5\
r\xc4\xa6q_E\xd5\x85P\x82\xfe\xe6\x10u\xdc\xd8uF\x84\x8b\xf8\x171\xab.\xc0V\
\xbdA\xb8x\x87\x11w\x9a\x8c(\xad\x86\'<?uKQW9Wu+Z\x88\xf9\x9bG\xd4qc\xe1\x88\
\xf0:a_\xb6\xec\xed:\xd3\x05U#\xffE\xeb\xa5\xad\x07\xa8\xeeF\xa2U\xee\x0c\
\x0e\xdf\x10,N[m:\x964\xe2\xc6\xaan\x80\x91\xca\xcb\x1dWUZk]\x11\xe0\xba\xdd\
\t+_+\xf8\xf3\x8b\x1bt\xde\xb2 \x85_cx\xbe\x9ab4\xbe\xde\x88:nM\x16\xdcn\xef\
\xc7\xb3\xc9h0\x8cm\xf8\xe6P\xfa\xbdA\xa8\xc3\xe9\x9a\xbay\xde\xf0\x8d\xe2m\
\x0e\x92\xff\xb5\xaf\xba\xb9\xd6\xdb|\xdc\xd6\x1dQ\xc7\xad\xaa\x1b\xb57\x1d\
\rV\xfd\xbeE\x1f\x1b\xbe\t\xb8[\xe4\xeb>\x86\x98W\xe3x\xd8A\xd4\xf1J\xbc\xae\
H\xb8;Q\xcf\xe7#s\xb7\x83!\xdb\xba\xe2mE\xd4a\x82\x7fW$A\xc7\xdb\x8c\xadw\
\x01\xc0\x10\xa2\x0e\x00\x86\x10u\x000\x84\xa8\x03\x80!D\x1d\x00\x0c!\xea\
\x00`\x08Q\x07\x00C\x88:\x00\x18B\xd4\x01\xc0\x10\xa2\x0e\x00\x86\x10u\x000\
\x84\xa8\x03\x80!D\x1d\x00\x0c!\xea\x00`\x08Q\x07\x00C\x88:\x00\x18B\xd4\x01\
\xc0\x10\xa2\x0e\x00\x86\x10u\x000\x84\xa8\x03\x80!D\x1d\x00\x0c!\xea\x00`\
\x08Q\x07\x00C\x88:\x00\x18B\xd4\x01\xc0\x10\xa2\x0e\x00\x86\x10u\x000\x84\
\xa8\x03\x80!D\x1d\x00\x0c!\xea\x00`\x08Q\x07\x00C\x88:\x00\x18B\xd4\x01\xc0\
\x10\xa2\x0e\x00\x86\x10u\x000\x84\xa8\x03\x80!D\x1d\x00\x0c!\xea\x00`\x08Q\
\x07\x00C\x88:\x00\x18B\xd4\x01\xc0\x10\xa2\x0e\x00\x86\x10u\x000\x84\xa8\
\x03\x80!D\x1d\x00\x0c!\xea\x00`\x08Q\x07\x00C\x88:\x00\x18B\xd4\x01\xc0\x10\
\xa2\x0e\x00\x86\x10u\x000\x84\xa8\x03\x80!D\x1d\x00\x0c!\xea\x00`\x08Q\x07\
\x00C\x88:\x00\x18B\xd4\x01\xc0\x10\xa2\x0e\x00\x86\x10u\x000\x84\xa8\x03\
\x80!D\x1d\x00\x0c!\xea\x00`\x08Q\x07\x00C\x88:\x00\x18B\xd4\x01\xc0\x10\xa2\
\x0e\x00\x86\x10u\x000\x84\xa8\x03\x80!D\x1d\x00\x0c!\xea\x00`\x08Q\x07\x00C\
\x88:\x00\x18B\xd4\x01\xc0\x10\xa2\x0e\x00\x86\x10u\x000\x84\xa8\x03\x80!D\
\x1d\x00\x0c!\xea\x00`\x08Q\x07\x00C\x88:\x00\x18B\xd4\x01\xc0\x10\xa2\x0e\
\x00\x86\x10u\x000\x84\xa8\x03\x80!D\x1d\x00\x0c!\xea\x00`\x08Q\x07\x00C\x88\
:\x00\x18B\xd4\x01\xc0\x10\xa2\x0e\x00\x86\x10u\x000\x84\xa8\x03\x80!D\x1d\
\x00\x0c!\xea\x00`\x08Q\x07\x00C\x88:\x00\x18B\xd4\x01\xc0\x10\xa2\x0e\x00\
\x86\x10u\x000\x84\xa8\x03\x80!D\x1d\x00\x0c!\xea\x00`\x08Q\x07\x00C\x88:\
\x00\x18B\xd4\x01\xc0\x10\xa2\x0e\x00\x86\x10u\x000\x84\xa8\x03\x80!D\x1d\
\x00\x0c!\xea\x00`\x08Q\x07\x00C\x88:\x00\x18B\xd4\x01\xc0\x10\xa2\x0e\x00\
\x86\x10u\x000\x84\xa8\x03\x80!D\x1d\x00\x0c!\xea\x00`\x08Q\x07\x00C\x88:\
\x00\x18B\xd4\x01\xc0\x10\xa2\x0e\x00\x86\x10u\x000\x84\xa8\x03\x80!D\x1d\
\x00\x0c!\xea\x00`\x08Q\x07\x00C\x88:\x00\x18B\xd4\x01\xc0\x10\xa2\x0e\x00\
\x86\x10u\x000\x84\xa8\x03\x80!D\x1d\x00\x0c!\xea\x00`\x08Q\x07\x00C\x88:\
\x00\x18B\xd4\x01\xc0\x10\xa2\x0e\x00\x86\x10u\x000\x84\xa8\x03\x80!D\x1d\
\x00\x0c!\xea\x00`\x08Q\x07\x00C\x88:\x00\x18B\xd4\x01\xc0\x10\xa2\x0e\x00\
\x86\x10u\x000\x84\xa8\x03\x80!D\x1d\x00\x0c!\xea\x00`\x08Q\x07\x00C\x88:\
\x00\x18B\xd4\x01\xc0\x10\xa2\x0e\x00\x86\x10u\x000\x84\xa8\x03\x80!D\x1d\
\x00\x0c!\xea\x00`\x08Q\x07\x00C\x88:\x00\x18B\xd4\x01\xc0\x10\xa2\x0e\x00\
\x86\x10u\x000\x84\xa8\x03\x80!D\x1d\x00\x0c\xf9?\xd2xo\xfe\xadF\xd4\xef\x00\
\x00\x00\x00IEND\xaeB`\x82' 



def getSageImage():
    stream = cStringIO.StringIO(getSageData())
    return ImageFromStream(stream)

sageImg = getSageImage()#.Rescale(300,254)
def getSageBitmap():
    return BitmapFromImage(sageImg)#getSageImage())



#----------------------------------------------------------------------
def getSageStartUpData():
    return \
'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x82\x00\x00\x002\x08\x06\
\x00\x00\x00\x90\xc9\x03\x88\x00\x00\x00\x04sBIT\x08\x08\x08\x08|\x08d\x88\
\x00\x00\t&IDATx\x9c\xed\x9c_l\xdb\xc6\x1d\xc7\xbf\x92%eV\x9c\x00.\xed\rv\
\xe4\xd8\xc8*\xd9\xe8\x1cL\x9b\x03t\xb2\x83!\x813\xa4\xe8\xacb\x0fE\xeb\x05\
\xc5\xe0\xbe\xac\xe8\xd6>9\x18\x86"o\xc1\x02\x0c\x8d\x9f\x83\x0e\xc1\xea\xbe\
\xac\x80\xd1=d\xf20\x14M\x16\x03K\xa6\x16\xb5\r\xadq1[n\x13\xff\x91ld"\xedX\
\x94\xf8_\xe2\x1e\x18\xd2\xa4I\xd92-\xff\x91\xc3\xcf\x8bt\xd4\xf1\xeeD~y\xf7\
\xfb\xfd\xeex.\x97\xbb\x06\xa5\xb8\xff\xdf\x7f\xc9\xeaw\x86gJ\xe6s8xHE\t\x00\
 J"x\x89\x87(\x89\xb8\xf4\xd37\\\xa5\xf2\xbb\xac\x840\xf9\xed\xb8\x0c\x00\
\xac\xc0\x02PD\xa0\x16,\x15\xa4\xca\xb7\xda\xa1\xa2\xc8\xb2\xf6\xfcj"\xe0D\
\x0e4G\x83\x17y\xfc\xee\x17\xbf7\t\xc2$\x84\xc9o\xc7\xe5\x8d\x02\xd0\xab\xca\
\xa1\xba\xe0DN\xfb\xae\n\x81fi\\\xfd\xe5\x1f\x0cb\xd0\x84\xa0\x1f\x06\x00 \
\xcbf\x91\xe3r\x0659T/\xbc\xc8\x03\x00\x04I@\x96\xc9\x82\x17y\xe4\xf9<n\xfe\
\xe6\xcf.\x00\xf0l<\x81\xe1\x19<a\x9e\x80fi\xd0\x1c\r\x9a\xa5\xb5B\xd4O\x87\
\xea\xe2\x88\xf7\x88!\xcd\x8b<\x18\x9e\x81\xc0\n\xda1\x97\xcb]\x83\x7fL\xfe]\
\x06\x94\xf1\x9f\x139\xd0,\x8d\xa5\xd5%M9bA\xd4l\x04\xc08\x069\x1cL\\\xae\
\xf5\x9e\xdf\xe3\xf6\xc0[\xe3\xd5\xd2\xac\xc8\x82\xcbs\xe0\xf3<\xb8<\x87[\
\x7f\x8c\xb9<\x00\xb4\xb1\x9f\x97x,\xad.\x81fid\x19ehP\x05\xe0\xdc\xfc\xeaB\
\x7f\xbf\xa4\xa2\x04\xa9(\xc1\xe3V\x06\x00I\x90 \xf2"\xb8<\x07.\xa7\xd8\x10\
\xae\x8f\xef},\x03\xebF\x05I\x93 \xb3\xa4#\x82C\x86\xbe\x87P{\x83\xfcj\x1e\
\xb9\xd5\x1c\x00\xc0\xa3\xb7*I\x9a\xd4l\x02\xb1\xe0x\x08\x87\tY\x96\xe1r\xb9\
\xb4\x87\xba \x16 \n\xca=\xcef\xb2\xf0\xe8\xbd\x01A\x124\x11\xe8Or8\x1c\xe8\
\xef\xa7(\x88(\x88\x05d3Y\x00\x80[\xfdA\xef\x19HE\xc9\x11\xc13\x04Gs\x8a\xfb\
X\t\xf7\xd0\xef\xf3\xe3\x04q\xc2t<M\xa5\xc1\x08Nx\xfa "\t\xeb\x9e\xa0G\x1fh\
\xb0C$\x14\xc1\x85\xd3\x17\x10 \x02%\xf3\xb0\x02\x8b\x99\xa5\x19L\xa7\xa7\
\xf1\xc5\xec\x17e\x0b\xe3\x83_\x7f\xa0}O.\'1\x14\x1b\xb2\xd5\xc6jf/\xae\x81(\
\x88\xe6\x80\x12P\x9e\x97\xe0\xf7\xf91\x18\x1d\xdcT\x00*\xb5\xbeZ\x84\xdb\
\xc2\x08\xb7\x85\x91ZIavyv\xfb\xadu\xd8U,\x85P\x0eo_|\xdb \x02\xf5\xa9OQ)\
\xedX\xa89\x84\x16\xa2\x05\xb5\xbe\xda\x9d\xb5\xd2a\xd7\xb1%\x84\xce\x93\x9d\
\x085\x85\xb4t<\x19\xc7\xc8\xbfG\xcc]\xfe\x84\xf2\xd1\xda\xd8\x8aS\xdf=\x85\
\xb3\x1dgm7\xb4R\x04\x9b\x82\xe8h\xee\x00q\x8c\x00q\x8c\xd0\x8e3<\x83\x14\
\x95\xc2W\x0b_a>3_vy\x1bm#2Kb5\xbf\xaa\xa5;Ov\xe2\x85\x13/\xa0\xa5\xa1E;\xb6\
H."\x93\xcd\xe0\xee\xd7ww\xf8o*\x87\xeb\xfd\xbf\xbd/\x03\xeb\xaec\x96\xc9n9\
\x86\x0f\x9c\x1b@$\x14\x01\xa0\xf4\x04\xef\xfd\xe5\xbd\x1d\x1b\x84\x83\xd1A\
\x83\xb8\xecp=v\xddr\xd8\xa9?Z\x8f\xfe\x9e~\x84\xdb\xc2e\x95\x13O\xc61<6\\V\
\xde`S\x10\x97\xa3\x97\xb5\xf4\xe8\xc4(b\x131\x04\x9b\x82x\xf3\xfc\x9b \xea\
\x88\x92\xe7\xbe\xf5\xa7\xb7\x0c\xe9\xdd\xbc\x06zx\x86\xc7\xda\xff\xd6\xb0\
\xf6x\r\xd9L\x164E\xdb\xeb\x11\xf4O\x12ES\x07\xde+h8\xdeP\xb6\x08\x00\xc5\
\x00fx\x06#\xf1\x11[\xf5EB\x11\x0c\x9c\x1b\xb0u\xee~a\xdbFP\t\x10\x01\xb46\
\xb6n\xab;\xddO\x12s\tL\xa7\xa7\x91ZI\x81\xcc\x92\x00\x80\x13\xc4\t\\\xfc\
\xe1E\xc3\xd3\xd8\xdd\xdemK\x08\xe1\xb6\xb0\xc9vZ\xa4\x16\x91\\J\x828F \xdc\
\x16>\x906\x93-!P4\x054\xad\xa7_\xfe\xd1\xcb\xf8h\xec\xa3\x1d\xf5\x0cVnQ\xa5\
\\\'A\x120:1\x8a;\x0f\xeeX\xb6q5\xbf\x8a\xa9\x85)C\xd7\\\xeb\xabE\xb0)\xb8m\
\x0fG/\x02\xab:7\xeb\xfew\xf3\x1al\x85{\xeb,ff\x96f\x0c\xe9p[\x18W^\xbd\x82\
\xf3?8\x0f\xbf\xcf_\x91\x86U\x92\xf9\xcc<b\x13\xb1-\x85:\xf9p\xd2\x90\x0e<\
\xb7\xb5kl\x05+\xb0\xb8\x1e\xbb^V\x9d\x07\x05[=B<\x19Gw{\xb7A\xd9D\x1d\x81\
\xfe\x9e~\xf4\xf7\xf4#1\x97@b.\x81x2^\xb1\x86\xee\x05\xa9\x95\x94!]\xf7\x9d:\
[\xe5\xdc\xfc\xe7\xcd\x92=\xc9\'\x9f\x7f\x02\x9f\xc7g\xab\xdc\xdd\xc4\xb6\
\x8dp\xe3\xd3\x1bx\xad\xfb5\xcd{\xd0\xa3\x06\x8f^\xef~\x1d\x89\xb9\x04\xc6\
\x1f\x8ecjajG\r\xad\x16\xee<\xb8\xb3\xe9\x7f=\xa8\xb6\x94m!0\x02\x83\xe1\xb1\
a\xdc\x9f\xb9\x8fW\xce\xbcb9\xee\xd5\xfaj\x11\tE\x10\tE@\xe5(|x\xf7\xc3\x03\
\x11U,\x15K\xa8\xc4\xb0\xa6.\xfc\xad6v\xec5\xcc.\xcfb(6\x84\xd6\xc6V\xbc\xf8\
\xfc\x8b\xe8n\xef\xb6\xb4\x8a\x89:\x02\x97\xa3\x971<6\xbcoCF\xb4+\x8aH{dS\
\xdf\xfeYe\xc7BP\x99\xcf\xccc>3\x8f\x91\xf8\x08:Ov\xe2\xcc\xa93\x96\xc3\xc6\
\xc0\xb9\x01\x904\xb9\xa7=C\xfd\xd1z\xbc\xf3\xd2;\x96\xf3"\xc9\xe5\xa4\xf6\
\xdd\xef\xf3\x975wr\x18\xa9\x98\x10\xf4L-Laja\n\xb7\xbe\xbc\x85\xb3\x1dg\xd1\
\xd7\xd5g\xf8\xbd\xbf\xbb\x1fW\xffzu7\xaa6\xe1\xf7\xf9M"H\xcc%p\xfb\xc1m\x93\
\x187F\t\x9f%vE\x08*\xab\xf9U\xc4&b i\xd2\x10i\xdb\xcb\xa7\xae\xf7t\xaf\xc9\
\xb7\x8fM\xc4\xf6\xac\xfej\xc1V\x1ca\xbb\xc4\x93\xf1}3\xa2"\xed\xeb\xc3\x13+\
\xb0\x8e\x08J\xb0\'B\x00\x80Ejq\xaf\xaa2\xa07\x0c\xab%\xb8\xb3\x1f\xd8\x12B\
\xe7\xc9\xcem\xe5\xf7\xfb\xfch!\xd6\xa7a\xa9\x1cU\xd6y\xfa|\x95p\xed\x88:\
\xc2\xd2\x80U\xcb\xefi\xef\xd9q\x1d\x95Fo\xcc\xea]\xddJcK\x08\xef\xbe\xf4.\
\xae]\xba\x86hW\x14\xf5G\xeb7\xcd[\x7f\xb4\x1e\x83\xd1A\x83K\x19\x9f)\xcf}\\\
$\xd7{\x91\x00\x11@\xb4+\xba\xed\xb6n\x14\xdd\x85\xd3\x17L\xa2\x8a\x84"\xb8\
\xf2\xea\x15\x93Hv\xf3\xc2\x97\x0bE\xaf\xb7\x9f\xa8#vmV\xd3\xb6\xb1H\xd4\x11\
\xe8\xeb\xeaC_W\x1fRT\n3K3\xc8d3Z\x98\xb6\xa3\xb9\x03\x01"`\x9a\xfeMQ\xa9\
\xb2\xc7\xe9\xc4\\\xc2p~_W\x1f\xc2ma$\xe6\x12\xa6\xbc\xa1\xe6\x10&\x1fN\x9a\
\x16{|\xf6\x9f\xcf\xd0\xdf\xd3\xaf\xa5\x03D\x00\xd7.]\xd3\x86\xaa\xcdVP\xa9\
\xc2\xa0h\n\xf7\xa6\xef\x19\x16\x9c\xec\x15\xe3\x0f\xc7\r\x02\x8d\x84"\x085\
\x87\x90x\x940\xd9]\xa5\xaeA9T\xc4k\x08\x10\x81\xb2<\x81\xe4r\x127>\xbdQv\
\xb9\xf1d\xdc\xb40v\xb3\xba\x92KI\xd3\xb1\xbb_\xdfEkc\xab\xe1b\xd6\xfaj-#\
\xa1\xa3\x13\xa3&\x0fG\x7f\xde~\x18\x9aS\x0bSHQ)\xc3\x7f&\xea\x08\xf4\x9e\
\xee\xb5\xccou\r\xca\xc1\x96\x10\x86\xc7\x86\x11n\x0b\xa3\xa5\xa1\xa5\xac(]\
\x8aJ\xe1\xf6\x83\xdb\xb6"\x8aC\xb1\xa1\x92s\x1a\xe52<6\x0c\x8a\xa6\xd0{\xba\
\xd7\xf2\xe9\x8f\'\xe3\xb8\xf5\xe5-\xed\x89oon7\xd5\x97\xe3r\xb6\xeb\xdf)C\
\xb1!\xf4u\xf5\x95\x8c\xdaV\x02[K\xd5\xf4\xa8k\xf6\x02\xcf\x05L\xb3u\x8f2\
\x8f\x90\xa6\xd2\x15\xebR\x83MA4\x1ck@\xc3\xb1\x06\xed\x18I\x93 i\x12\x82$\
\x945\xa1\x13l\n\x1a\xd2\xa5"\x9c\xad\x8d\xad\xda,\xe1\xc6u\x88\xfbI%\xae\
\x81\xd5R\xb5\x1d\x0ba+\x9cW\xe7\x0e\x1eVBp\x03\xf6_n)\x07G\x04\x07\x8c\xa7\
\xb7\xa3 \x14\x0c\x87\xdd\xbb)\x02\x87\xea@dE\xe3K\xb0\xce\xd68\x87\x1f\x192\
D~\xfdux\x8eV\xb6E\xf0X\xdd|\xf5]z\x87C\x86\x0c\x14\xa5"\x00h{#\x88\x82\xa8\
\xbc\xfb\xb8\xb1\'P\xf7F\x80\x0c\xc0\xd1\xc2\xa1B\x86\x0cI\x94 \xb2\xa2\xb2\
\x7f\x12\xcdAdE\x14\xc5"<\xfa-r\xb4\x13\x9e\x1ax.\xd9\xe5\x88\xe1\x90 \xcb2\
\x8aRQ\xd9;)\xc7!\x9b\xc9B\x14\x14A\x00OwU\xfb\xd5\xd0\x1b\x06\xd3\xde\xe3U\
\xe2Ln\x8f\x1b.8b\xa8jd\xa5\'(JE\xb09\x16\xcc\x1a\x83\xb5\xc7kHO\xa7\x91#\
\x95 \xd9\xf27\x8f\x95]\xd5\x98\'\x8c6fx}^\xd4xk\xe0\xf6\xb8\xe1=\xe2\x85\
\xc7\xeb\x81\xdb\xa3\xd8\x94\x8e(\xaa\x04Y\xfdP\x04 \x89\x92a\xf3,\xbd\x08T\
\xb4\x9dW/\xfe\xf6grAT|\xcb\x1ao\x8d"\x08_\x8dA\x18\x0e\xd5\x83j\x14\x16\xc4\
\x02\xb8\x1c\x07.\xcfa%\xbd\x02\x9a\xa2\r"X\xfe\xe6\xb1q\xe7\xd5\x82X\xc0Jz\
\x05\xc7\x1b\x8fc%\xbd\x02\x008\xdex|O\x1b\xefPy\xd4\xcd\xb28\x9a\xc3Zf\rE\
\xb1h\x99\xcf\xb4)\xf7\x8f\x7f\x1e\x96U\xdf\xd2\xa1z\xd1\xdcCVq\x0f7\n@\xed\
\tT,\xb7\xe9\x0f\xfe\xe4\xfbr\xa9\x02\x1c\xaa\x9f\x8d"\x00J\x08A\xa5\xe9\xf9\
\xef9\x13\x05\x87\x08+\x01\xa8\xfc\x1f\x05\x81\x11\xc3\xb6\xc2\xdf\x94\x00\
\x00\x00\x00IEND\xaeB`\x82' 

def getSageStartUpBitmap():
    return BitmapFromImage(getSageStartUpImage())

def getSageStartUpImage():
    stream = cStringIO.StringIO(getSageStartUpData())
    return ImageFromStream(stream)

#----------------------------------------------------------------------
def getSageStartDownData():
    return \
'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x82\x00\x00\x002\x08\x06\
\x00\x00\x00\x90\xc9\x03\x88\x00\x00\x00\x04sBIT\x08\x08\x08\x08|\x08d\x88\
\x00\x00\x06\nIDATx\x9c\xed\x9d1h\xdbX\x18\xc7\xffN\x1b\x1f\x166=xYb,\xf0\
\xf4\xbc\\\xb1\xc0\x934\x05\x0c\xbd\xc5\xde\x8a\x03]\x128\xae%]\xbd\x95\x0c\
\x07\x85l\x9eC\xaf\x14|\xcb\r\x86\xa3\x83\xbd\xf4\xa8!\x93\x0cG\x0c\n\xe9bA\
\xa9\x0f\x99\x18\x8e\xbc.\x0e1u9\xee\x86D\x8ae\xc9\x8e"\xcbv\x1a\xbf\x1f\x84\
D\xb2\xa4\xf7\xf4\xf4\x7f\xdf\xf7\xbd\xef=+\xa1\xd0\xca=\x8c\xe3\xe7\xfd\x9f\
\xfe\x1b\xfb!\xe7\x9b\xe3\xf5\xce\x9b\xd0\xb8\xcfBnB\xe0\x02\xb8\xdb\xb8\tbe\
t\x07\x17\xc1\xdd\xc7\xed\x19[\x16\x81\x0b`91\xad\x83\xc3"p\x96\x93\x15\x80[\
\x83e\xc6|\xf6\xdc"p\x00\x00\xa1\xa7\xaf\x9erk\xc0\xe1\x16\x81s\x01\x17\x02\
\x07\x00\x17\x02\xe7\x92\xfbA]H\x08\x0bH\xac%\x1c\xfb;\xa7\x1d\x9c\x0f\xce\
\x83*\x863#\xa6\x16\x82B\x15d\x1ff\x91 N\x11\x98\xf4\x07}\xe8\':Z\xdd\x16\
\x1a\xad\x86ga\xbcz\xfa\xca\xfa[\xef\xea(UK\xd3V\xf7\x9bc^m\xe0[\x08BX@1_\
\x9c(\x00\x93H8\x82t2\x8dt2\r\x83\x19\xd0Ot\xbf\xc5rf\x84o!\xec\xfc\xb8c\x13\
\x81\xd9\xeb\rfX\xfbh\x9cB$""\xe1\xc8t\xb5\xe4\xcc\x1c_B\x90\x92\x12\xe8:\
\xb5\xb6\x1bz\x03\x15\xb5\xe24\xf9\xcd\x8b_"\x11A\xe3\x14\nU|W4(h\x9c"\xb5\
\x9e\x02\x89\x11\x90\x18\xb1\xf6\xf7\xbf\xf4a0\x03Z[\xb3\x89\xf9:Fc#\xd6c`=f\
mKI\xc9\xea\x10&\x063\xc0z\x0c\xf5\xe3\xfa\x94w\x13\x1c\xbe\x12J\xdb\x1b\xdb\
\x90\xa9\x0c\xe0\xc2\x12\xbc\xf8\xfd\xc5\xd4\x01a1_\xb4\x89\xcb\x0f\xa5Z\xc9\
\xd5\xed\x90\x18\xc1\xa6\xbc\x89t2\xed\xe9:\r\xbd\x81\xf2A\xd9\xd3\xb14NQ\
\xcc\x15\xad\xedZ\xb3\x86j\xb3\n\x1a\xa7\xd8\xde\xd8\x06\x89\x92\xb1\xe7>\
\xfb\xf5\x99m{\x96mp\x1d\xbe,\xc2pOb=v\xebG\x05$F<\x8b\x00\x00d*\xe3|p\x8e\
\x8aZ\xf1U\x9eB\x15lml\xf9:wQL=jH\x90\x04D"\xde\xc8\x9c.\x92\xa3\xf6\x11Z\
\xdd\x96e\x9e\x81\x0b\xd7\x95}\x98\xb5\xf5F\x85*\xbe\x84 %%G\xecd\x06\xc8$F \
%\xa5[\x193\xf9\x12\x02\xeb1`\xfdj;\x9f\xc9\xa3|P\x9e\xca2\xb8\r\x8b\x82\x1a\
:\xf5\xbf\xf4Qk\xd6P?\xae\xbb\xd6\x91\xf5\x18\xb4\xb6f3\xcd\x91p\x044Nolf\
\x87E\xe0V\xe6$\xf3?\xcb6\xb8\x0e_\x99\xc5\xd1\xc6I\'\xd3\xd8}\xbc\x8b\xec\
\xc3,\x84\xb0\x10H\xc5\x82\xc4`\x06\xaa\xcd\xea\xb5B\xd5\xda\x9am{8\xc0\xbb\
\t\xfdA\x1f\xa5Z\xc9S\x99\xb7\x05_\x16A\xd5U\xc8)\xd9\xa6l\x12%(\xc8\x05\x14\
\xe4\x02\x8e\xdaG\xd0\xda\x1aT]\r\xac\xa2\xf3`\xd4\xbd\xf9\x15u\xf9\xa0<\xd6\
\x92T\xd4\n"\xdf\xdd\x11\xd7\x00\x00\xfb\xef\xf6QP\n\xd6\xe8a\x183yTP\n\xd0\
\xda\x9a\xf5\xb3\x0c\xd4?\xd4\'\xde\xebm\x8d\xa5|\x0b\xe1|p\x8e\xf2A\x19\xaa\
\xae"\x9f\xc9\xbb\xfa\xbdH8\x02\x99\xca\x90\xa9\x0cv\xc6&\xf6\x94y2.\x97\x10\
\x84[\xeb\x7f\xe9O}\x8dE0\xf5\xa8A?\xd1Q:)A$"\xe4\x94\x0c\x85*\xaeQ1\x89\x12\
\x14sE\xfcv\xf0\xdb\xc2\\F>\x93\x87\x9c\x92\'\x8e\xed\x97\x95\xc0f\x1f\rf\
\xc0P\rT\xd4\n\xa4\xa4\x04))\xb9\xba\x8d\xad\x8d-\x9c\x9e\x9d\xce\xd52\x90\
\x18\xc1\xf3G\xcf]\xe7E\xf4\xeeU=\x84\xb0\xe0i\xee\xe4.\x12\x98\x10\x861c\
\x82j\xb3\n\x85*\xc8er\xb6\xcf7\xe5M\xbc\xfc\xe3\xe5,\x8av \x84\x05\x87\x08\
\x8e\xdaGx\xff\xe1\xbdC\x8c\xa3Y\xc2eb&B0a=\x86j\xb3\n\xd6c\xb6L\xdb<{\xdd\
\xe8\x14\xb9\x99\x02\xe6\xd8\x99\xcb\n%UW\xd1\x1f,&\x88\x92SW\xee\xa9?\xe8s\
\x11\x8canK\xd5\x165l\x1a\x0e\x0c\xbf\x95\xe4\xce"\xf0%\x04))\xdd\xe8x!,\xd8\
\xb2t\xec\x8cM8\xfa\x8a\xe1\xe3\x82\x18\xda\x91(\x19;\x15.\x84\x85[1M>\xcap0\
;<\xd4\r\x1a_B\xd8y\xb4\x83\xbd\'{\xc8g\xf2\xd7V\x8e\xc4\x08\x8a\xf9\xa2mH\
\xd9h5<\x95\xd39\xedX\x7f\'H\x02\xf9L\xfe\xc6u\x1d\x15\x9d[\x1a\\\xa1\nv\x1f\
\xef:F9\xb3lx\xaf\x0c\xafm Q\x82\xed\x8d\xed\x99\x94\xe3;X$Q\x82\\&\x87\\&\
\x87\x0e\xeb\xa0\xd5m\x81\xf5\x98\xe5\x02R\xeb)\x88DtL\xffvX\xc7\xb3\x9f\xd6\
\xda\x9a\xed\xfc\\&\x07))\xb9f\xeeh\x9cBkk\x8e\xc5\x1e\xf5\xe3:\nr\xc1\xdaN\
\x90\x04\xf6\x9e\xecY\xf5\x9c\xb4\x82\xca\x14\x06\xeb1\xa8\xbaj{(\xf3Bkk6\
\x81\xcaT\xb6\xeeu4y5\xae\r\xbc\x10\xc8\xa8!A\x12\x9eF\x02zW\xc7\xfe\xbb}\
\xcf\xd7Uu\xd5\x11\xf5O*\xcb-7Q?\xae_$\xbb\x86\x1a3\x12\x8e\xb8fBk\xcd\x9ac\
\x843|\xde"\x02M\xad\xad\xa1\xc3:\xb6{&Q\x82\xec\x0fY\xd7\xe3\xfd\xe6g\xeee\
\xf2\x99_nz\xd2\xe7\xdeg\x84\x10\xc2\xea\xfdUO\xbe\xbb\xc3:x\xfb\xd7[T\x1a\
\x15|\xfd\xf7\xeb\x8d\xca:\xfcx\x88\x07\xc2\x03O3\x81zW\xb7\xf9T\x13\xad\xad\
!\x84\x10\xc45\x11\xab\xf7V\x1d\x9f7\xf4\x06\xf6\xff\xdc\xb7\x96\xa9\xad\xc5\
\xd6\x1c\xe5i\x7fk\xf8\xf4\xcf\'\xc7\xb9$f\x8f;\xc6\xd5a\x1a\x0e?\x1eb\xf5\
\xfe*\xd6\xbf_w\xad\xff0~\xcb\x9f\xfa\xbb\x8f\xe6\x9a=\x91\x88\x0eQ\x18\xcc\
\xb0-\x00\x99\x16\x1a\xa7X\x8b\xae9VH\x9d\x9e\x9dZk\x0e\xbd\\c\x98q=H$\xa25K\
8\xba\x0eq\x91\x04\xd1\x06n\xf0/\xc1r\x00\xf0\xaf\xbcq.\xe1B\xe0\x00\xe0B\
\xe0\\\xc2\x85\xc0\x01\xc0\x85\xc0\xb9\x84\x0b\x81\x03\x00X\x99\xf4ZV\xcer\
\xf0z\xe7M\x88[\x04\x0e\x80K\xd7\xc0\xad\xc2\xf2\xc2\xdf\xbc\xca\xb1\xe1x;;\
\x7f\x0b\xebr0\xea\x05\x1c\x16\x81\xbb\x89\xbb\x8f\xdb3v\xfd\x7f\r&\xdc:\xdc\
-&u\xf2\xff\x01\x07\x85\x9d\x95\xbbRg\x1a\x00\x00\x00\x00IEND\xaeB`\x82' 

def getSageStartDownBitmap():
    return BitmapFromImage(getSageStartDownImage())

def getSageStartDownImage():
    stream = cStringIO.StringIO(getSageStartDownData())
    return ImageFromStream(stream)

#----------------------------------------------------------------------
def getSageStopDownData():
    return \
'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x82\x00\x00\x002\x08\x06\
\x00\x00\x00\x90\xc9\x03\x88\x00\x00\x00\x04sBIT\x08\x08\x08\x08|\x08d\x88\
\x00\x00\x06}IDATx\x9c\xed\x9dOh\xdbV\x1c\xc7\xbfN[\x0f\x9b\x84\x0c^`\x8d\
\x91\xc1\xf4 _\x16,p/\xce\xc9`h/\xd2m$l\x97\x18\xc6\n\xee\xd5\xb7\xd0\xc3\
\x0e%\xb7\xd2\xddL)\x05\xe7\xb2\x81a\xf4\x90\\Z0d=H0\x1a\xb0i;\xf0\x83\x81A"\
\xbe\xf8\xf5\xe2\x10\xd3\x94\xb1\x1d\x1ci\xd6\x1f\xdbrb\xc9i\xf2>\x97\xe4\
\xe9\xcf{O\xd2\xf7\xfd~\xbf\xf7{\x8a\x12\x89,\xdc\xc0(~\xaa\xfc\xf8\xef\xc8\
\x9d\x9c/\x8e\xe7\xa5\x17\x91Q\xfb"^B\xe0\x02\xb8\xdax\tb\xc1\xb9\x81\x8b\
\xe0\xea\xe3\xf5\x8c-\x8b\xc0\x05p=1\xad\x83\xcb"p\xae\'\x0b\x00\xb7\x06\xd7\
\x19\xf3\xd9s\x8b\xc0\x01\x00D\x1e<{\xc0\xad\x01\x87[\x04\xce\x00.\x04\x0e\
\x00.\x04\xce\x197\xe7\xd1h<\x1a\x87\xb0"\xb8\xb6\x1b]\x03\'\xa7\'s\xe8\x11\
\'T!\xac\x8b\xeb(\xac\x15 \x10\xb7\x08L\xfa\xa7}\xd0#\x8aV\xa7\x05\xad\xa5\
\xf9\x16\xc6\xb3\x07\xcf\xac\xdfi\x87\xe2\xc9\xde\x93\x0b\xf7\xf7:\x11\x8a\
\x10\xe2\xd18\xcaJy\xac\x00Lb\xd1\x182\xa9\x0c2\xa9\x0ct\xa6\x83\x1e\xd1\x10\
z\xc8\tE\x08\xa5\xfb%\x9b\x08\xccQ\xaf3\xdd\xda&&D$I\x12\xb1h,\x8c.q\x1c\x04\
.\x04)%A\\\x15\xad\xb2F5\xd4\xd4\x9a\xdb\xe4\x1f\x0e~$I\x12bB\xc4\xba\xb8\
\x1et\xd7&\x12\x8f\xc6!\xa5$\x08+\x02\x92$im\xd7\x99\x0e\xa3k\xa0\xd1n\xf8r]\
d\x89\x80,\x11\xab<\x1c\x0b\x91%\x82uq\x1dbbp\x8f\xfa\x9f\xfaS\xbb\xc5Y\x10x\
B\xa9\x98/"\'\xe6\x00\x0c,\xc1\xf6\xaf\xdb\x17\xbe\xc0\xb2R\xb6\x89\xeb<<\
\xd9\x7f2\xd6\xed(Y\x05\x85\xb5\xc2D\x0b\xb5\x7f\xb8\x8f\xfa\xbb\xfa\xd8kR\
\xb2\n\xe4\xac\xecj{c}\x03\x85o\x0b\x9e\xe7\xf4O\xfb\xa8\x1eT\xd1h7&\\\xc9l\
\x08|\xfa8<\x12X\x8f}\x11\xb3\x82b\xbe\x089+\xfbrSrVFY)#\x1e\x8dO\xd5FY)\x8f\
\x14\x010\x88\x95J\xf7J\x90R\xd2T\xf5\x9e\x97Pg\r\x02\x19\x98\xd8\xe1\xd8\
\xe0\xb21l\xc1L4\xaaA\xa5*\x8c\xae\x01aE@z5m\xb3\x16\x02\x11P\xba_\xf2=S\xd9\
\xccmZ1S\xff\xb4\x8fF\xbb\x01\xd6c K\x04RJ\xb2\t\xb0\x98/\xce\xc4\x8aN"p!\
\xb0\x1e\x03V\xff/+Y\x05\xd5\x83\xea\x85.\xcc\xeb\x86\xcfb\xfa(&D\x97\x08*\
\xaf+6\xf3L\x8f(\xe8\x11E\xa3\xdd@Y)[\x0fM\\\x1d\xc45*U\'\xb6c\x8a\xc0+^J\
\x92\xa4\xad\xdeX4\x86\xc2Z\x01{\x87{S_\xcf4\x04\xee\x1a\x9c~8\x93\xca\xe0\
\xd1w\x8fPX+LmN\x83F\xc9*\xb6\xf2\xfe\xe1\xfeH\x1f\xad3\x1d5\xb5f\xdb&\xdf\
\x95=\x8f\xf5B\xa3\x9a\xe7\x80\xf0\xaa7\x97\xb6\x8b3\x08\x02\x17\x82JU\xd0\
\x8e]\x0cd\x91`#\xb7\x81\xa7\xc5\xa7xx\xef\xe1\xa5\x99!8\x03\xd0\xfa\xbb\xfa\
\xd8sT\xaa\x82\x1d3\xabL\x16\x89mv1\nS\x04\xe3\xea\x1d\x86,\x92\xc0\x07M(k\r\
\x95W\x15hT\xf3\xdc\x97Ie\xb0\x95\xdf\xc2/\xc5_P\xcc\x17C\x0b\x8e\x9c\x98\
\xd37\x93f\xbb\xe9\xcb}9-\x86\x9f\xfe\xfbq\x1f\xce\xc1\xe3\x95\x92\x9f%\xa1\
\x04\x8b\'\xa7\'\xa8\x1eT\xa1R\x15JV\xf1\x9c\xfa\xc5\xa21\xe4\xc4\x1crb\x0e\
\xec\x98\xa1zP\r5\xab\xe8\x1c\xc9~\x03Z\xa3k\xd8\xca\xb1\xaff\x93\x10s\xc6VA\
\x13\xea\xea#=\x1a\x04q\x8f\x7f\x7f\x8c\xfa\xfb:\xfa\xa7}\xcf\xe3\xc8"AY._\n\
\x971\x89\xeeq\xd7V\xf6\xe3\x1a\xfc\xc0z\xccV\x9eU\xbd\xa3\x98\xcb\xea\xa3\
\xcet\xe8\xea (\x92R\x12\xa4\x94\xe4\x8a\xd6\x01`+\xbf\x85\xeeq\x97\xaf7\xc0\
-\x8cY3\xf7\xf7\x11\x1a\xed\x06\xaa\x07Ul\xff\xb6\x8d\xfd\xc3}\xd7\xfe\xcd\
\xdc\xe6\x1cz5\x7f\x86\x13q\x00\x02\xcf#\xcc]\x08&\xac\xc7\xb0w\xb8\x87\xdd\
\x83]\xdbv?+\x96\xf3\xc4i\xb2ge\xbd\x9cB\xe8\x7f\xf2v\xa3\xb3\xe2\xd2\x08\
\xc1D\xa5\xea\xc8\xd8!HZ\x9d\x96\xad\xecw\xf6\xe2\x14\xc2\xacL\xf8y\x83\xd7\
\xf3r\xe9\x84\x00\x04\x7f\xd1^8G\xb2@\x04\xd7\xa8tb\xaeN\x0e\xe3\x14\xd4yp\
\xa6\x99\x9b\xed\xe6\x85\xeb\x9cD\xe0B\x986/\x10\x8f\xc6m\xa3a8a3\x8e\xe1\
\xe3\xce\x9b|q\xe6:&\xc5\'\xf2]\xfb\xc2\x14\xedP_\x16a\xd2l\xa8\xb0f_\x8c\nc\
\x052p!\x94\xee\x95\xb0\xf3\xc3\x0e\x94\xac2q\x84\x91%b\xcb\xb3\x03\x80\xd6\
\xf2ND9\x19\x9e\xcf\x0bDp\xa5\x8b\xfd\xb0w\xb8gsK\x99T\x06\xc5|\xd1\xf3\xd8\
\xc2Z\xc1\xb5z\xe8w= \'\xe6PV\xca\x9e\xf7\xa3\x98/\xda\xf2,\x063|%\xa0.J(\
\xd3G\xb2H ge\xc8Y\x19\x063\xd0\xea\xb4\xc0z\xccr\x01\xe9\xd54\x92$\x89L*c;\
\xcf`\x86\xef\x9b\xdbh7l\xe7\xcbY\x19RJ\xf2\x1cMbBD\xa3\xddp\xa5\x90Y\x8f\
\xa1\xa6\xd6\xb0\x95\xdf\xb2\xb6\xe5\xc4\x1c\xc4\x84h\x13\xa4\x94\x92\\Al\
\xfd}}\xaa@Q\\\x15\xb1\xf3\xfd\x0e4\xaaYV\xc4\xab\xdeq\xa9\xe8Y\x12z\x1eA \
\x82\xaf\x99\x00\xedPT^U|\xd7\xabR\xd5\xf5b\xec\xb8\xb6F=4s\xf4\r\x8b\xc1\
\x14\xf2(\xea\xef\xeb\xae\x85\xa2qhT\xb3\xf2&^\xf9\x13\x93\xdd\x83\xdd\xd0\
\xe2\xa5\x1bY%\xfbs\x90\r|\xec}D\x04\x11\xdc\xbay\xcb\x97\xef6\x98\x81\x97\
\x7f\xbeDM\xab\xe1\xf3?\x9f\xa7j\xeb\xed\xdfo\xb1\x1c_\xf6\x95\x85\xa3\x1d\
\xea\xca\xe7\x9b\xe8LG\xb3\xdd\xc4r|\x19\xb7\xbf\xbe=\xb6\x8e\xea\x1fU\xbc\
\xf9\xeb\xcd\xd8\xb6\xd2\x89\xb4m-\xa3\xa6\xd5\xd0l7q\xe7\x9b;\x9e\xf7\x84v(\
*\xaf+\xf8`|\x98x\x1d\xb3"\xd4\xbf}4\xff\x9e!I\x92\xae\x1b\xa03\x1d:\xd3g6\
\xfd\x12\x13"V\x16W\\oHu\x8f\xbb\xe8\x7f\xea\xfb\x1eif\x9f\xd3\xabik\x9b\xe9\
\xda\xfc\xf6u\xd4\xabjf?\xcd\xfb\xc1z\xcc\xaa;lBu\r\'\xa7\'\xd6\x8b\x1dAC\
\x8f((.\xdeN\xd0}\x0e\xeb~L\xe2R\xe6\x118\xe1\xc3\x85\xc0\x01\xc0\x85\xc09\
\x83\x0b\x81\x03\x80\x0b\x81s\x06\xfft\x0e\x07\x00\xb00\xee\xb3\xac\x9c\xeb\
\xc1\xf3\xd2\x8b\x08w\r\x1c\x00g1\x02\xb7\n\xd7\x17\xfe\xe5U\x8e\r\xd7\xd7\
\xd9\xf9WX\xaf\x07N/\xe0\xb2\x08\xdcM\\}\xbc\x9e\xb1\xe7\xffk0\xe1\xd6\xe1j1\
n\x90\xff\x07\x00?\xc8\r\xeep)4\x00\x00\x00\x00IEND\xaeB`\x82' 

def getSageStopDownBitmap():
    return BitmapFromImage(getSageStopDownImage())

def getSageStopDownImage():
    stream = cStringIO.StringIO(getSageStopDownData())
    return ImageFromStream(stream)

#----------------------------------------------------------------------
def getSageStopUpData():
    return \
'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x82\x00\x00\x002\x08\x06\
\x00\x00\x00\x90\xc9\x03\x88\x00\x00\x00\x04sBIT\x08\x08\x08\x08|\x08d\x88\
\x00\x00\t\x91IDATx\x9c\xed\x9coh\x1b\xe7\x1d\xc7\xbf\x92%eV\x9c\x80{\xf66;r\
,\x92E5\x145\xea\x94\x17S\x12\x863wII\xa5\xd0\x17#8]\x19\x82\xc2\xc0K\xde\
\x14\x95\x11J\xdf\x8d\x85\x8e\xd6\xb4/\n\xa1\xd0\xaena+1\x85\x91\xd8c+\xd4\
\x8d\xd9\xe6h\xa5qpk\xc6\xa4\xf3\xda\xd9\xb1\xfe\x90Ig\xc7:Iw\xba;\xe9\xf6\
\xe2zg\x9dt\xfa\x17K\x8a\xed\xdc\xe7\x8d\xf4\x9c\xee\xcf\xa3\xbb\xef\xf3\xfb\
ww\x8f\xc1`\xec@%\xe6\xfe\xfdwQ\xfe\x9e\xcde+\xae\xa7\xb3\xfd\x10\n\x02\x00\
\x80\x17x\xe4\x84\x1cx\x81\xc7\xf3?~\xc1Pi}\x83\x96\x10\xee|}[\x04\x00\x86c\
\x00H"\x90w,\xe4\x85\xe6\xf7Z\xa7\xa9\x88\xa22~\x15\x11\xb0<\x8b4\x9b\x06\
\xcb\xb3\xf8\xf5s\x97\xcb\x04Q&\x84;_\xdf\x16K\x05P\xac*\x9d\x9d\x05\xcb\xb3\
\xcawY\x084C\xe37\x17~\xab\x12\x83"\x84b7\x00\x00)&\x854\x9bV\xa9Ig\xe7"\x0b\
\x82\x138\xa4\xb2)\xe4\xf8\x1c2\xb9\x0c\xde\xfd\xd5\xef\r\x00`*\xdd \x9b\xcb\
\xe2~\xf6>h\x86F\x9aM#\xc5H\x1b\x01P>uv\x16{\xcc{T\xed\x1c\x9fC6\x97\x05\xc7\
p\xca2\x83\xc1\xd8\x81\xbf\xdc\xf9\xb3\x08H\xfe_6\x1d\xb1\xf5\x98\xa2\x1c>\
\xcf+1\x02\xa0\xf6A:\xdb\x13\x83a\xd3\xf2\x9b\x8c&\x98;\xccJ\x9b\xe1\x19\xb0\
\x19\x16\xb9L\x0el\x86\xc5\xf5\xdfM\x19L\x00\x14\xdf\x9ff\xd3H\xd2I\xa4\x98\
\x14RY\xc95\xc8\x02\xd0/\xfe\xce\xa2\xf8z\t\x05\x01BA\x80\xc9(9\x00\x81\x13\
\xc0\xe7x\xb0\x19\x16lZr\x19\x86\x8f\xfe\xf1\x91\x08l\xfa\x90$\x9dD2\x95\xd4\
E\xb0\xcb(\xb6\x10\xb25\xc8\xacg\x90^\x97b?SqT\x99\xa4\x93\xa0\x19Zq\x07:\
\xbb\x07Q\x14a0\x18\x94A\x9d\xe7\xf3\xe09\xe9\x1a\xa7\x12)\x98\x8a\xb3\x01N\
\xe0\x14\x11\x14o\xa4\xb3;(\xbe\x9e<\xc7#\xcf\xe7\x91J\xa4\x00\x00F\xf9\x07\
\xd92\xe4\xf8\x1c\x84\x82\xa0\x8b\xe0\x11\x82\xa5Y\xb5khWzh\xb5Xq\x808P\xb6<\
JE\x91\xe5\xf4Rv\xbb\x10\xb8\xcdLP\xa9#p\x02\xa7\xb9r3\xf18<x\xda\xf94l\x84\
\xad\xe2:\x0c\xc7 \x1c\x0b#\x14\r\xe1\xf3\xa5\xcf\xeb\x16\xc6;\xbf|G\xf9N\
\xc6I\x8cO\x8do\xb9\xbf\x8f\n<\xc7\x97\x17\x94\x80\xe6g\tV\x8b\x15\x01_\xa0\
\xaa\x00d:-\x9dp\xd9]p\xd9]\x88\xacE\xb0\x14_jj_t\xb4\xd1\x14B\xb3\x19;3\xa6\
\x12\x81<\xea#TDY\xe6\xe8w`\x80\x18@\xa7\xa5\xb3\x1d]\xd2)\xa1\xe5Bp\x1et\
\xc2\xd1\xe7P\xdaA2\x88\xc9[\x93\xe5&\x7f^\xfa\x18\xec\x1d\xc4\xa1\xef\x1e\
\xc2\xc9\xa1\x93\xad\xeeZM\xac\x16+\x8e\xda\x8fb\x80\x18\xc0@\xcf\x80\xb2|5\
\xb9\x8aUj\x15_.\x7fY\x97\xeb\xea\xde\xdb\x8d\x9e\xfd=J\xbb8\x16\xea\xde\xdb\
\x8d\x93C\'\xe1\xe8\x97\xceQ6\x97m\xd8-6\x03\xc3\xeb7^\x17\x81\xcd\xd41\x95M\
5\xb5\x03\xfea?<\x0e\x0f\x00\xc9\x12\xbc\xf2\xc7W\xb6\xbc\xff\x80/\xa0\x12\
\xd7\x83\xf0\xc6\xd4\x1bU\xdd\x8e\xcf\xed\xc3\x88s\xa4\xa6\x85\x9a\x9e\x9f\
\xc6\xcc\xe2L\xd5\xff\xe4s\xfb\xe0u{\xcb\x8e}\xdes\x1e#\xce\x11\xcdm\x18\x8e\
\xc1{\x9f\xbd\x87\xc5\xbb\x8b5\xfeI\xe3\xe4\xb29l\xfco\x03\x1b\xf76\x90J\xa4\
@S\xf4f\xfa\xd8*\x88}\x84\xf2\x9d\xa2\xa9\x1d\x91\x15\xf8\x87\xfd\xf0\xba\
\xbdu\xb9)\xaf\xdb\x8b\x80/\x00\xab\xc5\xda\xd01\x02\xbe@E\x11\x00R\xact\xe9\
\x99Kp\x1et6\xb4\xdf\x07\xa5-1\x82\x8c\x8d\xb0a\xb0w\x10+\x89\x95v\x1e\xb6!\
\x8a-\x98L\x90\x0cb.<\x87(\x15\xc5\x01\xe2\x00\x86\xfa\x87T\xd6\xc2F\xd80vf\
\xac\xeeLe\xf4\xf8\xa8\x1231\x1c\x83\x85\xe5\x05P4\x05b\x1f\x01\x97\xdd\xa5\
\x12\xe0\x8b?y\xb1)V\xb4\x16-\x17\x02ES@\xdff\xfb\xecSg\xf1\xc1\xec\x07[\xfa\
cZ\'\xbc\x19\xe9\xe3\x91\xbe#e"x\xfb\xafo\xab\xcc\xf3R|\tK\xf1%|u\xf7+\xbc\
\xf4\xecK\xcaEs\xf49\xe0qx\x10$\x835\x8f#\x8b@+^\x1a\xec\x1dT\xed\xb7\xd3\
\xd2\x89\x11\xe7\x08\xa6\xe6\xa7\x1a\xfe?\x8d\xd0r\xd7\x10\x8e\x85Um\x97\xdd\
\x85W\x7f\xf6*N=q\xaaas\xdaj\xce\x1d;\xa7jO\xcfOW\xf4\xd1+\x89\x15\\\xbbuM\
\xb5\xccw\xccW\xf7\xb1\x82d\x10\x13\xb3\x13e\x03Bk\xbf\x9e\xc7\xd5\xe2l\x05-\
\x17B\x90\x0c\x82\x8c\x93\xaaeD\x17\x81\xd1\x13\xa3x\xd3\xff&\xc6N\x8f\x95\
\x8d\xc2\x87\x81\xd5b-\x0b@g\x16g\xaan\x13$\x83\xa0\xd2\x94\xd2&\xba\x08\x0c\
\xf6\x0e\xd6<\x96,\x82j\xbf\x17Ct\x11-\x1f4-\x17\x02\x00\\\xfd\xe4jE\x93\xe9\
\xb2\xbb\xe0\x1f\xf6\xe3-\xff[\xf0\x0f\xfb\xdb\x16\x1c\x95r\xf8\xfb\x87U\xed\
\x85\xe5\x85\xba\xdc\xd7\xc2\x7f\x17T\xed\'\x0f>Ys\x9b\xb9\xf0\\\xcduJ\x07\
\x8fVI\xbe\x99\xb4%X\xccrYL\xccN`.<\x87s\xc7\xcei\xa6~\x9d\x96Nx\x1c\x1ex\
\x1c\x1ePi\n\xef\xdf|\xbf\xadUE{\xaf]\xd5..vUc\x95ZU\xb5\x9bU\x10+\x8d\xadZM\
[,\x82\xccR|\t\xe3S\xe3\xb8\xf2\xa7+\x98Y\x9cQ\x1e\x97/\x85\xe8"\xf0\xb2\xef\
\xe5m\xe12j\x91\xa4\x93\xaavq\xe1i+P4\xa5j\xdb\x1e\xab]\x9e\xdf\nmM\x1feV\
\x12+XI\xac`28\t\xe7A\'\xdc\x87\xdc\x9a\x17\xdd?\xecG\x92N\xea\xf7\x1bP.\xb8\
f\xd3V\x8b\xa0\xc5\xe2\xddEL\xccN\xe0\xf2\x1f.cz~\xba\xec\xf7\xd1\xe3\xa3\
\x0f\xa1W\x0f\x9f\xe2B\x1c\xa0~?\xa1\x15<t!\xc8\xacg\xd615?U\x16M\xd7s\xc7\
\xf2aRj\xb2\xc9\x18Ya\xcd\xc6(\x15B\xab\x1f\x13\xd86B\x90\t\x92\xc1\x8a\xb1C\
+\t\xc5B\xaa\xb6\xcb\xee\xaak\xbb\xd2t\xb1Y&|\x80P\xc7\x1a\xad\xae\xc6n;!\
\x00\xe5\x91x;(\x8dCl\x84\r\xdd{\xbb\xabnc\xb5X\xcb\x04\x13\x8a\x86*\xac]?\
\xce\x83NU\xf6\xb1\xb0\xbcPe\xed\xe6\xd0r!4Z\x17\xb0Z\xac\xaa\xd1P\\\xb0\xa9\
F\xf1z\x0fZ|)\xadu\x8c\x9e\xa8\x1e\x9f\x94\xde\x98"\xe3$\xd63\xeb5\x8fs\xe2\
\xf1\x13U\x7f?}\xf4\xb4\xaa\xbd+\x84p\xe9\x99K\xb8\xf2\xfc\x15\xf8\xdc\xbe\
\x9a#\xac{o7\x02\xbe\x80\xea\xe4\x06\xc3\xb5k\xf7\x80\xf4\x8c\x80\x8c\x8d\
\xb0\xc1\xe7\xae\xbf\xdc+s\xfd\x8b\xeb*\xb7$\x17\xbb\xb48\xf5\xc4\xa9\xb2\
\xbb\x877n\xdf\xa8\xeb8\x1e\x87\x07\x01_@\xf3|\xf8\x87\xfd\xaa:K\x84\x8a\xd4\
u\xffb\xab\xb4%}$\xba\x08x\xdd^x\xdd^D\xa8\x08\xc2\xb10\x12\xa9\x04"kR\xd1f\
\xa8\x7f\x086\xc2Vff#T\xa4\xee\x9b-\x0b\xcb\x0b\xaa\xed\xbdn/\\v\x97\xe6hr\
\xf4;p\xe7\x9b;\xb8\xf9\xaf\x9b\xaa\xe5\xeb\x99u\\\xbbuMu\xf1=\x0e\x0f\x1c\
\xfd\x0e\x95 ]vWY\x10;\xb38\xd3P\x9a\xeb\xe8s\xe0\xb5\x9f\xbf&\x95\xa9\xbf\
\xad\x19h\xed\xf7\xc3\xbf}X\xf7>\xb7B\xdb\xeb\x086\xc2VW&@\xc6I\\\xfd\xe4j\
\xdd\xfb\r\x92\xc1\xb2\x07c\xab\x1d\xabRt/\x8f\xbeb1\xc8B\xae\xc4\xcc\xe2\
\x0c&\x83\x93\r\xf5U\xae\x9bT+\x9aM\xccN\xb4\xed\x96}\xcb\x8501;\x01\x97\xdd\
\x85\x81\x9e\x01\x10]D\xcd\xf5#T\x04\x9f.~\xfa@\xe6p|j\x1c\xe7\x8f\x9f\xdfrE\
2H\x06\x11[\x8f\xe1\xecSg\xabf\x0fd\x9c\xc4\x8d\xdb7\x1a.x\xcd\x85\xe70\xff\
\xcd<.\x9c\xbc\xa0yN\xc88\x89\x8f\xff\xf9q[\x9f\xdbh\xf9\xa3j\xc5\xc8\xef3\
\xd8\x1e\xb3\xa1\xeb;]\xaa\xdf\x96\x13\xcb\x88P\x91\xba\x82\xadz8\xd2w\x04=\
\xfbz\xd0\xb3o\xf3Y\xc1$\x9dD\x92N\x82\x13\xb8\xbaO\xb2\xdc\xe7\xa1\xfe!eY(\
\x16B2\x95\xac\xbb\xaf\x95\x1eU\x93\xfb)\x9f\x8f$\x9dD(\x1aj\xda9\xa8\x84\
\xd6\xa3jmu\rY.\xab<\xd8\xd1j\x9au\x9cV\xf7\xb9]\xe7\xa3\x16F\xa0=/\xb7\xe8l\
\x13\xbe}e%\xcf\xe5U\x8b\x8d\xba\x08tx\x86\xdf\xac#\xe4\xf8\x9c>5\xce#\x80\
\x08\x11|n\xf3ux\x96\x96nf\x99\xb4.\xbe\xfc.\xbd\xce.C\x04\nB\x01\x00\x94\
\xb9\x11x\x8e\x97\xde},\xb5\x04\xf2\xdc\x08\x10\x01\xe8Z\xd8U\x88\x10!\xf0\
\x02x\x86\x97\xe6O\xa2Y\xf0\x0c\x8f\x02_\x80\xe1\xe2\xbb\x17\xc5\xe2\x89\xb2\
\x00\xa0P\x90Tc\x80A\x17\xc3.A\x14E\x14\x84\x02\x984\x03:A#F\xc6@S4\xd2Ii\
\xa2\x14\x83\xc1\xd8\x81_\x8c\xbf\xa0z\xfd\xd9d\x96\xb2J\xa3\xc9\xa8\x8ba\
\xa7#J\x96@\x16Av#\x8b\x8d{\x1b\x88\x86\xa2\x8a\x08\xe2\xff\xb9\'\xcd\xaa\
\x96\xbd\x9fU|\x86\xd9bF\x87\xb9\x03F\x93\x11\xe6=f\x98\xcc&\x18MRL\xa9\x8bb\
\x87 \xca\x1f\x92\x00\x04^PM\x9eU,\x02\x19e\xe6\xd53\x17\x7f*\xe6y)\xb7\xec0\
wH\x82\xb0t\xa8\x84\xa1\xb3s\x90\x83\xc2<\x9f\x07\x9bf\xc1fX\xacE\xd7T\xee\
\x00\x90\xac\x01Pt\xaf!\xcf\xe7\xb1\x16]\xc3\xfe\xde\xfdX\x8b\xae\x01\x00\
\xf6\xf7\xeeok\xe7u\x9a\x8f<Y\x16K\xb3\xd8Hl\xa0\xc0\x174\xd7+\x9b\x94\xfb\
\x87\xcf\xbaD9\xb7\xd4\xd9\xb9(\xe9!#\xa5\x87\xa5\x02\x90-\x81\x8c\xe64\xfdG\
~tX\xac\xb4\x03\x9d\x9dO\xa9\x08\x80\nB\x90\xe9\xfb\xc1\xf7\xf49\xf6v\x11Z\
\x02\x90\xf9?\xec\x08#j\x16n\xfd\xae\x00\x00\x00\x00IEND\xaeB`\x82' 

def getSageStopUpBitmap():
    return BitmapFromImage(getSageStopUpImage())

def getSageStopUpImage():
    stream = cStringIO.StringIO(getSageStopUpData())
    return ImageFromStream(stream)





##########################################################
##########################################################
##########################################################
#
# start everything
#
##########################################################

if __name__ == '__main__':
    # change to the folder where the script is running
    # so that the relative paths work out correctly
    os.chdir(sys.path[0])  
    main()
