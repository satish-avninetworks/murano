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
from murano.db.services import instance_credentials
from murano.db.services import core_services
from murano.db import session as db_session

LOG = logging.getLogger(__name__)

API_NAME = 'InstanceCredentials'

VALID_NAME_REGEX = re.compile('^[a-zA-Z]+[\w.-]*$')


class Controller(object):
    @request_statistics.stats_count(API_NAME, 'Index')
    def index(self, request):
        all_tenants = request.GET.get('all_tenants', 'false').lower() == 'true'
        LOG.debug('InstanceCredentials:List <all_tenants: {tenants}>'.format(
                  tenants=all_tenants))

        if all_tenants:
            policy.check('list_instance_credentials_all_tenants', request.context)
            filters = {}
        else:
            policy.check('list_instance_credentials', request.context)
            # Only cloud credentials from same tenant as user
            # should be returned
            filters = {'tenant_id': request.context.tenant}

        instancecredentials = instance_credentials.InstanceCredentialServices.\
            get_instance_credentials_by(filters)
        instancecredentials = [cred.to_dict() for cred in instancecredentials]

        return {"instancecredentials": instancecredentials}

    @request_statistics.stats_count(API_NAME, 'Create')
    def create(self, request, body):
        LOG.debug('InstanceCredentials:Create <Body {body}>'.format(body=body))
        policy.check('create_instance_credentials', request.context)

        if not body.get('name'):
            msg = _('Please, specify a name of the instance credential to create')
            LOG.exception(msg)
            raise exc.HTTPBadRequest(explanation=msg)

        name = unicode(body['name'])
        if len(name) > 255:
            msg = _('Instance Credentials name should be 255 characters '
                    'maximum')
            LOG.exception(msg)
            raise exc.HTTPBadRequest(explanation=msg)
        if VALID_NAME_REGEX.match(name):
            try:
                instance_cred_obj = instance_credentials.\
                    InstanceCredentialServices.create(
                    body.copy(),
                    request.context)
            except db_exc.DBDuplicateEntry:
                msg = _('Instance Credentials with specified name already'
                        ' exists')
                LOG.exception(msg)
                raise exc.HTTPConflict(explanation=msg)
        else:
            msg = _('Instance Credentials name must contain only alphanumeric '
                    'or "_-." characters, must start with alpha')
            LOG.exception(msg)
            raise exc.HTTPClientError(explanation=msg)

        return instance_cred_obj.to_dict()

    @request_statistics.stats_count(API_NAME, 'Show')
    def show(self, request, instance_cred_id):
        LOG.debug('InstanceCredentials:Show <Id: {id}>'
                  .format(id=instance_cred_id))
        target = {"instance_credential_id": instance_cred_id}
        policy.check('show_instance_credentials', request.context, target)

        session = db_session.get_session()
        credential = session.query(models.InstanceCredentials)\
            .get(instance_cred_id)

        if not credential:
            raise exc.HTTPNotFound

        return credential.to_dict()

    @request_statistics.stats_count(API_NAME, 'Update')
    def update(self, request, instance_cred_id, body):
        LOG.debug('InstancceCredentials:Update <Id: {id}, '
                  'Body: {body}>'.format(id=instance_cred_id, body=body))
        target = {"instance_credential_id": instance_cred_id}
        policy.check('update_instance_credentials', request.context, target)

        self._validate_request(request, instance_cred_id)

        session = db_session.get_session()
        instance_cred = session.query(models.InstanceCredentials)\
            .get(instance_cred_id)
        if VALID_NAME_REGEX.match(str(body['name'])):
            try:
                instance_cred.update(body)
                instance_cred.save(session)
            except db_exc.DBDuplicateEntry:
                msg = _('Instance Credential with specified name already'
                        ' exists')
                LOG.error(msg)
                raise exc.HTTPConflict(explanation=msg)
        else:
            msg = _('Instance Credential name must contain only alphanumeric '
                    'or "_-." characters, must start with alpha')
            LOG.error(msg)
            raise exc.HTTPClientError(explanation=msg)

        return instance_cred.to_dict()

    @request_statistics.stats_count(API_NAME, 'Delete')
    def delete(self, request, instance_cred_id):
        LOG.debug('InstanceCredentials:Delete <Id: {id}>'
                  .format(id=instance_cred_id))
        target = {"instance_credential_id": instance_cred_id}
        policy.check('delete_instance_credentials', request.context, target)
        self._validate_request(request, instance_cred_id)
        instance_credentials.InstanceCredentialServices\
            .remove(instance_cred_id)

    @request_statistics.stats_count(API_NAME, 'LastStatus')
    def last(self, request, instance_cred_id):
        session_id = None
        if hasattr(request, 'context') and request.context.session:
            session_id = request.context.session
        services = core_services.CoreServices.get_data(instance_cred_id,
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
    def _validate_request(request, instance_cred_id):
        instance_cred_srvs = instance_credentials.InstanceCredentialServices
        if not instance_cred_srvs.instance_credential_exist(instance_cred_id):
            msg = _('InstanceCredentials <InstanceCredentialId {id}> is not '
                    'found').format(id=instance_cred_id)
            LOG.exception(msg)
            raise exc.HTTPNotFound(explanation=msg)
        credential = instance_cred_srvs.\
            get_instance_credential(instance_cred_id)
        if credential.tenant_id != request.context.tenant:
            LOG.exception(_LE('User is not authorized to access this tenant '
                              'resources.'))
            raise exc.HTTPUnauthorized


def create_resource():
    return wsgi.Resource(Controller())
