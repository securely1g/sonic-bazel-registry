"""Exercise the public libraries with the owner's real Common binding."""

from lldp_syncd.conventions import LldpChassisIdSubtype, LldpPortIdSubtype
from lldp_syncd.daemon import LldpSyncDaemon, parse_time
from sonic_syncd import SonicSyncDaemon
from swsscommon.swsscommon import SonicV2Connector

assert SonicV2Connector.__module__ == "swsscommon.swsscommon"
assert issubclass(LldpSyncDaemon, SonicSyncDaemon)
assert parse_time("2 days, 03:04:05") == 183845
assert parse_time("0 day, 00:00:30") == 30
assert LldpChassisIdSubtype.macAddress == 4
assert LldpPortIdSubtype.interfaceName == 5


class OneUpdate(SonicSyncDaemon):
    def __init__(self):
        super().__init__(update_frequency=0.001)
        self.saved = []

    def source_update(self):
        return {"Ethernet0": "peer"}

    def parse_update(self, value):
        return {key: name.upper() for key, name in value.items()}

    def sync(self, value):
        self.saved.append(value)
        self.stop()


daemon = OneUpdate()
daemon.start()
daemon.join(timeout=5)
assert not daemon.is_alive()
assert daemon.saved == [{"Ethernet0": "PEER"}]
print("Public Common-backed LLDP parser and one real sync thread passed")
