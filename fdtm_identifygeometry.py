#-----------------------------------------------------------
#
#
# Copyright    : (C) 2013 Denis Rouzaud
# Email        : denis.rouzaud@gmail.com
#
#-----------------------------------------------------------
#
# licensed under the terms of GNU GPL 2
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this progsram; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#
#---------------------------------------------------------------------

from PyQt4.QtCore import pyqtSignal
from PyQt4.QtGui import QPixmap, QCursor
from qgis.core import QgsVectorLayer, QgsFeature, QgsPoint
from qgis.gui import QgsMapToolIdentify

#from cursor import Cursor


class IdentifyGeometry(QgsMapToolIdentify):
    geomIdentified = pyqtSignal(QgsVectorLayer, QgsFeature, QgsPoint)

    def __init__(self, canvas, layerList, DEM=None):
        self.canvas = canvas
        self.layerList = layerList
        self.DEM = DEM
        QgsMapToolIdentify.__init__(self, canvas)
        self.setCursor(QCursor())

    def canvasReleaseEvent(self, mouseEvent):
        results = self.identify(mouseEvent.x(), mouseEvent.y(), layerList=self.layerList, mode=self.LayerSelection )
        if len(results) > 0:
            self.geomIdentified.emit(results[0].mLayer, QgsFeature(results[0].mFeature), QgsPoint())
        else:
            clickOnMap = self.canvas.getCoordinateTransform().toMapCoordinates(mouseEvent.x(), mouseEvent.y())
            self.geomIdentified.emit(self.DEM, QgsFeature(), clickOnMap)

