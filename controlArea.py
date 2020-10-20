import re
import numpy as np

def RegOn():
  ctx.field("RegOn").value=True
  
def RegOff():
  ctx.field("RegOn").value=False
  
def ContourOn():
  ctx.field("ContourOn").value=True
  
def ContourOff():
  ctx.field("ContourOn").value=False

def updateListViewSelection1():
  l=ctx.control("volumeListView1")
  if l.selectedItem()==None:
    ctx.field("parent:MultiFileVolumeListImageOutput1.outVolIdx").value=0
  else:
    ctx.field("parent:MultiFileVolumeListImageOutput1.outVolIdx").value=l.selectedItem().id()
  
def updateListViewSelection2():
  l=ctx.control("volumeListView2")
  if l.selectedItem()==None:
    ctx.field("parent:MultiFileVolumeListImageOutput2.outVolIdx").value=0
  else:
    ctx.field("parent:MultiFileVolumeListImageOutput2.outVolIdx").value=l.selectedItem().id()
  
  print(ctx.field("parent:ImageSwitch6.currentInput").value)
  
  
def updateListViewSelection3():  
  l=ctx.control("volumeListView3")
  if l.selectedItem()==None:
    ctx.field("parent:MultiFileVolumeListRTOutput.outVolIdx").value=0
  else:
    ctx.field("parent:MultiFileVolumeListRTOutput.outVolIdx").value=l.selectedItem().id()

_csos = []
_csoIds = {}
_csoGroups = []

_groups = []
_groupIds = {}
_groupCSOs = []

_tabTimer = 0

def buildListViews(field=None):
  #buildCSOListView()
  buildGroupListView()
  #csoSelectionChanged()
  groupSelectionChanged()  
  updateTabs()
  
def buildGroupListView(field=None):
  print("buildGroupListView")

  groupListView = ctx.control("groupListView")
  groupListView.clearItems()
  
  groupDisplayTree = ctx.field("groupDisplayTree").value
  groupStrings = groupDisplayTree.split("|")
  
  global numGroups
  if not groupDisplayTree == "":
    numGroups = int(groupStrings[0])
  else:
    numGroups = 0
  
  ctx.field("numGroups").updateValue(numGroups)
  zeroFill = 0
   
  global _groups
  _groups = []
  global _groupCSOs
  _groupCSOs = []
  global _groupIds
  _groupIds = {}
  
  groupRe = re.compile('(.*?)\s+?(.*?)\@(.*?)$')
  
  for i in range(numGroups):
    groupString = groupStrings[i+1]
    matches = groupRe.findall(groupString)
    if len(matches):
      groupId = matches[0][0]
      if len(groupId) > zeroFill:
        zeroFill = len(groupId)
      groupLabel = matches[0][1].strip()
      csoIds = matches[0][2].strip().split(" ")
      _groups.append([groupId,groupLabel])
      _groupIds[groupId] = i
      _groupCSOs.append(csoIds)
  
  for i in range(numGroups):
    groupId = _groups[i][0]
    if zeroFill > 0:
      groupId = groupId.rjust(zeroFill)
      
    #lvi = groupListView.insertItem()
    lvi = groupListView.insertCheckBoxItem()
    
    lvi.setText(1,groupId)
    lvi.setText(2,_groups[i][1])
    lvi.setCheckBoxOn(0,True)
    

  if numGroups > 0:
    ctx.control("groupBox").setTitle("Contours [" + str(numGroups) + "]")
  else:
    ctx.control("groupBox").setTitle("Contours")

def groupListViewCheckChanged():
  groupListView = ctx.control("groupListView")
    
  idx=ctx.field("parent:CSOManager.groupSelectedItems").value
  for i in range(numGroups):
    ctx.field("parent:CSOManager.groupSelectedItems").value=i+1
    if i in groupListView.checkedItemIds():
      ctx.field("parent:CSOManager.groupSinglePathPointStyle").value="LineStyleSolid"
    else:
      ctx.field("parent:CSOManager.groupSinglePathPointStyle").value="LineStyleNone"
  ctx.field("parent:CSOManager.groupSelectedItems").value=idx
  
def updateGroupListView(field=None):
  #print("updateGroupListView")
  listView = ctx.control("groupListView")
  alreadyCalledLater = listView.property("listNeedsUpdate") or listView.property("selectionNeedsUpdate")
  if not alreadyCalledLater:
    ctx.callLater(0, "updateGroupListViewLater")
  listView.setProperty("listNeedsUpdate", True)
  
