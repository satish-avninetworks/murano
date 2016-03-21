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

from murano.api.v1 import cloud_credentials
from murano.db import models
import murano.tests.unit.api.base as tb
import murano.tests.unit.utils as test_utils


class TestCloudCredentialApi(tb.ControllerTest, tb.MuranoApiTestCase):
    def setUp(self):
        super(TestCloudCredentialApi, self).setUp()
        self.controller = cloud_credentials.Controller()
        self.fixture = self.useFixture(config_fixture.Config())
        self.fixture.conf(args=[])

    def test_list_empty_cloud_credentials(self):
        """Check that with no cloud credentials an empty list is returned."""
        self._set_policy_rules(
            {'list_cloud_credentials': '@'}
        )
        self.expect_policy_check('list_cloud_credentials')

        req = self._get('/identity/cloudcredential')
        result = req.get_response(self.api)
        self.assertEqual({'cloudcredentials': []}, json.loads(result.body))

    def test_create_cloud_credentials(self):
        """Create an cloud credentials, test cloud credentials show()."""
        self._set_policy_rules(
            {'list_cloud_credentials': '@',
             'create_cloud_credentials': '@',
             'show_cloud_credentials': '@'}
        )
        self.expect_policy_check('create_cloud_credentials')

        fake_now = timeutils.utcnow()
        timeutils.utcnow.override_time = fake_now

        uuids = ['cloud_cred_id']
        mock_uuid = self._stub_uuid(uuids)

        body = {
            "name": "cc_name",
            "cloud_type": "EC2",
            "user": "username",
            "key": "provided_key",
            "private_key": "private_key",
            "endpoint": "cloud_endpoint_url",
            "options": {
                "data_center": "value1",
                "project": "value2",
                "default_vm_password":{
                    "user": "user_name",
                    "passwrod" : "password",
                    "key_pair" : "provided_keypair"
                    }
                }
            }

        expected = {'tenant_id': self.tenant,
                    'id': 'cloud_cred_id',
                    'version': 0,
                    'created': timeutils.isotime(fake_now)[:-1],
                    'updated': timeutils.isotime(fake_now)[:-1]}

        expected.update(**body)

        req = self._post('/identity/cloudcredential', json.dumps(body))
        result = req.get_response(self.api)
        self.assertEqual(expected, json.loads(result.body))

        # Reset the policy expectation
        self.expect_policy_check('list_cloud_credentials')

        req = self._get('/identity/cloudcredential')
        result = req.get_response(self.api)
        self.assertEqual(200, result.status_code)
        self.assertEqual({'cloudcredentials': [expected]}, json.loads(result.body))

        # Reset the policy expectation
        self.expect_policy_check('show_cloud_credentials',
                                 {'cloud_credential_id': 'cloud_cred_id'})

        req = self._get('/identity/cloudcredential/%s' % 'cloud_cred_id')
        result = req.get_response(self.api)

        self.assertEqual(expected, json.loads(result.body))
        self.assertEqual(1, mock_uuid.call_count)
