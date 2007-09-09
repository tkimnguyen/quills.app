#
# Authors: Maurits van Rees <m.van.rees@zestsoftware.nl>
#
# Copyright 2006, Maurits van Rees
#
# Adapted from topic.py.
#
# This file is part of Quills
#
# Quills is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# Quills is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Quills; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
###############################################################################

# Standard library imports
from types import StringTypes

# Zope imports
from zope.interface import implements
from zope.component.interface import interfaceToName
from Acquisition import Implicit, aq_base
from DateTime.DateTime import DateTime, DateError
from OFS.Traversable import Traversable

# CMF imports
from Products.CMFCore.utils import getToolByName

# Quills imports
from quills.core.interfaces import IWeblog, IWeblogEnhanced
from quills.core.interfaces import IWeblogEntry, IPossibleWeblogEntry
from quills.core.interfaces import IWeblogArchive, IWeblogArchiveContainer
from acquiringactions import AcquiringActionProvider
from weblogentrybrain import WeblogEntryCatalogBrain
from utilities import EvilAATUSHack, QuillsMixin


class BaseArchive(QuillsMixin, AcquiringActionProvider, Traversable, Implicit):
    """Implementation of IWeblogArchive.
    """

    __allow_access_to_unprotected_subobjects__ = EvilAATUSHack()

    def __init__(self, *args, **kwargs):
        self.results = None

    def Description(self):
        """
        """
        return 'Archived weblog posts.'

    def __len__(self):
        """See IWeblogArchive.
        """
        return len(self.getEntries())


class ArchiveContainer(BaseArchive):

    implements(IWeblogArchiveContainer)

    def __init__(self, id):
        self.id = str(id)
        self._years = None
        super(ArchiveContainer, self).__init__(self, id)

    def getId(self):
        """
        """
        return self.id

    def Title(self):
        """
        """
        return self.getId()

    def _getEntryYears(self):
        """
        """
        if self._years is None:
            # Make sure self.results is populated
            self.getEntries()
            years= {}
            for entry in self.results:
                year = entry['effective'].strftime('%Y')
                years[year] = year
            years = years.keys()
            years.sort()
            self._years = years
        return self._years

    def getSubArchives(self):
        """
        """
        years = self._getEntryYears()
        return [YearArchive(year).__of__(self) for year in years]

    def getEntries(self):
        """
        """
        # Just return the weblog's getEntries.
        self.results = self.getParentWeblog().getEntries()
        return self.results


class BaseDateArchive(BaseArchive):

    implements(IWeblogArchive)

    def getId(self):
        """
        """
        year = self.year
        month = getattr(self, 'month', None)
        day = getattr(self, 'day', None)
        if day is not None:
            return str(day)
        elif month is not None:
            return str(month)
        else:
            return str(year)

    def Title(self):
        """
        """
        return '%s %s' % (self.getTimeUnit(), self.getId())

    def getEntries(self):
        """
        """
        if self.results is None:
            min_datetime, max_datetime = self._getDateRange()
            catalog = getToolByName(self, 'portal_catalog')
            catalog._catalog.useBrains(WeblogEntryCatalogBrain)
            weblog = self.getParentWeblogContentObject()
            path = '/'.join(weblog.getPhysicalPath())
            ifaces = [interfaceToName(catalog.aq_parent, IWeblogEntry),
                      interfaceToName(catalog.aq_parent, IPossibleWeblogEntry)]
            results = catalog(
                object_provides={'query' : ifaces, 'operator' : 'or'},
                path={'query':path, 'level': 0},
                review_state='published',
                effective={
                     'query' : [min_datetime, max_datetime],
                     'range': 'minmax'}
                )
            self.results = results
        return self.results


class YearArchive(BaseDateArchive):

    def __init__(self, year):
        # Check year is of the right sort.
        int(year)
        self.year = year
        self._months = None
        super(BaseDateArchive, self).__init__(self, id)

    def getTimeUnit(self):
        return 'Year'

    def _getEntryMonths(self):
        """
        """
        if self._months is None:
            # Make sure self.results is populated
            self.getEntries()
            months = {}
            for entry in self.results:
                month = entry['effective'].strftime('%m')
                months[month] = month
            months = months.keys()
            months.sort()
            self._months = months
        return self._months

    def _getDateRange(self):
        min_datetime = DateTime('%s/01/01' % self.year)
        max_datetime = DateTime('%s/12/31' % self.year)
        return min_datetime, max_datetime

    def getSubArchives(self):
        """
        """
        months = self._getEntryMonths()
        return [MonthArchive(self.year, month).__of__(self) for month in months]


class MonthArchive(BaseDateArchive):

    def __init__(self, year, month):
        int(year)
        int(month)
        self.year = year
        self.month = month
        self._days = None
        super(BaseDateArchive, self).__init__(self, id)

    def getTimeUnit(self):
        return 'Month'

    def _getEntryDays(self):
        """
        """
        if self._days is None:
            # Make sure self.results is populated
            self.getEntries()
            days = {}
            for entry in self.results:
                day = entry['effective'].strftime('%d')
                days[day] = day
            days = days.keys()
            days.sort()
            self._days = days
        return self._days

    def getSubArchives(self):
        """
        """
        days = self._getEntryDays()
        return [DayArchive(self.year, self.month, day).__of__(self) for day in days]

    def _getDateRange(self):
        # XXX Test me!  Need test to ensure that months with less than 31 days
        # are correctly handled.
        min_datetime = DateTime('%s/%s/01' % (self.year, self.month))
        day = 31
        while 1:
            try:
                max_datetime = DateTime('%s/%s/%s' % (self.year, self.month, day))
                break
            except DateError:
                day = day - 1
        return min_datetime, max_datetime


class DayArchive(BaseDateArchive):
    """
    """

    def __init__(self, year, month, day):
        int(year)
        int(month)
        int(day)
        self.year = year
        self.month = month
        self.day = day
        self._items = {}
        super(BaseDateArchive, self).__init__(self, id)

    def getTimeUnit(self):
        return 'Day'

    def getSubArchives(self):
        """
        """
        []

    def _getDateRange(self):
        min_datetime = DateTime('%s/%s/%s' % (self.year, self.month, self.day))
        max_datetime = DateTime('%s/%s/%s' % (self.year, self.month, self.day))
        return min_datetime, max_datetime+1
    
    def __getitem__(self, key):
        if self._items.has_key(key):
            return self._items[key]
        min_datetime, max_datetime = self._getDateRange()
        catalog = getToolByName(self, 'portal_catalog')
        results = catalog(
                getId=key,
                review_state='published',
                effective={
                     'query' : [min_datetime, max_datetime],
                     'range': 'minmax'}
                )
        if len(results) != 1:
            # We can't find a suitable weblog entry, so raise a KeyError. This
            # causes the publisher to resort to looking-up/acquiring views.
            raise KeyError
        obj_brain = results[0]
        obj = obj_brain.getObject()
        self._items[key] = obj
        return obj