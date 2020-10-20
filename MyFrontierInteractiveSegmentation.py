from mevis import *
import numpy as np
from PythonQt import QtCore
from PythonQt import QtGui
import shutil
import os.path
import time
import radiomics
from radiomics import featureextractor
from radiomics import firstorder, getTestCase, glcm, glrlm, glszm, imageoperations, shape
import SimpleITK as sitk
import six
import matplotlib.pyplot as plt
import pandas as pd
from itertools import chain

#from PyQt5.QtWidgets import QApplication, QWidget, QInputDialog, QLineEdit, QFileDialog

ctx.field("controlArea.resampledPixelSpacing").value=[2,2,2]
ctx.field("controlArea.binWidth").value=0.5
ctx.field("controlArea.RadiomicsString").value=''
ctx.field("controlArea.RadiomicsShape").value=True
ctx.field("controlArea.RadiomicsFirstOrder").value=True
ctx.field("controlArea.RadiomicsGLCM").value=True
ctx.field("controlArea.RadiomicsGLRLM").value=True
ctx.field("controlArea.RadiomicsGLSZM").value=True
ctx.field("controlArea.RadiomicsNGTDM").value=True
ctx.field("controlArea.RadiomicsOriginal").value=True
ctx.field("controlArea.RadiomicsWavelet").value=False
ctx.field("ImageSwitch.currentInput").value=1

_frontier = None
def setupFrontier():
  global _frontier
  _frontier = ctx.module("FrontierSyngoInterface").object()

def setFrontierIsProcessing(isProcessingFlag):
  _frontier.setIsProcessing(isProcessingFlag)

def connectRenderersToLayout():
  if len(_frontier.getMonitorConfiguration())==1:
    _frontier.selectLayout("SINGLE_CA-LEFT_V(1,1|1)",["controlArea","viewer2D_reference","viewer2D_overlay","viewer2D_fused"])
  elif len(_frontier.getMonitorConfiguration())==2:
    _frontier.selectLayout("DUAL_CA-LEFT_H(1,1)_H(1)",["controlArea","viewer2D_reference","viewer2D_overlay","viewer2D_fused"])

def loadImageDataSetFromDirectory():
  ctx.field("DirectDicomImport.source").value = _frontier.getIncomingDicomDirectory()
  ctx.field("DirectDicomImport.dplImport").touch()
    
def settingsRef():
  if ctx.field("MultiFileVolumeListImageOutput1.output0").getDicomTagValueByName("Modality")=='PT': 
    SeriesTime = ctx.field("MultiFileVolumeListImageOutput1.output0").getDicomTree().getTag("SeriesTime").value()
    RadiopharmaceuticalStartTime = ctx.field("MultiFileVolumeListImageOutput1.output0").getDicomTree().getTag("RadiopharmaceuticalInformationSequence").getSequenceItem(0).getTag("RadiopharmaceuticalStartTime").value()
    ellapsedTime = np.array(RadiopharmaceuticalStartTime.secsTo(SeriesTime))
    halfLife = np.array(ctx.field("MultiFileVolumeListImageOutput1.output0").getDicomTree().getTag("RadiopharmaceuticalInformationSequence").getSequenceItem(0).getTag("RadionuclideHalfLife").value())
    RadionuclideTotalDose = np.array(ctx.field("MultiFileVolumeListImageOutput1.output0").getDicomTree().getTag("RadiopharmaceuticalInformationSequence").getSequenceItem(0).getTag("RadionuclideTotalDose").value())
    actualActivity = RadionuclideTotalDose*np.power(2,(-ellapsedTime/halfLife))
    PatientWeight = np.array(ctx.field("MultiFileVolumeListImageOutput1.output0").getDicomTree().getTag("PatientWeight").value())
    ctx.field("DicomRescale1.outputSlope").value=1/(PatientWeight*1000/actualActivity)
    
  ctx.field("View2DExtensions1.lut.center").value=100
  ctx.field("View2DExtensions1.lut.width").value=500
  ctx.field("SoOrthoView2D1.sliceZoom").value=5
  ctx.field("SoOrthoView2D1.viewingCenter").value=ctx.field("Calculator.resultVector1").value

