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
DEFAULT_ROADS_WIDTH = 0
DESC_ROADS_RC = 'Roads'
DEFAULT_ROADS_RC = 0.82
DESC_BUILDINGS_RC = 'Buildings'
DEFAULT_BUILDINGS_RC = 0.9
DESC_OTHER_RC = 'Other'
DEFAULT_OTHER_RC = 0.6
UNLIMITED_WR_ID = 99999999
MAX_DESCR_RC_LENGTH = 20
RC_FIELD_NAME = 'RC'
DESCR_RC_FIELD_NAME = 'Descr_RC'

EPp_FIELDS_TEMPLATE = (
    ("ID", "4|10|0", "Feature id"),
    ("DESC", "10|50|0", "Description"),
    ("NOTES", "10|50|0", "Notes on project unit"),
    ("AREA", "6|18|11", "Area"),
    ("PER", "6|18|11", "Perimeter"),
    ("SP", "6|18|11", "SP_Starting protection level (existing)"),
    ("MP", "6|18|11", "MP_Maximum_protection level (existing)"),
    ("MP_USER", "6|18|11", "MPD_Maximum protection level (design)"),
    ("TYP", "10|50|0", "Protection measure"),
    ("COST", "6|18|11", "Costs"),
    ("ROADS_W", "6|18|11", "Roads width for project unit"),
    ("VG", "6|18|11", "Ground Volume from level 0"),
    ("CW", "6|18|11", u"CW m\u00B3"),
    ("CW_DRAIN", "6|18|11", u"Drained CW m\u00B3"),
    ("RC", "6|18|11", "Mean Runoff coefficient"),
    ("RC_DEF", "10|254|0", "Run off coefficient parameters"),
    ("RC_USER", "6|18|11", "User Runoff coefficient"),
    ("RC_DETAIL", "10|50|0", "Detailed runoff coefficients"),
    ("ID_USER", "10|30|0", "Utente che ha modificato la scheda"),
    ("DATE_CR", "16|10|0", "Data di creazione scheda"),
    ("DATE_MOD", "16|10|0", "Data di modifica della scheda"),
)

EAp_FIELDS_TEMPLATE = (
    ("ID", "4|10|0", "Feature id"),
    ("DESC", "10|50|0", "Description"),
    ("NOTES", "10|50|0", "Notes on project unit"),
    ("AREA", "6|18|11", "Area"),
    ("PER", "6|18|11", "Perimeter"),
    ("SP", "6|18|11", "SP_Starting protection level (existing)"),
    ("MP", "6|18|11", "MP_Maximum protection level (existing)"),
    ("MP_USER", "6|18|11", "MPD_Maximum protection level (design)"),
    ("VG", "6|18|11", "Ground Volume from level 0"),
    ("VOL", "6|18|11", "Carried volume"),
    ("VOL_EX", "6|18|11", "Volume esistente dalla quota 0"),
    ("TYP", "10|50|0", "Protection measure"),
    ("COST", "6|18|11", "Costs"),
    ("CW", "6|18|11", u"CW m\u00B3"),
    ("CW_DRAIN", "6|18|11", u"Drained CW m\u00B3"),
    ("RC", "6|18|11", "Mean Runoff coefficient"),
    ("RC_DEF", "10|254|0", "Run off coefficient parameters"),
    ("RC_USER", "6|18|11", "User Runoff coefficient"),
    ("RC_DETAIL", "10|50|0", "Detailed runoff coefficients"),
    ("ID_USER", "10|30|0", "Utente che ha modificato la scheda"),
    ("DATE_CR", "16|10|0", "Data di creazione scheda"),
    ("DATE_MOD", "16|10|0", "Data di modifica della scheda"),
)

EPl_FIELDS_TEMPLATE = (
    ("ID", "4|10|0", "Feature id"),
    ("NOTES", "10|50|0", "Notes on project unit"),
    ("ID_EP", "4|10|0", "Collegamento ad EP id"),
    ("SP_SEG", "6|18|11", "SP (Segment)"),
    ("MP_SEG", "6|18|11", "MP (Segment)"),
    ("MP_SEG_U", "6|18|11", "MPD (Segment)"),
    ("BH", "6|18|11", "MP_SEG-SP_SEG"),
    ("LENGTH", "6|18|11", "Segment length"),
    ("TYP", "10|50|0", "Protection measure"),
    ("TEMP_TYP", "10|10|0", "Temporary type"),
    ("COST", "6|18|11", "Costs"),
    ("ID_USER", "10|30|0", "Utente che ha modificato la scheda"),
    ("DATE_CR", "16|10|0", "Data di creazione scheda"),
    ("DATE_MOD", "16|10|0", "Data di modifica della scheda"),
)


