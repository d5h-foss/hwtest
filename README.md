Setup
=====

```
pip install hatch
```

Running Tests
-------------

```
hatch run cov
```

Running Examples
----------------

```
hatch run examples/network.py
```

Using InfluxDB
--------------

`hwtest` includes an InfluxDB telemetry logger. If you choose to use this, make sure you have InfluxDB configured by following the [setup guide](https://docs.influxdata.com/influxdb/v2.6/install/?t=Linux). Be sure to install version 2+, as that's the API the logger uses.

You'll also need to create an org and access token inside the InfluxDB UI (accessible via http://localhost:8086/ if running locally). The logger creates the InfluxDB client using [environment variables](https://pypi.org/project/influxdb-client/#via-environment-properties) for configuration. Specifically, you'll need to set at least `INFLUXDB_V2_ORG` and `INFLUXDB_V2_TOKEN`.

To test your configuration, run:

```
hatch run examples/influxdb.py
```

This should write 10 datapoints to the bucket named `network-example`.

You can also try the subprocess driver example, which runs the same test as the `influxdb.py` example, but attempts to log telemetry at 50 Hz in the background while running the test.

Distributing `hwtest`
----------------------

Your users or customers may need a copy of `hwtest` so they can run tests against your hardware. They can simply `pip install hwtest` as part of a setup script.

If you've made changes that you need to distribute, then you can run

```
hatch build
```

This will create a `hwtest-*.whl` file under a `dist/` directory. This will include just the source code, not any examples, tests, or documentation. This `.whl` file can be installed on another machine with `pip install filename.whl`. You don't need `hatch` to use the `.whl` file.
