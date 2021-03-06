Quills browser tests
====================

Here we check for fixed bugs using tests, that don't fit into the 'narrative' in
the main browser test. First some boilerplate to get our browser up and running:

    >>> self.setRoles(("Contributor",))
    >>> browser = self.getBrowser(logged_in=True)
    >>> browser.handleErrors = False
    >>> entry = self.weblog.addEntry("Blog entry",
    ...                              "Just for testing",
    ...                              "Nothing to see.",
    ...                              ['fishslapping'],
    ...                              id="entry")
    >>> from quills.core.interfaces import IWeblogEntry
    >>> IWeblogEntry.providedBy(entry)
    True

Make it discussable and publish it

    >>> entry = self.weblog.getEntry('entry')
    >>> entry_content = entry.getWeblogEntryContentObject()
    >>> entry_content.allowDiscussion(allowDiscussion=True)
    >>> entry.publish()

    >>> date = entry.getPublicationDate()
    >>> year = str(date.year())
    >>> month = str(date.month()).zfill(2)
    >>> day = str(date.day()).zfill(2)

    >>> self.setRoles(("Contributor", "Reviewer", "Manager"))
    >>> browser.open('http://nohost/plone/weblog/%s/%s/%s/entry' 
    ...              % (year, month, day))
    >>> browser.getControl('Add Comment').click()
    >>> browser.getControl('Subject').value = "Parrot"
    >>> browser.getControl('Comment').value = "Is dead. Is deceased."

Issue #111 shows that the URLs generated by the archive portlet are not correct.
Even when the weblog is not supposed to be using an extra 'archive' URL segment,
the URLs always have that segment in them.

To test this, we'll first make sure that the weblog config is setup to use the
'archive' segment for URLs.

    >>> from quills.core.interfaces import IWeblogConfiguration
    >>> config = IWeblogConfiguration(self.weblog.getWeblogContentObject())
    >>> config.archive_format = 'archive'

Now we'll get a page and check its body for the appropriate link.

    >>> browser.open('http://nohost/plone/weblog/')
    >>> url = '<a href="http://nohost/plone/weblog/archive/%s/%s">'
    >>> url = url % (year, month)
    >>> url in browser.contents
    True

Now, if we change the archive_format, we should get different URLs.

    >>> config.archive_format = ''
    >>> browser.open('http://nohost/plone/weblog/')
    >>> url = '<a href="http://nohost/plone/weblog/%s/%s">'
    >>> url = url % (year, month)
    >>> url in browser.contents
    True


There was an issue whereby the correct comment count didn't get shown for each
weblog entry displayed in the weblog_view.  We verify that this is no longer
the case here.

First, let's add a comment so that we know one is there.

    >>> from Products.CMFCore.utils import getToolByName
    >>> dtool = getToolByName(self.portal, 'portal_discussion')
    >>> entry_discussion = dtool.getDiscussionFor(entry_content)
    >>> comment_id = entry_discussion.createReply(title='Comment Title',
    ...                                           text='a little test body')

