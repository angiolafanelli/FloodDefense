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

import sys
import os
import tempfile
import json
import uuid
import platform
import base64
import zlib

from qgis.gui import QgsAttributeDialog, QgsAttributeForm, QgsFieldValidator, QgsMessageBar, QgsFilterLineEdit
from qgis.core import QGis, QgsRaster, QgsRasterLayer,QgsFeatureRequest, QgsField, QgsFields, QgsVectorLayer, QgsFeature, QgsGeometry, QgsPoint, QgsMapLayerRegistry, QgsVectorFileWriter, QgsExpression, QgsVectorFileWriter, QgsRasterPipe, QgsRasterFileWriter, QgsEditFormConfig
from qgis.analysis import QgsRasterCalculator, QgsRasterCalculatorEntry

from PyQt4.QtGui import QLineEdit, QSpinBox, QDoubleSpinBox, QIntValidator, QDoubleValidator, QMessageBox, QComboBox, QTableWidgetItem, QTableWidgetSelectionRange, QColor, QIcon
from PyQt4.QtCore import Qt, QTimer, QDateTime, pyqtSignal, QObject
from PyQt4 import QtGui, uic

#sys.path.append(os.path.join(os.path.expanduser("~"),'.qgis2','python','plugins')) # processing is a core plugin now
from processing.core.Processing import Processing
Processing.initialize()
from processing.tools import *

from fdtm_definitions import DEFAULT_ROADS_WIDTH, DESC_ROADS_RC, DEFAULT_ROADS_RC, DESC_BUILDINGS_RC, DEFAULT_BUILDINGS_RC, DESC_OTHER_RC, DEFAULT_OTHER_RC, MAX_DESCR_RC_LENGTH, DESCR_RC_FIELD_NAME, RC_FIELD_NAME
from fdtm_definitions import EAp_FIELDS_TEMPLATE, EPp_FIELDS_TEMPLATE, EPl_FIELDS_TEMPLATE, WR_FIELDS_TEMPLATE, WDS_FIELDS_TEMPLATE,WR_TYPES_TABLE_limited, WR_TYPES_TABLE_point, WR_TYPES_TABLE_greenroof, DSV_FIELDS_TEMPLATE
from fdtm_definitions import EP_TYPES_TABLE, EA_TYPES_TABLE, UNLIMITED_WR_ID, WDS_TYPES_TABLE, WDS_DEST_TABLE, RC_TYPES_TABLE, WDS_VALVE_TABLE, EP_TEMP_TYPES_TABLE, DSV_TYPES_TABLE
from fdtm_utils import tempLayerFromPolygon, writeTIFF, writeSHP

FORM_CLASS_detail, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'fdtm_detail_dialog.ui'))


class fdtmDetailedDialog(QtGui.QDialog, FORM_CLASS_detail):

    def __init__(self, template, parent=None, current_feat=None, layer_instance=None):
        """Constructor."""
        super(fdtmDetailedDialog, self).__init__(parent)
        self.setupUi(self)
        self.buttonBox.accepted.connect(self.acceptedAction)
        self.buttonBox.rejected.connect(self.rejectedAction)
        self.addRowButton.clicked.connect(self.addRowAction)
        self.removeRowButton.clicked.connect(self.removeRowAction)
        self.current_feat = current_feat
        self.layer_instance = layer_instance
        self.template = template
        self.tabWidget.setTabEnabled(1,False)
        self.tabWidget.setStyleSheet("QTabBar::tab::disabled {width: 0; height: 0; margin: 0; padding: 0; border: none;} ")
        for fieldName, label, qgis_field, content, enabled, combo in self.template:
            '''
            if qgis_field and qgis_field.comment():
                label = qgis_field.comment()
            else:
                label = fieldName
            '''

            if combo:
                widget = QComboBox()
                if content == 'invalid':
                    widget.addItem('invalid', 'invalid')
                else:
                    for item in combo:
                        widget.addItem(item[1],item[0])
                    search = widget.findData(content)
                    if search != -1:
                        widget.setCurrentIndex(search)
                    else:
                        widget.setCurrentIndex(0) #insert preferred logic
                widget.currentIndexChanged.connect(self.update)
            else:
                widget = QgsFilterLineEdit(self)#UNICODEEEEE & NULLLLL
                widget.setValue(str(content))
                if fieldName == 'ROADS_W':
                    widget.editingFinished.connect(self.updateRoads)
                else:
                    widget.editingFinished.connect(self.update)

                if qgis_field:
                    if qgis_field.type() == 4:
                        widget.setValidator(QIntValidator())
                    elif qgis_field.type() == 6:
                        widget.setValidator(QDoubleValidator())

            widget.setEnabled(enabled)
            globals()[fieldName] = widget

            if fieldName in ('RC_DEF',):
                widget.hide()
                if fieldName == 'RC_DEF':
                    self.setupRCTable(content)
                    self.rcTypesCombo.clear()
                    for rcItem in RC_TYPES_TABLE:
                        self.rcTypesCombo.addItem(rcItem[1],rcItem[0])
                    self.rcTypesCombo.setCurrentIndex(self.layer_instance.datasetWrapper.parent_instance.defaultRC.currentIndex())
            else:
                self.formLayout.addRow(label,globals()[fieldName])

        self.adjustSize()

    def closeEvent(self,evt):
        self.rejectedAction()

    def updateRoads(self, changedText=None):
        self.current_feat['ROADS_W'] = float(globals()['ROADS_W'].value())
        new_RC_content = self.layer_instance.datasetWrapper.landuseWrapper.getDescRC(self.current_feat)
        self.setupRCTable(new_RC_content)
        self.update()

    def update(self, changedText=None):
        self.acceptedAction(update=True)

    def acceptedAction(self,update=None):
        self.result = {}
        if update:
            self.result['UPDATE'] = True
        for fieldName, label, qgis_field, content, enabled, combo in self.template:
            if qgis_field and enabled or fieldName in ('CW','RC',):
                if combo:
                    self.result[fieldName] = globals()[fieldName].itemData(globals()[fieldName].currentIndex())
                else:
                    if qgis_field.type() == 4:
                        self.result[fieldName] = int(globals()[fieldName].value())#text())
                    elif qgis_field.type() == 6:
                        self.result[fieldName] = float(globals()[fieldName].value())#text())
                    else:
                        self.result[fieldName] = globals()[fieldName].value()#text()
        self.close()
        self.acceptedFlag = True

    def rejectedAction(self):
        self.close()
        self.acceptedFlag = None

    def addRowAction(self):
        self.RCTable.cellChanged.disconnect(self.verifyRCTable)
        row_idx = self.RCTable.rowCount()-1
        self.RCTable.insertRow(row_idx)
        idx = self.rcTypesCombo.currentIndex()
        rowValues = [self.rcTypesCombo.itemText(idx), 0.0, 0.0, self.rcTypesCombo.itemData(idx)]
        for col_idx,val in enumerate(rowValues):
            self.RCTable.setItem(row_idx, col_idx, QTableWidgetItem(str(val)))
        self.value_matrix.append(rowValues)
        self.RCTable.cellChanged.connect(self.verifyRCTable)
        self.updateGlobals()

    def removeRowAction(self):
        if self.RCTable.selectedItems():
            selected_rows = set()
            for item in self.RCTable.selectedItems():
                selected_rows.add(item.row())
            for row_idx in list(selected_rows):
                if row_idx != 0:
                    self.RCTable.cellChanged.disconnect(self.verifyRCTable)
                    self.value_matrix[0][1] += self.value_matrix[row_idx][1]
                    self.value_matrix[0][2] = round(self.value_matrix[0][1]/self.total_area*100,1)
                    self.RCTable.item(0, 1).setText( str(self.value_matrix[0][1]))
                    self.RCTable.item(0, 2).setText( str(self.value_matrix[0][2]))
                    self.RCTable.removeRow(row_idx)
                    del self.value_matrix[row_idx]
                    self.RCTable.cellChanged.connect(self.verifyRCTable)
                    self.updateGlobals()
            self.RCTable.clearSelection()

    def setupRCTable(self,json_content):
        try:
            self.RCTable.cellChanged.disconnect(self.verifyRCTable)
        except:
            pass
        content = json.loads(json_content)
        self.tabWidget.setTabEnabled(1, True)
        self.tabWidget.setStyleSheet("")
        self.RCTable.clear()
        self.RCTable.setColumnCount(4)
        self.RCTable.setRowCount(len(content.keys())+1)
        self.RCTable.setAlternatingRowColors(True)
        self.RCTable.setColumnWidth(0, 120)
        self.RCTable.setHorizontalHeaderItem(0,QTableWidgetItem('type'))
        self.RCTable.setHorizontalHeaderItem(1,QTableWidgetItem('area'))
        self.RCTable.setHorizontalHeaderItem(2,QTableWidgetItem('%'))
        self.RCTable.setHorizontalHeaderItem(3,QTableWidgetItem('RC'))
        row_idx = 0
        self.total_area = 0
        for RClabel, RCValues in content.iteritems():
            self.total_area += float(RCValues[1])
        for RClabel, RCValues in content.iteritems():
            #print row_idx,RClabel,RCValues
            wLabel = QTableWidgetItem(RClabel)
            wArea = QTableWidgetItem(str(RCValues[1]))
            wRC = QTableWidgetItem(str(round(float(RCValues[0])/100,2)))
            wCoverage = QTableWidgetItem(str(round(float(RCValues[1])/self.total_area*100,1)))
            self.RCTable.setItem(row_idx,0,wLabel)
            self.RCTable.setItem(row_idx,1,wArea)
            self.RCTable.setItem(row_idx,2,wCoverage)
            self.RCTable.setItem(row_idx,3,wRC)

            row_idx += 1
        self.RCTable.resizeColumnsToContents()
        #self.RCTable.sortByColumn(1,Qt.DescendingOrder);
        self.value_matrix = []
        for row_idx in range(0, self.RCTable.rowCount()-1):
            label =   self.RCTable.item(row_idx,0).text()
            area =    float(self.RCTable.item(row_idx,1).text())
            percent = float(self.RCTable.item(row_idx,2).text())
            rc =      float(self.RCTable.item(row_idx,3).text())
            self.value_matrix.append([label,area,percent,rc])
        #print self.value_matrix
        self.RCTable.cellChanged.connect(self.verifyRCTable)
        self.verifyRCTable()

    def rollback(self):
        for row_idx, row_list in enumerate(self.value_matrix):
            for col_idx in range(0,3):
                self.RCTable.item(row_idx, col_idx).setText(str(row_list[col_idx]))


    def verifyRCTable(self, row=None, col=None):

        exclusions = {
            'Buildings': 0,
            'Roads': 0
        }

        if col == 2:
            try:
                self.RCTable.item(row, 1).setText(str(round(float(self.RCTable.item(row,2).text())*self.total_area/100,1)))
            except:
                self.RCTable.item(row, 2).setText(str(self.value_matrix[row][2]))
            return

        self.RCTable.cellChanged.disconnect(self.verifyRCTable)

        min = 9999999
        max = 0
        #min_max detection
        for row_idx,row_list in enumerate(self.value_matrix):
            if row_list[0] in exclusions:
                exclusions[row_list[0]] = row_list[1]
            else:
                try:
                    float(self.RCTable.item(row_idx,1).text())
                    float(self.RCTable.item(row_idx,2).text())
                except:
                    self.RCTable.item(row, 1).setText(str(self.value_matrix[row][1]))
                    self.RCTable.item(row, 2).setText(str(round(self.value_matrix[row][2],1)))
                    return
                if row != row_idx:
                    if row_list[1] < min:
                        min = row_list[1]
                        min_idx = row_idx
                    if row_list[1] >= max:
                        max = row_list[1]
                        max_idx = row_idx

        if min == 9999999 and max == 0:
            self.rollback()
            self.layer_instance.iface.messageBar().pushMessage("Can’t Update Roads and Buildings",
                                                "Roads and Buildings area amounts are autocalculated and can’t be updated on user input, try adding a new row",
                                                level=1, duration=4)
            self.RCTable.cellChanged.connect(self.verifyRCTable)
            return

        if col == 1:
            delta = self.value_matrix[row][1] - float(self.RCTable.item(row,1).text())
            if delta < 0:
                update_idx = max_idx
            else:
                update_idx = min_idx
            new_area = float(self.RCTable.item(update_idx, 1).text()) + delta

            if new_area < 0:
                self.RCTable.item(row, 1).setText(str(float(self.RCTable.item(row, 1).text()) + new_area))
                new_area = 0
                self.layer_instance.iface.messageBar().pushMessage("Update RC overflow",
                                                "%s area change has pushed %s category area to 0.00" %(self.RCTable.item(row, 0),self.RCTable.item(update_idx, 0)),
                                                level=1, duration=4)

            self.RCTable.item(update_idx, 1).setText(str(float(new_area)))
            self.value_matrix[update_idx][1] = new_area

        if row != None and col !=None:
            try:
                self.value_matrix[row][col] = float(self.RCTable.item(row, col).text())
            except:
                self.value_matrix[row][col] = self.RCTable.item(row, col).text()

        lastrow_idx = self.RCTable.rowCount()-1
        mean_rc = 0
        verify_area = 0

        for row_idx,row in enumerate(self.value_matrix):
            mean_rc += row[1]*row[3]
            verify_area += row[1]
            self.value_matrix[row_idx][2] = round(row[1] / self.total_area * 100, 1)
            wCoverage = QTableWidgetItem(str(self.value_matrix[row_idx][2]))
            self.RCTable.setItem(row_idx, 2, wCoverage)
        mean_rc = mean_rc/verify_area
        wLabel = QTableWidgetItem('Mean RC/Total Area')
        wArea = QTableWidgetItem(str(round(verify_area,1)))
        wRC = QTableWidgetItem(str(round(mean_rc,2)))
        wCoverage = QTableWidgetItem('100.0')
        wLabel.setFlags(Qt.ItemIsSelectable|Qt.ItemIsEnabled )
        wArea.setFlags(Qt.ItemIsSelectable|Qt.ItemIsEnabled )
        wRC.setFlags(Qt.ItemIsSelectable|Qt.ItemIsEnabled )
        wCoverage.setFlags(Qt.ItemIsSelectable|Qt.ItemIsEnabled )
        self.RCTable.setItem(lastrow_idx,0,wLabel)
        self.RCTable.setItem(lastrow_idx,1,wArea)
        self.RCTable.setItem(lastrow_idx,2,wCoverage)
        self.RCTable.setItem(lastrow_idx,3,wRC)
        for col_idx in range(0,4):
            self.RCTable.item(lastrow_idx,col_idx).setFlags(Qt.ItemIsSelectable|Qt.ItemIsEnabled )
            self.RCTable.item(lastrow_idx, col_idx).setBackground(QColor(212, 212, 212))
        self.RCTable.cellChanged.connect(self.verifyRCTable)
        self.RCTable.resizeColumnsToContents()
        self.updateGlobals()

    def updateGlobals(self):
        globals()['RC_DEF'].setText(self.getRCDef())
        globals()['RC'].setText (str(self.getMeanRc()))
        globals()['CW'].setText (str(self.getMeanRc()*self.current_feat['AREA']*float(self.layer_instance.datasetWrapper.parent_instance.averagePrecipitation.text())/1000))

    def getMeanRc(self):
        meanRc = 0
        for row in self.value_matrix:
            meanRc += row[3]*row[1]
        return round (meanRc/self.total_area,2)

    def getRCDef(self):
        RCDef = {}
        for row in self.value_matrix:
            RCDef[row[0][:MAX_DESCR_RC_LENGTH]] = [int(row[3]*100),int(row[1])]
        return json.dumps(RCDef, separators=(',', ':') )

    @staticmethod
    def from_feat(layer_instance, feat, fieldsDef, labelsMap, caption):
        template = []
        for fieldName,enabled,combo in fieldsDef:
            qgis_field = feat.fields().field(fieldName)
            label = labelsMap[fieldName]
            content = feat[fieldName]
            template.append([fieldName, label, qgis_field, content, enabled, combo])
        dialog = fdtmDetailedDialog(template, current_feat=feat, layer_instance=layer_instance)
        dialog.setWindowTitle(caption)
        #dialog.setWindowFlags(Qt.WindowSystemMenuHint | Qt.WindowTitleHint)
        result = dialog.exec_()
        dialog.show()
        if dialog.acceptedFlag:
            return (dialog.result)
        else:
            return {'GO_ON': True}

    @staticmethod
    def view_data(data_map):
        template = []
        for label,content in data_map:
            template.append([label, label, None, content, False, None])
        dialog = fdtmDetailedDialog(template)
        #dialog.setWindowFlags(Qt.WindowSystemMenuHint | Qt.WindowTitleHint)
        result = dialog.exec_()
        dialog.show()

