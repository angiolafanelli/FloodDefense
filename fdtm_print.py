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
import sys
import json
import uuid
import tempfile
import subprocess
import platform
import math

from qgis.core import QGis, QgsComposition, QgsComposerMap, QgsComposerAttributeTable, QgsComposerTableColumn, QgsVectorLayer, QgsMapLayerRegistry
from qgis.gui import QgsProjectionSelectionWidget,QgsMessageBar

from PyQt4.QtGui import qApp,QDoubleValidator, QFileDialog ,QProgressBar, QFileDialog
from PyQt4.QtCore import Qt, pyqtSignal
from PyQt4.QtXml import QDomDocument

from jinja2 import Environment, FileSystemLoader
from PyPDF2 import PdfFileMerger


def merge_pdfs(pdf_list,output):
    merger = PdfFileMerger()
    for pdf in pdf_list:
        merger.append(pdf)
    merger.write(output)

def open_file(targetFile):
    if sys.platform == "win32":
        os.startfile(targetFile)
    else:
        opener = "open" if sys.platform == "darwin" else "xdg-open"
        subprocess.call([opener, targetFile])

class progressBar:
    def __init__(self, parent, msg = '', steps=0):
        '''
        progressBar class instatiation method. It creates a QgsMessageBar with provided msg and a working QProgressBar
        :param parent:
        :param msg: string
        '''
        self.iface = parent.iface
        widget = self.iface.messageBar().createMessage("fdtm plugin:",msg)
        self.progressBar = QProgressBar()
        self.progressBar.setRange(0,steps) #(1,steps)
        self.progressBar.setValue(0)
        self.progressBar.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        widget.layout().addWidget(self.progressBar)
        qApp.processEvents()
        self.iface.messageBar().pushWidget(widget, QgsMessageBar.INFO, 50)
        qApp.processEvents()

    def setStep(self,step):
        self.progressBar.setValue(step)
        qApp.processEvents()

    def stop(self, msg = ''):
        '''
        the progressbar is stopped with a succes message
        :param msg: string
        :return:
        '''
        self.iface.messageBar().clearWidgets()
        message = self.iface.messageBar().createMessage("fdtm plugin:",msg)
        self.iface.messageBar().pushWidget(message, QgsMessageBar.SUCCESS, 3)