def settingsOverlay():
  ctx.field("View2DExtensions2.lut.center").value=2.5
  ctx.field("View2DExtensions2.lut.width").value=5
  ctx.field("SoOrthoView2D2.sliceZoom").value=5
  ctx.field("SoOrthoView2D2.viewingCenter").value=ctx.field("Calculator1.resultVector1").value
  
  if ctx.field("MultiFileVolumeListImageOutput2.output0").getDicomTagValueByName("Modality")=='PT': 
    SeriesTime = ctx.field("MultiFileVolumeListImageOutput2.output0").getDicomTree().getTag("SeriesTime").value()
    RadiopharmaceuticalStartTime = ctx.field("MultiFileVolumeListImageOutput2.output0").getDicomTree().getTag("RadiopharmaceuticalInformationSequence").getSequenceItem(0).getTag("RadiopharmaceuticalStartTime").value()
    ellapsedTime = np.array(RadiopharmaceuticalStartTime.secsTo(SeriesTime))
    halfLife = np.array(ctx.field("MultiFileVolumeListImageOutput2.output0").getDicomTree().getTag("RadiopharmaceuticalInformationSequence").getSequenceItem(0).getTag("RadionuclideHalfLife").value())
    RadionuclideTotalDose = np.array(ctx.field("MultiFileVolumeListImageOutput2.output0").getDicomTree().getTag("RadiopharmaceuticalInformationSequence").getSequenceItem(0).getTag("RadionuclideTotalDose").value())
    actualActivity = RadionuclideTotalDose*np.power(2,(-ellapsedTime/halfLife))
    PatientWeight = np.array(ctx.field("MultiFileVolumeListImageOutput2.output0").getDicomTree().getTag("PatientWeight").value())
    ctx.field("DicomRescale2.outputSlope").value=1/(PatientWeight*1000/actualActivity)

def settings():
  ctx.field("wheel_1").value=100
  ctx.field("wheel").value=100
  ctx.field("controlArea.alphaFactor").value=0.5
  ctx.field("controlArea.filename").value="RTSTRUCT"
  ctx.field("controlArea.RegOn").value=False
  ctx.field("controlArea.ContourOn").value=False
  ctx.field("controlArea.drawSize").value=20
  ctx.field("controlArea.DelMethod").value="Arrow"
  ctx.field("controlArea.IsoMode").value="Mode1"
  ctx.field("controlArea.ActiveScreen").value="Screen1"
  ctx.field("controlArea.DelMethod").value="Arrow"
  settingsRef()
  settingsOverlay()
  LUTAdapt()
  
def attached():
  setupFrontier()
  setFrontierIsProcessing(True)
  connectRenderersToLayout()
  loadImageDataSetFromDirectory()
  settings()
  setFrontierIsProcessing(False)

def finalize():
  pass

def LUTAdapt():
  min_range = ctx.field("View2DExtensions2.lut.center").value-0.5*ctx.field("View2DExtensions2.lut.width").value
  max_range = ctx.field("View2DExtensions2.lut.center").value+0.5*ctx.field("View2DExtensions2.lut.width").value
  min_image = ctx.field("ImageStatistics2.totalMinVal").value
  max_image = ctx.field("ImageStatistics2.totalMaxVal").value
  
  if (min_image!=None and max_image!=None):
    stuff_in_string = "[ %f 0 0 0, %f 0 0 0, %f 0 0 1, %f 1 0 0, %f 1 1 0, %f 1 1 1, %f 1 1 1 ]" % (min_image,min_range+0*(max_range-min_range),min_range+0.25*(max_range-min_range),min_range+0.5*(max_range-min_range),min_range+0.75*(max_range-min_range),max_range,max_image)
    ctx.field("SoLUTEditor.colorPoints").setStringValue(stuff_in_string)

def WheelAdapt():
  if ctx.field("SoMouseGrabber.maskValid").value:
    ctx.field("View2DExtensions1.slicerOn").value=False
    ctx.field("View2DExtensions2.slicerOn").value=False

    ctx.field("wheel").value=ctx.field("SoMouseGrabber.wheel").value
    ctx.field("SoOrthoView2D1.sliceZoom").value=ctx.field("SoOrthoView2D1.sliceZoom").value+ctx.field("wheel").value-ctx.field("wheel_1").value
    ctx.field("wheel_1").value=ctx.field("wheel").value

  if ctx.field("SoMouseGrabber.maskValid").value==0:
    ctx.field("View2DExtensions1.slicerOn").value=True
    ctx.field("View2DExtensions2.slicerOn").value=True

    ctx.field("wheel").value=ctx.field("SoMouseGrabber.wheel").value
    ctx.field("wheel_1").value=ctx.field("SoMouseGrabber.wheel").value

def RegOn():
  if ctx.field("controlArea.RegOn").value==True:
    ctx.field("SoView2DRigidRegistrationEditor.drawingOn").value=True
    ctx.field("SoView2DRigidRegistrationEditor.editingOn").value=True
  elif ctx.field("controlArea.RegOn").value==False:  
    ctx.field("SoView2DRigidRegistrationEditor.drawingOn").value=False
    ctx.field("SoView2DRigidRegistrationEditor.editingOn").value=False

def ContourOn():
  print("ContourOn")
  if ctx.field("controlArea.ContourOn").value==True:
    DelMethodAdapt()
  elif ctx.field("controlArea.ContourOn").value==False:  
    ctx.field("controlArea.DelMethod").value="Arrow"

