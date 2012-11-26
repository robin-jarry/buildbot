# This file is part of Buildbot.  Buildbot is free software: you can
# redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation, version 2.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51
# Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#
# Copyright Buildbot Team Members

import mock, re
from twisted.trial import unittest
from buildbot.data import base, exceptions
from buildbot.test.util import endpoint
from buildbot.test.fake import fakemaster

class ResourceType(unittest.TestCase):

    def makeResourceTypeSubclass(self, **attributes):
        attributes.setdefault('type', 'thing')
        return type('ThingResourceType', (base.ResourceType,), attributes)

    def test_sets_master(self):
        cls = self.makeResourceTypeSubclass()
        master = mock.Mock()
        inst = cls(master)
        self.assertIdentical(inst.master, master)

    def test_getEndpoints_instances_fails(self):
        ep = base.Endpoint(None)
        cls = self.makeResourceTypeSubclass(endpoints=[ep])
        inst = cls(None)
        self.assertRaises(TypeError, lambda : inst.getEndpoints())

    def test_getEndpoints_classes(self):
        class MyEndpoint(base.Endpoint):
            pass
        cls = self.makeResourceTypeSubclass(endpoints=[MyEndpoint])
        master = mock.Mock()
        inst = cls(master)
        eps = inst.getEndpoints()
        self.assertIsInstance(eps[0], MyEndpoint)
        self.assertIdentical(eps[0].master, master)

    def test_produceEvent(self):
        cls = self.makeResourceTypeSubclass(
                type='singular',
                keyFields=('fooid', 'barid'))
        master = fakemaster.make_master(testcase=self, wantMq=True)
        master.mq.verifyMessages = False # since this is a pretend message
        inst = cls(master)
        inst.produceEvent(dict(fooid=10, barid='20'), # note integer vs. string
                         'tested')
        master.mq.assertProductions([
            (('singular', '10', '20', 'tested'), dict(fooid=10, barid='20'))
        ])


class Endpoint(endpoint.EndpointMixin, unittest.TestCase):

    class MyEndpoint(base.Endpoint):
        pathPattern = ( 'my', 'pattern' )

    endpointClass = MyEndpoint

    def setUp(self):
        self.setUpEndpoint()

    def tearDown(self):
        self.tearDownEndpoint()

    def test_sets_master(self):
        self.assertIdentical(self.master, self.ep.master)


class Link(unittest.TestCase):

    def test_path(self):
        l = base.Link(('a', 'b'))
        self.assertEqual(l.path, ('a', 'b'))

    def test_repr(self):
        l = base.Link(('a', 'b'))
        self.assertEqual(`l`, "Link(('a', 'b'))")

class ControlParamsCheckMixin(unittest.TestCase):
    def doTest(self, arg, specs, error, action="act"):
        class TestedEndpoint(base.ControlParamsCheckMixin):
            called = False
            def safeControl(self, action, args, kwargs):
                self.called = True
        check = TestedEndpoint()
        check.action_specs = {"act":specs}
        try:
            check.control(action, arg, {})
        except exceptions.InvalidOptionException,e:
            self.assertEqual(str(e), error)
            return
        except exceptions.InvalidActionException,e:
            self.assertEqual(str(e), error)
            return
        self.assertEqual(error, None)
        self.assertEqual(check.called, True)
    def test_re(self):
        self.doTest( dict(a="Aslkj"),
                     dict(a=dict(re=re.compile("[a-z]+"))),
                     "need 'a' param to match regular expression '[a-z]+' its 'Aslkj'")
    def test_re_pass(self):
        self.doTest( dict(a="aslkj"),
                     dict(a=dict(re=re.compile("[a-z]+"))),
                     None)
    def test_type(self):
        self.doTest( dict(a="Aslkj"),
                     dict(a=dict(type=dict)),
                     "need 'a' param to be a '<type 'dict'>' while its 'Aslkj'")
    def test_type_pass(self):
        self.doTest( dict(a="aslkj"),
                     dict(a=dict(type=str)),
                     None)
    def test_required(self):
        self.doTest( dict(a="Aslkj"),
                     dict(a=dict(), b=dict(required=True)),
                     "need 'b' param")
    def test_required_pass(self):
        self.doTest( dict(a="aslkj"),
                     dict(a=dict(required=True)),
                     None)
    def test_unknown(self):
        self.doTest( dict(a="aslkj", b="bar"),
                     dict(a=dict(required=True)),
                     "param 'b' is not supported by this api only ['a'] are")
    def test_unknown_action(self):
        self.doTest( dict(a="aslkj"),
                     dict(a=dict(required=True)),
                     "'unknown' action is not supported. Only ['act'] are",
                     action="unknown")
