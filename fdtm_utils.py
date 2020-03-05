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
import uuid
import tempfile
import re

from qgis.core import QGis, QgsVectorFileWriter, QgsVectorLayer, QgsFields, QgsField, QgsMapLayerRegistry, QgsCoordinateReferenceSystem, QgsRasterFileWriter, QgsVectorFileWriter, QgsRasterPipe
from qgis.gui import QgsProjectionSelectionWidget

from PyQt4.QtGui import QDoubleValidator, QFileDialog
from PyQt4.QtCore import pyqtSignal


from fdtm_definitions import EAp_FIELDS_TEMPLATE, EPp_FIELDS_TEMPLATE, EPl_FIELDS_TEMPLATE, WR_FIELDS_TEMPLATE, WDS_FIELDS_TEMPLATE, DSV_FIELDS_TEMPLATE

def getFieldFromDefinition(field_type):
    type_pack = field_type[1].split("|")
    if field_type[2]:
        comment = field_type[2]
    else:
        comment = field_type[0]
    return QgsField(name=field_type[0], type=int(type_pack[0]), len=int(type_pack[1]), prec=int(type_pack[2]), comment=comment)

def exclude_checkForTemplateFields(layer):
    return

def checkForTemplateFields(layer):
    layerFileName = os.path.splitext(os.path.basename(layer.source()))[0]
    if re.search('(-(\d)+)$', layerFileName):
        idx = -2
    else:
        idx = -1
    templateName = layerFileName.split('-')[idx].replace('_','')
    layerTemplate = globals()[templateName+'_FIELDS_TEMPLATE']

    layerFieldNamesList = []
    for field in layer.fields().toList():
        layerFieldNamesList.append(field.name())

    for fieldDef in layerTemplate:
        if not fieldDef[0] in layerFieldNamesList:
            #print "Creating",fieldDef
            layer.startEditing()
            layer.addAttribute(getFieldFromDefinition(fieldDef))
            layer.commitChanges()

def create_shplayer_from_template(template,legend=True):
    #print "creating",template['datasource']
    fieldSet = QgsFields()
    for fieldDef in template['fields']:
        fieldSet.append(getFieldFromDefinition(fieldDef))

    writer = QgsVectorFileWriter(template['datasource'], 'UTF-8', fieldSet, template['geomtype'], QgsCoordinateReferenceSystem(template['srs']))
    if writer.hasError():
        print writer.errorMessage()
    del writer
    lyr = QgsVectorLayer(template['datasource'],template['name'],'ogr')
    if template['style']:
        lyr.loadNamedStyle(template['style'])
    if legend:
        QgsMapLayerRegistry.instance().addMapLayer(lyr)
    return lyr

def getNextVersionNumber(fileName):
    if os.path.exists(fileName):
        basePathName, extension = os.path.splitext(fileName)
        if re.search( '(-(\d)+)$',basePathName):
            version = int(basePathName.split('-')[-1]) + 1
        else:
            basePathName += '-0'
            version = 0
        nextFileName= ""
        for comps in basePathName.split('-')[:-1]:
            nextFileName += comps +'-'
        nextFileName += str(version)+extension
        return getNextVersionNumber(nextFileName)
    return fileName

def create_EAp_layer(ds_dir,srs,legend=True,project=''):
    if project:
        project += '-'
    tmpl = {
        'datasource': getNextVersionNumber(os.path.join(ds_dir, project+'EA_p.shp')),
        'name': 'EA polygons',
        'geomtype': QGis.WKBPolygon,
        'srs': srs,
        'style': os.path.join(os.path.dirname(__file__), 'res', 'EA_p.qml'),
        'fields': EAp_FIELDS_TEMPLATE
    }
    return create_shplayer_from_template(tmpl,legend=legend)