def DelMethodAdapt():
  print("DelMethodAdapt")
  ctx.field("SoView2DDrawVoxels3D1.editingOn").value=True

  if ctx.field("controlArea.DelMethod").value=="Arrow":
    ctx.field("SoCSOSplineEditor.allowCreation").value=False
    ctx.field("SoView2DRectangle.editingOn").value=False
    ctx.field("SoView2DRectangle.drawingOn").value=False
    #ctx.field("CSOIsoGenerator.updateMode").value="Off"
    #ctx.field("CSOIsoGenerator1.updateMode").value="Off"
    ctx.field("SoBypass3.bypass").value=False
    ctx.field("GetVoxelValue1.updateMode").value="AutoClear"
    ctx.field("FieldBypass.noBypass").value=True
    ctx.field("SoView2DDrawVoxels3D1.editingOn").value=False
    
  if ctx.field("controlArea.DelMethod").value=="Spline":
    ctx.field("SoCSOSplineEditor.allowCreation").value=True
    ctx.field("SoView2DRectangle.editingOn").value=False
    ctx.field("SoView2DRectangle.drawingOn").value=False
    #ctx.field("CSOIsoGenerator.updateMode").value="Off"
    #ctx.field("CSOIsoGenerator1.updateMode").value="Off"
    ctx.field("SoBypass3.bypass").value=False
    ctx.field("GetVoxelValue1.updateMode").value="AutoClear"
    ctx.field("FieldBypass.noBypass").value=True
    ctx.field("SoView2DDrawVoxels3D1.editingOn").value=False
  
  if ctx.field("controlArea.DelMethod").value=="Iso":
    
    ctx.field("SoCSOSplineEditor.allowCreation").value=False
    ctx.field("SoView2DRectangle.editingOn").value=False
    ctx.field("SoView2DRectangle.drawingOn").value=False
    #ctx.field("CSOIsoGenerator.updateMode").value="Off"
    #ctx.field("CSOIsoGenerator1.updateMode").value="Off"
    ctx.field("SoBypass3.bypass").value=False
    ctx.field("GetVoxelValue1.updateMode").value="AutoClear"
    ctx.field("FieldBypass.noBypass").value=True
    ctx.field("SoView2DDrawVoxels3D1.editingOn").value=False
    
  
  #if ctx.field("controlArea.DelMethod").value=="IsoRect":
  #  createItem()
  #  ctx.field("SoCSOSplineEditor.allowCreation").value=False
  #  ctx.field("SoView2DRectangle.editingOn").value=True
  #  ctx.field("SoView2DRectangle.drawingOn").value=True
  #  #ctx.field("CSOIsoGenerator.updateMode").value="Off"
  #  #ctx.field("CSOIsoGenerator1.updateMode").value="Off"
  #  ctx.field("SoBypass3.bypass").value=False
  #  ctx.field("GetVoxelValue.updateMode").value="AutoClear"
  #  ctx.field("SoView2DDrawVoxels3D1.editingOn").value=False

  if ctx.field("controlArea.DelMethod").value=="Draw": 
    ctx.field("SoCSOSplineEditor.allowCreation").value=False
    ctx.field("SoView2DRectangle.editingOn").value=False
    ctx.field("SoView2DRectangle.drawingOn").value=False
    ##ctx.field("CSOIsoGenerator.updateMode").value="Off"
    #ctx.field("DrawVoxels3D.copyInputImage").touch()
    #ctx.field("SoView2DPosition1.editingOn").value=True
    ##ctx.field("CSOIsoGenerator1.updateMode").value="Off"
    #ctx.field("DrawVoxels3D.voxelWriteValue").value=1
    #ctx.field("SoBypass.bypass").value=True
    #ctx.field("GetVoxelValue.updateMode").value="AutoClear"
    
    
    
    ctx.field("CSOConvertToImage2.apply").touch()
    ctx.field("DrawVoxels3D1.copyInputImage").touch()
    ctx.field("SoView2DPosition3.editingOn").value=True
    ctx.field("DrawVoxels3D1.voxelWriteValue").value=1
    ctx.field("SoBypass3.bypass").value=True
    ctx.field("GetVoxelValue1.updateMode").value="AutoUpdate"
    ctx.field("FieldBypass.noBypass").value=True
    ctx.field("SoView2DDrawVoxels3D1.editingOn").value=True
  
  if ctx.field("controlArea.DelMethod").value=="Erase":
    ctx.field("SoCSOSplineEditor.allowCreation").value=False
    ctx.field("SoView2DRectangle.editingOn").value=False
    ctx.field("SoView2DRectangle.drawingOn").value=False
    ##ctx.field("CSOIsoGenerator.updateMode").value="Off"
    #ctx.field("DrawVoxels3D.copyInputImage").touch()
    #ctx.field("SoView2DPosition1.editingOn").value=True
    ##ctx.field("CSOIsoGenerator1.updateMode").value="Off"
    #ctx.field("DrawVoxels3D.voxelWriteValue").value=0
    #ctx.field("SoBypass3.bypass").value=True
    #ctx.field("GetVoxelValue.updateMode").value="AutoClear"
    
    ctx.field("CSOConvertToImage2.apply").touch()
    ctx.field("DrawVoxels3D1.copyInputImage").touch()
    ctx.field("SoView2DPosition3.editingOn").value=True
    ctx.field("DrawVoxels3D1.voxelWriteValue").value=-1
    ctx.field("SoBypass3.bypass").value=True
    ctx.field("GetVoxelValue1.updateMode").value="AutoUpdate"
    ctx.field("FieldBypass.noBypass").value=True
    ctx.field("SoView2DDrawVoxels3D1.editingOn").value=True
    
  if ctx.field("controlArea.DelMethod").value=="DrawErase":
    ctx.field("SoCSOSplineEditor.allowCreation").value=False
    ctx.field("SoView2DRectangle.editingOn").value=False
    ctx.field("SoView2DRectangle.drawingOn").value=False
    ##ctx.field("CSOIsoGenerator.updateMode").value="Off"
    #ctx.field("DrawVoxels3D.copyInputImage").touch()
    #ctx.field("SoView2DPosition1.editingOn").value=False
    ##ctx.field("CSOIsoGenerator1.updateMode").value="Off"
    #ctx.field("SoBypass3.bypass").value=True
    #ctx.field("GetVoxelValue.updateMode").value="AutoUpdate"
    ctx.field("CSOConvertToImage2.apply").touch()
    ctx.field("DrawVoxels3D1.copyInputImage").touch()
    ctx.field("SoView2DPosition3.editingOn").value=True
    ctx.field("SoBypass3.bypass").value=True
    ctx.field("GetVoxelValue1.updateMode").value="AutoUpdate"
    ctx.field("FieldBypass.noBypass").value=False
    ctx.field("SoView2DDrawVoxels3D1.editingOn").value=True