class fdtmDatasetWrapper(QObject):

    updated = pyqtSignal(object)

    def __init__(self, settings_instance=None):
        super(fdtmDatasetWrapper, self).__init__()
        self.iface = settings_instance.iface
        self.parent_instance = settings_instance
        self.update()
        Processing.initialize()

        self.DEMWrapper = baseDemLayerWrapper(self, settings_instance.DEMLayer.currentLayer())
        self.EApWrapper = EApLayerWrapper(self, settings_instance.EApLayer)
        self.EPlWrapper = EPlLayerWrapper(self, settings_instance.EPlLayer)#before EPpWrapper!
        self.EPpWrapper = EPpLayerWrapper(self, settings_instance.EPpLayer)
        self.WRWrapper = WRLayerWrapper(self, settings_instance.WRLayer)
        self.WDSWrapper = WDSLayerWrapper(self, settings_instance.WDSLayer)

        self.EApWrapper.updated.connect(self.advertise)
        self.EPpWrapper.updated.connect(self.advertise)
        self.WRWrapper.updated.connect(self.advertise)
        self.WDSWrapper.updated.connect(self.advertise)

        self.checkDSVWrapper()


    def update(self):
        self.buildingsWrapper = fdtmSupportLayerWrapper(self,self.parent_instance.buildingsLayer.currentLayer())
        self.roadsDefaultBuffer = DEFAULT_ROADS_WIDTH/2
        self.roadsWrapper = fdtmSupportLayerWrapper(self,self.parent_instance.roadsLayer.currentLayer(),buffer=self.roadsDefaultBuffer)
        self.railwaysWrapper = fdtmSupportLayerWrapper(self,self.parent_instance.optionalRailwaysLayer.currentLayer(),buffer=3)
        self.landuseWrapper = landuseWrapper(self,self.parent_instance.optionalLanduseLayer.currentLayer())
        self.floodAreaWrapper = fdtmSupportLayerWrapper(self,self.parent_instance.optionalFloodAreaLayer.currentLayer())
        self.drainageSystemWrapper = fdtmSupportLayerWrapper(self,self.parent_instance.optionalDrainageSystemLayer.currentLayer())
        self.checkDSVWrapper()

    def checkDSVWrapper(self):
        if self.parent_instance.optionalDrainageSystemLayer.isChecked():
            self.DSVWrapper = DSVLayerWrapper(self, self.parent_instance.optionalDrainageSystemLayer.DSVLayer())
            self.DSVWrapper.updated.connect(self.advertise)
        else:
            self.DSVWrapper = None
        return self.DSVWrapper

    def updateCW(self):
        for ds in [self.EApWrapper,self.EPpWrapper]:
            ds.updateCW()

    def advertise(self,layerWrapper):
        #print "dataset advertise"
        self.updated.emit(layerWrapper)

    def getActiveLayerList(self):
        return [wrapper.lyr for wrapper in self.getActiveWrappers()]

    def getActiveWrappers(self):
        for wrapper in [self.EPpWrapper, self.EApWrapper, self.WRWrapper, self.WDSWrapper, self.DSVWrapper]:
            if wrapper:
                yield wrapper
            else:
                continue

    def getAllWrappers(self):
        allWrappers =[
            self.EPpWrapper,
            self.EApWrapper,
            self.WRWrapper,
            self.WDSWrapper,
            self.DSVWrapper,
            self.buildingsWrapper,
            self.roadsWrapper,
            self.railwaysWrapper,
            self.landuseWrapper,
            self.floodAreaWrapper,
            self.drainageSystemWrapper,
            self.DEMWrapper,
        ]
        for wrapper in allWrappers:
            if wrapper and wrapper.lyr.name() != 'mock optional layer':
                yield wrapper
            else:
                continue