class fdtmPrint:

    PREDEFINED_SCALES = [10000.0, 5000.0, 2000.0, 1000.0, 500.0, 200.0]

    def __init__(self, settings_instance):
        self.settings_instance = settings_instance
        self.iface = settings_instance.iface
        self.env = Environment(
            loader=FileSystemLoader(os.path.join(os.path.dirname(__file__), 'res')),
        )

    def exportToPdf(self,print_context,targetFile=None):
        self.iface.mapCanvas().setDestinationCrs(self.settings_instance.projection.crs())
        myComposition = QgsComposition(self.iface.mapCanvas().mapSettings())
        template = self.env.get_template(print_context['template'])

        custom_qpt = template.render(CONTEXT=print_context)
        myDocument = QDomDocument()
        myDocument.setContent(custom_qpt)
        myComposition.loadFromTemplate(myDocument)

        suggestedFile = os.path.join(self.settings_instance.projectFolderPath.text(),print_context['title']+".pdf")
        if not targetFile:
            targetFile = QFileDialog.getSaveFileName(None,"Export "+print_context['job'], suggestedFile, "*.pdf")
            interactive = True
            if not targetFile:
                return
        else:
            interactive = None

        outputDir = tempfile.gettempdir()

        with open(os.path.join(targetFile+'.qpt'), "wb") as qpt_file:
            qpt_file.write(custom_qpt)

        if   print_context['type'] == 'report':
            myComposition.exportAsPDF(targetFile)

        elif print_context['type'] == 'map':
            print myComposition.getComposerMapById(0)
            print myComposition.getComposerItemById('5')

            for composer_map in myComposition.composerMapItems():
                print composer_map, composer_map.id()

            fdtm_extent = None
            for layer in [self.settings_instance.EPpLayer,self.settings_instance.EApLayer,self.settings_instance.WRLayer,self.settings_instance.WDSLayer] :
                if layer.featureCount() > 0:
                    if fdtm_extent:
                        fdtm_extent.combineExtentWith(layer.extent())
                    else:
                        fdtm_extent = layer.extent()
            fdtm_extent.scale(1.1)
            composer_map.zoomToExtent(fdtm_extent)
            composer_map.updateItem()
            myComposition.refreshItems()

            myComposition.exportAsPDF(targetFile)

        elif print_context['type'] == 'mapppp':
            print print_context
            myComposition = QgsComposition(self.iface.mapCanvas().mapSettings())
            myComposition.setPlotStyle(QgsComposition.Print)
            myComposition.setPaperSize(297,210)
            composer_map = QgsComposerMap(myComposition, 10, 10, 190, 190)
            fdtm_extent = self.settings_instance.EPpLayer.extent()
            for layer in [self.settings_instance.EApLayer,self.settings_instance.WRLayer,self.settings_instance.WDSLayer]:
                fdtm_extent.combineExtentWith(layer.extent())
            composer_map.zoomToExtent(fdtm_extent)
            composer_map.updateItem()
            myComposition.addItem(composer_map)

            table = QgsComposerAttributeTable(myComposition)
            table.setItemPosition(205, 170)
            table.setVectorLayer(QgsMapLayerRegistry.instance().mapLayer(print_context['id']))
            table.setMaximumNumberOfFeatures(20)
            table.setFilterFeatures(True)
            col1 = QgsComposerTableColumn()
            col1.setAttribute('types')
            col1.setHeading("types")
            col2 = QgsComposerTableColumn()
            col2.setAttribute('project units')
            col2.setHeading("project units")
            col3 = QgsComposerTableColumn()
            col3.setAttribute('Areas')
            col3.setHeading("Areas")
            col4 = QgsComposerTableColumn()
            col4.setAttribute('Lengths')
            col4.setHeading("Lengths")
            col5 = QgsComposerTableColumn()
            col5.setAttribute('Cost')
            col5.setHeading("Cost")
            table.setColumns([col1, col2, col3, col4, col5])
            myComposition.addItem(table)

            myComposition.exportAsPDF(targetFile)

        elif print_context['type'] == 'atlas':

            myComposition.setAtlasMode(QgsComposition.ExportAtlas)
            for composer_map in myComposition.composerMapItems():
                print composer_map, composer_map.id()

            atlas = myComposition.atlasComposition()
            atlas.setComposerMap(composer_map) #DEPRECATED
            atlas.setPredefinedScales(self.PREDEFINED_SCALES)
            composer_map.setAtlasDriven(True)
            composer_map.setAtlasScalingMode(QgsComposerMap.Predefined)

            atlas.beginRender()
            rendered_pdf = []
            progress = progressBar(self,"exporting "+print_context['job'],atlas.numFeatures())
            for i in range(0, atlas.numFeatures()):
                atlas.prepareForFeature(i)
                current_filename = atlas.currentFilename()
                file_name = '_'.join(current_filename.split())
                file_path = '%s.pdf' % file_name
                path = os.path.join(outputDir, file_path)
                myComposition.exportAsPDF(path)
                rendered_pdf.append(path)
                progress.setStep(i)
            progress.stop(print_context['job'] + "exported to " + targetFile)
            atlas.endRender()

            merge_pdfs(rendered_pdf,targetFile)

        if interactive:
            open_file(targetFile)

        return targetFile

    @staticmethod
    def exportEP(settings_instance,targetFile=None):
        print_context = {
            'type': 'atlas',
            'job': 'EP summary',
            'title': 'EP',
            'template': "EP_a4.qpt",
            'id': settings_instance.EPpLayer.id(),
            'name': settings_instance.EPpLayer.name(),
            'source': settings_instance.EPpLayer.source(),
            'relation': 'EP_lines_on_polygons'
        }
        print_engine = fdtmPrint(settings_instance)
        return print_engine.exportToPdf(print_context,targetFile=targetFile)

    @staticmethod
    def exportEPReport(settings_instance,targetFile=None):
        print_context = {
            'type': 'report',
            'job': 'EP report',
            'title': 'EP_report',
            'template': "EP_report_a4.qpt",
            'id': settings_instance.EPpLayer.id(),
            'name': settings_instance.EPpLayer.name(),
            'source': settings_instance.EPpLayer.source(),
            'pages': int(math.ceil(settings_instance.EPpLayer.featureCount()/34))
        }
        print_engine = fdtmPrint(settings_instance)
        return print_engine.exportToPdf(print_context,targetFile=targetFile)

    @staticmethod
    def exportEA(settings_instance,targetFile=None):
        print_context = {
            'type': 'atlas',
            'job': 'EA summary',
            'title': 'EA',
            'template': "EA_a4.qpt",
            'id': settings_instance.EApLayer.id(),
            'name': settings_instance.EApLayer.name(),
            'source': settings_instance.EApLayer.source(),
            'relation': ''
        }
        print_engine = fdtmPrint(settings_instance)
        return print_engine.exportToPdf(print_context,targetFile=targetFile)

    @staticmethod
    def exportEAReport(settings_instance,targetFile=None):
        print_context = {
            'type': 'report',
            'job': 'EA report',
            'title': 'EA_report',
            'template': "EA_report_a4.qpt",
            'id': settings_instance.EApLayer.id(),
            'name': settings_instance.EApLayer.name(),
            'source': settings_instance.EApLayer.source(),
        }
        print_engine = fdtmPrint(settings_instance)
        return print_engine.exportToPdf(print_context,targetFile=targetFile)


    @staticmethod
    def exportWR(settings_instance,targetFile=None):
        print_context = {
            'type': 'atlas',
            'job': 'WR summary',
            'title': 'WR',
            'template': "WR_a4.qpt",
            'id': settings_instance.WRLayer.id(),
            'name': settings_instance.WRLayer.name(),
            'source': settings_instance.WRLayer.source(),
            'relation': ''
        }
        print_engine = fdtmPrint(settings_instance)
        return print_engine.exportToPdf(print_context,targetFile=targetFile)

    @staticmethod
    def exportWRReport(settings_instance,targetFile=None):
        print_context = {
            'type': 'report',
            'job': 'WR report',
            'title': 'WR_report',
            'template': "WR_report_a4.qpt",
            'id': settings_instance.WRLayer.id(),
            'name': settings_instance.WRLayer.name(),
            'source': settings_instance.WRLayer.source(),
        }
        print_engine = fdtmPrint(settings_instance)
        return print_engine.exportToPdf(print_context,targetFile=targetFile)

    @staticmethod
    def exportWDS(settings_instance,targetFile=None):
        print_context = {
            'type': 'atlas',
            'job': 'WDS summary',
            'title': 'WDS',
            'template': "WDS_a4.qpt",
            'id': settings_instance.WDSLayer.id(),
            'name': settings_instance.WDSLayer.name(),
            'source': settings_instance.WDSLayer.source(),
            'relation': ''
        }
        print_engine = fdtmPrint(settings_instance)
        return print_engine.exportToPdf(print_context,targetFile=targetFile)

    @staticmethod
    def exportWDSReport(settings_instance,targetFile=None):
        print_context = {
            'type': 'report',
            'job': 'WDS report',
            'title': 'WDS_report',
            'template': "WDS_report_a4.qpt",
            'id': settings_instance.WDSLayer.id(),
            'name': settings_instance.WDSLayer.name(),
            'source': settings_instance.WDSLayer.source(),
        }
        print_engine = fdtmPrint(settings_instance)
        return print_engine.exportToPdf(print_context,targetFile=targetFile)

    @staticmethod
    def exportDSVReport(settings_instance,targetFile=None):
        if settings_instance.optionalDrainageSystemLayer.DSVLayer():
            print_context = {
                'type': 'report',
                'job': 'DSV report',
                'title': 'DSV_report',
                'template': "DSV_report_a4.qpt",
                'id': settings_instance.optionalDrainageSystemLayer.DSVLayer().id(),
                'name': settings_instance.optionalDrainageSystemLayer.DSVLayer().name(),
                'source': settings_instance.optionalDrainageSystemLayer.DSVLayer().source(),
            }
            print_engine = fdtmPrint(settings_instance)
            return print_engine.exportToPdf(print_context,targetFile=targetFile)
        else:
            return None

    @staticmethod
    def exportGlobalSummary(settings_instance,targetFile=None):
        #settings_instance.getSummaryWidget().updateTotals()
        csvFileName = settings_instance.summaryWidget.globalSummaryToCSV()
        csvLayer = QgsVectorLayer(csvFileName, 'summary report', 'ogr')
        QgsMapLayerRegistry.instance().addMapLayer(csvLayer)
        print_context = {
            'type': 'map',
            'job': 'project summary report',
            'title': settings_instance.projectDescription.text(),
            'template': "global_map.qpt",
            'id': csvLayer.id(),
            'name': csvLayer.name(),
            'source': csvLayer.source(),
        }
        print_engine = fdtmPrint(settings_instance)
        result = print_engine.exportToPdf(print_context,targetFile=targetFile)
        QgsMapLayerRegistry.instance().removeMapLayer(csvLayer)
        return result

    @staticmethod
    def exportGlobalReport(settings_instance,targetFile=None):

        suggestedFile = os.path.join(settings_instance.projectFolderPath.text(),"summary_report.pdf")
        if not targetFile:
            targetFile = QFileDialog.getSaveFileName(None,"Export project summary report", suggestedFile, "*.pdf")
            interactive = True
            if not targetFile:
                return
        else:
            interactive = None

        exported_pdf = []
        reports = [fdtmPrint.exportGlobalSummary, fdtmPrint.exportEPReport, fdtmPrint.exportEAReport, fdtmPrint.exportWRReport, fdtmPrint.exportWDSReport, fdtmPrint.exportDSVReport]
        progress = progressBar(settings_instance, "exporting summary report", len(reports))
        for i,export in enumerate(reports):
            if export:
                pdfFile = tempfile.NamedTemporaryFile(mode='w',suffix='.pdf',delete=False)
                exported_pdf.append(export(settings_instance, targetFile=pdfFile.name))
                progress.setStep(i)
        progress.stop("Summary report exported to " + targetFile)
        #print exported_pdf

        merge_pdfs(exported_pdf,targetFile)
        if interactive:
            open_file(targetFile)
        return targetFile