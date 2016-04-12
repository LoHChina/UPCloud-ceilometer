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

import datetime
from influxdb import InfluxDBClient

from oslo_config import cfg
from oslo_log import log

from ceilometer import dispatcher
from ceilometer.i18n import _LE, _LW
from ceilometer.publisher import utils as publisher_utils

LOG = log.getLogger(__name__)

OPTS = [
    cfg.StrOpt('influxdb_host',
               default="localhost",
               help="InfluxDB host."),
    cfg.IntOpt('influxdb_port',
               default=8086,
               help="InfluxDB port."),
    cfg.StrOpt('influxdb_username',
               default="root",
               help="InfluxDB username."),
    cfg.StrOpt('influxdb_password',
               default="password",
               help="InfluxDB password."),
    cfg.StrOpt('influxdb_database',
               default="ceilometer",
               help="InfluxDB database."),

]

cfg.CONF.register_opts(OPTS, group='influxdb')


class InfluxDBDispatcher(dispatcher.Base):
    """Dispatcher class for recording metering data into InfluxDB.

    The dispatcher class which records each meter into a database configured
    in ceilometer configuration file.

    To enable this dispatcher, the following section needs to be present in
    ceilometer.conf file

    [DEFAULT]
    dispatcher = influxdb
    """
    def __init__(self, conf):
        super(InfluxDBDispatcher, self).__init__(conf)

        self._meter_conn = self._get_db_conn('metering', True)

    def _get_db_conn(self, purpose, ignore_exception=False):
        try:
            conn = InfluxDBClient(
                cfg.CONF.influxdb.influxdb_host,
                cfg.CONF.influxdb.influxdb_port,
                cfg.CONF.influxdb.influxdb_username,
                cfg.CONF.influxdb.influxdb_password,
                cfg.CONF.influxdb.influxdb_database)
            return conn
        except Exception as err:
            params = {"purpose": purpose, "err": err}
            LOG.exception(_LE("Failed to connect to influxdb, purpose %(purpose)s "
                              "re-try later: %(err)s") % params)
            if not ignore_exception:
                raise

    @property
    def meter_conn(self):
        if not self._meter_conn:
            self._meter_conn = self._get_db_conn('metering')

        return self._meter_conn

    def record_metering_data(self, data):
        # We may have receive only one counter on the wire
        if not isinstance(data, list):
            data = [data]

        for meter in data:
            LOG.debug(
                'metering data %(counter_name)s '
                'for %(resource_id)s @ %(timestamp)s: %(counter_volume)s',
                {'counter_name': meter['counter_name'],
                 'resource_id': meter['resource_id'],
                 'timestamp': meter.get('timestamp', 'NO TIMESTAMP'),
                 'counter_volume': meter['counter_volume']})
            if publisher_utils.verify_signature(
                    meter, self.conf.publisher.telemetry_secret):
                try:
                    if meter.get('timestamp'):
                        timestamp = meter.get('timestamp')
                    else:
                        utcnow= datetime.datetime.utcnow()
                        timestamp = utcnow.strftime("%Y-%m-%dT%H:%M:%SZ")
                    # Record metric to InfluxDB
                    metric = ("%(resource_id)s.%(counter_name)s"
                        % ({'counter_name': meter['counter_name'],
                            'resource_id': meter['resource_id']}))

                    measure = [{'measurement': metric,
                                'time': timestamp,
                                'fields': {'value': meter['counter_volume']}}]
                    self.meter_conn.write_points(measure)
                except Exception as err:
                    LOG.exception(_LE('Failed to record metering data: %s'),
                                  err)
                    # raise the exception to propagate it up in the chain.
                    raise
            else:
                LOG.warning(_LW(
                    'message signature invalid, discarding message: %r'),
                    meter)

    @staticmethod
    def record_events(events):
        pass