class baseDemLayerWrapper:

    def __init__(self, parent_instance, dem_raster_layer):
        self.iface = parent_instance.iface
        self.datasetWrapper = parent_instance
        self.lyr = dem_raster_layer
        self.lyr.layerNameChanged.connect(self.test)

    def test(self):
        print "CHANGED", self.lyr.name()

    def viewSample(self,identifyPoint):
        #print self.sample(identifyPoint)
        return fdtmDetailedDialog.view_data([['Surface elevation on DEM (SP)', "{0:.2f}".format(self.sample(identifyPoint))]])


    def sample(self,p):
        return self.lyr.dataProvider().identify(p, QgsRaster.IdentifyFormatValue).results()[1]

    def multi_sample(self,geometry):
        if geometry.type() == QGis.Point:
            return [self.sample(geometry.asPoint())]
        elif geometry.type() == QGis.Line:
            points_vector = geometry.asPolyline()
        elif geometry.type() == QGis.Polygon:
            points_vector = geometry.asPolygon()[0]
        else:
            points_vector = None

        if points_vector:
            multi_result = []
            for vrtx in points_vector:
                multi_result.append(self.sample(vrtx))
            return multi_result

    def min_max_along_line(self, line_geom, step_measure = None):
        if not step_measure:
            step_measure = (self.lyr.rasterUnitsPerPixelX()+self.lyr.rasterUnitsPerPixelY())/2
        currentLen = 0
        min_elevation = 99999999.0
        max_elevation = - 99999999.0
        while currentLen < line_geom.length():
            elevation_point = line_geom.interpolate(currentLen).asPoint()
            elevation_measure = self.sample(elevation_point)
            if elevation_measure < min_elevation:
                min_elevation = elevation_measure
            if elevation_measure > max_elevation:
                max_elevation = elevation_measure
            currentLen += step_measure
        return min_elevation, max_elevation

    def intersect(self,polygon):
        #self.cliplayer = QgsVectorLayer("Polygon?crs="+self.lyr.crs().authid(),"clip_layer", "memory")
        self.intersection_polygon = polygon
        #clipFile = tempfile.NamedTemporaryFile(mode='w',suffix='.geojson') #dir=os.path.dirname(__file__),delete=False, suffix='.'+gdal_format.lower()
        #clipFile = os.path.join(tempfile.gettempdir(),'__'+str(uuid.uuid4()) + ".geojson")
        '''
        writer = QgsVectorFileWriter(clipFile.name, 'UTF8', QgsFields(), QGis.WKBPolygon, self.lyr.crs(), 'GeoJSON')
        feat = QgsFeature()
        feat.setGeometry(polygon)
        writer.addFeature(feat)
        del writer
        '''
        '''
        geojson_tmpl = '{"type":"FeatureCollection","crs":{"type":"name","properties":{"name":"urn:ogc:def:crs:%s"}},"features":[{"type":"Feature","properties":{"properties":""},"geometry":%s}]}'
        with open(clipFile,'w') as geojson_file:
            geojson_file.write(geojson_tmpl % (self.lyr.crs().authid(), polygon.exportToGeoJSON()))
        '''

        clipLayer = tempLayerFromPolygon(polygon, self.lyr.crs())#QgsVectorLayer(clipFile,'clip','GeoJSON')
        #QgsMapLayerRegistry.instance().addMapLayer(clipLayer)
        result = general.runalg('gdalogr:cliprasterbymasklayer', self.lyr, clipLayer, "0", True, True, True, 5, 0, 1, 1, 1, False, 0, False, "",   None, progress=None)
        self.intersectionDEMLayer = QgsRasterLayer(result['OUTPUT'], "clip_raster")
        #QgsMapLayerRegistry.instance().removeMapLayer(clipLayer.id())
        #os.remove(clipLayer.source())
        self.update_intersection_dem_info()
        return self.intersection_DEM_info

    def contains(self,geometry):
        demBoundary = self.lyr.extent()
        return QgsGeometry.fromRect(demBoundary).contains(geometry)

    def update_intersection_dem_info(self):
        try:
            extent = self.intersectionDEMLayer.extent()
            rows = self.intersectionDEMLayer.height()
            columns = self.intersectionDEMLayer.width()
            xsize = self.intersectionDEMLayer.rasterUnitsPerPixelX()
            ysize = self.intersectionDEMLayer.rasterUnitsPerPixelY()
            cell_area = xsize * ysize
            block = self.intersectionDEMLayer.dataProvider().block(1, extent, columns, rows)
            sum = 0
            max = 0
            min = 99999999
            min_perim = min
            max_perim = max

            #evaluates max and min elevation within polygon
            for i in range(rows):
                for j in range(columns):
                    val = block.value(i, j)
                    sum += val
                    if val > max:
                        max = val
                    if val != 0.0 and val < min:
                        min = val

            #evaluates max and min elevation along perimeter
            min_perim, max_perim = self.min_max_along_line(self.intersection_polygon)

            self.intersection_DEM_info = {
                'SP': min,
                'MP': max,
                'SP_p': min_perim,
                'MP_p': max_perim,
                'AREA': self.intersection_polygon.area(),
                'PER': self.intersection_polygon.length(),
                'VOL': sum*cell_area,
            }

            #print self.intersection_DEM_info

        except Exception as e:
            print(e)
            self.intersection_DEM_info = None

    def exportLayer(self, targetDir):
        wrtr = QgsRasterFileWriter(os.path.join(targetDir, self.lyr.name())+'.tif')
        provider = self.lyr.dataProvider()
        pipe = QgsRasterPipe()
        pipe.set(provider.clone())
        res = wrtr.writeRaster (
            pipe,
            self.lyr.width(),
            self.lyr.height(),
            self.lyr.extent(),
            self.lyr.crs(),
        )
        if res != QgsRasterFileWriter.NoError:
            print "Error writing layer %s: %s" % (self.lyr.name(), res)


