# -*- coding: utf-8 -*-
"""
/***************************************************************************
 fdtm_plugin
                                 A QGIS plugin
 testing hwbs
                             -------------------
        begin                : 2017-05-11
        git sha              : $Format:%H$
        copyright            : (C) 2017 by arma informatica snc
        email                : info@armainformatica.it
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

import os
import json
import csv
import sys
import tempfile
import zipfile
import shutil
import xml.etree.ElementTree as ET

from qgis.core import QGis, QgsProject, QgsExpressionContextUtils, QgsCoordinateReferenceSystem, QgsMapLayerRegistry, QgsVectorLayer, QgsMapLayer, QgsRelation, QgsLayerTreeNode
from qgis.gui import QgsProjectionSelectionWidget, QgsMapLayerProxyModel
from qgis.core import QgsComposition, QgsComposerMap

from PyQt4.QtGui import QDoubleValidator, QFileDialog, QLineEdit, QTableWidgetItem, QTableWidgetSelectionRange,  QItemSelectionModel
from PyQt4.QtCore import Qt, pyqtSignal, QObject, QFileInfo
from PyQt4.QtXml import QDomDocument

from fdtm_utils import create_EAp_layer, create_EPl_layer, create_EPp_layer, create_WDS_layer, create_WR_layer, checkForTemplateFields, create_DSV_layer, writeTIFF, writeSHP
from fdtm_definitions import RC_TYPES_TABLE
from fdtm_dataset import fdtmDatasetWrapper


from PyQt4 import QtGui, uic

FORM_CLASS_EA, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'fdtm_EA_dialog.ui'))

FORM_CLASS_EP, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'fdtm_EP_dialog.ui'))

FORM_CLASS_info, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'fdtm_info_dialog.ui'))

FORM_CLASS_WR, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'fdtm_WR_dialog.ui'))

FORM_CLASS_WDS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'fdtm_WDS_dialog.ui'))

FORM_CLASS_settings, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'fdtm_settings_dialog.ui'))

FORM_CLASS_about, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'fdtm_about_dialog.ui'))

FORM_CLASS_print, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'fdtm_print_dialog.ui'))

FORM_CLASS_summary, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'fdtm_summary_dialog.ui'))


class fdtmEADialog(QtGui.QDialog, FORM_CLASS_EA):

    def __init__(self, parent=None):
        """Constructor."""
        super(fdtmEADialog, self).__init__(parent)
        self.setupUi(self)


class fdtmEPDialog(QtGui.QDialog, FORM_CLASS_EP):

    def __init__(self, parent=None):
        """Constructor."""
        super(fdtmEPDialog, self).__init__(parent)
        self.setupUi(self)


class fdtmWRDialog(QtGui.QDialog, FORM_CLASS_WR):

    def __init__(self, parent=None):
        """Constructor."""
        super(fdtmWRDialog, self).__init__(parent)
        self.setupUi(self)


class fdtmWDSDialog(QtGui.QDialog, FORM_CLASS_WDS):

    def __init__(self, parent=None):
        """Constructor."""
        super(fdtmWDSDialog, self).__init__(parent)
        self.setupUi(self)


class fdtmInfoDialog(QtGui.QDialog, FORM_CLASS_info):

    def __init__(self, parent=None):
        """Constructor."""
        super(fdtmInfoDialog, self).__init__(parent)
        self.setupUi(self)

class fdtmPrintDialog(QtGui.QDialog, FORM_CLASS_print):

    def __init__(self, parent=None):
        """Constructor."""
        super(fdtmPrintDialog, self).__init__(parent)
        self.setupUi(self)

class optionalLayerControl(QObject):

    layerChanged = pyqtSignal(object)

    def __init__(self, module, checkbox, layerCombo):
        super(optionalLayerControl, self).__init__()
        self.checkbox = checkbox
        self.layerCombo = layerCombo
        self.layerCombo.layerChanged.connect(self.emitLayerChanged)
        self.fakeLayerCombo = getattr(module,layerCombo.objectName()+'Fake')
        self.fakeLayerCombo.setMinimumSize(self.layerCombo.minimumSize())
        self.fakeLayerCombo.setMaximumSize(self.layerCombo.maximumSize())
        self.fakeLayerCombo.setSizePolicy(self.layerCombo.sizePolicy())
        try:
            self.type = self.layerCombo.currentLayer().geometryType()
        except:
            self.type = QGis.Polygon
        self.module = module
        if self.type == QGis.Point:
            uri = "Point?crs=epsg:3857"
        elif self.type == QGis.Line:
            uri = "LineString?crs=epsg:3857"
        elif self.type == QGis.Polygon:
            uri = "Polygon?crs=epsg:3857"
        self.mockLayer = QgsVectorLayer(uri,'mock optional layer', 'memory')
        self.mockLayer.MOCKLAYER = True
        self.checkbox.stateChanged.connect(self.optionStateChanged)
        self.checkbox.setChecked(False)

    def emitLayerChanged(self,layer):
        self.layerChanged.emit(layer)

    def isChecked(self):
        return self.checkbox.isChecked()

    def optionStateChanged(self,state):
        if state == Qt.Checked:
            self.fakeLayerCombo.hide()
            self.layerCombo.show()
            self.layerChanged.emit(self.layerCombo.currentLayer())
        else:
            self.layerCombo.hide()
            self.fakeLayerCombo.show()
            self.layerChanged.emit(None)

    def setCheckState(self,state):
        self.checkbox.setChecked(state)

    def checkState(self):
        return self.checkbox.checkState()

    def haveCrs(self,crsID):
        if self.checkbox.isChecked():
            return self.layerCombo.currentLayer().crs().authid() == crsID
        else:
            return True

    def currentLayer(self):
        if self.checkbox.isChecked():
            return self.layerCombo.currentLayer()
        else:
            return self.mockLayer

    def currentLayerId(self):
        if self.checkbox.isChecked():
            return self.layerCombo.currentLayer().id()
        else:
            return ''

    def setLayer(self,layer):
        if layer:
            self.setCheckState(True)
            self.layerCombo.setLayer(layer)
        else:
            self.setCheckState(False)

class optionalDrainageLayerControl(optionalLayerControl):

    def __init__(self,module, checkbox, layerCombo):
        super(optionalDrainageLayerControl, self).__init__(module, checkbox, layerCombo)
        self.valve_layer = None

    def DSVLayer(self):
        return self.valve_layer

    def DSVLayerId(self):
        if self.valve_layer:
            return self.valve_layer.id()
        else:
            return None

    def setDSVLayer(self, layer):
        self.valve_layer = layer


class fdtmSettingsDialog(QtGui.QDialog, FORM_CLASS_settings):

    validated = pyqtSignal(bool)

    def __init__(self, module, parent=None ):
        """Constructor."""
        super(fdtmSettingsDialog, self).__init__(parent)
        self.iface = module.iface
        self.setupUi(self)
        self.DEMLayer.setFilters(QgsMapLayerProxyModel.RasterLayer)
        self.isValidated = None
        self.newProjectIsNotYetSaved = None
        self.buttonBox.accepted.connect(self.datasetValidation)
        self.exportProjectButton.clicked.connect(self.export_action)
        self.exportProjectButton.setEnabled(False)
        self.averagePrecipitation.setText('10')
        self.defaultRoadsWidth.setText('8')
        self.averagePrecipitation.setValidator(QDoubleValidator(0, 1000, 2, self.averagePrecipitation) )
        self.defaultRoadsWidth.setValidator(QDoubleValidator(0, 100, 2, self.defaultRoadsWidth) )
        self.defaultRoadsWidth.hide()
        self.defaultRoadsWidthLabel.hide()
        self.projectFolderPath.hide()
        self.projectFolderLabel.hide()
        #self.projection.setOptionVisible(QgsProjectionSelectionWidget.ProjectCrs,True)
        self.updateDataset = None
        self.averagePrecipitationChanged = None
        self.setNullProjectFiles()
        self.setOptionalSupportFiles()
        self.validated.connect(self.handleUpdateSignals)
        self.debugCheck.stateChanged.connect(self.toggleDebug)
        self.qgis_stdout = sys.stdout
        self.debugCheck.setChecked(False)
        self.debugCheck.hide()
        self.debugLabel.hide()
        self.allowValidationLabel.show()
        self.adjustSize()
        self.loadRCCombo()
        self.activate()

    def toggleDebug(self,state):
        if state == Qt.Checked:
            "checked"
            sys.stdout = self.qgis_stdout
        else:
            pass#sys.stdout = open(os.devnull, 'w')

    def loadRCCombo(self):
        #self.defaultRC.hide()
        #self.defaultRClabel.hide()
        for row in RC_TYPES_TABLE:
            self.defaultRC.addItem(row[1]+" (%s)" % row[0], float(row[0]))

    def setNullProjectFiles(self):
        self.EApLayer = None
        self.EPpLayer = None
        self.EPlLayer = None
        self.WRLayer = None
        self.WDSLayer = None
        self.WDSLayer = None
        self.DEMWrapper = None
        self.datasetWrapper = None
        self.projectDescription.setText('')
        self.projectFolderPath.setText('')

    def setOptionalSupportFiles(self):

        self.optionalRailwaysLayer = optionalLayerControl(self,self.railwaysCheckbox,self.railwaysLayer)
        self.optionalLanduseLayer = optionalLayerControl(self,self.landuseCheckbox,self.landuseLayer)
        self.optionalFloodAreaLayer = optionalLayerControl(self,self.floodAreaCheckbox,self.floodAreaLayer)
        self.optionalDrainageSystemLayer = optionalDrainageLayerControl(self,self.drainageSystemCheckbox,self.drainageSystemLayer)

    def handleUpdateSignals(self, validated):
        if validated:
            self.iface.messageBar().pushMessage("FDTM plugin", "The provided dataset is validated.",level=0, duration=3)
            self.reorderLegendInterface()
            self.applyStyles()
            self.applyRelations()
            self.applyScales()
            self.iface.mapCanvas().setDestinationCrs(self.projection.crs())
            self.exportProjectButton.setEnabled(True)
            try:
                self.connectUpdateSignals()
            except:
                pass
        else:
            self.exportProjectButton.setEnabled(False)
            try:
                self.disconnectUpdateSignals()
            except:
                pass

    def connectUpdateSignals(self):
        self.DEMLayer.layerChanged.connect(self.setUpdateDataset)
        self.buildingsLayer.layerChanged.connect(self.setUpdateDataset)
        self.roadsLayer.layerChanged.connect(self.setUpdateDataset)
        self.optionalRailwaysLayer.layerChanged.connect(self.setUpdateDataset)
        self.optionalLanduseLayer.layerChanged.connect(self.setUpdateDataset)
        self.optionalFloodAreaLayer.layerChanged.connect(self.setUpdateDataset)
        self.optionalDrainageSystemLayer.layerChanged.connect(self.setUpdateDataset)
        self.projectDescription.textChanged.connect(self.autoSaveSettings)
        self.averagePrecipitation.textChanged.connect(self.averagePrecipitationChangedAction)
        self.defaultRC.currentIndexChanged.connect(self.autoSaveSettings)
        
    def disconnectUpdateSignals(self):
        self.DEMLayer.layerChanged.disconnect(self.setUpdateDataset)
        self.buildingsLayer.layerChanged.disconnect(self.setUpdateDataset)
        self.roadsLayer.layerChanged.disconnect(self.setUpdateDataset)
        self.optionalRailwaysLayer.layerChanged.disconnect(self.setUpdateDataset)
        self.optionalLanduseLayer.layerChanged.disconnect(self.setUpdateDataset)
        self.optionalFloodAreaLayer.layerChanged.disconnect(self.setUpdateDataset)
        self.optionalDrainageSystemLayer.layerChanged.disconnect(self.setUpdateDataset)
        self.projectDescription.textChanged.disconnect(self.averagePrecipitationChangedAction)
        self.averagePrecipitation.textChanged.disconnect(self.autoSaveSettings)
        self.defaultRC.currentIndexChanged.disconnect(self.autoSaveSettings)

    def autoSaveSettings(self,idx=None):
        try:
            self.save_settings()
        except:
            self.disconnectUpdateSignals

    def averagePrecipitationChangedAction(self):
        self.averagePrecipitationChanged = True
        self.autoSaveSettings()

    def setUpdateDataset(self, layer):
        self.updateDataset = True

    def activate(self):
        self.iface.projectRead.connect(self.projectRead)
        QgsProject.instance().projectSaved.connect(self.projectSaved)
        self.iface.newProjectCreated.connect(self.newProjectCreated)

    def deactivate(self):
        self.iface.projectRead.disconnect(self.projectRead)
        QgsProject.instance().projectSaved.disconnect(self.projectSaved)
        self.iface.newProjectCreated.disconnect(self.newProjectCreated)

    def newProjectCreated(self):
        self.buttonBox.setEnabled(False)
        self.allowValidationLabel.show()
        self.autoLoadSettings()

    def projectSaved(self):
        self.allowValidationLabel.hide()
        self.buttonBox.setEnabled(True)

    def projectRead(self):
        self.allowValidationLabel.hide()
        self.buttonBox.setEnabled(True)
        self.autoLoadSettings()

    def autoLoadSettings(self):
        self.isValidated = False
        self.validated.emit(False)
        self.setNullProjectFiles()
        self.setOptionalSupportFiles()

        ps = QgsExpressionContextUtils.projectScope()
        if ps.hasVariable('fdtm_current_project'):
            if os.path.exists(ps.variable('fdtm_current_project')):
                self.load_action(fileName=ps.variable('fdtm_current_project'))
        if ps.hasVariable('fdtm_current_settings'):
            self.load_action(settings=json.loads(ps.variable('fdtm_current_settings')))

    def getSummaryWidget(self):
        self.summaryWidget = fdtmSummaryDialog(self)
        return self.summaryWidget

    def checkDSVLayer(self,dirPath, selectedCrsAuthid, pName):
        if self.optionalDrainageSystemLayer.currentLayerId():
            if not self.optionalDrainageSystemLayer.DSVLayer():
                self.optionalDrainageSystemLayer.setDSVLayer(create_DSV_layer(dirPath,selectedCrsAuthid,project=pName))
            else:
                checkForTemplateFields(self.optionalDrainageSystemLayer.DSVLayer())
            return self.optionalDrainageSystemLayer.DSVLayer()
        else:
            return None

    def datasetValidation(self):
        if self.isValidated:
            if self.averagePrecipitationChanged:
                self.datasetWrapper.updateCW()
                self.averagePrecipitationChanged = None
            if self.updateDataset:
                #print "updating"
                self.checkDSVLayer(self.projectFolderPath.text(), self.projection.crs().authid(), QgsProject.instance().fileInfo().baseName())
                self.datasetWrapper.update()
                QgsExpressionContextUtils.setProjectVariable('fdtm_current_settings',json.dumps(self.save_settings()))
                self.updateDataset = False
                self.validated.emit(True)
            return

        if not self.projectFolderPath.text():
            self.projectFolderPath.setText(QgsProject.instance().homePath())
        # check if all fdtm base layers have been selected:

        self.projection.setEnabled(True)
        self.averagePrecipitation.setEnabled(True)
        self.defaultRoadsWidth.setEnabled(True)
        self.isValidated = self.DEMLayer.currentLayer() and \
                         self.buildingsLayer.currentLayer() and \
                         self.roadsLayer.currentLayer() # and \
                         #self.landuseLayer.currentLayer() and \
                         #self.floodAreaLayer.currentLayer() and \
                         #self.drainageSystemLayer.currentLayer()
                         #self.railwaysLayer.currentLayer() and \
        # checkif all layers are default crs compatible:
        if self.isValidated:
            selectedCrsAuthid = self.projection.crs().authid()
            self.isValidated = self.DEMLayer.currentLayer().crs().authid() == selectedCrsAuthid and \
                             self.buildingsLayer.currentLayer().crs().authid() == selectedCrsAuthid and \
                             self.roadsLayer.currentLayer().crs().authid() == selectedCrsAuthid and \
                             self.optionalRailwaysLayer.haveCrs(selectedCrsAuthid)  and \
                             self.optionalLanduseLayer.haveCrs(selectedCrsAuthid) and \
                             self.optionalFloodAreaLayer.haveCrs(selectedCrsAuthid) and \
                             self.optionalDrainageSystemLayer.haveCrs(selectedCrsAuthid)

            if not self.isValidated:
                self.iface.messageBar().pushMessage("FDTM plugin", "The provided dataset is not validated: all layers must have the same crs", level=2, duration=3)
                self.setNullProjectFiles()
                pass #insert messagebox about that all layers must have the same crs
            else:#add project files if not present
                dirPath = self.projectFolderPath.text()
                pName = QgsProject.instance().fileInfo().baseName()
                if not self.EApLayer:
                    self.EApLayer = create_EAp_layer(dirPath,selectedCrsAuthid,project=pName)
                else:
                    checkForTemplateFields(self.EApLayer)
                if not self.EPpLayer:
                    self.EPpLayer = create_EPp_layer(dirPath,selectedCrsAuthid,project=pName)
                else:
                    checkForTemplateFields(self.EPpLayer)
                if not self.EPlLayer:
                    self.EPlLayer = create_EPl_layer(dirPath,selectedCrsAuthid,project=pName)
                else:
                    checkForTemplateFields(self.EPlLayer)
                if not self.WRLayer:
                    self.WRLayer = create_WR_layer(dirPath,selectedCrsAuthid,project=pName)
                else:
                    checkForTemplateFields(self.WRLayer)
                if not self.WDSLayer:
                    self.WDSLayer = create_WDS_layer(dirPath,selectedCrsAuthid,project=pName)
                else:
                    checkForTemplateFields(self.WDSLayer)
                self.checkDSVLayer(dirPath, selectedCrsAuthid, pName)

        else:
            self.iface.messageBar().pushMessage("FDTM plugin","The provided dataset is not validated: please indicate oll needed layers",level=2, duration=3)

        if self.isValidated:
            self.datasetWrapper = fdtmDatasetWrapper(self)
            self.projection.setEnabled(False)
            self.defaultRoadsWidth.setEnabled(False)
            QgsExpressionContextUtils.setProjectVariable('fdtm_current_settings', json.dumps(self.save_settings()))
            self.validated.emit(True)
        else:
            self.validated.emit(False)


    def save_settings(self, fileName=None):
        settings = {
            "projectDescription": self.projectDescription.text(),
            "averagePrecipitation": self.averagePrecipitation.text(),
            "projection": self.projection.crs().authid(),
            "defaultRC": self.defaultRC.itemData(self.defaultRC.currentIndex()),
            "DEMLayer": self.DEMLayer.currentLayer().id(),
            "buildingsLayer": self.buildingsLayer.currentLayer().id(),
            "roadsLayer": self.roadsLayer.currentLayer().id(),
            "defaultRoadsWidth":self.defaultRoadsWidth.text(),
            "railwaysLayer": self.optionalRailwaysLayer.currentLayerId(),
            "landuseLayer": self.optionalLanduseLayer.currentLayerId(),
            "floodAreaLayer": self.optionalFloodAreaLayer.currentLayerId(),
            "drainageSystemLayer": self.optionalDrainageSystemLayer.currentLayerId(),
            "projectFolderPath": self.projectFolderPath.text(),
            "EApLayer": self.EApLayer.id(),
            "EPpLayer": self.EPpLayer.id(),
            "EPlLayer": self.EPlLayer.id(),
            "WRLayer": self.WRLayer.id(),
            "WDSLayer": self.WDSLayer.id(),
            "DSVLayer": self.optionalDrainageSystemLayer.DSVLayerId(),
        }
        return settings

    def save_action(self):
        if self.isValidated:
            fileName = QFileDialog().getSaveFileName(None, self.tr("Save FDTM project"), self.projectFolder.text(), "*.json")
            if fileName:
                self.save_settings(fileName=fileName)

    def load_action(self, fileName=None, settings=None):
        if not fileName and not settings:
            fileName = QFileDialog().getSaveFileName(None, self.tr("Load FDTM project"),
                                                 QgsProject.instance().homePath(), "*.json")
        if fileName:
            with open(fileName, 'r') as infile:
                settings = json.load(infile)

        if settings:
            if not 'DSVLayer' in settings:
                settings['DSVLayer'] = ''
            try:
                self.projectDescription.setText(settings['projectDescription'])
                self.averagePrecipitation.setText(settings['averagePrecipitation'])
                self.projectFolderPath.setText(settings['projectFolderPath'])
                self.defaultRC.setCurrentIndex(self.defaultRC.findData(settings['defaultRC']))
                self.projection.setCrs(QgsCoordinateReferenceSystem(settings['projection']))
                self.DEMLayer.setLayer(QgsMapLayerRegistry.instance().mapLayer(settings['DEMLayer']))
                self.buildingsLayer.setLayer(QgsMapLayerRegistry.instance().mapLayer(settings['buildingsLayer']))
                self.roadsLayer.setLayer(QgsMapLayerRegistry.instance().mapLayer(settings['roadsLayer']))
                try:
                    self.defaultRoadsWidth.setText(settings['defaultRoadsWidth'])
                except:
                    self.defaultRoadsWidth.setText('8')
                self.optionalRailwaysLayer.setLayer(QgsMapLayerRegistry.instance().mapLayer(settings['railwaysLayer']))
                self.optionalLanduseLayer.setLayer(QgsMapLayerRegistry.instance().mapLayer(settings['landuseLayer']))
                self.optionalFloodAreaLayer.setLayer(QgsMapLayerRegistry.instance().mapLayer(settings['floodAreaLayer']))
                self.optionalDrainageSystemLayer.setLayer(QgsMapLayerRegistry.instance().mapLayer(settings['drainageSystemLayer']))
                if settings['EApLayer']:
                    self.EApLayer = QgsMapLayerRegistry.instance().mapLayer(settings['EApLayer'])
                else:
                    self.EApLayer = None
                if settings['EPpLayer']:
                    self.EPpLayer = QgsMapLayerRegistry.instance().mapLayer(settings['EPpLayer'])
                else:
                    self.EApLayer = None
                if settings['EPlLayer']:
                    self.EPlLayer = QgsMapLayerRegistry.instance().mapLayer(settings['EPlLayer'])
                else:
                    self.EPlLayer = None
                if settings['WRLayer']:
                    self.WRLayer = QgsMapLayerRegistry.instance().mapLayer(settings['WRLayer'])
                else:
                    self.WRLayer = None
                if settings['WDSLayer']:
                    self.WDSLayer = QgsMapLayerRegistry.instance().mapLayer(settings['WDSLayer'])
                else:
                    self.WDSLayer = None
                if settings['DSVLayer']:
                    self.optionalDrainageSystemLayer.setDSVLayer(QgsMapLayerRegistry.instance().mapLayer(settings['DSVLayer']))
                else:
                    self.optionalDrainageSystemLayer.setDSVLayer(None)
                loaded = True
            except Exception as e:
                self.iface.messageBar().pushMessage("FDTM plugin", "Error loading FDTM dataset: " + e,level=2, duration=5)
                loaded = None #messagebox for malformed brigaid settings file error
            if loaded:
                self.datasetValidation()

    def reorderLegendInterface(self):
        legendRoot = QgsProject.instance().layerTreeRoot()
        fdtmGroups = ['FDTM project layers', 'FDTM support layers' , 'FDTM other layers']
        fdtm_project_layers = [
            self.EApLayer.name(),
            self.EPlLayer.name(),
            self.EPpLayer.name(),
            self.WRLayer.name(),
            self.WDSLayer.name(),
        ]
        if self.optionalDrainageSystemLayer.currentLayerId():
            fdtm_project_layers.append(self.optionalDrainageSystemLayer.DSVLayer().name())
        fdtm_support_layers = [
            self.DEMLayer.currentLayer().name(),
            self.buildingsLayer.currentLayer().name(),
            self.roadsLayer.currentLayer().name(),
            self.optionalRailwaysLayer.currentLayer().name(),
            self.optionalLanduseLayer.currentLayer().name(),
            self.optionalFloodAreaLayer.currentLayer().name(),
            self.optionalDrainageSystemLayer.currentLayer().name(),
        ]

        for defaultGroup in fdtmGroups:
            searchResult = legendRoot.findGroup(defaultGroup)
            if not searchResult:
                legendRoot.addGroup(defaultGroup)

        otherGroup = legendRoot.findGroup('FDTM other layers')
        otherGroup.setExpanded(False)
        supportGroup = legendRoot.findGroup('FDTM support layers')
        supportGroup.setExpanded(False)
        projectGroup = legendRoot.findGroup('FDTM project layers')
        projectGroup.setExpanded(True)

        for node in legendRoot.findGroup('FDTM project layers').children():
            if not node.name() in fdtm_project_layers:
                cloned_node = node.clone()
                legendRoot.insertChildNode(0, cloned_node)
                projectGroup.removeChildNode(node)

        for node in legendRoot.findGroup('FDTM support layers').children():
            if not node.name() in fdtm_support_layers:
                cloned_node = node.clone()
                legendRoot.insertChildNode(0, cloned_node)
                supportGroup.removeChildNode(node)

        for node in legendRoot.children():
            if not node.name() in ['FDTM project layers', 'FDTM support layers' , 'FDTM other layers']:
                if node.name() in fdtm_project_layers:
                    cloned_node = node.clone()
                    projectGroup.insertChildNode(len(projectGroup.children()), cloned_node)
                    legendRoot.removeChildNode(node)
                elif node.name() in fdtm_support_layers:
                    cloned_node = node.clone()
                    supportGroup.insertChildNode(len(supportGroup.children()), cloned_node)
                    legendRoot.removeChildNode(node)
                else:
                    cloned_node = node.clone()
                    otherGroup.insertChildNode(len(otherGroup.children()), cloned_node)
                    legendRoot.removeChildNode(node)

    def applyStyles(self):
        stylesMap = [
            [self.EApLayer, "EA_p.qml"],
            [self.EPlLayer, "EP_l.qml"],
            [self.EPpLayer, "EP_p.qml"],
            [self.WRLayer, "WR.qml"],
            [self.WDSLayer, "WDS.qml"],
        ]
        if self.optionalDrainageSystemLayer.currentLayerId():
            stylesMap.append([self.optionalDrainageSystemLayer.DSVLayer(), "DSV.qml"])
        for layer, styleFile in stylesMap:
            layer.loadNamedStyle(os.path.join(os.path.dirname(__file__), 'res', styleFile))

    def applyRelations(self):
        searchEPRelation = QgsProject.instance().relationManager().relation("EA_lines_on_polygons")
        if not searchEPRelation.isValid():
            EPRelation = QgsRelation()
            EPRelation.setReferencingLayer(self.EPlLayer.id())
            EPRelation.setReferencedLayer(self.EPpLayer.id())
            EPRelation.addFieldPair("ID_EP", "ID")
            EPRelation.setRelationId("EP_lines_on_polygons")
            EPRelation.setRelationName("EP lines on polygons")
            QgsProject.instance().relationManager().addRelation(EPRelation)

        searchEPRelation = QgsProject.instance().relationManager().relation("WDS_on_EP")
        if not searchEPRelation.isValid():
            EPRelation = QgsRelation()
            EPRelation.setReferencingLayer(self.WDSLayer.id())
            EPRelation.setReferencedLayer(self.EPpLayer.id())
            EPRelation.addFieldPair("ID_EP", "ID")
            EPRelation.setRelationId("WDS_on_EP")
            EPRelation.setRelationName("WDS on EP")
            QgsProject.instance().relationManager().addRelation(EPRelation)

        searchEPRelation = QgsProject.instance().relationManager().relation("WDS_on_EA")
        if not searchEPRelation.isValid():
            EPRelation = QgsRelation()
            EPRelation.setReferencingLayer(self.WDSLayer.id())
            EPRelation.setReferencedLayer(self.EPpLayer.id())
            EPRelation.addFieldPair("ID_EA", "ID")
            EPRelation.setRelationId("WDS_on_EA")
            EPRelation.setRelationName("WDS on EA")
            QgsProject.instance().relationManager().addRelation(EPRelation)

        searchEPRelation = QgsProject.instance().relationManager().relation("WDS_on_WR")
        if not searchEPRelation.isValid():
            EPRelation = QgsRelation()
            EPRelation.setReferencingLayer(self.WDSLayer.id())
            EPRelation.setReferencedLayer(self.EPpLayer.id())
            EPRelation.addFieldPair("ID_WR", "ID")
            EPRelation.setRelationId("WDS_on_WR")
            EPRelation.setRelationName("WDS on WR")
            QgsProject.instance().relationManager().addRelation(EPRelation)

    def applyScales(self):
        QgsProject.instance().writeEntry("Scales", "/useProjectScales",True)
        QgsProject.instance().writeEntry("Scales", "/ScalesList",[u'1:10000',u'1:5000', u'1:2000', u'1:1000', u'1:500'])

    def export_action(self):

        def traverseLegend(group):
            for node in group.children():
                if node.nodeType() == QgsLayerTreeNode.NodeGroup:
                    traverseLegend(node)
                elif node.nodeType() == QgsLayerTreeNode.NodeLayer:
                    if node.layer().type() == QgsMapLayer.VectorLayer:
                        if node.layer().dataProvider().name() == 'ogr':
                            path, target_filename = os.path.split(node.layer().source())
                        else:
                            target_filename = node.layer().name()+'.shp'
                        writeSHP(node.layer(),os.path.join(tempDir,target_filename))
                        output[node.layer().id()] = ['./' + target_filename,'ogr']
                    elif node.layer().type() == QgsMapLayer.RasterLayer:
                        writeTIFF(node.layer(), os.path.join(tempDir, node.layer().name() + '.tif'))
                        output[node.layer().id()] = ['./' + node.layer().name() + '.tif','gdal']

        saveFileName = QFileDialog().getSaveFileName(None, self.tr("Export FDTM project to zip"), self.projectFolderPath.text(), "*.zip")
        legendRoot = QgsProject.instance().layerTreeRoot()
        if saveFileName:
            tempDir = tempfile.mkdtemp()
            output = {}
            if self.isValidated:
                traverseLegend(QgsProject.instance().layerTreeRoot())
                cloned_project_path = os.path.join(tempDir,QgsProject.instance().fileInfo().fileName())
                QgsProject.instance().write(QFileInfo(cloned_project_path))
                tree = ET.parse(cloned_project_path)
                root = tree.getroot()
                for layer_node in root.iter(tag='layer-tree-layer'):
                    layer_node_id = layer_node.get('id')
                    layer_node.set('source', output[layer_node_id][0])

                for layer_node in root.iter(tag='maplayer'):
                    layer_node_id = layer_node.find('id')
                    layer_node_source = layer_node.find('datasource')
                    layer_node_provider = layer_node.find('provider')
                    layer_node_source.text = output[layer_node_id.text][0]
                    layer_node_provider.text = output[layer_node_id.text][1]

                tree.write(cloned_project_path)

        with zipfile.ZipFile(saveFileName, 'w') as TMzip:
            for project_file in os.listdir(tempDir):
                project_file_path = os.path.join(tempDir,project_file)
                TMzip.write(project_file_path, project_file)

        shutil.rmtree(tempDir)


class fdtmAboutDialog(QtGui.QDialog, FORM_CLASS_about):

    def __init__(self, parent=None):
        """Constructor."""
        super(fdtmAboutDialog, self).__init__(parent)
        self.setupUi(self)


class fdtmSummaryDialog(QtGui.QWidget, FORM_CLASS_summary):

    def __init__(self, settingsWidget, parent=None):
        """Constructor."""
        super(fdtmSummaryDialog, self).__init__(parent)
        self.setupUi(self)
        self.settingsWidget = settingsWidget
        self.settingsWidget.validated.connect(self.enableTables)
        self.tabWidget.setCurrentIndex(0)
        self.tabWidget.currentChanged.connect(self.unselect)
        self.tempdir = tempfile.mkdtemp()
        self.formatGlobalSummary()

    def enableTables(self,validated):
        if validated:
            self.tabWidget.setEnabled(True)
            self.settingsWidget.datasetWrapper.updated.connect(self.populateTables)
            self.globalTablesUpdate()
        else:
            self.tabWidget.setEnabled(False)

    def populateTables(self,modifiedLayerWrapper):
        modifiedLayerWrapper.checkModel()
        self.globalTablesUpdate()

    def globalTablesUpdate(self):
        for layerWrapper in self.settingsWidget.datasetWrapper.getActiveWrappers():
            contents = layerWrapper.updateSummary(self)
            self.setGlobalRow(layerWrapper.position, contents)

    def formatGlobalSummary(self):
        table = self.projectSummary
        table.setColumnCount(4)
        table.setRowCount(6)
        table.setHorizontalHeaderItem(0,QTableWidgetItem("project units"))
        table.setHorizontalHeaderItem(1,QTableWidgetItem("Areas"))
        table.setHorizontalHeaderItem(2,QTableWidgetItem("Lengths"))
        table.setHorizontalHeaderItem(3,QTableWidgetItem("Cost"))
        table.setVerticalHeaderItem(0,QTableWidgetItem("EP"))
        table.setVerticalHeaderItem(1,QTableWidgetItem("EA"))
        table.setVerticalHeaderItem(2,QTableWidgetItem("WR"))
        table.setVerticalHeaderItem(3,QTableWidgetItem("WDS"))
        table.setVerticalHeaderItem(4,QTableWidgetItem("DSV"))
        table.setVerticalHeaderItem(5,QTableWidgetItem("Total"))

    def getCSVFilePath(self):
        #return os.path.join(QgsProject.instance().fileInfo().dir().absolutePath(),QgsProject.instance().fileInfo().baseName()+"_projectSummary.csv")
        return os.path.join(self.tempdir,'FDTM_projectSummary.csv')

    def globalSummaryToCSV(self):
        csvFileName = self.getCSVFilePath()
        rows = [['types', 'project units', 'Areas', 'Lengths', 'Cost']]
        for row in range (0, self.projectSummary.rowCount()):
            rowList = [self.projectSummary.verticalHeaderItem(row).text()]
            for column in range(0,self.projectSummary.columnCount()):
                if self.projectSummary.item(row,column):
                    rowList.append(self.projectSummary.item(row,column).text())
                else:
                    rowList.append('')
            rows.append(rowList)
        with open(csvFileName, 'wb') as csvfile:
            summaryWriter = csv.writer(csvfile, delimiter=';')
            summaryWriter.writerows(rows)
        return csvFileName

    def setGlobalRow(self,row,columns):
        for column,cell in enumerate(columns):
            widget = QTableWidgetItem(str(cell))
            if column > 0:
                widget.setTextAlignment(Qt.AlignVCenter | Qt.AlignRight)
            self.projectSummary.setItem(row,column,widget)
        self.updateTotals()

    def updateTotals(self):
        for col in range(0,4):
            colTot = 0
            for row in range(0,5):
                if self.projectSummary.item(row,col):
                    colTot += float(self.projectSummary.item(row,col).text())
            widget = QTableWidgetItem(str(colTot))
            if col > 0:
                widget.setTextAlignment(Qt.AlignVCenter | Qt.AlignRight)
            self.projectSummary.setItem(5,col,widget)
        self.globalSummaryToCSV()

    def unselect(self,tab):
        for table in [self.projectSummary, self.EPSummary, self.EASummary, self.WRSummary, self.WDSSummary, self.DSVSummary ]:
            #table.setRangeSelected(QTableWidgetSelectionRange(0,0,table.rowCount()-1,table.columnCount()-1),False)
            #table.setCurrentCell(table.currentRow(),table.currentColumn(), QItemSelectionModel.Deselect)
            table.setCurrentCell(-1, -1)
            table.clearSelection()