Now, when we look at the weblog view, we should find that there is a link to the
comments for `entry', together with a count of how many comments there are on
it.

    >>> browser.open('http://nohost/plone/weblog/')
    >>> url = '<a href="http://nohost/plone/weblog/%s/%s/%s/entry#comments"'
    >>> url = url % (year, month, day)
    >>> url in browser.contents
    True
    >>> '<span>1</span>' in browser.contents
    True

>> repr(browser.contents)

This last line of test is fairly lame as it could potentially match anywhere in
the source.  An example of what we are really trying to match is the following:

"""
          <a href="http://nohost/plone/weblog/2007/09/24/entry#comments"
           style="text-decoration: none;">
          Comments:
          </a>

          <span>3</span>
"""


Issue #112 found that the recent comments portlet was generating incorrect links
to comments as it wasn't utilising the archive URL of the weblog entry objects.

    >>> txt = '<a href="http://nohost/plone/weblog/%s/%s/%s/entry#%s"'
    >>> txt = txt % (year, month, day, comment_id)
    >>> txt in browser.contents
    True


Issue #117 found that the weblog admin portlet got displayed to anonymous users,
rather than being restricted to admin-ish users.  Let's verify that this is no
longer the case.

    >>> self.setRoles([])
    >>> browser = self.getBrowser(logged_in=False)
    >>> browser.handleErrors = False
    >>> browser.open('http://nohost/plone/weblog/')
    >>> 'portletWeblogAdmin' in browser.contents
    False


Issue #143: Portlets do not show up in empty blogs
--------------------------------------------------

This issue is caused by the way BasePortletRenderer implements ``available``.

We do not use one of Quills' portlet here but make our own, as the problem
is located in BasePortletRenderer.

    >>> from plone.app.portlets.portlets import base
    >>> from quills.app.portlets.base import BasePortletRenderer
    >>> class TestRenderer(BasePortletRenderer, base.Renderer):
    ...     """A simple Renderer"""
    ...     pass

Now create a blog. And see if we can get our portlet renderer. We first try
with an empty blog. This a bit overly complicated because this test must work
with both Quills and QuillsEnabled.

    >>> blog = self.createBlog('issue-143')
    >>> blogFolder = self.portal['issue-143']
    >>> from zope.component import getMultiAdapter
    >>> request = blogFolder.REQUEST

The request will normally be marked by the traversal code to show we are inside
a weblog. We have to do it here ourselves.

    >>> from zope.interface import alsoProvides
    >>> from quills.app.traversal import IInsideWeblog
    >>> alsoProvides(request, IInsideWeblog)

    >>> view = getMultiAdapter((blogFolder, request), name='view')
    >>> renderer = TestRenderer(blogFolder, request, view, None, None)
    >>> renderer.available
    True

Now with one private entry in it.

    >>> entry = blog.addEntry('Tesing issue #143', 'Nothing', 'Nothing',
    ...	                      id="issue-143")
    >>> renderer.available
    True

And now with that one published. In all three cases the portlet should show up.
We cannot do this directly on entry as it might be only an adapter.

    >>> from Products.CMFCore.utils import getToolByName
    >>> wft = getToolByName(self.getPortal(), 'portal_workflow')
    >>> wft.getInfoFor(blogFolder['issue-143'], 'review_state')
    'private'

    >>> entry.publish()
    >>> renderer.available
    True


Issue #115: Blog posts published in the future should not appear
----------------------------------------------------------------

This was not a bug, really. Quills behave correctly, hiding entries scheduled
for future publication as it should. This test-case confirms this.

We will test here access by Quills API and through the web.

    >>> from quills.core.interfaces.weblog import IWeblog
    >>> blog = self.weblog
    >>> IWeblog.providedBy(blog)
    True

We create a entry and publish, though not yet in the future.
    

    >>> id = 'issue-115'
    >>> entry = blog.addEntry("Issue #115", "Tesing for issue 115",
    ...                       "Nothing.", id=id)
    >>> entry.publish()

This entry should have an effective date before now, or none at best. We cannot
get effective directly from the entry because it might be only an adapter.

    >>> from DateTime import DateTime # We cannot use python datetime here, alas
    >>> effective = self.portal.weblog[id].effective()
    >>> now = DateTime()
    >>> effective is None or effective <= now
    True
    
It is visible.

    >>> id in map(lambda x: x.id, blog.getEntries())
    True

Now make it become effective in the future. It should still be visible since
we are managers and possess the appropriate rights.

    >>> from Products.CMFCore.permissions import AccessInactivePortalContent
    >>> from Products.CMFCore.utils import _checkPermission
    >>> _checkPermission(AccessInactivePortalContent,
    ...		 self.portal.weblog) and True
    True

    >>> futureDate = now + 7
    >>> self.portal.weblog[id].setEffectiveDate(futureDate)
    >>> self.portal.weblog[id].indexObject()
    >>> id in map(lambda x: x.id, blog.getEntries())
    True
        
Now we drop that right. The entry should no longer be visible.

    >>> from AccessControl import getSecurityManager
    >>> self.logout()
    >>> _checkPermission(AccessInactivePortalContent,
    ...                  self.portal.weblog) and True
        
    >>> id in map(lambda x: x.id, blog.getEntries())
    False

If published in the past it should be visible again.
    
    >>> self.portal.weblog[id].setEffectiveDate(effective)
    >>> self.portal.weblog[id].indexObject()
    >>> id in map(lambda x: x.id, blog.getEntries())
    True
    
Login again and set for future publication.

    >>> self.loginAsPortalOwner()
    >>> _checkPermission(AccessInactivePortalContent,
    ...	                 self.portal.weblog) and True
    True
    >>> self.portal.weblog[id].setEffectiveDate(futureDate)
    >>> self.portal.weblog[id].indexObject()
    >>> id in map(lambda x: x.id, blog.getEntries())
    True

Now same procedure through the web. Our entry should be invisible.

    >>> browser = self.getBrowser(logged_in=False)
    >>> browser.handleErrors = False
    >>> browser.open('http://nohost/plone/weblog/')
    >>> browser.getLink(url="http://nohost/plone/weblog/%s" % (id,))
    Traceback (most recent call last):
        ...
    LinkNotFoundError

After resetting the date it should be visible again.

    >>> self.portal.weblog[id].setEffectiveDate(effective)
    >>> self.portal.weblog[id].indexObject()
    >>> browser.open('http://nohost/plone/weblog/')
    >>> browser.getLink(url="http://nohost/plone/weblog/%s" % (id,))
    <Link ...>

We do not test for draft stated entries, because those are hidden from public
viewing anyway. We have to check the archive, though.

First some preparations, like getting the archive URL prefix.

    >>> from quills.app.interfaces import IWeblogEnhancedConfiguration
    >>> weblog_config = IWeblogEnhancedConfiguration(self.portal.weblog)
    >>> archivePrefix = weblog_config.archive_format

We check through the web only. First with effective in the past.

    >>> path = "/".join([archivePrefix, "%s" % (effective.year(),)])
    >>> browser.open('http://nohost/plone/weblog/%s' % (path,))
    >>> browser.getLink(url="http://nohost/plone/weblog/%s" % (id,))
    <Link ...>

Then with effective in the future.

    >>> path = "/".join([archivePrefix, "%s" % (futureDate.year(),)])
    >>> self.portal.weblog[id].setEffectiveDate(futureDate)
    >>> self.portal.weblog[id].indexObject()
    >>> browser.open('http://nohost/plone/weblog/%s' % (path,))
    >>> browser.getLink(url="http://nohost/plone/weblog/%s" % (id,))
    Traceback (most recent call last):
        ...
    LinkNotFoundError

Finally we should test syndication, but this would require some package
implementing that feature, which we do not want do depend on here.


Issue #158 — "Add Entry" of the Weblog Admin portlet fails
-----------------------------------------------------------

An exception is raised that, because the specified portal type does not exist.
In fact the type specified is "None". This is happens because no default
type is configured for Products.Quills weblogs.

XXX: Test-case does not work for QuillsEnabled!

Create a fresh blog, in the case someone might accidentally have set a default
portal type before. Populate it a little.

    >>> self.setRoles(("Manager",))
    >>> blog = self.createBlog('issue-158')
    >>> blogFolder = self.portal['issue-158']
    >>> entry = blog.addEntry('Tesing issue #158', 'Nothing',
    ...                       'Nothing', id="issue-158")
    >>> entry.publish()

Now click the "Add Entry" link. The edit form should be present.

    >>> browser = self.getBrowser(logged_in=True)
    >>> browser.handleErrors = True
    >>> browser.open('http://nohost/plone/issue-158/')
    >>> browser.getLink(text='Add Entry').click()
    >>> '/portal_factory/' in browser.url
    True


Issues #149 & #162: Memory leak and folder listing breakage
-----------------------------------------------------------

Both issues are cause by the way Quills wraps up Catalog Brains into an
IWeblogEntry adapter. It sets this wrapper class with "useBrains" of
Products.ZCatalog.Catalog. Doing so on each query causes the memory leak, as
the Catalog creates a class on the fly around the class passed to useBrains.
Never resetting the class causes the folder listing to break, because now
all catalog queries, even those from non Quills code, use Quills custom Brain.
This brain however defines methods which are simple member variable in the
default Brain, causing those clients to break.

To test for those bug, first publish a post, then render the Weblog View once.
This will cause some of the incriminating code to be called. Testing all 
occurances would not be sensible. A fix must make sure to break all those
calls by renaming the custom catalog class!

An exception is raised that, because the specified portal type does not exist.
In fact the type specified is "None". This is happens because no default
type is configured for Products.Quills weblogs.
Create a fresh blog, in the case someone might accidentally have set a default
portal type before. Populate it a little.

    >>> entry = self.weblog.addEntry('Tesing issue # 149 & #162', 'Nothing',
    ...                       'Nothing', id="issue-158")
    >>> entry.publish()
    >>> browser = self.getBrowser(logged_in=True)
    >>> browser.handleErrors = True
    >>> browser.open('http://nohost/plone/weblog/')

Now query a non Quills object from the catalog (in fact no query should ever
return a custom Quills brain). At least the Welcome message should exist.
Then check if the brain is a Quills adapter.

    >>> from Products.CMFCore.utils import getToolByName
    >>> catalog = getToolByName(self.portal, 'portal_catalog')
    >>> results = catalog(path="/", portal_type="Document")
    >>> len(results) > 0
    True

    >>> from quills.core.interfaces import IWeblogEntry
    >>> IWeblogEntry.providedBy(results[0])
    False

    
Issue #172 — Can't log comments from default view on weblog entries
-------------------------------------------------------------------

Quills default view for Weblog Entries is named 'weblogentry_view'. Plone
however links to individual items via the 'view' alias. This happens for
instance in collections or the recent items portlet. The Weblog Entries
still get rendered, important actions are missing though, e.g. the user
actions for copy/paste/delete or workflow actions. The commenting button 
is also missing.

We will need write access to the blog.

    >>> self.logout()
    >>> self.login()
    >>> self.setRoles(("Manager",))

Create a discussable weblog entry first.

    >>> from quills.app.browser.weblogview import WeblogEntryView
    >>> traverseTo = self.portal.restrictedTraverse # for brevity
    >>> entry = self.weblog.addEntry("Test for issue #172", "Nothing",
    ...                              "Nothing", id="issue-172")
    >>> entry_content = entry.getWeblogEntryContentObject()
    >>> entry_content.allowDiscussion(allowDiscussion=True)
    >>> entry.publish()

There should be a fully functionaly WeblogEntryView at 'weblogentry_view'.

    >>> browser = self.getBrowser(logged_in=True)
    >>> browser.handleErrors = False
    >>> browser.open('http://nohost/plone/weblog/issue-172/weblogentry_view')

That inculdes actions like cut and paste,

    >>> browser.getLink(text='Actions') # of issue-172/weblogentry_view
    <Link ...>

and also workflow control,

    >>> browser.getLink(text='State:') # of issue-172/weblogentry_view
    <Link ...>

    >>> browser.getForm(name='reply') # of issue-172/weblogentry_view
    <zope.testbrowser.browser.Form object at ...>

and finally commenting, which must be enabled, of course.

The same should be available when we navigate to issue-172/view.

    >>> browser = self.getBrowser(logged_in=True)
    >>> browser.handleErrors = False
    >>> browser.open('http://nohost/plone/weblog/issue-172/view')

That inculdes actions like cut and paste,

    >>> browser.getLink(text='Actions') # of issue-172/view
    <Link ...>

and also workflow control,

    >>> browser.getLink(text='State:') # of issue-172/view
    <Link ...>

and finally commenting, which must be enabled, of course.

    >>> browser.getForm(name='reply') # of issue-172/view
    <zope.testbrowser.browser.Form object at ...>


Issue #180: Incorrect author links in bylines
---------------------------------------------

Our screen name must differ from the login name to make this issue apparent.

    >>> self.login()
    >>> self.setRoles(('Manager',))
    >>> from Products.CMFCore.utils import getToolByName
    >>> pmtool = getToolByName(self.portal, 'portal_membership')
    >>> iAm = pmtool.getAuthenticatedMember()
    >>> myId  = iAm.getId()
    >>> oldName = iAm.getProperty('fullname')
    >>> newName = "User Issue180"
    >>> iAm.setProperties({'fullname': newName})

We need to add a page. Usually we would do so as a Contributor, but publishing
the entry without approval requires the Manager role, too.

    >>> entry = self.weblog.addEntry(title="Issue #180", id="issue180",
    ...                      excerpt="None", text="None")
    >>> entry.publish()
    
Now check the author links. First when showing the entry only.

    >>> browser = self.getBrowser()
    >>> browser.open("http://nohost/plone/weblog/issue180")
    >>> link = browser.getLink(text=newName)
    >>> link.url == "http://nohost/plone/weblog/authors/%s" % (myId,)
    True

Now the blog view.

    >>> browser.open("http://nohost/plone/weblog")
    >>> link = browser.getLink(text=newName)
    >>> link.url == "http://nohost/plone/weblog/authors/%s" % (myId,)
    True

Reset user name.
    
    >>> iAm.setProperties({'fullname': oldName})


Issue #119: Archive URL not respected when commenting a post
------------------------------------------------------------

When you add comment to a post, you will end up at the absolute URL of
the post no matter if you came from the archive.

To test this I will add a post and navigate to it by archive URL. The entry
must be commentable. It will have a fixed publication date to easy testing.

    >>> self.login()
    >>> self.setRoles(('Manager',))

    >>> entry = self.weblog.addEntry(title="Issue #119", id="issue119",
    ...                      excerpt="None", text="None")
    >>> entry_content = entry.getWeblogEntryContentObject()
    >>> entry_content.allowDiscussion(allowDiscussion=True)
    >>> entry.publish(pubdate=DateTime("2009-04-28T09:46:00"))

    >>> browser = self.getBrowser(logged_in=True)
    >>> browser.open("http://nohost/plone/weblog/2009/04/28/issue119")

Now add a comment through the web. Saving it should take us back from where we
from.

    >>> browser.handleErrors = True
    >>> browser.getControl("Add Comment").click()
    >>> browser.getControl('Subject').value = "Issue 119"
    >>> browser.getControl('Comment').value = "Redirect to archive, please!"

Unfortunately, the clicking submit will cause a 404 error. At least up until
Zope 2.10.6 zope.testbrowser and/or mechanize handle URL fragments incorrectly.
They send them to the server (which they should) who then chokes on them.
Recent versions of mechanize (?) and testbrowser (3.5.1) have fixed that. I
cannot find out though which version of testbrowser ships with individual Zope
releases. As soon as this is fixed the try-except-clause may safely go away.

With Products.Quills this test-case will fail for another reason. There the
redirect handler (quills.app.browser.discussionreply) is not registered during
testing; probably because of the GS profile in the tests module. FIX ME!

    >>> from urllib2 import HTTPError
    >>> try:
    ...     browser.getControl('Save').click()
    ... except HTTPError, ex:
    ...     if ex.code != 404:
    ...         raise
    >>> browser.url.split('#')[0]
    'http://nohost/plone/weblog/2009/04/28/issue119'


Issue #189: Replying to an comment raises a non-fatal TypeError
---------------------------------------------------------------

This issue was caused by Quills' portlets trying to locate the weblog object.
They would try to adapt a DiscussionItem to IWeblogLocator. This would happen
only for responses given, because comment on post have the weblog entry as
context set.

Btw. adding visiting Quills uploads or topic image folder or adding anything
to them would raise the same error.

To test for this issue we will add a comment and a reply and see whether
our portlet show up in the reply form.

    >>> self.login()
    >>> self.setRoles(('Manager',))

    >>> entry = self.weblog.addEntry(title="Issue #189", id="issue189",
    ...                      excerpt="None", text="None")
    >>> entry_content = entry.getWeblogEntryContentObject()
    >>> entry_content.allowDiscussion(allowDiscussion=True)
    >>> entry.publish( pubdate=DateTime("2009-04-28T16:48:00") )

    >>> browser = self.getBrowser(logged_in=True)
    >>> browser.handleErrors = True
    >>> browser.open("http://nohost/plone/weblog/issue189")

Add the comment to the post. See if there appears some text which indicates
the presence of the Administration portlet.

    >>> browser.getControl("Add Comment").click()
    >>> browser.getControl('Subject').value = "Comment"
    >>> browser.getControl('Comment').value = "This works"

See test for issue #119 why this try-except statement is here.

    >>> from urllib2 import HTTPError
    >>> try:
    ...     browser.getControl('Save').click()
    ... except HTTPError, ex:
    ...     if ex.code == 404:
    ...         browser.open("http://nohost/plone/weblog/issue189")
    ...     else:
    ...         raise
    >>> 'Weblog Admin' in browser.contents
    True
    
Add a reply to that comment.
      
    >>> browser.getControl("Reply").click()
    >>> 'Weblog Admin' in browser.contents
    True


Issue #194: Quills breaks commenting for non-weblog content
-----------------------------------------------------------

Adding a comment to non-Quills content, say a plain Document, would raise
a NameError. This was caused by an undefined variable `redirect_target` in 
`quills.app.browser.discussionreply`.

To test for this issue we will add a comment to a Document outside the blog.

    >>> self.login()
    >>> self.setRoles(('Manager',))

    >>> id = self.portal.invokeFactory("Document", id="issue194",
    ...           title="Issue 179", description="A test case for issue #194.")
    >>> self.portal[id].allowDiscussion(allowDiscussion=True)

    >>> browser = self.getBrowser(logged_in=True)
    >>> browser.handleErrors = True
    >>> browser.open("http://nohost/plone/issue194")
    >>> browser.getControl("Add Comment").click()
    >>> browser.getControl('Subject').value = "Issue 194 fixed!"
    >>> browser.getControl('Comment').value = "This works"

See test for issue #119 why this try-except statement is here.

    >>> from urllib2 import HTTPError
    >>> try:
    ...     browser.getControl('Save').click()
    ... except HTTPError, ex:
    ...     if ex.code == 404:
    ...         browser.open("http://nohost/plone/issue194")
    ...     else:
    ...         raise
    >>> 'Issue 194 fixed!' in browser.contents
    True


Issue #195: Topic view shows only one keyword
---------------------------------------------

This obviously only hurts when one tries to filter by more than just
one keyword. Filtering by multiple keywords is done appending more
keywords to the blog URL, separated by slashes.

First blog a post in more than one catagory.

    >>> self.login()
    >>> self.setRoles(('Manager',))

    >>> entry = self.weblog.addEntry(title="Issue #195", id="issue195",
    ...                      topics=['i195TopicA', 'i195TopicB'],
    ...                      excerpt="None", text="None")
    >>> entry.publish()

Now browse the weblog by those two keywords. They should appear in a
heading.

    >>> browser = self.getBrowser()
    >>> browser.handleErrors = True
    >>> browser.open("http://nohost/plone/weblog/topics/i195TopicA/i195TopicB")

    >>> import re
    >>> r1 = 'i195TopicA.+i195TopicB|i195TopicB.+i195TopicA'
    >>> r2 = '<h1>(%s)</h1>' % (r1,)
    >>> re.search(r2, browser.contents)
    <_sre.SRE_Match object at ...>

    >>> re.search(r1, browser.title)
    <_sre.SRE_Match object at ...>

Author topics face the same problem. So, the same with them. We need a second
author first.

    >>> from Products.CMFCore.utils import getToolByName
    >>> aclUsers = getToolByName(self.getPortal(), 'acl_users')
    >>> aclUsers.userFolderAddUser('Issue195Author2', 'issue195',['manager'],[])
    >>> rawPost = self.portal.weblog['issue195']
    >>> rawPost.setCreators(rawPost.Creators()+('Issue195Author2',))

    >>> authors = rawPost.Creators()
    >>> browser.open("http://nohost/plone/weblog/authors/%s/%s" % authors)

    >>> import re
    >>> from string import Template
    >>> templ = Template('${a}.+${b}|${b}.+${a}')
    >>> r1 = templ.substitute(a=authors[0], b=authors[1])
    >>> r2 = '<h1>(%s)</h1>' % (r1,)  
    >>> re.search(r2, browser.contents)
    <_sre.SRE_Match object at ...>

    >>> re.search(r1, browser.title)
    <_sre.SRE_Match object at ...>


Issue #198: Images disappear blog entry is viewed by Tag Cloud or Author Name
-----------------------------------------------------------------------------

The two topic views for authors and keyword would display an empty result page
for keywords or author without associated posts. Surprisingly the archive view
behaved correctly, most certainly because it is used more intensly and hence
the bug could not go undetected there. Nonetheless we will test image handling
for all three virtual containers here.

Quills and QuillsEnabled handle image uploads differently. While a Quills blog
contains a special folder for uploads, QuillsEnabled leaves folder organization
to the user. Both however ought to be able to acquire content from containing
locations. This is where we will put our test image.

Image loading and creation is inspired by the test-cases ATContentTypes Image
portal type and the test cases of quills.remoteblogging.

    >>> import os
    >>> import quills.app.tests as home
    >>> path = os.path.dirname(home.__file__)
    >>> file = open('%s/quills_powered.gif' % (path,), 'rb')
    >>> imageBits = file.read()
    >>> file.close()
    
    >>> id = self.portal.invokeFactory('Image', 'issue198.gif',
    ...                                title="Image for Issue 198")
    >>> image = self.portal[id]
    >>> image.setImage(imageBits)

Now we navigate to the image via the virtual URLs for archive, authors
and topics. We log in as manager, because the image is private still.

    >>> browser = self.getBrowser(logged_in=True)
    >>> browser.handleErrors = False

Before we start, let's try the canonical URL of the image.

    >>> browser.open('http://nohost/plone/%s/view' % (id,))
    >>> browser.title
    '...Image for Issue 198...'

We begin the archive. We create a post to make sure we actually have an
archive. 

    >>> self.login()
    >>> self.setRoles(('Manager',))
    >>> keyword = 'issue198kw' # id clashes would cause mayhem
    >>> entry = self.weblog.addEntry(title="Issue #198", id="issue198",
    ...                             topics=[keyword],
    ...                             excerpt="None", text="None")
    >>> entry.publish() 
    >>> year = entry.getPublicationDate().year()
    >>> month = entry.getPublicationDate().month()
    >>> browser.open('http://nohost/plone/weblog/%s/%s/%s/view'
    ...               % (year, month, id))
    >>> browser.title
    '...Image for Issue 198...'

Now the author container. The bug caused a fat internal server error here, 
which was in fact the ``TypeError: unsubscriptable object`` described
in it's issue report.

    >>> self.portal.error_log._ignored_exceptions = ()
    >>> author = entry.getAuthors()[0].getId()
    >>> browser.open('http://nohost/plone/weblog/authors/%s/view'
    ...               % (id,))
    >>> browser.title
    '...Image for Issue 198...'

Images and other acquired stuff may only appear directly after the name
of the topic container (``authors`` here). Later names will be taken for
keywords, no matter if they designated a picture somewhere. It simply would
not make sense otherwise.

    >>> browser.open('http://nohost/plone/weblog/authors/%s/%s/view'
    ...               % (author,id))
    >>> browser.title
    'Posts by ...issue198.gif...'

And finally the same for the keyword container.

    >>> browser.open('http://nohost/plone/weblog/topics/%s/view'
    ...               % (id,))
    >>> browser.title
    '...Image for Issue 198...'

    >>> browser.open('http://nohost/plone/weblog/topics/%s/%s/view'
    ...               % (keyword, id))
    >>> browser.title
    'Posts about ...issue198.gif...'



Issue 202: Filtering by an non-existing author id causes a TypeError
--------------------------------------------------------------------

This was very much related to issue #198. Two scenarios cause this error
actually, the one described in issue #198, and when a non existant author
is queried. We simulate the latter here. It renders no blog entry.

    >>> browser = self.getBrowser()
    >>> browser.handleErrors = False
    >>> browser.open('http://nohost/plone/weblog/authors/meNotThere202')
    >>> browser.title
    'Posts by meNotThere202...'

    >>> browser.contents
    '...No weblog entries have been posted...'

On the other hand, querying an real *and* a fictive user name will render
all posts of the reals user. This is due to "posts by any of the given
authors" semantics of author topics.

Before we check this, we post an entry.

    >>> self.login()
    >>> self.setRoles(('Manager',))
    >>> entry = self.weblog.addEntry(title="Issue #202", id="issue202",
    ...                             excerpt="None", text="None")
    >>> entry.publish()

Now, find out who we are.

    >>> pmtool = getToolByName(self.portal, 'portal_membership')
    >>> iAm = pmtool.getAuthenticatedMember()
    >>> myId  = iAm.getId()

And finally do the query.

    >>> browser.open('http://nohost/plone/weblog/authors/meNotThere202/%s'
    ...              % myId)
    >>> browser.title
    'Posts by meNotThere202...'
    
    >>> myId in browser.title
    True

    >>> browser.contents
    '...<h2>...Issue #202...</h2>...'
       

Issue #203 — archive portlet broken: ValueError: invalid literal for int()
---------------------------------------------------------------------------

This bug was cause by quills.app.archive.BaseDateArchive.getId accidentally
acquiring values for the attributes 'year', 'month' or 'day'. The product
CalendarX unveiled this because it defines a page named 'day'. But in fact
any property named 'day', 'month' or 'year' that might be acquired by
climbing up the acquisition chain from an archive will cause this fault.

To test this we will simply add three pages of those names just above the
weblog. Then we will see, what the various archive report as their id.

    >>> self.login()
    >>> self.setRoles(('Manager',))
    >>> portal = self.getPortal()

We post an entry to be sure, that there is an archive.

    >>> entry = self.weblog.addEntry(title="Issue #203", id="issue203",
    ...                             excerpt="None", text="None")
    >>> entry.publish() 

No get the archives from year to day.

    >>> aYearArchive = self.weblog.getSubArchives()[0]
    >>> aMonthArchive = aYearArchive.getSubArchives()[0]
    >>> aDayArchive = aMonthArchive.getSubArchives()[0]

Create an potential acquisition target for attribute 'year' above the 
blog. Then check if ``getId`` still reports numbers...

    >>> portal.invokeFactory('Document', id='year', title='Year')
    'year'
    >>> type(int(aYearArchive.getId()))
    <type 'int'>
    >>> type(int(aMonthArchive.getId()))
    <type 'int'>
    >>> type(int(aDayArchive.getId()))
    <type 'int'>

Same for month.

    >>> portal.invokeFactory('Document', id='month', title='Month')
    'month'
    >>> type(int(aYearArchive.getId()))
    <type 'int'>
    >>> type(int(aMonthArchive.getId()))
    <type 'int'>
    >>> type(int(aDayArchive.getId()))
    <type 'int'>

Same for day.

    >>> portal.invokeFactory('Document', id='day', title='Day')
    'day'
    >>> type(int(aYearArchive.getId()))
    <type 'int'>
    >>> type(int(aMonthArchive.getId()))
    <type 'int'>
    >>> type(int(aDayArchive.getId()))
    <type 'int'>

Issue #204: Not Found when going to posts by archive URL
--------------------------------------------------------

This much the same as issue #203, only located elsewhere: this time
time the traversal code. We simulate it here by simply going to any
post in the archive.

Do not move this test-case away from the one for issue #203, as it
continues it! It depend on the pages created there.

    >>> browser.open('http://nohost/plone/weblog')
    >>> link = browser.getLink('Issue #203')
    >>> link.click()
    >>> browser.title
    'Issue #203...'


Issue #209 — UnicodeDecodeError in topics view
----------------------------------------------

Quills must allow non-ascii characters in topic names. This used to
work but broke with a fix for issue #195 at r87933.

We start as usual by post an entry, this time under a non-ascii
topic.

    >>> self.login()
    >>> self.setRoles(('Manager',))
    >>> keyword = 'issue198kw' # id clashes would cause mayhem
    >>> entry = self.weblog.addEntry(title="Issue #209", id="issue209",
    ...                             topics=['München'],
    ...                             excerpt="None", text="None")
    >>> entry.publish() 

Now we click that topic in the tag cloud. It should lead us to the
topic view for topic 'München'.

    >>> browser = self.getBrowser()
    >>> browser.handleErrors = False
    >>> browser.open('http://nohost/plone/weblog')
    >>> link = browser.getLink('München')
    >>> link.click()
    >>> browser.title
    '...M\xc3\xbcnchen...'

Now multi topic filtering...

    >>> browser.open('http://nohost/plone/weblog/topics/München/Hamburg/Berlin')
    >>> browser.title
    '...M\xc3\xbcnchen...'

Explicit view selection...

    >>> browser.open('http://nohost/plone/weblog/topics/München/@@topic_view')
    >>> browser.title
    '...M\xc3\xbcnchen...'

Finally, selecting a non-existant view should raise an exception.

    >>> browser.open('http://nohost/plone/weblog/topics/München/@@notaview')
    Traceback (most recent call last):
    ...
    ComponentLookupError: ...
    
While we're at it, let's see if foreign characters in author names
give us any trouble.

    >>> from Products.CMFCore.utils import getToolByName
    >>> pmtool = getToolByName(self.portal, 'portal_membership')
    >>> iAm = pmtool.getAuthenticatedMember()
    >>> myId  = iAm.getId()
    >>> oldName = iAm.getProperty('fullname')
    >>> newName = 'Üsör Ässué180'
    >>> iAm.setProperties({'fullname': newName})
    >>> browser.open('http://nohost/plone/weblog/authors/%s' % (myId,))
    >>> print browser.title
    Posts by Üsör Ässué180...
    
    >>> iAm.setProperties({'fullname': oldName})