def create_EPp_layer(ds_dir,srs,legend=True,project=''):
    if project:
        project += '-'
    tmpl = {
        'datasource': getNextVersionNumber(os.path.join(ds_dir, project+'EP_p.shp')),
        'name': 'EP polygons',
        'geomtype': QGis.WKBPolygon,
        'srs': srs,
        'style': os.path.join(os.path.dirname(__file__), 'res', 'EP_p.qml'),
        'fields': EPp_FIELDS_TEMPLATE
    }
    return create_shplayer_from_template(tmpl,legend=legend)

def create_EPl_layer(ds_dir,srs,legend=True,project=''):
    if project:
        project += '-'
    tmpl = {
        'datasource': getNextVersionNumber(os.path.join(ds_dir, project+'EP_l.shp')),
        'name': 'EP lines',
        'geomtype': QGis.WKBLineString,
        'srs': srs,
        'style': os.path.join(os.path.dirname(__file__), 'res', 'EP_l.qml'),
        'fields': EPl_FIELDS_TEMPLATE
    }
    return create_shplayer_from_template(tmpl,legend=legend)

def create_WR_layer(ds_dir,srs,legend=True,project=''):
    if project:
        project += '-'
    tmpl = {
        'datasource': getNextVersionNumber(os.path.join(ds_dir, project+'WR.shp')),
        'name': 'WR polygons',
        'geomtype': QGis.WKBPolygon,
        'srs': srs,
        'style': os.path.join(os.path.dirname(__file__), 'res', 'WR.qml'),
        'fields': WR_FIELDS_TEMPLATE
    }
    return create_shplayer_from_template(tmpl,legend=legend)

def create_WDS_layer(ds_dir,srs,legend=True,project=''):
    if project:
        project += '-'
    tmpl = {
        'datasource': getNextVersionNumber(os.path.join(ds_dir, project+'WDS.shp')),
        'name': 'WDS lines',
        'geomtype': QGis.WKBLineString,
        'srs': srs,
        'style': os.path.join(os.path.dirname(__file__), 'res', 'WDS.qml'),
        'fields': WDS_FIELDS_TEMPLATE
    }
    return create_shplayer_from_template(tmpl,legend=legend)

def create_DSV_layer(ds_dir,srs,legend=True,project=''):
    if project:
        project += '-'
    tmpl = {
        'datasource': getNextVersionNumber(os.path.join(ds_dir, project+'DSV.shp')),
        'name': 'DSV points',
        'geomtype': QGis.WKBPoint,
        'srs': srs,
        'style': os.path.join(os.path.dirname(__file__), 'res', 'DSV.qml'),
        'fields': DSV_FIELDS_TEMPLATE
    }
    return create_shplayer_from_template(tmpl,legend=legend)

def tempLayerFromPolygon(polygon,crs, properties={}):
    clipFile = os.path.join(tempfile.gettempdir(), '__' + str(uuid.uuid4()) + ".geojson")
    geojson_tmpl = '{"type":"FeatureCollection","crs":{"type":"name","properties":{"name":"urn:ogc:def:crs:%s"}},"features":[{"type":"Feature","properties":%s,"geometry":%s}]}'
    with open(clipFile, 'w') as geojson_file:
        geojson_file.write(geojson_tmpl % (crs.authid(), json.dumps(properties), polygon.exportToGeoJSON()))
    tempLayer = QgsVectorLayer(clipFile, 'clip', 'ogr')
    tempLayer.setCrs(crs)
    return tempLayer

def writeTIFF(layer,path):
    wrtr = QgsRasterFileWriter(path)
    provider = layer.dataProvider()
    pipe = QgsRasterPipe()
    pipe.set(provider.clone())
    res = wrtr.writeRaster (
        pipe,
        layer.width(),
        layer.height(),
        layer.extent(),
        layer.crs(),
    )
    if res != QgsRasterFileWriter.NoError:
        print "Error writing layer %s: %s" % (layer.name(), res)
        return ''
    else:
        return path

def writeSHP(layer,path):
    res = QgsVectorFileWriter.writeAsVectorFormat(
        layer,
        path,
        'UTF-8',
        layer.crs(),
    )
    if res != QgsVectorFileWriter.NoError:
        print "Error writing layer %s: %s" % (layer.name(),res)
        return ''
    else:
        return path