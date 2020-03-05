# -*- coding: utf-8 -*-
"""
/***************************************************************************
 hwbs
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
import shutil

from PyQt4.QtCore import QSettings, QTranslator, qVersion, QCoreApplication, Qt, QPoint, QUrl
from PyQt4.QtGui import QAction, QIcon, QMenu, QActionGroup, QDockWidget

from qgis.core import QgsNetworkAccessManager

# check for qgis_customwidgets.py
if "QGIS_PREFIX_PATH" in os.environ:
    qgis_loc = os.path.abspath(os.environ["QGIS_PREFIX_PATH"])
    bad_loc = os.path.abspath(os.path.join(qgis_loc, "python", "PyQt4", "uic", "widget-plugins", "qgis_customwidgets.py"))
    right_loc = os.path.abspath(
        os.path.join(qgis_loc, "..", "Python27", "Lib", "site-packages", "PyQt4", "uic", "widget-plugins",
                     "qgis_customwidgets.py"))
    if os.path.exists(bad_loc) and not os.path.exists(right_loc):
        print "fixed qgis_customwidgets.py bad location"
        shutil.copyfile(bad_loc, right_loc)

# Import the code for the DockWidget
from fdtm_user_interface import (
    fdtmEADialog, 
    fdtmEPDialog, 
    fdtmWRDialog, 
    fdtmWDSDialog, 
    fdtmInfoDialog, 
    fdtmPrintDialog,
    fdtmSettingsDialog,
    fdtmAboutDialog
)

from fdtm_identifygeometry import IdentifyGeometry
from fdtm_print import fdtmPrint
    
import os.path



class fdtm:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface

        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)

        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'fdtm_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&fdtm')
        # TODO: We are going to let the user set this up in a future iteration
        self.toolbar = self.iface.addToolBar(u'fdtm')
        self.toolbar.setObjectName(u'fdtm')

        self.pluginIsActive = False



    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('fdtm', message)


    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu='toolbar',
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        isMenu=None,
        checkable=None,
        checked=None,
        parent=None):

        if not parent:
            parent = self.iface.mainWindow()

        icon = QIcon(icon_path)
        if add_to_menu == 'toolbar':
            action = QAction(icon, text, parent)
        else:
            action = self.tools[add_to_menu].menu().addAction(text)
            action.setActionGroup(self.tools[add_to_menu].actionGroup)
            add_to_toolbar = False

        if checkable:
            action.setCheckable(True)
            if checked:
                action.setChecked(True)
            if callback:
                action.toggled.connect(callback)
        else:
            if callback:
                action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            self.toolbar.addAction(action)

        if isMenu:
            newMenu = QMenu()
            action.setMenu(newMenu)
            newActionGroup = QActionGroup(newMenu)
            action.actionGroup = newActionGroup

        if add_to_menu == 'toolbar':
            self.iface.addPluginToMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action


    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""
        self.tools = {
            'about': self.add_action(
                os.path.join(self.plugin_dir,'res','icon_00_about.png'),
                text=self.tr(u'about FDTM plugin'),
                callback=self.run_about,),

            'settings': self.add_action(
                os.path.join(self.plugin_dir,'res','icon_01_settings.png'),
                text=self.tr(u'settings'),
                callback=self.run_settings,),

            'print': self.add_action(
                os.path.join(self.plugin_dir,'res','icon_07_print.png'),
                text=self.tr(u'print'),
                callback=self.run_print,
                enabled_flag=False,
                isMenu=True,),

            'summary': self.add_action(
                os.path.join(self.plugin_dir,'res','icon_08_summary.png'),
                text=self.tr(u'summary'),
                callback=self.toggle_summary,
                enabled_flag=False,),

            'info': self.add_action(
                os.path.join(self.plugin_dir,'res','icon_06_info.png'),
                text=self.tr(u'info summary'),
                callback=self.run_info,
                enabled_flag=False,
                checkable=True,),

            'EP': self.add_action(
                os.path.join(self.plugin_dir,'res','icon_02_EP.png'),
                text=self.tr(u'input/edit strategies'),
                callback=self.run_EP,
                enabled_flag=False,
                checkable=True,),

            'EA': self.add_action(
                os.path.join(self.plugin_dir,'res','icon_03_EA.png'),
                text=self.tr(u'input/edit strategies'),
                callback=self.run_EA,
                enabled_flag=False,
                checkable=True,),

            'WR': self.add_action(
                os.path.join(self.plugin_dir,'res','icon_04_WR.png'),
                text=self.tr(u'input/edit water_rec'),
                callback=self.run_WR,
                enabled_flag=False,
                checkable=True,
                isMenu=True,),

            'WDS': self.add_action(
                os.path.join(self.plugin_dir,'res','icon_05_WDS.png'),
                text=self.tr(u'input/edit water_ds'),
                callback=self.run_WDS,
                enabled_flag=False,
                checkable=True,),

            'DSV': self.add_action(
                os.path.join(self.plugin_dir,'res','icon_09_DSV.png'),
                text=self.tr(u'rebuild dranaige system valve'),
                callback=self.run_DSV,
                enabled_flag=False,
                checkable=False,),
        }

        self.tools['WRp'] = self.add_action(
                os.path.join(self.plugin_dir,'res','icon_04_WR.png'),
                text=self.tr(u'point water_rec'),
                callback=None,#self.check_WR,
                enabled_flag=True,
                checkable=True,
                add_to_menu='WR',)

        self.tools['WRg'] = self.add_action(
                os.path.join(self.plugin_dir,'res','icon_04_WR.png'),
                text=self.tr(u'green roof water_rec'),
                callback=None,#self.check_WR,
                enabled_flag=True,
                checkable=True,
                add_to_menu='WR')

        self.tools['WRl'] = self.add_action(
                os.path.join(self.plugin_dir,'res','icon_04_WR.png'),
                text=self.tr(u'limited water_rec'),
                callback=None,#self.check_WR,
                enabled_flag=True,
                checked=True,
                checkable=True,
                add_to_menu='WR')

        self.tools['Print project report'] = self.add_action(
                os.path.join(self.plugin_dir,'res','icon_04_WR.png'),
                text=self.tr(u'print global report'),
                callback=self.print_global,
                enabled_flag=True,
                add_to_menu='print')

        self.tools['Print EP report'] = self.add_action(
                os.path.join(self.plugin_dir,'res','icon_04_WR.png'),
                text=self.tr(u'print EP report'),
                callback=self.print_EP,
                enabled_flag=True,
                add_to_menu='print')

        self.tools['Print EA report'] = self.add_action(
                os.path.join(self.plugin_dir,'res','icon_04_WR.png'),
                text=self.tr(u'print EA report'),
                callback=self.print_EA,
                enabled_flag=True,
                add_to_menu='print')

        self.tools['Print WR report'] = self.add_action(
                os.path.join(self.plugin_dir,'res','icon_04_WR.png'),
                text=self.tr(u'print WR report'),
                callback=self.print_WR,
                enabled_flag=True,
                add_to_menu='print')

        self.tools['Print WDS report'] = self.add_action(
                os.path.join(self.plugin_dir,'res','icon_04_WR.png'),
                text=self.tr(u'print WDS report'),
                callback=self.print_WDS,
                enabled_flag=True,
                add_to_menu='print')

        self.dlg_EA = fdtmEADialog()
        self.dlg_EP = fdtmEPDialog()
        self.dlg_WR = fdtmWRDialog()
        self.dlg_WDS = fdtmWDSDialog()
        self.dlg_info = fdtmInfoDialog()
        self.dlg_print = fdtmPrintDialog()
        self.dlg_settings = fdtmSettingsDialog(self)
        self.dlg_about = fdtmAboutDialog()
        self.dlg_about.webView.page().setNetworkAccessManager(QgsNetworkAccessManager.instance())
        # ---------------------------------------------------------------------

        self.dlg_settings.validated.connect(self.enableTools)

        self.dlg_summary = self.dlg_settings.getSummaryWidget()
        self.fdtmDockwidget=QDockWidget("FDTM summary" , self.iface.mainWindow() )
        self.fdtmDockwidget.setObjectName("fdtmSummary")
        self.fdtmDockwidget.setWidget(self.dlg_summary)
        self.iface.addDockWidget(Qt.BottomDockWidgetArea, self.fdtmDockwidget)
        self.fdtmDockwidget.hide()


    #--------------------------------------------------------------------------

    def enableTools(self, validated):
        tool_set = {'print':'icon_07_print','EP':'icon_02_EP','EA':'icon_03_EA','info':'icon_06_info','WR':'icon_04_WR','WDS':'icon_05_WDS','DSV':'icon_09_DSV','summary':'icon_08_summary'}#'print':'icon_07_print','WR':'icon_04_WR','WDS':'icon_05_WDS'
        if validated:
            disabled_sufx = ''
            self.fdtmDockwidget.show()
        else:
            disabled_sufx = '_disabled'
            self.fdtmDockwidget.hide()
        for t,f in tool_set.items():
            self.tools[t].setEnabled(validated)
            icon = QIcon(os.path.join(self.plugin_dir,'res',f + disabled_sufx +'.png'))
            self.tools[t].setIcon(icon)
        if self.dlg_settings.optionalDrainageSystemLayer.isChecked() and self.dlg_settings.optionalDrainageSystemLayer.DSVLayer():
            self.tools['DSV'].setEnabled(True)
            self.tools['DSV'].setIcon(QIcon(os.path.join(self.plugin_dir,'res', 'icon_09_DSV.png')))
        else:
            self.tools['DSV'].setEnabled(False)
            self.tools['DSV'].setIcon(QIcon(os.path.join(self.plugin_dir,'res', 'icon_09_DSV_disabled.png')))

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""

        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&fdtm'),
                action)
            self.iface.removeToolBarIcon(action)
        # remove the toolbar
        self.dlg_settings.deactivate()
        self.iface.removeDockWidget(self.fdtmDockwidget)
        del self.toolbar

    #--------------------------------------------------------------------------

    def setUncheckedActions(self,uncheckedActions):
        for action in uncheckedActions:
            self.tools[action].setChecked(False)

    def run_EP(self, checked):
        if checked:
            self.setUncheckedActions(['EA','WR','WDS'])
            self.dlg_settings.datasetWrapper.EPpWrapper.fdtm_startEditing()
        else:
            self.dlg_settings.datasetWrapper.EPpWrapper.confirmEdits()
        
    def run_EA(self, checked):
        if checked:
            self.setUncheckedActions(['EP','WR','WDS'])
            self.dlg_settings.datasetWrapper.EApWrapper.fdtm_startEditing()
        else:
            self.dlg_settings.datasetWrapper.EApWrapper.confirmEdits()

    def check_WR(self):
        self.tools['WR'].setChecked(True)

    def run_WR(self, checked):
        if checked:
            self.setUncheckedActions(['EA','EP','WDS'])
            if self.tools['WR'].actionGroup.checkedAction() == self.tools['WRp']:
                WRType = 'point'
            elif self.tools['WR'].actionGroup.checkedAction() == self.tools['WRl']:
                WRType = 'limited'
            elif self.tools['WR'].actionGroup.checkedAction() == self.tools['WRg']:
                WRType = 'greenroof'
            self.dlg_settings.datasetWrapper.WRWrapper.fdtm_startEditing(WRType)
            self.tools['WR'].actionGroup.setEnabled(False)
        else:
            self.dlg_settings.datasetWrapper.WRWrapper.confirmEdits()
            self.tools['WR'].actionGroup.setEnabled(True)
        
    def run_WDS(self, checked):
        if checked:
            self.setUncheckedActions(['EA','WR','EP'])
            self.dlg_settings.datasetWrapper.WDSWrapper.fdtm_startEditing()
        else:
            self.dlg_settings.datasetWrapper.WDSWrapper.confirmEdits()

    def toggle_summary(self):
        if self.fdtmDockwidget.isVisible():
            self.fdtmDockwidget.hide()
        else:
            self.fdtmDockwidget.show()

        
    def run_info(self, checked):
        if checked:
            self.backupMapTool = self.iface.mapCanvas().mapTool()
            layerList = [
                self.dlg_settings.EApLayer,
                self.dlg_settings.EPpLayer,
                self.dlg_settings.EPlLayer,
                self.dlg_settings.WRLayer,
                self.dlg_settings.WDSLayer
            ]
            if self.dlg_settings.optionalDrainageSystemLayer.DSVLayer():
                self.drainageSystemLayerManagement = True
                layerList.append(self.dlg_settings.datasetWrapper.DSVWrapper.lyr)
            else:
                self.drainageSystemLayerManagement = False
            #print layerList
            self.fdtm_infoMapTool = IdentifyGeometry(self.iface.mapCanvas(),layerList, self.dlg_settings.DEMLayer)
            self.fdtm_infoMapTool.geomIdentified.connect(self.editFeature)
            self.iface.mapCanvas().setMapTool(self.fdtm_infoMapTool)
            self.iface.mapCanvas().mapToolSet.connect(self.restoreInfoAction)
        else:
            if self.backupMapTool:
                self.iface.mapCanvas().mapToolSet.disconnect(self.restoreInfoAction)
                self.iface.mapCanvas().setMapTool(self.backupMapTool)

    def restoreInfoAction(self,MT):
        self.iface.mapCanvas().mapToolSet.disconnect(self.restoreInfoAction)
        self.backupMapTool = None
        self.tools['info'].setChecked(False)

    def editFeature(self, selLayer, selFeature, identifyPoint):
        if selLayer == self.dlg_settings.DEMLayer:
            if self.dlg_settings.datasetWrapper.DEMWrapper.contains(identifyPoint):
                self.dlg_settings.datasetWrapper.DEMWrapper.viewSample(identifyPoint)
            else:
                self.iface.messageBar().pushMessage("Info tool error",
                                                    "Sampling outside digital elevation model boundary",
                                                    level=1, duration=3)  # QgsMessageBar.Warning
        elif self.drainageSystemLayerManagement and selLayer == self.dlg_settings.datasetWrapper.DSVWrapper.lyr:
            self.dlg_settings.datasetWrapper.DSVWrapper.fdtm_startEditing(changeActiveLayer=False)
            self.dlg_settings.datasetWrapper.DSVWrapper.editAttributes(selFeature)
            self.dlg_settings.datasetWrapper.DSVWrapper.fdtm_commitChanges()
        else:
            selLayer.fdtm_wrapper.editAttributes(selFeature)

    def run_settings(self):
        """Run method that loads and starts the plugin"""
        self.dlg_settings.show()
        
    def run_about(self):
        """Run method that loads and starts the plugin"""
        self.dlg_about.webView.load(QUrl("http://brigaid.eu/"))
        self.dlg_about.show()
        
    def run_print(self):
        """Run method that loads and starts the plugin"""
        self.tools['print'].menu().exec_(self.toolbar.mapToGlobal(QPoint(0, self.toolbar.height())))

    def print_global(self):
        fdtmPrint.exportGlobalReport(self.dlg_settings)

    def print_EP(self):
        fdtmPrint.exportEP(self.dlg_settings)

    def print_EA(self):
        fdtmPrint.exportEA(self.dlg_settings)

    def print_WR(self):
        fdtmPrint.exportWR(self.dlg_settings)

    def print_WDS(self):
        fdtmPrint.exportWDS(self.dlg_settings)

    def undef(self):
        pass

    def run_DSV(self):
        self.dlg_settings.datasetWrapper.DSVWrapper.rebuildLayer()