WR_FIELDS_TEMPLATE = (
    ("ID", "4|10|0", 'Feature id'),
    ("DESC", "10|50|0", "Description"),
    ("NOTES", "10|50|0", "Notes on project unit"),
    ("AREA", "6|18|11", 'Area'),
    ("PER", "6|18|11", 'Perimeter'),
    ("SP", "6|18|11", 'Minimum level (existing)'),
    ("MP", "6|18|11", 'Maximun level (existing)'),
    ("MP_USER", "6|18|11", 'MPD (Design)'),
    ("VG", "6|18|11", "Ground Volume from level 0"),
    ("VOL", "6|18|11", 'Carried volume'),
    #("MOD", "10|50|0", u'Modalità di inserimento'),
    ("TYP", "10|50|0", 'Tipology'),
    ("COST", "6|18|11", 'Costs'),
    ("CAP", "6|18|11", u"Calculated capacity m\u00B3"),
    ("CAP_USER", "6|18|11", u"User capacity m\u00B3"),
    ("COLLECTED", "6|18|11", u'Water collected m\u00B3'),
    ("ID_USER", "10|30|0", "Utente che ha modificato la scheda"),
    ("DATE_CR", "16|10|0", "Data di creazione scheda"),
    ("DATE_MOD", "16|10|0", "Data di modifica della scheda"),
)

WDS_FIELDS_TEMPLATE = (
    ("ID", "4|10|0", 'Feature id'),
    ("DESC", "10|50|0", "Description"),
    ("NOTES", "10|50|0", "Notes on project unit"),
    ("ID_EP", "4|10|0", 'EP origin'),
    ("ID_EA", "4|10|0", 'EA origin'),
    ("ID_WR", "4|10|0", 'WR destination'),
    ("CW_EP", "6|18|11", u'CW_EP m\u00B3'),
    ("CW_EA", "6|18|11", u'CW_EA m\u00B3'),
    ("CAP_WR", "6|18|11", u'CAP_WR m\u00B3'),
    ("MP_EP", "6|18|11", 'Max elevation of EP origin'),
    ("MP_EA", "6|18|11", 'Max elevation of EA origin'),
    ("MP_WR", "6|18|11", 'Max elevation of WR origin'),
    ("LENGTH", "6|18|11", 'Length of WDS segment'),
    ("TYP", "10|20|0", 'Type'),
    ("DEST_TYP", "10|10|0", 'Destination type (limited/unlimited)'),
    ("VALVE_TYP", "10|50|0", 'Valve type (pump/check valve'),
    ("COST", "6|18|11", ''),
    ("ID_USER", "10|30|0", ''),
    ("DATE_CR", "16|10|0", ''),
    ("DATE_MOD", "16|10|0", ''),
)

DSV_FIELDS_TEMPLATE = (
    ("ID", "4|10|0", 'Feature id'),
    ("DESC", "10|50|0", "Description"),
    ("NOTES", "10|50|0", "Notes on project unit"),
    ("ID_EP", "4|10|0", 'EP origin'),
    ("ID_EA", "4|10|0", 'EP origin'),
    ("ELEV", "6|18|11", 'Elevation on ground'),
    ("TYP", "10|50|0", 'Valve type'),
    ("COST", "6|18|11", ''),
    ("ID_USER", "10|30|0", ''),
    ("DATE_CR", "16|10|0", ''),
    ("DATE_MOD", "16|10|0", ''),
)

EP_TYPES_TABLE = [
    #['item value', 'item label', 'validation_rule', 'mobile cost x unit', 'fixed cost x unit'],
    ['Existing', 'existing', 'validation_rule:', '0.0', '0'],
    ['Sand', 'sand', 'validation_rule:', '1000.0', '1000'],
    ['Airdam', 'airdam', 'validation_rule:', '5000.0', '5000'],
    ['Concrete', 'concrete', 'validation_rule:', '15000.0', '15000'],
    ['MiniMose', 'MiniMose', 'validation_rule:', '13000.0', '13000'],
    ['Rialzo5m', 'Rialzo5m', 'validation_rule:', '2000.0', '2000'],
    ['Rialzo10m', 'Rialzo10m', 'validation_rule:', '6000.0', '6000'],
    ['Mobilebarrier', 'MobileBarrier', 'validation_rule:', '1000.0', '1000'],
]

EP_TEMP_TYPES_TABLE = [
    #['item value', 'item label', 'validation_rule', 'attribution_rule', 'cost x unit'],
    ['fixed', 'fixed protection', 'validation_rule:', 'attribution_rule:', '0'],
    ['mobile', 'mobile protection', 'validation_rule:', 'attribution_rule:', '0'],
]