class AbstractVectorLayerWrapper(QObject):

    updated = pyqtSignal(object)

    def __init__(self, parent_instance, lyr, interactive=True, baseLayer=None):
        super(AbstractVectorLayerWrapper, self).__init__()
        self.iface = parent_instance.iface
        self.datasetWrapper = parent_instance
        self.default_crs = self.datasetWrapper.parent_instance.projection.crs()
        self.lyr = lyr
        self.lyr.fdtm_wrapper = self
        self.fdtm_editing = None
        if baseLayer:
            return
        self.enableEditingSignals()
        self.lyr.beforeCommitChanges.connect(self.beforeCommitChanges)
        self.lyr.editingStarted.connect(self.editingStarted)
        self.lyr.beforeRollBack.connect(self.beforeRollBack)
        self.lyr.layerModified.connect(self.layerModified)
        self.lyr.editingStopped.connect(self.editingStopped)
        self.lyr.selectionChanged.connect(self.selectionChanged)
        #self.lyr.setFeatureFormSuppress(QgsVectorLayer.SuppressOn)
        self.lyr.editFormConfig().setSuppress(QgsEditFormConfig.SuppressOn)
        self.editDialogClass = fdtmDetailedDialog
        self.interactive = interactive
        self.disableEditAttributes = None
        self.stop_recursion = None
        self.child_layer = None
        self.parent_layer = None
        self.committing = None
        self.selectOnEdit = None
        self.mapFieldsLabel()
        self.type_table = []
        self.temp_fid_map = {}
        self.alert = None
        self.dockWidgetTable = None
        self.recoveringEdit = False
        self.processingEdits = None
        self.allow_update = True
        self.checkGeometriesSet = {
            'intersects': self,
            'overlaps': None
        }

    def enableEditingSignals(self):
        self.lyr.featureAdded.connect(self.featureAdded)
        self.lyr.geometryChanged.connect(self.geometryChanged)
        self.lyr.featureDeleted.connect(self.featureDeleted)

    def disableEditingSignals(self):
        self.lyr.featureAdded.disconnect(self.featureAdded)
        self.lyr.geometryChanged.disconnect(self.geometryChanged)
        self.lyr.featureDeleted.disconnect(self.featureDeleted)

    def getFid(self):
        control = []
        for feat in self.lyr.getFeatures():
            if feat['ID']:
                control.append(int(feat['ID']))
        featureid = 0
        for fid in control:
            if fid and fid > featureid:
                featureid = fid
        return featureid +1

    def mapFieldsLabel(self):
        self.labelsMap = {}
        for field in self.lyr.fields().toList():
            self.labelsMap[field.name()] = field.name()

    def setInteractive(self,bool):
        self.interactive = bool

    def editTemplate(self,feat=None):
        pass

    def summaryTemplate(self):
        return self.editTemplate(feat=None)

    def updateFeature(self,feat):
        pass

    def setCheckGeometriesSet(self,wrappersDict):
        self.checkGeometriesSet = wrappersDict

    def check_intersects(self,geom):
        for feat in self.lyr.getFeatures():
            if feat.geometry().intersects(geom):
                return feat
        else:
            return None

    def check_overlaps(self,geom):
        for feat in self.lyr.getFeatures():
            if feat.geometry().overlaps(geom):
                return feat
        else:
            return None

    def editAttributes(self, feat, disableEditAttributes=None ):
        if self.committing:
            #print "committing - edit attribute aborted"
            return
        if not self.interactive or self.disableEditAttributes or disableEditAttributes:
            if not self.interactive:
                print "%s not interactive" % self.lyr.name()
            if self.disableEditAttributes or disableEditAttributes:
                print "Disabled editing attributes on %s" % self.lyr.name()
            return #unittest execution
        if self.selectOnEdit:
            self.lyr.selectByIds([feat.id()])
        changes = self.editDialogClass.from_feat(self, feat, self.editTemplate(feat), self.labelsMap, self.editCaption)
        for change, value in changes.iteritems():
            if change in self.labelsMap.keys(): #not change in ("UPDATE","GO_ON"):
                feat[change] = value
                feat['ID_USER'] = os.path.split(os.path.expanduser('~'))[-1]
                feat['DATE_MOD'] = QDateTime.currentDateTime()
        self.lyr.updateFeature(feat)
        self.updateFeature(feat, geom_update=False)
        self.lyr.updateFeature(feat)
        #self.updated.emit(self)
        if "UPDATE" in changes.keys():
            self.editAttributes(feat, disableEditAttributes=disableEditAttributes)
        if "GO_ON" in changes.keys():
            self.fast_feature_creation = True
        if self.selectOnEdit:
            self.lyr.selectByIds([])

    def confirmEdits(self):
        if self.lyr.isModified():
            reply = QMessageBox.question(None, "Saving fdtm layers" , "Do you want to save %s layer edits?" % self.lyr.name(), QMessageBox.Yes, QMessageBox.No)
            #print "reply", reply
            if reply == QMessageBox.Yes:
                self.lyr.commitChanges()
            else:
                #print "rollback"
                self.lyr.rollBack()
        else:
            self.lyr.rollBack()

    def intersects(self,geometry):
        for feat in self.lyr.getFeatures():
            if feat.geometry().intersects(geometry):
                return True
        return False

    def check_inside_dem(self,featToCheck):
        inside_dem = self.datasetWrapper.DEMWrapper.contains(featToCheck.geometry())
        if not inside_dem:
            self.iface.messageBar().pushMessage("Geometry error",
                                                "The feature is outside digital elevation model boundary" ,
                                                level=1, duration=3)  # QgsMessageBar.Warning
        return inside_dem

    def check_simple_geometry(self,featToCheck):
        simple_geom = featToCheck.geometry().isGeosValid() and not featToCheck.geometry().isMultipart()
        if not simple_geom:
            self.iface.messageBar().pushMessage("Geometry error",
                                                "The feature has not a valid geometry" ,
                                                level=1, duration=3)  # QgsMessageBar.Warning
        return simple_geom


    def checkIntersections(self,featToCheck,layerWrappers):
        for check in ['intersects', 'overlaps']:
            for layerWrapper in layerWrappers[check]:
                for feat in layerWrapper.lyr.getFeatures():
                    if layerWrapper.lyr == self.lyr and featToCheck.id() == feat.id():
                        continue
                    if getattr(featToCheck.geometry(),check)(feat.geometry()):
                        #print featToCheck.id(), feat.id(), layerWrapper.lyr.name()
                        #print featToCheck.geometry().exportToGeoJSON (precision=2)
                        #print feat.geometry().exportToGeoJSON (precision=2)
                        self.iface.messageBar().pushMessage("Geometry error", "The feature %s underlying geometries of layer: %s" % (check,layerWrapper.lyr.name()),
                                                       level=1, duration=3) #QgsMessageBar.Warning
                        return True
        return None

    def test_checkIntersections(self,featToCheck,layerWrappers):
        for check in ['intersects', 'overlaps']:
            for layerWrapper in layerWrappers[check]:
                result_feature = getattr(layerWrapper,"check_"+check)(featToCheck)
                if result_feature:
                    if layerWrapper.lyr.id() == self.lyr.id() and featToCheck.id() == result_feature.id():
                        continue
                    self.iface.messageBar().pushMessage("Geometry error", "The feature %s %s underlying geometries (%s) of layer: %s" % (featToCheck['ID'],check,result_feature['ID'],layerWrapper.lyr.name()),
                                                   level=1, duration=3) #QgsMessageBar.Warning
                    return True
        return None

    def resetDSVWrapperOnGeometryChange(self):
        pass

    def geometryChanged(self,fid,geometry):
        #print "geometryChanged",fid,geometry.exportToWkt(precision=1),"processingMod:"
        if self.committing:
            return
        if self.recoveringEdit:
            self.recoveringEdit = False
            return
        feat = self.lyr.getFeatures(QgsFeatureRequest(fid)).next()
        if self.checkIntersections(feat,self.checkGeometriesSet) or not self.check_inside_dem(feat)  or not self.check_simple_geometry(feat):
            self.disableEditingSignals()
            try:
                unchanged_feat = self.lyr.dataProvider().getFeatures(QgsFeatureRequest(fid)).next()
                feat.setGeometry(unchanged_feat.geometry())
            except Exception, e:
                print e
                unchanged_geometry = self.geometryEditBuffer[int(fid)]
                feat.setGeometry(unchanged_geometry)
            self.enableEditingSignals()
            return
        if self.alert and self.interactive:
            QMessageBox.warning(None, "fdtm warning",self.alert)
        feat['ID_USER'] = os.path.split(os.path.expanduser('~'))[-1]
        feat['DATE_MOD'] = QDateTime.currentDateTime()
        self.updateFeature(feat)
        self.geometryEditBuffer[int(fid)] = feat.geometry()
        self.postFeatureAdded(feat)
        self.resetDSVWrapperOnGeometryChange()

    def featureDeleted(self,fid):
        if self.committing:
            return
        if self.recoveringEdit:
            self.recoveringEdit = False
            return
        try:
            feat = self.lyr.dataProvider().getFeatures(QgsFeatureRequest(fid)).next()
            feat_id = feat['ID']
        except StopIteration: #means that is a fid previously created in current edit session
            feat_id = self.temp_fid_map[fid]
        if int(fid) in self.geometryEditBuffer:
            self.geometryEditBuffer.pop(int(fid))
        self.postFeatureDelete(feat_id)

    def featureFactory(self):
        return QgsFeature(self.lyr.pendingFields())

    def featuresDeleted(self,fids):
        for fid in fids:
            if fid > 0:
                feat = self.lyr.dataProvider().getFeatures(QgsFeatureRequest(fid)).next()
                if feat:
                    self.postFeatureDelete(feat)

    def postFeatureDelete(self, feat_id):
        pass

    def featureAdded(self,fid, force_create=None):
        if self.committing and not force_create:
            return
        feat = self.lyr.getFeatures(QgsFeatureRequest(fid)).next()

        if self.checkIntersections(feat, self.checkGeometriesSet) or not self.check_inside_dem(feat)  or not self.check_simple_geometry(feat):
            self.disableEditingSignals()
            self.lyr.deleteFeature(fid)
            self.enableEditingSignals()
            print "Intersections found"
            return
        else:
            self.recoveringEdit = None

        feat['ID'] = self.getFid()
        feat['ID_USER'] = os.path.split(os.path.expanduser('~'))[-1]
        feat['DATE_CR'] = QDateTime.currentDateTime()
        self.temp_fid_map[feat.id()] = feat['ID']
        self.lyr.updateFeature(feat)
        if feat.geometry().isMultipart():
            self.lyr.deleteFeature(fid)
        else:
            self.updateFeature(feat)
            self.editAttributes(feat)
        self.geometryEditBuffer[int(fid)] = feat.geometry()
        self.postFeatureAdded(feat)
        return True

    def postFeatureAdded(self,feat):
        pass

    def editingStarted(self):
        self.temp_fid_map = {}
        self.geometryEditBuffer = {}
        if not self.fdtm_editing:
            self.lyr.rollBack()

    def fdtm_startEditing(self, changeActiveLayer=True, disableEditAttributes=None):
        self.fdtm_editing = True
        self.fast_feature_creation = None
        self.committing = disableEditAttributes
        self.lyr.startEditing()
        if changeActiveLayer:
            self.iface.setActiveLayer(self.lyr)
        if self.child_layer:
            self.child_layer.fdtm_startEditing(changeActiveLayer=None)

    def beforeCommitChanges(self):
        self.committing = True
        self.fdtm_editing = None
        if self.child_layer:
            self.child_layer.lyr.commitChanges()

    def fdtm_commitChanges(self):
        self.lyr.commitChanges()
        self.committing = None

    def editingStopped(self):
        self.committing = None
        self.updated.emit(self)

    def beforeRollBack(self):
        self.committing = True
        self.lyr.undoStack().clear()
        if self.child_layer:
            self.child_layer.lyr.rollBack()
            self.child_layer.lyr.triggerRepaint()
        self.fdtm_editing = None

    def fdtm_rollBack(self):
        self.lyr.rollBack()
        self.committing = None

    def check_for_intersections(self):
        #added features
        pass

    def check_EA_source(self,vertex):
        return self.datasetWrapper.EApWrapper.check_intersects(QgsGeometry.fromPoint(vertex))

    def check_EP_source(self,vertex):
        return self.datasetWrapper.EPpWrapper.check_intersects(QgsGeometry.fromPoint(vertex))

    def check_WR_target(self,vertex):
        return self.datasetWrapper.WRWrapper.check_intersects(QgsGeometry.fromPoint(vertex))

    def layerModified(self):
        if self.allow_update:
            self.updated.emit(self) #test

    def calcCW(self,feat):
        if not 'CW' in self.labelsMap.keys():
            return #exception if not EPp or EAp
        area = feat['AREA'] #feat.geometry().area()
        averagePrecipitation = float(self.datasetWrapper.parent_instance.averagePrecipitation.text())
        runoffCoefficient = feat['RC']
        CW = area*averagePrecipitation*runoffCoefficient/1000
        return CW

    def updateCW(self):
        if not 'CW' in self.labelsMap.keys():
            return
        if not self.fdtm_editing:
            self.fdtm_editing = True
            final_commit = True
            self.lyr.startEditing()
        else:
            final_commit = None
        for feat in self.lyr.getFeatures():
            feat['CW'] = self.calcCW(feat)
            self.lyr.updateFeature(feat)
        if final_commit:
            final_commit = None
            self.lyr.commitChanges()

    def copySummaryToClipboard(self,table):
        print table
        pass

    def updateSummary(self,widget):

        layerRows = 0
        layerArea = 0.0
        layerLenght = 0.0
        layerCost = 0.0
        isWaterPrecessor = None
        waterIncoming = 0.0
        waterProcessed = 0.0

        if not hasattr(self,'dockWidgetTable'):
            return

        self.table = getattr(widget,self.dockWidgetTable)
        self.tabWidget = getattr(widget,"tabWidget")
        self.table.clear()
        try:
            self.table.itemSelectionChanged.disconnect(self.tableSelectionChanged)
            self.table.cellDoubleClicked.disconnect(self.editFeatureAttributes)
        except :
            pass
        fieldsDef = self.summaryTemplate()
        self.table.setColumnCount(len(fieldsDef))
        for idx,field in enumerate(fieldsDef):
            self.table.setHorizontalHeaderItem(idx,QTableWidgetItem(field[0]))
        self.table.setRowCount(self.lyr.featureCount())
        self.project_unit_processed_icon = QIcon(os.path.join(os.path.dirname(__file__), "res", 'dot_blue.png'))
        datasetInvalidFlag = False
        for idx,feat in enumerate(self.lyr.getFeatures()):
            layerRows += 1
            vertical_header = QTableWidgetItem("")
            self.table.setVerticalHeaderItem(idx, vertical_header)
            test_value1 = None
            test_value2 = None
            water_processed_icon = self.project_unit_processed_icon
            is_basin = None
            featureInvalidFlag = None
            for idy,field in enumerate(fieldsDef):
                content = feat[field[0]]

                if content:
                    try:
                        content = round(content,2)
                    except:
                        pass
                    tableContent = str(content) #handle unicode
                else:
                    tableContent = ''

                widget = QTableWidgetItem(tableContent)
                widget.setFlags(Qt.ItemIsSelectable |  Qt.ItemIsEnabled)
                if idy > 2:
                    widget.setTextAlignment(Qt.AlignVCenter | Qt.AlignRight)
                self.table.setItem(idx,idy,widget)
                if field[0] == 'COST':
                    layerCost += float(content)
                if field[0] == 'AREA':
                    layerArea += float(content)
                if field[0] == 'PER':
                    layerLenght += float(content)
                if field[0] == 'LENGTH':
                    layerLenght += float(content)

                if field[0] == 'TYP' and content == 'invalid':
                    featureInvalidFlag = True
                    datasetInvalidFlag = True

                if field[0] in ["CW","CAP"]:
                    test_value1 = float(content)
                    isWaterPrecessor = True
                    waterIncoming += float(content)
                        
                if field[0] in ["CW_DRAIN","COLLECTED"]:
                    isWaterPrecessor = True
                    if content:
                        test_value2 = float(content)
                        waterProcessed += float(content)
                    else:
                        test_value2 = 0.00
                        waterProcessed = 0.00
                        
                if field[0] == "CAP":
                    is_basin = True
                    
            if isWaterPrecessor:
                if test_value2 == 0:
                    if is_basin:
                        water_processed_icon = QIcon(os.path.join(os.path.dirname(__file__), "res", 'dot_blue_void.png'))

                    else:
                        water_processed_icon = QIcon(os.path.join(os.path.dirname(__file__), "res", 'dot_red.png'))

                elif test_value2 != test_value1:
                    if is_basin:
                        water_processed_icon = QIcon(os.path.join(os.path.dirname(__file__), "res", 'dot_blue-half.png'))
                    else:
                        water_processed_icon = QIcon(os.path.join(os.path.dirname(__file__), "res", 'dot_red-blue.png'))
            else:
                if featureInvalidFlag:
                    water_processed_icon = QIcon(os.path.join(os.path.dirname(__file__), "res", 'dot_red.png'))
                else:
                    water_processed_icon = QIcon(os.path.join(os.path.dirname(__file__), "res", 'dot_white.png'))
            vertical_header.setIcon(water_processed_icon)
            
        if isWaterPrecessor:
            if waterProcessed == 0:
                    if is_basin:
                        self.project_unit_processed_icon = QIcon(os.path.join(os.path.dirname(__file__), "res", 'dot_blue_void.png'))

                    else:
                        self.project_unit_processed_icon = QIcon(os.path.join(os.path.dirname(__file__), "res", 'dot_red.png'))
            elif waterProcessed < waterIncoming:
                    if is_basin:
                        self.project_unit_processed_icon = QIcon(os.path.join(os.path.dirname(__file__), "res", 'dot_blue-half.png'))
                    else:
                        self.project_unit_processed_icon = QIcon(os.path.join(os.path.dirname(__file__), "res", 'dot_red-blue.png'))
        else:
            if datasetInvalidFlag:
                self.project_unit_processed_icon = QIcon(os.path.join(os.path.dirname(__file__), "res", 'dot_red.png'))
            else:
                self.project_unit_processed_icon = QIcon(os.path.join(os.path.dirname(__file__), "res", 'dot_white.png'))

        self.tabWidget.setTabIcon(self.position+1, self.project_unit_processed_icon)
        self.table.itemSelectionChanged.connect(self.tableSelectionChanged)
        self.table.cellDoubleClicked.connect(self.editFeatureAttributes)
        return layerRows,layerArea,layerLenght,layerCost

    def tableSelectionChanged(self):
        selected_feats = []
        clipboard = ''
        QtGui.QApplication.clipboard().clear()
        for col in range(0, self.table.columnCount()):
            clipboard += self.table.horizontalHeaderItem(col).text() + '\t'
        clipboard = clipboard[:-1] + '\n'
        processed_rows = set()
        for item in self.table.selectedItems():
            feat_id = self.table.item(item.row(),0).text()
            if not feat_id in processed_rows:
                for col in range(0, self.table.columnCount()):
                    clipboard += self.table.item(item.row(),col).text() + '\t'
                clipboard = clipboard[:-1] + '\n'
                processed_rows.add(feat_id)
            exp = QgsExpression('"ID" = %s' % feat_id)
            selected_feats.append(self.lyr.getFeatures(QgsFeatureRequest(exp)).next().id())
        self.lyr.selectByIds(selected_feats)
        QtGui.QApplication.clipboard().setText(clipboard)

    def selectionChanged(self,selected, deselected):
        if not hasattr(self,'table'):
            return
        self.table.itemSelectionChanged.disconnect(self.tableSelectionChanged)
        self.lyr.selectionChanged.disconnect(self.selectionChanged)
        columnCount = len(self.summaryTemplate())
        self.table.clearSelection()
        for feat_id in selected:
            feat = self.lyr.getFeatures(QgsFeatureRequest(feat_id)).next()
            for row in range(0, self.table.rowCount()):
                try:
                    if self.table.item(row,0) and int(self.table.item(row,0).text()) == feat[0]:
                        self.table.setRangeSelected(QTableWidgetSelectionRange(row,0,row,columnCount-1),True)
                except:
                    pass

        self.table.itemSelectionChanged.connect(self.tableSelectionChanged)
        self.lyr.selectionChanged.connect(self.selectionChanged)

    def editFeatureAttributes(self,row,col):
        feat_id = self.table.item(row, 0).text()
        exp = QgsExpression('"ID" = %s' % feat_id)
        feat = self.lyr.getFeatures(QgsFeatureRequest(exp)).next()
        self.editAttributes(feat)

    def getFeatureFromID(self,featId):
        exp = QgsExpression('"ID" = %d' % featId)
        return self.lyr.getFeatures(QgsFeatureRequest(exp)).next()

    def getFeatureAttribute(self,feat,AttributeName):
        return feat[AttributeName]

    def setFeatureAttribute(self,feat,AttributeName,value):
        attributeIdx = self.lyr.fields().indexFromName(AttributeName)
        if self.lyr.isEditable():
            self.allow_update = None
            self.lyr.changeAttributeValue(feat.id(),attributeIdx,value)
            #feat[AttributeName] = value
            self.allow_update = True
        else:
            mods = {
                feat.id(): {
                    attributeIdx:value
                }
            }
            if not self.lyr.dataProvider().changeAttributeValues(mods):
                print "Writing mods failed:", mods

    def resetAttribute(self,AttributeName,value):
        attributeIdx = self.lyr.fields().indexFromName(AttributeName)
        mods = {}
        for feat in self.lyr.getFeatures():
            if self.lyr.isEditable():
                self.allow_update = None
                self.lyr.changeAttributeValue(feat.id(), attributeIdx, value)
                #feat[AttributeName] = value
                self.allow_update = True
            else:
                mods[feat.id()] = {attributeIdx:value}
        if not self.lyr.isEditable():
            if not self.lyr.dataProvider().changeAttributeValues(mods):
                print "Writing mods failed:", mods

    def checkModel(self):

        def processUnlimited(sourceId,sourceWrapper,targetId,targetWrapper):
            if targetId == UNLIMITED_WR_ID:
                sourceFeat = sourceWrapper.getFeatureFromID(sourceId)
                sourceWrapper.setFeatureAttribute(sourceFeat, 'CW', sourceWrapper.calcCW(sourceFeat))
                sourceCW = sourceWrapper.getFeatureAttribute(sourceFeat, 'CW')
                sourceWrapper.setFeatureAttribute(sourceFeat, 'CW_DRAIN', sourceCW)

        def processLimited(sourceId,sourceWrapper,targetId,targetWrapper):
            if targetId != UNLIMITED_WR_ID:
                sourceFeat = sourceWrapper.getFeatureFromID(sourceId)
                targetFeat = targetWrapper.getFeatureFromID(targetId)
                sourceWrapper.setFeatureAttribute(sourceFeat, 'CW', sourceWrapper.calcCW(sourceFeat))
                sourceCW = sourceWrapper.getFeatureAttribute(sourceFeat, 'CW')
                sourceCW_DRAIN = sourceWrapper.getFeatureAttribute(sourceFeat, 'CW_DRAIN')
                targetCAP = targetWrapper.getFeatureAttribute(targetFeat, 'CAP')
                targetCOLLECTED = targetWrapper.getFeatureAttribute(targetFeat, 'COLLECTED')
                target_collection_capacity = targetCAP - targetCOLLECTED
                source_residual_CW = sourceCW - sourceCW_DRAIN
                if source_residual_CW > target_collection_capacity:
                    sourceWrapper.setFeatureAttribute(sourceFeat, 'CW_DRAIN', sourceCW_DRAIN + target_collection_capacity)
                    targetWrapper.setFeatureAttribute(targetFeat, 'COLLECTED', targetCOLLECTED + target_collection_capacity)
                else:
                    sourceWrapper.setFeatureAttribute(sourceFeat, 'CW_DRAIN', sourceCW_DRAIN + source_residual_CW)
                    targetWrapper.setFeatureAttribute(targetFeat, 'COLLECTED', targetCOLLECTED + source_residual_CW)

        self.datasetWrapper.WRWrapper.resetAttribute('COLLECTED',0)
        self.datasetWrapper.EPpWrapper.resetAttribute('CW_DRAIN',0)
        self.datasetWrapper.EApWrapper.resetAttribute('CW_DRAIN',0)

        for process in (processUnlimited, processLimited):
            for WDS_feat in self.datasetWrapper.WDSWrapper.lyr.getFeatures():
                if WDS_feat["ID_EP"]:
                    sourceId = WDS_feat["ID_EP"]
                    sourceWrapper = self.datasetWrapper.EPpWrapper
                elif WDS_feat["ID_EA"]:
                    sourceId = WDS_feat["ID_EA"]
                    sourceWrapper = self.datasetWrapper.EApWrapper
                else:
                    sourceId =  None
                targetId = WDS_feat["ID_WR"]
                targetWrapper = self.datasetWrapper.WRWrapper
                if sourceId and targetId:
                    try:
                        process(sourceId,sourceWrapper,targetId,targetWrapper)
                    except StopIteration:
                        pass


    def exportLayer(self, targetDir):
        res = QgsVectorFileWriter.writeAsVectorFormat(
            self.lyr,
            os.path.join(targetDir, self.lyr.name()),
            'UTF-8',
            self.lyr.crs(),
        )
        if res != QgsVectorFileWriter.NoError:
            print "Error writing layer %s: %s" % (self.lyr.name(),res)

        '''
        writeAsVectorFormat(QgsVectorLayer * layer, const
        QString & fileName, const
        QString & fileEncoding, const
        QgsCoordinateReferenceSystem * destCRS, const
        QString & driverName = "ESRI Shapefile", bool
        onlySelected = false, QString * errorMessage = nullptr, const
        QStringList & datasourceOptions = QStringList(), const
        QStringList & layerOptions = QStringList(), bool
        skipAttributeCreation = false, QString * newFilename = nullptr, SymbologyExport
        symbologyExport = NoSymbology, double
        symbologyScale = 1.0, const
        QgsRectangle * filterExtent = nullptr, QgsWKBTypes::Type
        overrideGeometryType = QgsWKBTypes::Unknown, bool
        forceMulti = false, bool
        includeZ = false, QgsAttributeList
        attributes = QgsAttributeList(), FieldValueConverter * fieldValueConverter = nullptr)
        '''