#def RectAdapt():
  #if ctx.field("controlArea.DelMethod").value=="IsoRect":
  #  if ctx.field("SoMouseGrabber1.maskValid").value==True:
  #    ctx.field("ImageSwitch1.currentInput").value=0
  #    ctx.field("SoBypass1.bypass").value=True
  #    ctx.field("SoBypass2.bypass").value=False
  #  if ctx.field("SoMouseGrabber2.maskValid").value==True:
  #    ctx.field("ImageSwitch1.currentInput").value=1
  #    ctx.field("SoBypass1.bypass").value=False
  #    ctx.field("SoBypass2.bypass").value=True

def IsoModeAdapt():
  print("IsoModeAdapt")
  print(ctx.field("controlArea.IsoMode").value)
  if ctx.field("controlArea.IsoMode").value=="Mode1": #Whole image   
    ctx.field("SoView2DRectangle.editingOn").value=False
    ctx.field("SoView2DRectangle.drawingOn").value=False
    ctx.field("ImageSwitch1.currentInput").value=0
  if ctx.field("controlArea.IsoMode").value=="Mode2": #Rectangle
    ctx.field("SoView2DRectangle.editingOn").value=True
    ctx.field("SoView2DRectangle.drawingOn").value=True
    ctx.field("ImageSwitch1.currentInput").value=1
  if ctx.field("controlArea.IsoMode").value=="Mode3": #Delineation
    ctx.field("CSOImageStatisticsOverTime.update").touch()
    ctx.field("SoView2DRectangle.editingOn").value=False
    ctx.field("SoView2DRectangle.drawingOn").value=False
    ctx.field("ImageSwitch1.currentInput").value=2

def PercAdapt():  
  print("PercAdapt")
  ctx.field("IntervalThreshold.clampThresholds").touch()
  PercLB_temp=np.round((ctx.field("IntervalThreshold.threshMin").value-ctx.field("IntervalThreshold.changedMin").value)/np.abs(np.diff(np.array((ctx.field("IntervalThreshold.changedMax").value,ctx.field("IntervalThreshold.changedMin").value))))*100)
  PercUB_temp=np.round((ctx.field("IntervalThreshold.threshMax").value-ctx.field("IntervalThreshold.changedMin").value)/np.abs(np.diff(np.array((ctx.field("IntervalThreshold.changedMax").value,ctx.field("IntervalThreshold.changedMin").value))))*100)

  if ctx.field("controlArea.PercLB").value!=PercLB_temp:
    ctx.field("controlArea.PercLB").value=PercLB_temp
  if ctx.field("controlArea.PercUB").value!=PercUB_temp:
    ctx.field("controlArea.PercUB").value=PercUB_temp
  
def GVAdapt():
  print("GVAdapt")
  ctx.field("IntervalThreshold.clampThresholds").touch()
  threshMin_temp=ctx.field("controlArea.PercLB").value*np.abs(np.diff(np.array((ctx.field("IntervalThreshold.changedMax").value,ctx.field("IntervalThreshold.changedMin").value))))/100+ctx.field("IntervalThreshold.changedMin").value
  threshMax_temp=ctx.field("controlArea.PercUB").value*np.abs(np.diff(np.array((ctx.field("IntervalThreshold.changedMax").value,ctx.field("IntervalThreshold.changedMin").value))))/100+ctx.field("IntervalThreshold.changedMin").value

  if ctx.field("IntervalThreshold.threshMin").value!=threshMin_temp:
    ctx.field("IntervalThreshold.threshMin").value=threshMin_temp
  if ctx.field("IntervalThreshold.threshMax").value!=threshMax_temp:
    ctx.field("IntervalThreshold.threshMax").value=threshMax_temp