EA_TYPES_TABLE = [
    #['item value', 'item label', 'validation_rule', 'attribution_rule', 'cost x unit'],
    ['Groundrise', 'groundrise', 'validation_rule:', 'attribution_rule:', '25'],
    ['Platform', 'platform', 'validation_rule:', 'attribution_rule:', '2000'],
    ['Pilework', 'pilework', 'validation_rule:', 'attribution_rule:', '1500'],
]

WR_TYPES_TABLE_point = [
    #['item value', 'item label', 'validation_rule', 'attribution_rule', 'cost x unit'],
    ['tank', 'tank', 'validation_rule:', 'attribution_rule:', '1000'],
    #['rain_garden', 'giardino pluviale', 'validation_rule:', 'attribution_rule:', '150'],
]

WR_TYPES_TABLE_greenroof = [
    #['item value', 'item label', 'validation_rule', 'attribution_rule', 'cost x unit'],
    ['green_roof_01', u'green roof 0.01 m\u00B3/m\u00B2', 'validation_rule:', '0.01', '100'],
    ['green_roof_02', u'green roof 0.02 m\u00B3/m\u00B2', 'validation_rule:', '0.02', '150'],
    ['green_roof_03', u'green roof 0.03 m\u00B3/m\u00B2', 'validation_rule:', '0.03', '200'],
    ['green_roof_04', u'green roof 0.04 m\u00B3/m\u00B2', 'validation_rule:', '0.04', '250'],
    ['green_roof_09', u'green roof 0.09 m\u00B3/m\u00B2', 'validation_rule:', '0.09', '570']
    #['rain_garden', 'giardino pluviale', 'validation_rule:', 'attribution_rule:', '150'],
]

WR_TYPES_TABLE_limited = [
    #['item value', 'item label', 'validation_rule', 'attribution_rule', 'cost x unit'],
    ['Basin', 'basin', 'validation_rule:', 'attribution_rule:', '300'],
    ['Floodable_park', 'floodable_park', 'validation_rule:', 'attribution_rule:', '400'],
    ['Rain_garden', 'rain_garden', 'validation_rule:', 'attribution_rule:', '3000'],
]

WR_TYPES_TABLE_unlimited = [
    #['item value', 'item label', 'validation_rule', 'attribution_rule', 'cost x unit'],
    ['unlimited_basin', 'unlimited_basin', 'validation_rule:', 'attribution_rule:', '0'],
]

WDS_TYPES_TABLE = [
    #['item value', 'item label', 'validation_rule', 'attribution_rule', 'cost x unit'],
    ['tipo_x', 'tipo x', 'validation_rule:', 'attribution_rule:', '5'],
    ['tipo_y', 'tipo y', 'validation_rule:', 'attribution_rule:', '15'],
    ['tipo_z', 'tipo z', 'validation_rule:', 'attribution_rule:', '150'],
    #['invalid', 'invalid', 'validation_rule:', 'attribution_rule:', '0'],
]

DSV_TYPES_TABLE = [
    #['item value', 'item label', 'validation_rule', 'attribution_rule', 'cost x unit'],
    ['not_set', 'not set', 'validation_rule:', 'attribution_rule:', '0'],
    ['non_return_valve', 'non return valve', 'validation_rule:', 'attribution_rule:', '800'],
    ['pump', 'pump', 'validation_rule:', 'attribution_rule:', '12000'],
    ['interruption', 'interruption', 'validation_rule:', 'attribution_rule:', '500'],
]

WDS_DEST_TABLE = [
    #['item value', 'item label', 'validation_rule', 'attribution_rule', 'cost x unit'],
    ['limited', 'lead to water repository', 'validation_rule:', 'attribution_rule:', '0'],
    ['unlimited', 'leads to unlimited basin', 'validation_rule:', 'attribution_rule:', '0'],
]

WDS_VALVE_TABLE = [
    #['item value', 'item label', 'validation_rule', 'attribution_rule', 'cost x unit'],
    ['pump', 'pump', 'validation_rule:', 'attribution_rule:', '12000'],
    ['check valve', 'check valve', 'validation_rule:', 'attribution_rule:', '5000'],
    #['link', 'link', 'validation_rule:', 'attribution_rule:', '0'],
]

RC_TYPES_TABLE = [
    #['item value', 'item label'],
    [0.1, 'Forest',],
    [0.2, 'Parks,cemeteries',],
    [0.3, 'Cultivations, turf',],
    [0.4, 'Gardens, suburbs',],
    [0.5, 'Bare soil,dirt roads',],
    [0.6, 'Loam, macadam',],
    [0.7, 'Industrial, clay',],
    [0.8, 'Pavements,flat roofs',],
    [0.9, 'Roads, pitched roofs',],
    [1.0, 'Impervious surfaces',],
]

