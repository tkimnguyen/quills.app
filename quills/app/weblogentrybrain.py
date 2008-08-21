# Zope imports
from zope.interface import implements

# Quills imports
from utilities import QuillsMixin
from utilities import recurseToInterface
from quills.core.interfaces import IWeblog
from quills.core.interfaces import IWeblogEnhanced
from quills.core.interfaces import IWeblogEntry
# Commented out to avoid circular import problems with archive and topic
# modules. The imports happen within each of the methods that require them.
#from topic import Topic, AuthorTopic


class WeblogEntryCatalogBrain(QuillsMixin):
    """A catalog brain that implements IWeblogEntry (as efficiently as
    possible).

    >>> from zope.interface.verify import verifyClass
    >>> verifyClass(IWeblogEntry, WeblogEntryCatalogBrain)
    True
    """

    implements(IWeblogEntry)

    def getTitle(self):
        """See IWeblogEntry.
        """
        return self['Title']

    def getTopics(self):
        """See IWeblogEntry.
        """
        from topic import Topic
        subjects = self['Subject']
        weblog_content = self.getWeblogContentObject()
        return [Topic(each).__of__(weblog_content) for each in subjects]

    def getAuthors(self):
        """See IWeblogEntry.
        """
        from topic import AuthorTopic
        creators = self['listCreators']
        weblog_content = self.getWeblogContentObject()
        return [AuthorTopic(each).__of__(weblog_content) for each in creators]

    def getExcerpt(self):
        """See IWeblogEntry.
        """
        return self['Description']

    def getText(self):
        """See IWeblogEntry.
        """
        return self._getObject().getText()

    def getMimeType(self):
        """See IWeblogEntry.
        """
        # In order to keep this implementation generic, we adapt the real object
        # to IWeblogEntry and just defer to that getMimeType implementation. The
        # reason being that we don't know if we're in a Quills world or a
        # QuillsEnabled world.
        return IWeblogEntry(self._getObject()).getMimeType()

    def getWeblogContentObject(self):
        """See IWeblogEntry.
        """
        return recurseToInterface(self._getObject(), (IWeblog, IWeblogEnhanced))
        
    def getWeblogEntryContentObject(self):
        """See IWeblogEntry
        """
        return self._getObject()

    def _getObject(self):
        return self.getObject()

    def _getWeblogEntry(self):
        return IWeblogEntry(self.getObject())

    def getPublicationDate(self):
        """See IWeblogEntry.
        """
        return self['effective']

    def setTitle(self, title):
        """See IWeblogEntry.
        """
        self._getWeblogEntry().setTitle(title)

    def setTopics(self, topic_ids):
        """See IWeblogEntry.
        """
        self._getWeblogEntry().setTopics(topic_ids)

    def setExcerpt(self, excerpt):
        """See IWeblogEntry.
        """
        self._getWeblogEntry().setExcerpt(excerpt)

    def setText(self, text, mimetype=None):
        """See IWeblogEntry.
        """
        self._getWeblogEntry().setText(text, mimetype=mimetype)

    def edit(self, title, excerpt, text, topics, mimetype=None):
        """See IWeblogEntry.
        """
        self._getWeblogEntry().edit(title, excerpt, text, topics, mimetype=mimetype)

    def setPublicationDate(self, datetime):
        """See IWeblogEntry.
        """
        self._getWeblogEntry().setPublicationDate(datetime)

    def publish(self, pubdate=None):
        """See IWeblogEntry.
        """
        self._getWeblogEntry().publish(pubdate)

    def retract(self):
        """See IWeblogEntry.
        """
        self._getWeblogEntry().retract()

    def isPublished(self):
        """See IWeblogEntry.
        """
        # this is insane! it counteracts Plones separation between brain and object!
        self._getWeblogEntry().isPublished()