def CalculateIsoRect():
  print("CalculateIsoRect")
  if ctx.field("controlArea.IsoMode").value=="Mode3":
    ctx.field("CSOConvertToImage5.apply").touch()
  createItem()
  ctx.field("Bypass2.noBypass").value=False
  ctx.field("CSOIsoGenerator.apply").touch()
  ctx.field("Bypass2.noBypass").value=True

def MenuAdapt():
  if ctx.field("SoMenuItem1.selected").value==True:
    ctx.field("SoOrthoView2D1.layoutMode").value="LAYOUT_AXIAL"
  if ctx.field("SoMenuItem2.selected").value==True:
    ctx.field("SoOrthoView2D1.layoutMode").value="LAYOUT_SAGITTAL"
  if ctx.field("SoMenuItem3.selected").value==True:
    ctx.field("SoOrthoView2D1.layoutMode").value="LAYOUT_CORONAL"
  if ctx.field("SoMenuItem4.selected").value==True:
    ctx.field("SoOrthoView2D1.layoutMode").value="LAYOUT_ROW_EQUAL"
  if ctx.field("SoMenuItem5.selected").value==True:
    ctx.field("SoOrthoView2D2.layoutMode").value="LAYOUT_AXIAL"
  if ctx.field("SoMenuItem6.selected").value==True:
    ctx.field("SoOrthoView2D2.layoutMode").value="LAYOUT_SAGITTAL"
  if ctx.field("SoMenuItem7.selected").value==True:
    ctx.field("SoOrthoView2D2.layoutMode").value="LAYOUT_CORONAL"
  if ctx.field("SoMenuItem8.selected").value==True:
    ctx.field("SoOrthoView2D2.layoutMode").value="LAYOUT_ROW_EQUAL"
  if ctx.field("SoMenuItem10.selected").value==True:
    ctx.field("SoView2DPosition.drawingOn").value=True
  if ctx.field("SoMenuItem10.selected").value==False:
    ctx.field("SoView2DPosition.drawingOn").value=False
  

def generateIsoAdapt():
  ctx.field("CSOIsoGenerator3.apply").touch()
  
def alphaFactorAdapt():
  ctx.field("SoLUTEditor.alphaFactor").value=ctx.field("controlArea.alphaFactor").value
  
def drawSizeAdapt():
  ctx.field("DrawVoxels3D1.drawSize").value=ctx.field("controlArea.drawSize").value

def createItem():
  #print("createItem")
  ctx.field("DrawVoxels3D1.clear").touch()
  ctx.field("CSOManager.groupCreateNew").touch()
  ctx.field("CSOManager.groupSingleLabel").value="Untitled"
  ctx.field("CSOManager.groupSingleUsePathPointStyle").value=True
  ctx.field("CSOManager.groupSingleUsePathPointWidth").value=True
  ctx.field("CSOManager.groupSinglePathPointWidth").value=1#ctx.field("csoSinglePathPointWidth").value
  ctx.field("CSOManager.groupSingleUsePathPointColor").value=True
  ctx.field("CSOManager.groupSinglePathPointColor").value=ctx.field("StylePalette.currentColor").value
  
