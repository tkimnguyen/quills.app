# Zope imports
from zope.interface import implements
from zope.component import getMultiAdapter

# Plone imports
from plone.portlets.interfaces import IPortletRetriever
from plone.portlets.interfaces import IPortletManager
from plone.portlets.interfaces import IPortletStorage

# Quills imports
from quills.core.interfaces import IWeblog, IWeblogEnhanced
from quills.app.utilities import recurseToInterface


class AcquiringWeblogPortletRetriever(object):
    """This implementation just delegates to the acquisition parent's
    IPortletRetriever implementation.
    """

    implements(IPortletRetriever)

    def __init__(self, context, storage):
        self.context = context
        self.storage = storage

    def getPortlets(self):
        """See IPortletRetriever.
        """
        weblog = self._getWeblog()
        weblog_retriever = getMultiAdapter((weblog, self.storage), IPortletRetriever)
        return weblog_retriever.getPortlets()

    def _getWeblog(self):
        return recurseToInterface(self.context.aq_inner,
                                  (IWeblog, IWeblogEnhanced))