class EApLayerWrapper(AbstractVectorLayerWrapper):

    def __init__(self, *args, **kwargs):
        super(EApLayerWrapper, self).__init__(*args, **kwargs)
        self.editCaption = "elevated area (EA) parameters"
        self.type_table = EA_TYPES_TABLE
        self.cost_ref = {}
        self.dockWidgetTable = "EASummary"
        self.position = 1

        for row in EA_TYPES_TABLE:
            self.cost_ref[row[0]] = row[-1]

    def editingStarted(self):
        self.setCheckGeometriesSet({
            'intersects':[self, self.datasetWrapper.EPpWrapper, self.datasetWrapper.buildingsWrapper, self.datasetWrapper.roadsWrapper],
            'overlaps': [self.datasetWrapper.WRWrapper]
        })
        super(EApLayerWrapper, self).editingStarted()

    def mapFieldsLabel(self):
        self.labelsMap = {}
        for field,typ,label in EAp_FIELDS_TEMPLATE:
            self.labelsMap[field] = label
        return self.labelsMap

    def editTemplate(self, feat=None):
        return [
            ["ID",False,None],
            ["DESC",True and self.lyr.isEditable(),None],
            ["NOTES",True and self.lyr.isEditable(),None],
            ["PER",False,None],
            ["AREA",False,None],
            ["SP",False,None],
            ["MP",False,None],
            ["CW",False,None],
            ["RC",True and self.lyr.isEditable(),RC_TYPES_TABLE],
            ["MP_USER",True and self.lyr.isEditable(),None],
            ["TYP",True and self.lyr.isEditable(),self.type_table],
            ["VOL",False,None],
            ["CW_DRAIN",False,None],
            ["COST",False,None],
        ]

    def updateFeature(self, feat, geom_update=True):
        #print "updating:", feat.id()
        if geom_update or not feat['VG']:
            dem_info = self.datasetWrapper.DEMWrapper.intersect(feat.geometry())
            if not feat['RC']:
                feat['RC'] = float(self.datasetWrapper.parent_instance.defaultRC.itemData(self.datasetWrapper.parent_instance.defaultRC.currentIndex()))
            feat['SP'] = dem_info['SP']
            feat['MP'] = dem_info['MP']
            if not feat['MP_USER']:
                feat['MP_USER'] = dem_info['MP']
            feat['PER'] = dem_info['PER']
            feat['AREA'] = dem_info['AREA']
            feat['VG'] = dem_info['VOL']
        if feat['MP_USER'] < feat['MP']:
            feat['MP_USER'] = feat['MP']
        feat['VOL'] = feat['AREA']*feat['MP_USER'] - feat['VG']
        feat['CW'] = self.calcCW(feat)
        if not feat['TYP']:
            feat['TYP'] = self.type_table[0][0] #insert preferred logic
        feat['COST'] = float(feat['VOL'])*float(self.cost_ref[feat['TYP']])
        self.lyr.updateFeature(feat)

    def resetDSVWrapperOnGeometryChange(self):
        if self.datasetWrapper.DSVWrapper:
            self.datasetWrapper.DSVWrapper.clearLayer()


class EPlLayerWrapper(AbstractVectorLayerWrapper):

    def __init__(self, *args, **kwargs):
        super(EPlLayerWrapper, self).__init__(*args, **kwargs)
        #self.disableEditAttributes = True
        self.selectOnEdit = True
        self.editCaption = "elevated perimeter (EP) border parameters"
        self.type_table = EP_TYPES_TABLE
        self.noIntersectionSet = []
        self.cost_ref = {}
        for row in EP_TYPES_TABLE:
            self.cost_ref[row[0]] = row
        self.temp_cost_ref = {}
        for row in EP_TEMP_TYPES_TABLE:
            self.temp_cost_ref[row[0]] = row[-1]

    def editingStarted(self):
        self.setCheckGeometriesSet({
            'intersects':[],
            'overlaps': []
        })
        super(EPlLayerWrapper, self).editingStarted()

    def mapFieldsLabel(self):
        self.labelsMap = {}
        for field,typ,label in EPl_FIELDS_TEMPLATE:
            self.labelsMap[field] = label
        return self.labelsMap

    def featuresDeleted(self,fids):
        pass

    def editTemplate(self, feat):
        return [
            ["ID",False,None],
            ["NOTES",True and self.lyr.isEditable(),None],
            ["ID_EP",False,None],
            ["LENGTH",False,None],
            ["SP_SEG",False,None],
            ["MP_SEG",False,None],
            ["BH",False,None],
            ["MP_SEG_U",False,None],
            ["TYP",True and self.lyr.isEditable(),EP_TYPES_TABLE],
            ["TEMP_TYP",True and self.lyr.isEditable(),EP_TEMP_TYPES_TABLE],
            ["COST",False,None],
        ]

    def updateFeature(self, feat, geom_update=True):
        if not feat['TYP']:
            feat['TYP'] = self.type_table[1][0] #insert preferred logic
        if not feat['TEMP_TYP']:
            if self.datasetWrapper.roadsWrapper.intersects(feat.geometry()):
                feat['TEMP_TYP'] = EP_TEMP_TYPES_TABLE[1][0]
            else:
                feat['TEMP_TYP'] = EP_TEMP_TYPES_TABLE[0][0]
        feat['COST'] = float(feat['LENGTH'])*float(self.cost_ref[feat['TYP']][-1])
        if feat['TEMP_TYP'] == 'mobile':
            feat['COST'] += float(self.cost_ref[feat['TYP']][-2])
        exp = QgsExpression('"ID" = %s' % feat['ID_EP'])
        perimeter_feat = self.parent_layer.lyr.getFeatures(QgsFeatureRequest(exp)).next()
        #self.parent_layer.lyr.geometryChanged.disconnect(self.geometryChanged)
        #self.parent_layer.lyr.geometryChanged.connect(self.geometryChanged)
        self.lyr.updateFeature(feat)
        self.parent_layer.updateFeatureCost(perimeter_feat)