def creatingItem():
  print("creatingItem")

  if ctx.field("controlArea.DelMethod").value!="Arrow" and (ctx.field("SoView2DCSOExtensibleEditor.isCreatingNewCSO").value==False or ctx.field("SoView2DRectangle.maskValid").value==False or ctx.field("SoView2DPosition1.maskValid").value==True): # and ctx.field("controlArea.DelMethod").value=="Draw")
    if not ctx.field("CSOManager.groupSelectedItems").value:
      createItem()
    ctx.field("CSOManager.addCSOtoGroup").touch()
    
  #if ctx.field("controlArea.DelMethod").value in {"Draw", "Erase", "DrawErase"}:
  #  if ctx.field("SoView2DPosition1.maskValid").value==True:
  #    if ctx.field("controlArea.DelMethod").value=="DrawErase":
  #      if ctx.field("CalculateVoxelSum.outVoxelSum").value==0:
  #        ctx.field("DrawVoxels3D.voxelWriteValue").value=1
  #      else:
  #        ctx.field("DrawVoxels3D.voxelWriteValue").value=ctx.field("GetVoxelValue.storedValue").value
  #      ctx.field("SoView2DPosition1.editingOn").value=True
  #    ctx.field("DrawVoxels3D.copyInputImage").touch()
  #    ctx.field("CSOIsoGenerator1.updateMode").value="AutoUpdate"  
  #  else:
  #    ctx.field("CSOIsoGenerator1.updateMode").value="Off"
  #    if ctx.field("controlArea.DelMethod").value=="DrawErase":
  #      ctx.field("SoView2DPosition1.editingOn").value=False

  if ctx.field("controlArea.DelMethod").value in {"Draw", "Erase", "DrawErase"}:
    if ctx.field("SoView2DPosition3.maskValid").value==True:
      ctx.field("CSOConvertToImage2.apply").touch()
      if ctx.field("controlArea.DelMethod").value=="DrawErase":      
        if ctx.field("ImageStatistics3.totalMaxVal").value==0: #ctx.field("CSOConvertToImage2.output0").image().maxVoxelValue()==0:
          ctx.field("DrawVoxels3D1.voxelWriteValue").value=1
        else:
          ctx.field("DrawVoxels3D1.voxelWriteValue").value=ctx.field("GetVoxelValue1.storedValue").value
      ctx.field("DrawVoxels3D1.copyInputImage").touch()
    else:
      if ctx.field("controlArea.DelMethod").value=="DrawErase":
        ctx.field("DrawVoxels3D1.voxelWriteValue").value=0
      ctx.field("CSOIsoGenerator4.apply").touch()

  #if (ctx.field("SoView2DCSOExtensibleEditor.isCreatingNewCSO").value==False and ctx.field("controlArea.DelMethod").value=="Iso"):
  #  print("CSOImageStatisticsOverTime update")
  #  ctx.field("CSOImageStatisticsOverTime.update").touch()


def groupDisplayTreeAdapt():
  ctx.field("controlArea.groupDisplayTree").value=ctx.field("CSOManager.groupDisplayTree").value

def numGroupsAdapt():
  ctx.field("controlArea.numGroups").value=ctx.field("CSOManager.numGroups").value

def ignoreGroupListViewSelectionChangedAdapt():
  ctx.field("controlArea.ignoreGroupListViewSelectionChanged").value=ctx.field("CSOManager.ignoreGroupListViewSelectionChanged").value

def numSelectedGroupsAdapt():
  ctx.field("controlArea.numSelectedGroups").value=ctx.field("CSOManager.numSelectedGroups").value
  
def ignoreGroupSelectionChangedAdapt():
  ctx.field("controlArea.ignoreGroupSelectionChanged").value=ctx.field("CSOManager.ignoreGroupSelectionChanged").value
  
def groupSelectedItemsAdapt():
  ctx.field("controlArea.groupSelectedItems").value=ctx.field("CSOManager.groupSelectedItems").value  
  
def csoTabSelectedAdapt():
  ctx.field("controlArea.csoTabSelected").value=ctx.field("CSOManager.csoTabSelected").value  
  
def groupTabSelectedAdapt():
  ctx.field("controlArea.groupTabSelected").value=ctx.field("CSOManager.groupTabSelected").value  
  
def selectionTabSelectedAdapt():
  ctx.field("controlArea.selectionTabSelected").value=ctx.field("CSOManager.selectionTabSelected").value  
  
def notificationTabSelectedAdapt():
  ctx.field("controlArea.notificationTabSelected").value=ctx.field("CSOManager.notificationTabSelected").value  
  
def defaultTabSelectedAdapt():
  ctx.field("controlArea.defaultTabSelected").value=ctx.field("CSOManager.defaultTabSelected").value    
  


def groupDisplayTreeAdapt1():
  ctx.field("CSOManager.groupDisplayTree").value=ctx.field("controlArea.groupDisplayTree").value

def numGroupsAdapt1():
  ctx.field("CSOManager.numGroups").value=ctx.field("controlArea.numGroups").value

def ignoreGroupListViewSelectionChangedAdapt1():
  ctx.field("CSOManager.ignoreGroupListViewSelectionChanged").value=ctx.field("controlArea.ignoreGroupListViewSelectionChanged").value

def numSelectedGroupsAdapt1():
  ctx.field("CSOManager.numSelectedGroups").value=ctx.field("controlArea.numSelectedGroups").value
  
def ignoreGroupSelectionChangedAdapt1():
  ctx.field("CSOManager.ignoreGroupSelectionChanged").value=ctx.field("controlArea.ignoreGroupSelectionChanged").value
  
def groupSelectedItemsAdapt1():
  ctx.field("CSOManager.groupSelectedItems").value=ctx.field("controlArea.groupSelectedItems").value  
  
def csoTabSelectedAdapt1():
  ctx.field("CSOManager.csoTabSelected").value=ctx.field("controlArea.csoTabSelected").value  
  
def groupTabSelectedAdapt1():
  ctx.field("CSOManager.groupTabSelected").value=ctx.field("controlArea.groupTabSelected").value  
  
def selectionTabSelectedAdapt1():
  ctx.field("CSOManager.selectionTabSelected").value=ctx.field("controlArea.selectionTabSelected").value  
  