def updateGroupListViewSelection(field=None):
  #print("updateGroupListViewSelection")
  listView = ctx.control("groupListView")
  alreadyCalledLater = listView.property("listNeedsUpdate") or listView.property("selectionNeedsUpdate")
  if not alreadyCalledLater:
    ctx.callLater(0, "updateGroupListViewLater")
  listView.setProperty("selectionNeedsUpdate", True)
  
def updateGroupListViewLater():  
  #print("updateGroupListViewLater")
  listView = ctx.control("groupListView")
  if listView.property("listNeedsUpdate"):
    listView.setProperty("listNeedsUpdate", None)
    buildGroupListView()
  listView.setProperty("selectionNeedsUpdate", None)
  groupSelectionChanged()
  
def groupListViewSelectionChanged(field=None):
  print("groupListViewSelectionChanged")
  if ctx.field("ignoreGroupListViewSelectionChanged").value:
    return
  ctx.field("parent:DrawVoxels3D1.clear").touch()

  groupListView = ctx.control("groupListView")
  lvSelIds = groupListView.selectedItemIds()
  selIds = []
  for i in range(len(lvSelIds)):
    selIds.append(_groups[lvSelIds[i]][0])
    
  for i in range(len(_groups)):
    if groupListView.itemForId(i):
      groupListView.itemForId(i).setText(0,"")
         
  ctx.field("numSelectedGroups").updateValue(len(lvSelIds))
  
  ctx.field("ignoreGroupSelectionChanged").updateValue(True)
  ctx.field("groupSelectedItems").updateValue(" ".join(selIds))
  ctx.field("ignoreGroupSelectionChanged").updateValue(False)
  global _tabTimer
  if _tabTimer == 0:
    _tabTimer = ctx.callLater(0.1,"updateTabs")
  
  ctx.field("parent:CSOImageStatisticsOverTime.update").touch()
  #ctx.field("parent:IntervalThreshold.clampThresholds").touch()

def groupSelectionChanged(field=None):
  #print("groupSelectionChanged")
  if ctx.field("ignoreGroupSelectionChanged").value:
    return  

  groupListView = ctx.control("groupListView")
  ctx.field("ignoreGroupListViewSelectionChanged").updateValue(True)
  groupListView.clearSelection()
     
  for i in range(len(_groups)):
    groupListView.itemForId(i).setText(0,"")
  
  selItemIds = ctx.field("groupSelectedItems").stringValue().strip()
  if not selItemIds == "":
    selIds = selItemIds.split(" ")
    ctx.field("numSelectedGroups").updateValue(len(selIds))

    for i in range(len(selIds)):
      if selIds[i] in _groupIds:
        selId = _groupIds[selIds[i]]
        groupListView.setSelected(groupListView.itemForId(selId),1)

  else:
    ctx.field("numSelectedGroups").updateValue(0)
    
  ctx.field("ignoreGroupListViewSelectionChanged").updateValue(False)
  global _tabTimer
  if _tabTimer == 0:
    _tabTimer = ctx.callLater(0.1,"updateTabs")

#def updateSelectionMarks():
#  #print("updateSelectionMarks")
#  #csoListViewSelectionChanged()
#  groupListViewSelectionChanged()
#  return

def updateTabs(field=None):
  #print("updateTabs")
  global _tabTimer
  if _tabTimer == 0:
    return
  
  _tabTimer = 0
  
  #csoSelItemIds = ctx.control("csoListView").selectedItemIds()
  groupSelItemIds = ctx.control("groupListView").selectedItemIds()

  # if no CSOs or groups are selected disable corresponding tab
  #if len(csoSelItemIds) == 0:
  #  ctx.field("CSOManager.csoTabSelected").updateValue(0)
  if len(groupSelItemIds) == 0:
    ctx.field("groupTabSelected").updateValue(0)
  
  # auto-select CSO or group tab if only those are selected
  if ctx.field("csoTabSelected").value == 0 and ctx.field("groupTabSelected").value == 0 and ctx.field("selectionTabSelected").value == 0 and ctx.field("notificationTabSelected").value == 0 and ctx.field("defaultTabSelected").value == 0:
    #if len(csoSelItemIds) and len(groupSelItemIds) == 0:
    #  ctx.field("CSOManager.csoTabSelected").updateValue(1)
    if len(groupSelItemIds) ==0: #and len(csoSelItemIds) == 0:
      ctx.field("groupTabSelected").updateValue(1)

  

  
  


def wakeup(): 
  initFrontierStyle(ctx.window())