class EPpLayerWrapper(AbstractVectorLayerWrapper):

    def __init__(self, dataset_instance, lyr, **kwargs):
        super(EPpLayerWrapper, self).__init__(dataset_instance, lyr, **kwargs)
        self.child_layer = dataset_instance.EPlWrapper
        dataset_instance.EPlWrapper.parent_layer = self
        self.editCaption = "elevated perimeter (EP) parameters"
        self.type_table = EP_TYPES_TABLE
        self.cost_ref = {}
        self.alert = "EP geometry changed. All user edits on EP borders will be lost."
        self.dockWidgetTable = "EPSummary"
        self.position = 0
        for row in EP_TYPES_TABLE:
            self.cost_ref[row[0]] = row[-1]

    def editingStarted(self):
        self.setCheckGeometriesSet({
            'intersects':[self, self.datasetWrapper.EApWrapper],
            'overlaps': [self.datasetWrapper.buildingsWrapper, self.datasetWrapper.roadsWrapper, self.datasetWrapper.WRWrapper]
        })
        super(EPpLayerWrapper, self).editingStarted()

    def mapFieldsLabel(self):
        self.labelsMap = {}
        for field,typ,label in EPp_FIELDS_TEMPLATE:
            self.labelsMap[field] = label
        return self.labelsMap

    def editTemplate(self, feat):
        return [
            ["ID",False,None],
            ["DESC",True and self.lyr.isEditable(),None],
            ["NOTES",True and self.lyr.isEditable(),None],
            ["PER",False,None],
            ["AREA",False,None],
            ["ROADS_W",True and self.lyr.isEditable(),None],
            ["SP",False,None],
            ["MP",False,None],
            ["RC",False,None],
            #["RC_USER",True and self.lyr.isEditable(),RC_TYPES_TABLE],
            ["MP_USER",True and self.lyr.isEditable(),None],
            ["TYP",True and self.lyr.isEditable(),self.type_table],
            ["CW",False,None],
            ["CW_DRAIN",False,None],
            ["COST",False,None],
            ["RC_DEF",True,None],
        ]

    def updateFeatureCost(self, feat):
        border_cost = 0
        exp = QgsExpression('"ID_EP" = %s' % feat['ID'])
        for border_feat in self.child_layer.lyr.getFeatures(QgsFeatureRequest(exp)):
            border_cost += float(border_feat['COST'])
        feat['COST'] = border_cost
        self.lyr.updateFeature(feat)

    def ex_updateFeatureCost(self, feat):
        border_cost = 0
        for border_feat in self.child_layer.lyr.getFeatures():
            if border_feat['COST']:
                border_cost += float(border_feat['COST'])
        if border_cost > 0:
            #print "border_cost",border_cost,feat
            feat['COST'] = border_cost
        else:
            feat['COST'] = float(feat['PER'])*float(self.cost_ref[feat['TYP']])
        self.lyr.updateFeature(feat)

    def geometryChanged(self,fid,geometry):
        self.child_layer.disableEditAttributes = True
        super(EPpLayerWrapper, self).geometryChanged(fid,geometry)
        self.child_layer.disableEditAttributes = False

    def updateFeature(self, feat, geom_update=True):
        if geom_update or not feat['VG']:
            if not feat['ROADS_W']:
                feat['ROADS_W'] = DEFAULT_ROADS_WIDTH
            if not feat['RC_USER']:
                feat['RC_USER'] = self.datasetWrapper.parent_instance.defaultRC.itemData(self.datasetWrapper.parent_instance.defaultRC.currentIndex())
            dem_info = self.datasetWrapper.DEMWrapper.intersect(feat.geometry())
            feat['RC_DEF'] = self.datasetWrapper.landuseWrapper.getDescRC(feat)
            feat['RC'] = self.datasetWrapper.landuseWrapper.getMeanRC(descr_RC=feat['RC_DEF'])
            feat['SP'] = dem_info['SP_p']
            feat['MP'] = dem_info['MP_p']
            if not feat['MP_USER']:
                feat['MP_USER'] = dem_info['MP_p']
            feat['PER'] = dem_info['PER']
            feat['AREA'] = dem_info['AREA']
            feat['VG'] = dem_info['VOL']
            if not feat['TYP']:
                feat['TYP'] = self.type_table[1][0] #insert preferred logic
        feat['CW'] = self.calcCW(feat)
        self.updateFeatureCost(feat)


    def borders_garbage_collection(self, feat_table_id):
        '''
        not used anymore; collects and delete EPl border features that are unreferenced to EPp polygons
        :param feat_table_id:
        :return:
        '''
        referenced_EP_ids = []
        for feat in self.lyr.getFeatures():
            referenced_EP_ids.append(feat_table_id)
        #print "referenced_EP_ids", referenced_EP_ids

        unreferenced_border_feats = []
        for border_feat in self.child_layer.lyr.getFeatures():
            if not border_feat['ID_EP'] in referenced_EP_ids:
                #print "unreferenced:",border_feat['ID'], border_feat['ID_EP']
                unreferenced_border_feats.append(border_feat.id())
        self.child_layer.lyr.deleteFeatures(unreferenced_border_feats)
        self.child_layer.lyr.triggerRepaint()

    def postFeatureDelete(self, feat_table_id):
        exp = QgsExpression('"ID_EP" = %s' % feat_table_id)
        #print "postFeatureDelete", feat_table_id
        border_feats = []
        for feat in self.child_layer.lyr.getFeatures(QgsFeatureRequest(exp)):
            border_feats.append(feat.id())
        #print "DEL border feats",border_feats
        self.child_layer.lyr.deleteFeatures(border_feats)
        self.child_layer.lyr.triggerRepaint()

    def postFeatureAdded(self,feat):
        self.disableEditingSignals()
        self.postFeatureDelete(feat['ID'])
        perimeter = feat.geometry().asPolygon()
        outer_polygon = perimeter[0]
        vertex1 = outer_polygon[0]
        outer_polygon = outer_polygon[1:]
        #border_features = []
        for vertex2 in outer_polygon:
            border_feat = QgsFeature(self.child_layer.lyr.fields())
            border_feat['ID_EP'] = feat['ID']
            border_line = [vertex1,vertex2]
            border_geom = QgsGeometry.fromPolyline(border_line)
            border_feat.setGeometry(border_geom)
            border_feat['LENGTH'] = border_geom.length()
            border_feat['SP_SEG'], border_feat['MP_SEG'] = self.datasetWrapper.DEMWrapper.min_max_along_line(border_geom)
            border_feat['MP_SEG_U'] = feat['MP_USER']
            border_feat['TYP'] = feat['TYP']#insert preferred logic
            #print "CHECK post feature added", border_feat['LENGTH'],feat['TYP'], feat['PER'], feat.id()
            border_feat['COST'] = float(border_feat['LENGTH'])*float(self.cost_ref[feat['TYP']])
            border_feat['BH'] = border_feat['MP_SEG'] - border_feat['SP_SEG']
            #border_features.append(border_feat)
            vertex1 = vertex2
            if self.child_layer.fast_feature_creation:
                self.child_layer.disableEditAttributes = True
            self.child_layer.lyr.addFeature(border_feat)
        #self.child_layer.disableEditAttributes = True
        #self.child_layer.lyr.addFeatures(border_features)
        if self.child_layer.fast_feature_creation:
            self.child_layer.fast_feature_creation = None
            self.child_layer.disableEditAttributes = None
        self.child_layer.lyr.selectByIds([])
        feat.setGeometry(QgsGeometry.fromPolygon(perimeter)) #I don't know why it's necessary to rebuild geometry!
        self.updateFeatureCost(feat)
        self.lyr.updateFeature(feat)
        self.enableEditingSignals()
        #print "FLAGS:", self.committing, self.interactive, self.disableEditAttributes
        #self.child_layer.disableEditAttributes = False

    def resetDSVWrapperOnGeometryChange(self):
        if self.datasetWrapper.DSVWrapper:
            self.datasetWrapper.DSVWrapper.clearLayer()


