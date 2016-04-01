# coding: utf-8
# Copyright (c) 2014 Hewlett-Packard Development Company, L.P.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json

from oslo_config import fixture as config_fixture
from oslo_utils import timeutils

from murano.api.v1 import instance_credentials
from murano.db import models
import murano.tests.unit.api.base as tb
import murano.tests.unit.utils as test_utils


class TestInstanceCredentialApi(tb.ControllerTest, tb.MuranoApiTestCase):
    def setUp(self):
        super(TestInstanceCredentialApi, self).setUp()
        self.controller = instance_credentials.Controller()
        self.fixture = self.useFixture(config_fixture.Config())
        self.fixture.conf(args=[])

    def test_list_empty_instance_credentials(self):
        """Check that with no cloud credentials an empty list is returned."""
        self._set_policy_rules(
            {'list_instance_credentials': '@'}
        )
        self.expect_policy_check('list_instance_credentials')

        req = self._get('/identity/instancecredential')
        result = req.get_response(self.api)
        self.assertEqual({'instancecredentials': []}, json.loads(result.body))

    def test_create_instance_credentials(self):
        """Create an instance credentials, test instance credentials show()."""
        self._set_policy_rules(
            {'list_instance_credentials': '@',
             'create_instance_credentials': '@',
             'show_instance_credentials': '@'}
        )
        self.expect_policy_check('create_instance_credentials')

        fake_now = timeutils.utcnow()
        timeutils.utcnow.override_time = fake_now

        uuids = ['instance_cred_id']
        mock_uuid = self._stub_uuid(uuids)

        body = {
            "name": "cc_name",
            "cloud_type": "EC2",
            "user": "username",
            "password": "provided_password",
            "key_pair": "private_key_pair",
            "options": "{}",
            }

        expected = {'tenant_id': self.tenant,
                    'id': 'instance_cred_id',
                    'version': 0,
                    'created': timeutils.isotime(fake_now)[:-1],
                    'updated': timeutils.isotime(fake_now)[:-1]}

        expected.update(**body)

        req = self._post('/identity/instancecredential', json.dumps(body))
        result = req.get_response(self.api)
        self.assertEqual(expected, json.loads(result.body))

        # Reset the policy expectation
        self.expect_policy_check('list_instance_credentials')

        req = self._get('/identity/instancecredential')
        result = req.get_response(self.api)
        self.assertEqual(200, result.status_code)
        self.assertEqual({'instancecredentials': [expected]},
                         json.loads(result.body))

        # Reset the policy expectation
        self.expect_policy_check('show_instance_credentials',
                                 {'instance_credential_id': 'instance_cred_id'}
                                 )

        req = self._get('/identity/instancecredential/%s' % 'instance_cred_id')
        result = req.get_response(self.api)

        self.assertEqual(expected, json.loads(result.body))
        self.assertEqual(1, mock_uuid.call_count)

    def test_get_invalid_instance_credentials(self):
        self._set_policy_rules({'show_instance_credentials': '@'})

        self.expect_policy_check('show_instance_credentials',
                                 {'instance_credential_id': 'instance_cred_id'}
                                 )

        req = self._get('/identity/instancecredential/%s' % 'instance_cred_id')
        result = req.get_response(self.api)
        self.assertEqual(404, result.status_code)