# Standard library imports
from types import ListType
from types import TupleType
from types import StringTypes
import re

# Zope imports
from Acquisition import Explicit
from Acquisition import aq_parent

# Plone imports
from Products.CMFCore.interfaces import ISiteRoot

# Quills imports
from quills.core.interfaces import IWeblog
from quills.core.interfaces import IWeblogEnhanced
from quills.core.interfaces import IWeblogConfiguration


class EvilAATUSHack(Explicit):

    def __call__(self, name, value):
        """Deny access to attributes that are found on the class or instance,
        but allow access to anything else.  This locks down security on object
        attributes, but allows the lookup of portlets with the 'provider'
        TAL command.
        """
        context = aq_parent(self)
        idict = context.__dict__
        cdict = context.__class__.__dict__
        if idict.has_key(name) or cdict.has_key(name):
            return 0
        return 1


class QuillsMixin:
    """
    """

    def getWeblogContentObject(self):
        return recurseToInterface(self, (IWeblog, IWeblogEnhanced))

    def getWeblog(self):
        obj = self.getWeblogContentObject()
        if IWeblog.providedBy(obj):
            return obj
        return IWeblog(obj)


def getArchivePathFor(obj, weblog_content):
    """See IWeblogView.
    """
    # Handle published and getId either being an attribute on a catalog brain or
    # a method on a content object.
    id = getattr(obj, 'getId')
    if callable(id):
        id = id()
    published = getattr(obj, 'effective')
    if callable(published):
        published = published()
    path = []
    weblog_config = IWeblogConfiguration(weblog_content)
    archive_format = weblog_config.archive_format
    if isinstance(archive_format, StringTypes):
        archive_format = archive_format.strip()
    if archive_format is not None and archive_format is not '':
        path.append(archive_format)
    path.append(published.strftime('%Y'))
    path.append(published.strftime('%m'))
    path.append(published.strftime('%d'))
    path.append(id)
    return path

def getArchiveURLFor(obj, weblog_content):
    """See IWeblogView.
    """
    archive_path = getArchivePathFor(obj, weblog_content)
    return '%s/%s' % (weblog_content.absolute_url(), '/'.join(archive_path))

def recurseToInterface(item, ifaces):
    """Recurse up the aq_chain until an object providing `iface' is found,
    and return that.
    """
    if not isinstance(ifaces, (ListType, TupleType)):
        ifaces = [ifaces]
    parent = item.aq_parent
    for iface in ifaces:
        if iface.providedBy(item):
            return item
        elif iface.providedBy(parent):
            return parent
        elif ISiteRoot.providedBy(parent):
            # Stop when we get to the portal root.
            return None
    return recurseToInterface(parent, ifaces)


talkback_url_extractor = re.compile("(.*)/talkback/\d+")

def talkbackURL(discussion_brain):
    """expects the brain of a discussion item and constructs a url for it.
    n.b. we're using a regex in order to allow for the string 'talkback' to appear
    in the url in other places, too.
    """
    absolute_url = talkback_url_extractor.search(discussion_brain.getURL()).groups()[0]
    return "%s#%s" % (absolute_url, discussion_brain.id)