class WRLayerWrapper(AbstractVectorLayerWrapper):

    def __init__(self, *args, **kwargs):
        super(WRLayerWrapper, self).__init__(*args, **kwargs)
        self.dockWidgetTable = "WRSummary"
        self.position = 2
        self.editCaption = "Water recovery (WR) parameters"
        self.modMap = {}
        WR_types = ['point','greenroof','limited']
        for typ in WR_types:
            for sub_typ in globals()['WR_TYPES_TABLE_' + typ]:
                self.modMap[sub_typ[0]] = typ

    def editingStarted(self):
        if self.mod == 'limited':
            intersect_group = [self, self.datasetWrapper.buildingsWrapper, self.datasetWrapper.roadsWrapper]
        else:
            intersect_group = [self]
        self.setCheckGeometriesSet({
            'intersects': intersect_group,
            'overlaps': [self.datasetWrapper.EApWrapper, self.datasetWrapper.EPpWrapper]
        })
        super(WRLayerWrapper, self).editingStarted()

    def editAttributes(self, feat, disableEditAttributes=None ):
        if feat['TYP']:
            self.mod = self.modMap[feat['TYP']]
        else:
            self.mod = 'point'
        super(WRLayerWrapper, self).editAttributes(feat, disableEditAttributes=disableEditAttributes)

    def mapFieldsLabel(self):
        self.labelsMap = {}
        for field,typ,label in WR_FIELDS_TEMPLATE:
            self.labelsMap[field] = label
        return self.labelsMap

    def editTemplate(self, feat):
        fieldSet = [
            ["ID",False,None],
            ["DESC",True and self.lyr.isEditable(),None],
            ["NOTES",True and self.lyr.isEditable(),None],
            ["PER",False,None],
            ["AREA",False,None],
            ["SP",False,None],
            ["MP",False,None],
            ["TYP",True and self.lyr.isEditable(),self.type_table],
        ]
        if feat and self.modMap[feat['TYP']] == 'point':
            fieldSet += [
                #["MP_USER",False,None],
                ["CAP_USER",True and self.lyr.isEditable(),None]
            ]
        elif feat and self.modMap[feat['TYP']] == 'greenroof':
            fieldSet += [
                #["MP_USER",False,None],
                #["CAP_USER",False,None]
            ]
        else:
            fieldSet += [
                ["MP_USER",True and self.lyr.isEditable(),None],
                #["CAP_USER",False,None]
            ]

        fieldSet += [
            ["CAP",False,None],
            ["COLLECTED",False,None],
            ["COST",False,None],
        ]
        return fieldSet

    def updateFeature(self, feat, geom_update=True):
        #print "updating:", feat.id()
        dem_info = None

        if not feat['TYP']:
            self.type_table = globals()['WR_TYPES_TABLE_' + self.mod]
            feat['TYP'] = self.type_table[0][0] #insert preferred logic
        else:
            self.type_table = globals()['WR_TYPES_TABLE_' + self.modMap[feat['TYP']]]

        self.cost_ref = {}
        #print "type_table", self.type_table
        for row in self.type_table:
            self.cost_ref[row[0]] = row

        if geom_update or not feat['VG']:
            dem_info = self.datasetWrapper.DEMWrapper.intersect(feat.geometry())
            feat['SP'] = dem_info['SP']
            feat['MP'] = dem_info['MP']
            if not feat['MP_USER']:
                feat['MP_USER'] = dem_info['MP']
            feat['PER'] = dem_info['PER']
            feat['AREA'] = dem_info['AREA']
            feat['VG'] = dem_info['VOL']

        if not feat['CAP_USER']:
            feat['CAP_USER'] = 0
        if self.modMap[feat['TYP']] == 'point':
            feat['CAP'] = feat['CAP_USER']
        else:
            if not dem_info:
                dem_info = self.datasetWrapper.DEMWrapper.intersect(feat.geometry())
            if self.modMap[feat['TYP']] == 'greenroof':
                feat['CAP'] = dem_info['AREA']*float(self.cost_ref[feat['TYP']][-2])
            else:
                feat['CAP'] = dem_info['AREA']* feat['MP_USER'] - dem_info['VOL']
            feat['CAP_USER'] = feat['CAP']

        feat['VOL'] = feat['AREA']*feat['MP_USER'] - feat['VG']
        feat['COST'] = float(feat['CAP'])*float(self.cost_ref[feat['TYP']][-1])
        self.lyr.updateFeature(feat)

    def fdtm_startEditing(self, WRType, changeActiveLayer=True):
        self.mod = WRType
        super(WRLayerWrapper, self).fdtm_startEditing(changeActiveLayer=changeActiveLayer)

    def postFeatureAdded(self,WR_feat):
        #if the feature is succesfully added, if WR is greenroof a wds is auto added
        if self.modMap[WR_feat['TYP']] == 'greenroof' :
            EP_feat = self.check_EP_source(WR_feat.geometry().pointOnSurface().asPoint())
            WDS_feat = self.datasetWrapper.WDSWrapper.featureFactory()
            WDS_geom = QgsGeometry.fromPolyline([QgsPoint(EP_feat.geometry().pointOnSurface().asPoint()), QgsPoint(WR_feat.geometry().pointOnSurface().asPoint())])
            WDS_feat.setGeometry(WDS_geom)
            self.datasetWrapper.WDSWrapper.updateFeature(WDS_feat)
            WDS_feat['ID'] = self.datasetWrapper.WDSWrapper.getFid()
            WDS_feat['TYP'] = 'link'
            WDS_feat['VALVE_TYP'] = 'link'
            WDS_feat['COST'] = 0
            self.datasetWrapper.WDSWrapper.lyr.dataProvider().addFeatures([WDS_feat])

    def postFeatureDelete(self,WR_id):
        for WDS_feat in self.datasetWrapper.WDSWrapper.lyr.getFeatures():
            print (WDS_feat['ID_WR'],WR_id,WDS_feat.id())
            if WDS_feat['ID_WR'] == WR_id:
                self.datasetWrapper.WDSWrapper.lyr.dataProvider().deleteFeatures([WDS_feat.id()])
                if self.datasetWrapper.WDSWrapper.lyr.dataProvider().hasErrors():
                    print ("DATA PROVIDER ERRORS:", self.datasetWrapper.WDSWrapper.lyr.dataProvider().errors())

class WDSLayerWrapper(AbstractVectorLayerWrapper):

    def __init__(self, *args, **kwargs):
        super(WDSLayerWrapper, self).__init__(*args, **kwargs)
        self.disableEditAttributes = False
        self.selectOnEdit = True
        self.editCaption = "Water discharge system (WDS) parameters"
        #self.type_table = WDS_TYPES_TABLE
        self.noIntersectionSet = []
        self.cost_ref = {None:0,'link':0,'invalid':0}
        self.valve_cost_ref = {None:0,'link':0,'invalid':0}
        self.dockWidgetTable = "WDSSummary"
        self.position = 3
        for row in WDS_TYPES_TABLE:
            self.cost_ref[row[0]] = row[-1]
        for row in WDS_VALVE_TABLE:
            self.valve_cost_ref[row[0]] = row[-1]

    def editingStarted(self):
        self.setCheckGeometriesSet({
            'intersects':[self.datasetWrapper.buildingsWrapper,],
            'overlaps': []
        })
        super(WDSLayerWrapper, self).editingStarted()

    def featureAdded(self,fid):
        feat = self.lyr.getFeatures(QgsFeatureRequest(fid)).next()
        start_vertex = feat.geometry().asPolyline()[0]
        end_vertex = feat.geometry().asPolyline()[-1]
        EP_source = self.check_EP_source(start_vertex)
        WR_target = self.check_WR_target(end_vertex)
        if EP_source and WR_target and WR_target['TYP'][:5] == 'green':
            self.setCheckGeometriesSet({
                'intersects':[], #[self.datasetWrapper.buildingsWrapper,],
                'overlaps': []
            })
        else:
            self.setCheckGeometriesSet({
                'intersects':[self.datasetWrapper.buildingsWrapper,],
                'overlaps': []
            })
        super(WDSLayerWrapper, self).featureAdded(fid)

    def mapFieldsLabel(self):
        self.labelsMap = {}
        for field,typ,label in WDS_FIELDS_TEMPLATE:
            self.labelsMap[field] = label
        return self.labelsMap

    def no_featuresDeleted(self,fids):
        pass

    def editTemplate(self, feat):
        return [
            ["ID",False,None],
            ["DESC",True and self.lyr.isEditable(),None],
            ["NOTES",True and self.lyr.isEditable(),None],
            ["DEST_TYP", True and self.lyr.isEditable(), WDS_DEST_TABLE],
            ["TYP",True and self.lyr.isEditable(), WDS_TYPES_TABLE],
            ["VALVE_TYP", False, None],
            ["ID_EA",False,None],
            ["ID_EP",False,None],
            ["ID_WR",False,None],
            ["LENGTH",False,None],
            ["CW_EA",False,None],
            ["CW_EP",False,None],
            ["CAP_WR",False,None],
            ["MP_EA",False,None],
            ["MP_EP",False,None],
            ["MP_WR",False,None],
            ["COST",False,None],
        ]

    def updateFeature(self, feat, geom_update=True):
        start_vertex = feat.geometry().asPolyline()[0]
        end_vertex = feat.geometry().asPolyline()[-1]
        EA_feat_check = self.check_EA_source(start_vertex)
        EP_feat_check = self.check_EP_source(start_vertex)
        WR_feat_check = self.check_WR_target(end_vertex)

        #if not feat['DEST_TYP']:
        if WR_feat_check:
            feat['DEST_TYP'] = 'limited'
        else:
            feat['DEST_TYP'] = 'unlimited'
        
        if EA_feat_check:
            feat['ID_EA'] = EA_feat_check['ID']
            feat['CW_EA'] = EA_feat_check['CW']
            feat['MP_EA'] = EA_feat_check['MP']
            source_maximum_elevation = EA_feat_check['MP']
        else:
            feat['ID_EA'] = None
            feat['CW_EA'] = None
            feat['MP_EA'] = None
            source_maximum_elevation = None
            
        if EP_feat_check:
            feat['ID_EP'] = EP_feat_check['ID']
            feat['CW_EP'] = EP_feat_check['CW']
            feat['MP_EP'] = EP_feat_check['MP']
            source_maximum_elevation = EP_feat_check['MP']
        else:
            feat['ID_EP'] = None
            feat['CW_EP'] = None
            feat['MP_EP'] = None

        if feat['DEST_TYP'] == 'limited':
            if WR_feat_check:
                feat['ID_WR'] = WR_feat_check['ID']
                feat['CAP_WR'] = WR_feat_check['CAP']
                feat['MP_WR'] = WR_feat_check['MP']
                target_maximum_elevation = feat['MP_WR']
            else:
                feat['ID_WR'] = None
                feat['CAP_WR'] = None
                feat['MP_WR'] = None
                target_maximum_elevation = None
        else:
            feat['ID_WR'] = UNLIMITED_WR_ID
            feat['CAP_WR'] = float("inf")
            feat['MP_WR'] = self.datasetWrapper.DEMWrapper.sample(end_vertex)
            target_maximum_elevation = feat['MP_WR']

        if source_maximum_elevation and target_maximum_elevation:
            if source_maximum_elevation < target_maximum_elevation:
                feat['VALVE_TYP'] = WDS_VALVE_TABLE[0][0]
            else:
                feat['VALVE_TYP'] = WDS_VALVE_TABLE[1][0]

        feat['LENGTH'] = feat.geometry().length()

        mesg = ""
        #feat['TYP'] = None
        if not EP_feat_check and not EA_feat_check:
            mesg = "WDS polyline doesn't origin inside an EA/EP polygon "
        if not WR_feat_check and feat['DEST_TYP'] == 'limited':
            if mesg:
                mesg += 'and '
            mesg += "WDS polyline doesn't end inside a WR polygon "
        if mesg:
            feat['TYP'] = 'invalid'
            feat['COST'] = None
            self.iface.messageBar().pushMessage("WDS Geometry error", mesg,level=1, duration=3)
        else:

            if feat['TYP'] == 'invalid':
                feat['COST'] = 0
            else:
                if not feat['TYP']:
                    feat['TYP'] = WDS_TYPES_TABLE[0][0] #insert preferred logic
                feat['COST'] = float(feat['LENGTH'])*float(self.cost_ref[feat['TYP']]) + float(self.valve_cost_ref[feat['VALVE_TYP']])
        #print feat['DEST_TYP'], feat['ID_EA'], feat['ID_EP'], feat['ID_WR'], feat['LENGTH'],feat['TYP'], feat['VALVE_TYP'],feat['COST'], self.valve_cost_ref
        self.lyr.updateFeature(feat)

class DSVLayerWrapper(AbstractVectorLayerWrapper):

    def __init__(self, *args, **kwargs):
        super(DSVLayerWrapper, self).__init__(*args, **kwargs)
        self.disableEditAttributes = False
        self.selectOnEdit = True
        self.editCaption = "Drainage system valves"
        #self.type_table = WDS_TYPES_TABLE
        self.noIntersectionSet = []
        self.cost_ref = {None:0}
        self.dockWidgetTable = "DSVSummary"
        self.position = 4
        for row in DSV_TYPES_TABLE:
            self.cost_ref[row[0]] = row[-1]

    def mapFieldsLabel(self):
        self.labelsMap = {}
        for field,typ,label in DSV_FIELDS_TEMPLATE:
            self.labelsMap[field] = label
        return self.labelsMap

    def featuresDeleted(self,fids):
        pass

    def editTemplate(self, feat):
        return [
            ["ID",False,None],
            ["DESC",True and self.lyr.isEditable(),None],
            ["NOTES",True and self.lyr.isEditable(),None],
            ["TYP",True and self.lyr.isEditable(), DSV_TYPES_TABLE],
            ["ID_EP",False,None],
            ["ID_EA",False,None],
            ["ELEV",False,None],
            ["COST",False,None],
        ]

    def updateFeature(self, feat, geom_update=True):
        if not feat['TYP']:
            feat['TYP'] = DSV_TYPES_TABLE[0][0]
        feat['COST'] = self.cost_ref[feat['TYP']]

    def clearLayer(self):
        delete_list = []
        for feat in self.lyr.getFeatures():
            delete_list.append(feat.id())
        self.lyr.dataProvider().deleteFeatures(delete_list)
        self.lyr.triggerRepaint()

    def rebuildLayer(self):
        if self.lyr.featureCount > 0:
            reply = QMessageBox.question(None, "Rebuilding Drainage System Valves (DSV) Layer", "Do you really want to erase current DSV layer contents?", QMessageBox.Yes, QMessageBox.No)
            if reply == QMessageBox.No:
                return
        self.clearLayer()
        add_list = []
        idx = 0
        for unit_type,test_wrapper in (("EP",self.datasetWrapper.EPpWrapper,),("EA",self.datasetWrapper.EApWrapper,),):
            for test_feat in test_wrapper.lyr.getFeatures():
                for DSFeat in self.datasetWrapper.drainageSystemWrapper.lyr.getFeatures():
                    if test_feat.geometry().intersects(DSFeat.geometry()):
                        line_geom = test_feat.geometry().convertToType(QGis.Line)
                        intersection = line_geom.intersection(DSFeat.geometry())
                        for int_point in intersection.asGeometryCollection():
                            int_feat = QgsFeature(self.lyr.fields())
                            int_feat.setGeometry(int_point)
                            elev = self.datasetWrapper.DEMWrapper.sample(int_point.asPoint())
                            int_feat['ELEV'] = elev
                            int_feat['TYP'] = DSV_TYPES_TABLE[0][0]
                            int_feat['COST'] = float(DSV_TYPES_TABLE[0][-1])
                            int_feat['ID_'+unit_type] = test_feat['ID']
                            int_feat['ID'] = idx
                            idx += 1
                            add_list.append(int_feat)
        self.lyr.dataProvider().addFeatures(add_list)
        self.lyr.triggerRepaint()


