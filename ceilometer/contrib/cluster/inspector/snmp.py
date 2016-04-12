# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import itertools

from ceilometer.hardware.inspector import snmp
import logging

LOG = logging.getLogger(__name__)


class SNMPInspector(snmp.SNMPInspector):

    def inspect_generic(self, host, cache, extra_metadata, param):
        data = 0
        result = super(SNMPInspector, self).inspect_generic(
            host, cache, extra_metadata, param)
        for value, metadata, extra_metadata in result:
            if ("eth" in metadata.get('name') or
                "sd" in metadata.get('name')):
                data += value

        if param["oid_extra"]:
            param['metric_oid'] = param["oid_extra"]

        result = super(SNMPInspector, self).inspect_generic(
            host, cache, extra_metadata, param)
        for value, metadata, extra_metadata in result:
            if ("eth" in metadata.get('name') or
                "sd" in metadata.get('name')):
                data += value
        if param.get('identifier') == "network":
            data = data * 8
        yield (data, {}, {'resource_id': 'cluster'})

    def prepare_params(self, param):
        data = super(SNMPInspector, self).prepare_params(param)
        data["oid_extra"] = (param['oid_extra'], eval(param['type']))
        data['identifier'] = param.get('identifier')
        return data