def notificationTabSelectedAdapt1():
  ctx.field("CSOManager.notificationTabSelected").value=ctx.field("controlArea.notificationTabSelected").value  
  
def defaultTabSelectedAdapt1():
  ctx.field("CSOManager.defaultTabSelected").value=ctx.field("controlArea.defaultTabSelected").value  
 
def ActiveScreenAdapt():
  print("ActiveScreenAdapt")

  if ctx.field("controlArea.ActiveScreen").value=="Screen1":
    ctx.field("ImageSwitch.currentInput").value=0
  else:
    ctx.field("ImageSwitch.currentInput").value=1
  
def patientBrowser():
    ctx.field("FrontierPatientBrowser.openDialog").touch()  
    
#def fillOutFolder():
#  inDir = _frontier.getIncomingDicomDirectory()
#  outDir = _frontier.getOutgoingDicomDirectory()
#  if os.path.exists(outDir):
#      shutil.rmtree(outDir)
#      time.sleep(0.5)
#  shutil.copytree(inDir, outDir)    


def ImageSaveAdapt():
  outDir = _frontier.getOutgoingDicomDirectory()
  if os.path.exists(outDir):
      shutil.rmtree(outDir)
      time.sleep(0.5)
  os.mkdir(outDir)
  
  ctx.field("CreateRTStruct.update").touch()
  filename=ctx.field("controlArea.filename").value

  file=outDir +"/"+ filename
  print(file)
  ctx.field("RTObjectSave.filename").value=file
  print(ctx.field("RTObjectSave.filename").value)
  ctx.field("RTObjectSave.startTaskSynchronous").touch()
  
  _frontier.selectResultFolder()
  _frontier.sendResultFile(file, os.path.basename(file))
    
def ImportNifti():
  outDir = _frontier.getOutgoingDicomDirectory()
  if os.path.exists(outDir):
      shutil.rmtree(outDir)
      time.sleep(0.5)
  os.mkdir(outDir)
  #_frontier.storeFileFromClient(outDir, storeFileResultReceived, "Select a file")
  _frontier.storeMultipleFilesFromClient(outDir, storeFileResultReceived, "Select multiple files")

def storeFileResultReceived(resultFilenames):
  ctx.field("CSOIsoGenerator2.updateMode").value="AutoUpdate"
  for file in resultFilenames:
    print(file)
    createItem()
    ctx.field("CSOManager.groupSingleLabel").value=os.path.basename(file)
    ctx.field("itkImageFileReader.unresolvedFileName").setStringValue(file)
  ctx.field("CSOIsoGenerator2.updateMode").value="Off"
      
     

def Radiomics():
  ctx.field("CSOConvertToImage1.apply").touch()
  image = ctx.field("CSOConvertToImage1.output0").image()
  
  SV=ctx.field("CSOConvertToImage1.startVoxelBoundingBox").value
  EV=ctx.field("CSOConvertToImage1.endVoxelBoundingBox").value

  if image:
    mask=sitk.GetImageFromArray(np.squeeze(image.getTile((SV[0]-1,SV[1]-1,SV[2]-1,0,0,0), (EV[0]-SV[0]+2,EV[1]-SV[1]+2,EV[2]-SV[2]+2,1,1,1))))
    mask.SetSpacing(image.voxelSize())
  
  image = ctx.field("ImageSwitch.output0").image()
  if image:
    I=sitk.GetImageFromArray(np.squeeze(image.getTile((SV[0]-1,SV[1]-1,SV[2]-1,0,0,0), (EV[0]-SV[0]+2,EV[1]-SV[1]+2,EV[2]-SV[2]+2,1,1,1))))
    I.SetSpacing(image.voxelSize())
  
  settings = {}
  settings['binWidth'] = ctx.field("controlArea.binWidth").value
  settings['resampledPixelSpacing'] = ctx.field("controlArea.resampledPixelSpacing").value  # [3,3,3] is an example for defining resampling (voxels with size 3x3x3mm)
  settings['interpolator'] = sitk.sitkLinear #sitkBSpline
  
  I, mask = imageoperations.resampleImage(I, mask, **settings)
  bb, correctedMask = imageoperations.checkMask(I, mask)
  if correctedMask is not None:
    mask = correctedMask
  
  global final_table
  final_table = pd.DataFrame()

  ImageTypes = np.array(['Original','Wavelet'])
  feature_family = np.array(['shape','firstorder','glcm','glrlm','glszm','ngtdm'])
  merging = np.array([None,'no_weighting'])
  
  for h in ImageTypes[np.array([ctx.field("controlArea.RadiomicsOriginal").value,ctx.field("controlArea.RadiomicsWavelet").value])]:
        for i in feature_family[np.array([ctx.field("controlArea.RadiomicsShape").value,ctx.field("controlArea.RadiomicsFirstOrder").value,ctx.field("controlArea.RadiomicsGLCM").value,ctx.field("controlArea.RadiomicsGLRLM").value,ctx.field("controlArea.RadiomicsGLSZM").value,ctx.field("controlArea.RadiomicsNGTDM").value])]:
          k=0
          for j in merging:
              if not (i not in ['glcm','glrlm'] and k>0):
                settings['weightingNorm'] = j
                
                extractor = featureextractor.RadiomicsFeatureExtractor(**settings)
                extractor.disableAllFeatures()
                extractor.enableFeatureClassByName(i)
                extractor.disableAllImageTypes()
                extractor.enableImageTypeByName(h)
                
                featureVector = {}
                featureVector.update(extractor.computeShape(I, mask, bb))
                
                imageGenerators = []
                for imageType, customKwargs in six.iteritems(extractor.enabledImagetypes):
                  args = extractor.settings.copy()
                  args.update(customKwargs)
                  imageGenerators = chain(imageGenerators, getattr(imageoperations, 'get%sImage' % imageType)(I, mask, **args))
                
                for inputImage, imageTypeName, inputKwargs in imageGenerators:
                  featureVector.update(extractor.computeFeatures(I, mask, imageTypeName, **inputKwargs))

                table = pd.DataFrame(featureVector.items(), columns=['featureName', 'featureValue'])  
                
                if i in ['glcm','glrlm']:
                    if j==None:
                        table['featureName'] = table['featureName'] + '_avg'
                    else:
                        table['featureName'] = table['featureName'] + '_comb'
                
                final_table = pd.concat([final_table, table])
                k+=1

  final_table.index=np.arange(0,final_table.shape[0])

  #np_final_table = np.asarray(final_table)
  a=np.arange(0,len(np.asarray(final_table)))[:,np.newaxis]
  b=np.asarray(final_table)
  np_final_table=np.concatenate([a,b],axis=1)
  ctx.field("controlArea.RadiomicsString").value = '@'.join('%i,%s,%0.2f' %(x,y,z) for x,y,z in np_final_table)
    