class fdtmSupportLayerWrapper(AbstractVectorLayerWrapper):

    def __init__(self, dataset_instance, lyr, buffer=None):
        super(fdtmSupportLayerWrapper, self).__init__(dataset_instance, lyr, baseLayer=True)
        if buffer and not hasattr(self.lyr,'MOCKLAYER'):
            result = general.runalg('qgis:fixeddistancebuffer', self.lyr, buffer, 5, False, None, progress=None)
            self.bufferedLyr = QgsVectorLayer(result['OUTPUT'],'tmp_buffer','ogr')
            self.bufferedLyr.setCrs(self.default_crs)#self.lyr.crs())
        else:
            self.bufferedLyr = None

    def exportLayer(self, targetDir):
        res = QgsVectorFileWriter.writeAsVectorFormat(
            self.lyr,
            os.path.join(targetDir, self.lyr.name()),
            'UTF-8',
            self.lyr.crs(),
        )
        if res != QgsVectorFileWriter.NoError:
            print "Error writing layer %s: %s" % (self.lyr.name(),res)

    def intersect(self,geometry,addRC=None, dissolve=None, override_buffer=None):
        if self.bufferedLyr and not override_buffer:
            inputLayer = self.bufferedLyr
        else:
            inputLayer = self.lyr
        clipLayer = tempLayerFromPolygon(geometry, self.default_crs) #self.lyr.crs())
        #tmpShp_file = os.path.join(tempfile.gettempdir(), '__' + str(uuid.uuid4()) + ".shp")
        #print "error:", QgsVectorFileWriter.writeAsVectorFormat(clipLayer,tmpShp_file,'System',self.lyr.crs(),"ESRI Shapefile")
        #tmpShp_clip_layer = QgsVectorLayer(tmpShp_file,'tmp_clip','ogr')
        #QgsMapLayerRegistry.instance().addMapLayer(tmpShp_clip_layer)
        #result = general.runalg('gdalogr:clipvectorsbypolygon', inputLayer, clipLayer, '', None)

        result = general.runalg('qgis:extractbylocation', inputLayer, clipLayer, ['intersects'],0,  None, progress=None)
        outputFile = result['OUTPUT']
        outputLayer = QgsVectorLayer(outputFile, 'tmp_subset', 'ogr')
        #print "featureCount", outputLayer.featureCount()
        if outputLayer.featureCount() == 0:
            return None
        if override_buffer:
            result = general.runalg('qgis:fixeddistancebuffer', outputLayer, override_buffer, 5, False, None, progress=None)
            outputFile = result['OUTPUT']
            outputLayer = QgsVectorLayer(outputFile, 'tmp_buffer', 'ogr')
        if dissolve and outputLayer.featureCount() > 0:
            result = general.runalg('qgis:dissolve', outputLayer, False,"",None, progress=None)  #
            outputFile = result['OUTPUT']
            outputLayer = QgsVectorLayer(outputFile, 'tmp_dissolve', 'ogr')
        result = general.runalg('qgis:intersection', outputLayer, clipLayer, True, None, progress=None)
        outputFile = result['OUTPUT']
        outputLayer = QgsVectorLayer(outputFile,'tmp_intersect','ogr')
        #QgsMapLayerRegistry.instance().addMapLayer(outputLayer)
        if addRC and outputLayer.featureCount() > 0:
            outputLayer.startEditing()
            #print addRC
            for RCkey, RCvalue in addRC.iteritems():
                #print (type(RCvalue), RCkey, RCvalue)
                if type(RCvalue) == float:
                    RCField = QgsField(RCkey,type=6,len=18,prec=11)
                    RCvalue = round(RCvalue,2)
                elif type(RCvalue) in (str,unicode):
                    RCField = QgsField(RCkey,type=10,len=50,prec=0)
                else:
                    RCField = QgsField(RCkey, type=4, len=10, prec=0)
                outputLayer.addAttribute(RCField)
                #print (type(RCvalue), RCkey, RCvalue)
                for feat in outputLayer.getFeatures():
                    feat[RCkey]=RCvalue
                    outputLayer.updateFeature(feat)
            outputLayer.commitChanges()
        return outputLayer

    def clipped_area(self, clip_geometry):
        clipLayer = self.intersect(clip_geometry)
        area = 0
        for feat in clipLayer.getFeatures():
            area += feat.geometry().area()
        return area

    def subtract(self, layerToSubtract):
        if self.bufferedLyr:
            inputLayer = self.bufferedLyr
        else:
            inputLayer = self.lyr
        result = general.runalg('qgis:clip', inputLayer, layerToSubtract, None, progress=None)  # , False
        outputFile = result['OUTPUT']
        outputLayer = QgsVectorLayer(outputFile,'tmp_clip','ogr')
        QgsMapLayerRegistry.instance().addMapLayer(outputLayer)
        return outputLayer

class landuseWrapper(fdtmSupportLayerWrapper):

    def __init__(self, dataset_instance, lyr):
        super(landuseWrapper, self).__init__(dataset_instance, lyr)

    def getDescRC(self, feat=None, geometry=None, compress=None):

        if feat:
            geometry = feat.geometry()
            if feat['RC_USER']:
                defaultRC = feat['RC_USER']
            else:
                defaultRC = DEFAULT_OTHER_RC
            defaultRC = self.datasetWrapper.parent_instance.defaultRC.itemData(self.datasetWrapper.parent_instance.defaultRC.currentIndex())
            defaultDescRC = self.datasetWrapper.parent_instance.defaultRC.itemText(self.datasetWrapper.parent_instance.defaultRC.currentIndex())
        elif not geometry:
            return
        else:
            defaultRC = self.datasetWrapper.parent_instance.defaultRC.itemData(self.datasetWrapper.parent_instance.defaultRC.currentIndex())
            defaultDescRC = self.datasetWrapper.parent_instance.defaultRC.itemText(self.datasetWrapper.parent_instance.defaultRC.currentIndex())

        if hasattr(self.lyr,'MOCKLAYER'):
            baseLayer = tempLayerFromPolygon(geometry, self.lyr.crs(),properties={'Descr_RC':defaultDescRC,'RC':float(defaultRC)})
        else:
            #print "LAYERCOPERTURA"
            baseLayer = self.intersect(geometry)


        buildings_extraction = self.datasetWrapper.buildingsWrapper.intersect(geometry,addRC={DESCR_RC_FIELD_NAME: DESC_BUILDINGS_RC,RC_FIELD_NAME: DEFAULT_BUILDINGS_RC})
        #QgsMapLayerRegistry.instance().addMapLayer(buildings_extraction)
        try:
            roads_width = feat['ROADS_W']
        except:
            roads_width = DEFAULT_ROADS_WIDTH

        #print ("roads_width",roads_width)
        if roads_width > 0.0:
            roads_extraction = self.datasetWrapper.roadsWrapper.intersect(geometry,
                                                                          addRC={DESCR_RC_FIELD_NAME: DESC_ROADS_RC, RC_FIELD_NAME: DEFAULT_ROADS_RC},
                                                                          dissolve=True,
                                                                          override_buffer=roads_width / 2)
        else:
            roads_extraction = None
        #QgsMapLayerRegistry.instance().addMapLayer(roads_extraction)

        if roads_extraction:
            result = general.runalg('qgis:difference', baseLayer, roads_extraction, False, None, progress=None)
            step1File = result['OUTPUT']
            step1Layer = QgsVectorLayer(step1File, 'step1', 'ogr')
            result = general.runalg('qgis:mergevectorlayers', [step1Layer, roads_extraction], None, progress=None)
            step2File = result['OUTPUT']
            step2Layer = QgsVectorLayer(step2File, 'step2', 'ogr')
        else:
            step2Layer = baseLayer
        if buildings_extraction:
            result = general.runalg('qgis:difference', step2Layer, buildings_extraction, False, None, progress=None)
            step3File = result['OUTPUT']
            step3Layer = QgsVectorLayer(step3File, 'step3', 'ogr')
            result = general.runalg('qgis:mergevectorlayers', [step3Layer, buildings_extraction], None, progress=None)
            step4File = result['OUTPUT']
            step4Layer = QgsVectorLayer(step4File, 'step4', 'ogr')
        else:
            step4Layer = step2Layer

        #QgsMapLayerRegistry.instance().addMapLayer(step4Layer)

        descr_RC = {}

        for feature in step4Layer.getFeatures():
            if feature.geometry() and feature.geometry().isGeosValid(): #some features could be invalid
                if feature[DESCR_RC_FIELD_NAME] in descr_RC:
                    descr_RC[feature[DESCR_RC_FIELD_NAME]][1] += feature.geometry().area()
                else:
                    descr_RC[feature[DESCR_RC_FIELD_NAME]] = [float(feature[RC_FIELD_NAME]),feature.geometry().area()]

        #compactJSON
        compact_descr_RC = {}
        computed_area = 0
        for RCkey,RCvalue in descr_RC.iteritems():
            if int(RCvalue[1]) > 0:
                compact_descr_RC[RCkey[:MAX_DESCR_RC_LENGTH]] = [int(RCvalue[0]*100),int(RCvalue[1])]
                computed_area += int(RCvalue[1])

        #print ("TOTAL area geometry: %s area computed: %s" % (geometry.area(),computed_area))
        #print ("json-encoded", json.dumps(compact_descr_RC,separators=(',', ':') ))
        #print ("base64-json-encoded", base64.b64encode(json.dumps(compact_descr_RC)))
        #print ("base64-zip-json-encoded", base64.b64encode(zlib.compress(json.dumps(compact_descr_RC))))
        return json.dumps(compact_descr_RC,separators=(',', ':'))


    def getMeanRC(self, feat=None, geometry=None, descr_RC = None):
        if not descr_RC:
            descr_RC = self.getDescRC(feat=feat, geometry=geometry)
        descr_RC = json.loads(descr_RC)
        mean_RC = 0
        computed_area = 0
        for value in descr_RC.values():
            mean_RC += value[0]*value[1]
            computed_area += value[1]
        mean_RC = float(mean_RC/computed_area)/100
        return mean_RC


