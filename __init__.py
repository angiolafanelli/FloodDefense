# -*- coding: utf-8 -*-
"""
/***************************************************************************
 hwbs
                                 A QGIS plugin
 testing hwbs
                             -------------------
        begin                : 2017-05-11
        copyright            : (C) 2017 by enrico ferreguti
        email                : enricofer@gmail.com
        git sha              : $Format:%H$
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
 This script initializes the plugin, making it known to QGIS.
"""
import os 
import site
import sys

sys.path.append(os.path.dirname(__file__))

site.addsitedir(os.path.join(os.path.dirname(__file__),'extlibs'))

# noinspection PyPep8Naming
def classFactory(iface):  # pylint: disable=invalid-name
    """Load hwbs class from file hwbs.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from .fdtm import fdtm
    return fdtm(iface)
