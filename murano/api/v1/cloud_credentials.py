#    Copyright (c) 2013 Mirantis, Inc.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import re

from oslo_db import exception as db_exc
from oslo_log import log as logging
from sqlalchemy import desc
from webob import exc

from murano.api.v1 import request_statistics
from murano.common.i18n import _, _LE
from murano.common import policy
from murano.common import utils
from murano.common import wsgi
from murano.db import models
from murano.db.services import cloud_credentials
from murano.db.services import core_services
from murano.db import session as db_session

LOG = logging.getLogger(__name__)

API_NAME = 'CloudCredentials'

VALID_NAME_REGEX = re.compile('^[a-zA-Z]+[\w.-]*$')


class Controller(object):
    @request_statistics.stats_count(API_NAME, 'Index')
    def index(self, request):
        all_tenants = request.GET.get('all_tenants', 'false').lower() == 'true'
        LOG.debug('CloudCredentials:List <all_tenants: {tenants}>'.format(
                  tenants=all_tenants))

        if all_tenants:
            policy.check('list_cloud_credentials_all_tenants', request.context)
            filters = {}
        else:
            policy.check('list_environments', request.context)
            # Only environments from same tenant as user should be returned
            filters = {'tenant_id': request.context.tenant}

        cloudCredentials = cloud_credentials.CloudCredentialServices.\
            get_cloud_credentials_by(filters)
        cloudCredentials = [cred.to_dict() for cred in cloudCredentials]

        return {"cloudcredentials": cloudCredentials}

    @request_statistics.stats_count(API_NAME, 'Create')
    def create(self, request, body):
        LOG.debug('CloudCredentials:Create <Body {body}>'.format(body=body))
        policy.check('create_cloud_credentials', request.context)

        if not body.get('name'):
            msg = _('Please, specify a name of the cloud credential to create')
            LOG.exception(msg)
            raise exc.HTTPBadRequest(explanation=msg)

        name = unicode(body['name'])
        if len(name) > 255:
            msg = _('Cloud Credentials name should be 255 characters maximum')
            LOG.exception(msg)
            raise exc.HTTPBadRequest(explanation=msg)
        if VALID_NAME_REGEX.match(name):
            try:
                environment = cloud_credentials.CloudCredentialServices.create(
                    body.copy(),
                    request.context)
            except db_exc.DBDuplicateEntry:
                msg = _('Cloud Credentials with specified name already exists')
                LOG.exception(msg)
                raise exc.HTTPConflict(explanation=msg)
        else:
            msg = _('Cloud Credentials name must contain only alphanumeric or '
                    '"_-." characters, must start with alpha')
            LOG.exception(msg)
            raise exc.HTTPClientError(explanation=msg)

        return environment.to_dict()

    @request_statistics.stats_count(API_NAME, 'Show')
    def show(self, request, cloud_cred_id):
        LOG.debug('CloudCredentials:Show <Id: {id}>'.format(id=cloud_cred_id))
        target = {"cloud_credential_id": cloud_cred_id}
        policy.check('show_cloud_credential', request.context, target)

        session = db_session.get_session()
        credential = session.query(models.CloudCredentials).get(cloud_cred_id)
        return credential.to_dict()

    @request_statistics.stats_count(API_NAME, 'Update')
    def update(self, request, cloud_cred_id, body):
        LOG.debug('CloudCredentials:Update <Id: {id}, '
                  'Body: {body}>'.format(id=cloud_cred_id, body=body))
        target = {"cloud_credential_id": cloud_cred_id}
        policy.check('update_cloud_credential', request.context, target)

        self._validate_request(request, cloud_cred_id)

        session = db_session.get_session()
        cloud_cred = session.query(models.CloudCredentials).get(cloud_cred_id)
        if VALID_NAME_REGEX.match(str(body['name'])):
            try:
                cloud_cred.update(body)
                cloud_cred.save(session)
            except db_exc.DBDuplicateEntry:
                msg = _('Cloud Credential with specified name already exists')
                LOG.error(msg)
                raise exc.HTTPConflict(explanation=msg)
        else:
            msg = _('Environment name must contain only alphanumeric '
                    'or "_-." characters, must start with alpha')
            LOG.error(msg)
            raise exc.HTTPClientError(explanation=msg)

        return cloud_cred.to_dict()

    @request_statistics.stats_count(API_NAME, 'Delete')
    def delete(self, request, cloud_cred_id):
        LOG.debug('CloudCredentials:Delete <Id: {id}>'.format(id=cloud_cred_id)
                  )
        target = {"cloud_credential_id": cloud_cred_id}
        policy.check('delete_cloud_credential', request.context, target)
        self._validate_request(request, cloud_cred_id)
        cloud_credentials.CloudCredentialServices.remove(cloud_cred_id)

    @request_statistics.stats_count(API_NAME, 'LastStatus')
    def last(self, request, environment_id):
        session_id = None
        if hasattr(request, 'context') and request.context.session:
            session_id = request.context.session
        services = core_services.CoreServices.get_data(environment_id,
                                                       '/services',
                                                       session_id)
        session = db_session.get_session()
        result = {}
        for service in services or []:
            service_id = service['?']['id']
            entity_ids = utils.build_entity_map(service).keys()
            last_status = session.query(models.Status). \
                filter(models.Status.entity_id.in_(entity_ids)). \
                order_by(desc(models.Status.created)). \
                first()
            if last_status:
                result[service_id] = last_status.to_dict()
            else:
                result[service_id] = None
        return {'lastStatuses': result}

    @staticmethod
    def _validate_request(request, cloud_cred_id):
        cloudCredService = cloud_credentials.CloudCredentialServices
        if not cloudCredService.cloud_credential_exist(cloud_cred_id):
            msg = _('CloudCredentials <CloudCredentialId {id}> is not found').\
                format(id=cloud_cred_id)
            LOG.exception(msg)
            raise exc.HTTPNotFound(explanation=msg)
        credential = cloudCredService.get_cloud_credential(cloud_cred_id)
        if credential.tenant_id != request.context.tenant:
            LOG.exception(_LE('User is not authorized to access this tenant '
                              'resources.'))
            raise exc.HTTPUnauthorized


def create_resource():
    return wsgi.Resource(Controller())
