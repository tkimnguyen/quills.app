# Zope imports
from zope.component import adapts, getMultiAdapter
from zope.component import queryMultiAdapter
from zope.app.publisher.browser import getDefaultViewName
from zope.publisher.interfaces.http import IHTTPRequest
from ZPublisher.BaseRequest import DefaultPublishTraverse

# Quills imports
from quills.core.interfaces import IWeblog
from quills.core.interfaces import IWeblogEntry
from quills.core.interfaces import IWeblogArchive
from quills.core.interfaces import IWeblogConfiguration
from quills.core.interfaces import IPossibleWeblogEntry
from quills.core.interfaces import ITopicContainer

# Local imports
from topic import Topic
from topic import TopicContainer
from topic import AuthorContainer
from archive import ArchiveContainer
from archive import YearArchive
from archive import MonthArchive
from archive import DayArchive


class WeblogTraverser(DefaultPublishTraverse):

    adapts(IWeblog, IHTTPRequest)
    
    def publishTraverse(self, request, name):
        # Only intercept certain names...
        if name == 'topics':
            # XXX 'topics' should probably not be hard-coded here.  Rather,
            # it should be looked up on weblog config.
            return TopicContainer('topics').__of__(self.context)
        elif name == 'authors':
            # XXX 'authors' should probably not be hard-coded here.  Rather,
            # it should be looked up on weblog config.
            return AuthorContainer('authors').__of__(self.context)
        elif self.isArchiveFolder(name):
            return ArchiveContainer(name).__of__(self.context)
        elif self.isYear(name):
            return YearArchive(name).__of__(self.context)
        return super(WeblogTraverser, self).publishTraverse(request, name)

    def isArchiveFolder(self, name):
        """Test if 'name' is an archive folder.  This is True when:
            - name is the value indicated by weblog_config;
            - name is a year.
        """
        weblog_config = IWeblogConfiguration(self.context)
        if name == weblog_config.archive_format:
            return True
        return False

    def isYear(self, name):
        try:
            year = int(name)
        except ValueError:
            return False
        else:
            from DateTime import DateTime
            try:
                tryDate = DateTime(year,1,1)
            except:
                # Bad year
                return False
            else:
                return True


class WeblogArchiveTraverser(DefaultPublishTraverse):
    """
    """

    adapts(IWeblogArchive, IHTTPRequest)

    def publishTraverse(self, request, name):
        """
        """
        isdate = False
        try:
            int(name)
            isdate = True
        except ValueError:
            pass
        if not isdate:
            # We're at the end of the archive hierarchy, and now need to
            # traverse for the actual IWeblogEntry item.  The trick here is to
            # lookup the weblogentry-ish view on an object that is an
            # IPossibleWeblogEntry so that it gets rendered in the weblog-ish
            # way.
            # So, we do standard traversal to get the actual object.
            obj = super(WeblogArchiveTraverser,
                        self).publishTraverse(request, name)
            # if we've reached a blog entry we set the request's ACTUAL_URL to
            # the entry's absolute_url to signal to plone.app.layout.globals
            # that it's dealing with a view_template (see also #97)
            if IPossibleWeblogEntry.providedBy(obj) or \
                IWeblogEntry.providedBy(obj):
                request['ACTUAL_URL'] = obj.absolute_url()
            # Then we return a particular view on it if it provides what we're
            # after.
            if IPossibleWeblogEntry.providedBy(obj):
                view = queryMultiAdapter((obj, request),
                                         name='weblogentry_view')
                if view is not None:
                    return view.__of__(obj)
            # Otherwise, we just return obj, as would have happened normally.
            return obj
        year = getattr(self.context, 'year', None)
        month = getattr(self.context, 'month', None)
        day = getattr(self.context, 'day', None)
        if day is not None:
            return super(WeblogArchiveTraverser,
                         self).publishTraverse(request, name)
        if month is not None:
            archive = DayArchive(year, month, name)
        elif year is not None:
            archive = MonthArchive(year, name)
        else:
            archive = YearArchive(name)
        ob = archive.__of__(self.context)
        return ob


class TopicContainerTraverser(DefaultPublishTraverse):
    """
    """

    adapts(ITopicContainer, IHTTPRequest)

    def publishTraverse(self, request, name):
        """
        """
        return self.traverseSubpath(request, name, Topic)

    def traverseSubpath(self, request, name, klass):
        # Now the guts of it...
        furtherPath = request['TraversalRequestNameStack']
        # Empty furtherPath so no more traversal happens after us.
        subpath = [name] + self.popFurtherPath(furtherPath)
        view_name = name
        if len(subpath) == 0:
            # No subpath to eat, so just lookup the 'name' view for context
            view = getMultiAdapter((self.context, self.request), name=view_name)
            return view.__of__(self.context)
        elif len(subpath) > 0 and subpath[-1].startswith('@@'):
            # A view has explicitly been requested, so make that the
            # view_name (stripping off the leading @@ which causes view
            # lookups to fail otherwise).
            view_name = subpath[-1][2:]
            # Use the rest of the subpath as the keywords for the topic.
            topic = klass(subpath[:-1]).__of__(self.context)
            view = getMultiAdapter((topic, request), name=view_name)
            return view.__of__(self.context)
        else:
            # No @@view given, so just return the topic.
            # Use all of the subpath as the keywords for the topic.
            topic = klass(subpath).__of__(self.context)
            view_name = getDefaultViewName(topic, request)
            view = getMultiAdapter((topic, request), name=view_name)
            return view.__of__(self.context)

    def popFurtherPath(self, furtherPath):
        """Empty the furtherPath sequence into a new list.
        """
        # XXX This should probably do something (hacky?) to inform the request
        # of what the full URL is.  Otherwise, things like ACTUAL_URL will be
        # wrong.
        subpath = []
        subpath.extend(furtherPath)
        while furtherPath:
            furtherPath.pop()
        return subpath