def voxelBased():
  ctx.field("CSOConvertToImage1.apply").touch()
  image = ctx.field("CSOConvertToImage1.output0").image()
  
  SV=np.asarray(ctx.field("CSOConvertToImage1.startVoxelBoundingBox").value,dtype='int32')
  EV=np.asarray(ctx.field("CSOConvertToImage1.endVoxelBoundingBox").value,dtype='int32')
  
  if image:
    mask=sitk.GetImageFromArray(np.squeeze(image.getTile((SV[0]-1,SV[1]-1,SV[2]-1,0,0,0), (EV[0]-SV[0]+2,EV[1]-SV[1]+2,EV[2]-SV[2]+2,1,1,1))))
    mask.SetSpacing(image.voxelSize())
  
  image = ctx.field("Bypass1.output0").image()
  if image:
    I=sitk.GetImageFromArray(np.squeeze(image.getTile((SV[0]-1,SV[1]-1,SV[2]-1,0,0,0), (EV[0]-SV[0]+2,EV[1]-SV[1]+2,EV[2]-SV[2]+2,1,1,1))))
    I.SetSpacing(image.voxelSize())
  
  settings = {}
  settings['binWidth'] = 0.5
  settings['resampledPixelSpacing'] = None#[2,2,2]  # [3,3,3] is an example for defining resampling (voxels with size 3x3x3mm)
  settings['interpolator'] = sitk.sitkLinear #sitkBSpline

  bb, correctedMask = imageoperations.checkMask(I, mask)
  if correctedMask is not None:
    mask = correctedMask

  settings['additionalInfo'] = False
  settings['voxelBased'] = True
  extractor = featureextractor.RadiomicsFeatureExtractor(**settings)
  extractor.disableAllFeatures()
  extractor.enableFeaturesByName(glcm=['MaximumProbability'])
  result = extractor.computeFeatures(I, mask, 'glcm', **settings)
  array = sitk.GetArrayFromImage(result['glcm_glcm_MaximumProbability'])
  array=array[np.newaxis,np.newaxis,np.newaxis,:,:,:]
  array1 = np.zeros(np.flip(image.imageExtent()))
  array1[0:1,0:1,0:1,SV[2]-1:EV[2]+1,SV[1]-1:EV[1]+1,SV[0]-1:EV[0]+1]=array
  ctx.module("PythonImage2").call("getInterface").setImage(array1, voxelToWorldMatrix = image.voxelToWorldMatrix(), voxelSize = image.voxelSize())



def RadiomicSaveAdapt():
  outDir = _frontier.getOutgoingDicomDirectory()
  if os.path.exists(outDir):
      shutil.rmtree(outDir)
      time.sleep(0.5)
  os.mkdir(outDir)
  
  file=outDir +"/Radiomic_features.csv"
  final_table.to_csv(file,header=False,columns=['featureName', 'featureValue'],index=False)
  _frontier.selectResultFolder()
  _frontier.sendResultFile(file, os.path.basename(file))
    
