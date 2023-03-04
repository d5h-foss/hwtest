This document describes `hwtest`, a Python framework for testing.

Purpose of a Testing Framework
==============================

A testing framework is a useful foundation. Some of the benefits include:

- **Reusability:** Reusable code can be put in the framework. This avoids having to implement similar code over and over for each device test. Furthermore, it allows the author of each new test to focus only on what makes that test unique, and not have to spend time thinking about more generic code. E.g., a hardware driver often needs to be run in a background process to maximize telemetry frequency. This is tedious and error-prone code to write. However, it can be abstracted away and put in a framework. Then, each new hardware driver can be written as simply as possible, just directly doing I/O, without needing to think about multiprocessing, locking, shared memory, etc. The framework can include a generic class that wraps the concrete driver and continuously reads telemetry in the background.
- **Leverage:** Related to reusability, a framework provides leverage. This is because any improvements to the framework can be applied to multiple hardware tests. Hence, improvements to the framework are not just additive, but multiplicative. Also, common and tricky bugs, such as race conditions in multithreaded code, can be debugged once and for all if part of the framework. Thus, relegating tricky code to the framework where possible means it can be well debugged and tested, rather than having to write tricky code for each test.
- **Consistency:** Using a framework ensures that tests are more consistent, even across different hardware and users. Consistency makes the code more familiar to others across the company. This lowers the learning curve, and makes it easier to understand other people's code.
- **Best practices:** Related to consistency, you can encode best practices into the framework, which makes it much easier for everybody to abide by them. E.g., it's a good practice to continuously log telemetry to provide insight into how a device behaves throughout the test. This may be cumbersome to do for every device which is part of the test, but it can be made part of a framework which makes it easy.

How to Use the `hwtest` Framework
==================================

Structuring Code
----------------

Keep the following in mind when writing tests, or extending `hwtest`:

- `hwtest` should only contain generic testing framework code. It should noot contain any code specific to individual custom hardware. This is because it will need to be distributed to users / customers of your hardware if they're to run the tests, and you don't want to distribute code specific to one piece of hardware to another. Keeping this code generic also creates good boundaries, prevents coupling, and keeps the design clean and extensible.
- Low level device drivers for test hardware (e.g., a test rack module) should be kept in a separate library. Each driver should be independant of one another, ideally one file per device. This way if a device is used in multiple tests, then the specific driver files for the test can be cherry picked and distributed with the hardware.
- Code specific to a project should be kept with that project's test code. This includes custom drivers and functional test code.

Test code is split roughly along the following lines:

- **Low level drivers:** Interface with serial ports, test hardware, etc. `hwtest` doesn't contain any hardware drivers, as these are all specific to devices under test. However, `hwtest` includes a generic `Driver` interface. Using this enables running any driver in a background process, to maximize telemetry logging frequency.
- **Components:** Higher level abstraction over hardware. Composable. E.g., a single valve can be a component, and you can compose these into a board with an array of valves as a higher level component. Components may share a low level driver. E.g., if an array of valves are all controlled via the same serial port. `hwtest` includes the abstract `Component` base class that can be used to make concrete device components.
- **Test controllers:** These implement the logic for a test. E.g., it turns valves off and on. In general, it doesn't directly read and validate telemetry; it delegates this to each component. This is an important point that will be elaborated on later. `hwtest` includes the abstract `Controller` base class used as a parent for all test cases
- **Logging:** This stores the result of each bounds check, and also includes a telemetry logging framework, etc. `hwtest` includes a basic logger that writes to stdout, as well as an InfluxDB telemetry logger. It can be extended to include loggers that write to a database, etc. `hwtest` also includes a wrapper that can be composed with any other logger, to do I/O in a background thread. This prevents logging I/O from blocking the test execution, and also allows logging from multiple threads without risk of log corruption.

Example
-------

Let's use a hypothetical valve driver board as an example. The device under test will be a board with 10 valves, controlled by an RS422 serial port. The test will turn each valve on and off in turn, and check the power level for each valve. To keep the example simple, assume the RS422 driver already exists, with a simple interface as follows:

```python
class RS422:
    def read(self, valve: int) -> float:
        ...  # Returns a voltage reading associated with the given valve

    def write(self, valve: int, state: int) -> None
        ...  # Turn the given valve on (1) or off (0)
```

Note: Naively, this may be an inefficient design, since it implies the driver reads from the serial port for each valve. In reality it can probably get telemetry for all the valves with a single serial port read. This can be hidden away with various optimization techniques, such as caching true reads. This kind of optimization doesn't change the fundamentals of the example, so let's ignore that to avoid getting in the weeds.

We can model each valve as a component:

```python
from hwtest.component import Component

class Valve(Component):
    def __init__(self, channel: int, driver: RS422):
        self.name = f"valve-{channel}"  # Each component must have a unique name attribute
        self.channel = channel
        self.driver = driver

    def on(self):
        self.driver.write(self.channel, 1)
        self.state = 1  # Each component should keep track of its state

    def off(self):
        self.driver.write(self.channel, 0)
        self.state = 0

    def check(self):
        # Each component must implement a check() method. It uses the assert_* methods from
        # the base class to validate telemetry against the component's internal state.
        v = self.driver.read(self.channel)
        if self.state == 1:
            self.assert_between(4.5, v, 5.5)
        else:
            self.assert_lt(v, 0.5)
```

The comments highlight the important points. Let's go over them in more detail.

- **Name:** Each component must have a unique name attribute. This is so it can be uniquely identified in pass / fail logs.
- **State:** Each component must keep track of its own state. This is because the component is responsible for validating telemetry against its state. This is how the tests detect failure. This is different from the more straightforward way of writing a test, where hardware is commanded and then its telemetry is directly validated by the test code. There are some major benefits to the component-check approach. Namely, it allows testing of crosstalk between components. E.g., if one valve interferes with another, then this will be caught by the component-check approach, but may be missed by the command-check approach.
- **Checking:** Each component must implement a check() method which validates its internal state against telemetry. It should do this using the `assert_*` methods from the `Component` base class. These methods will log check passes / fails, along with the telemetry and bounds.

Now that we have a valve component, we can easily compose these into a valve board component:

```python
class ValveBoard(Component):
    def __init__(self, num_valves: int, driver: RS422):
        self.name = "valve board"
        self.valves = [
            Valve(i, driver) for i in range(num_valves)
        ]

    def check(self):
        # This component doesn't need to do any of its own checking, because it can delegate it
        # to the Valve components
        pass
```

Note: This component is so simple that you may chose not to create it in an actual test. However, for example purposes it serves some important points. Mainly, its `check()` method doesn't need to loop over each valve to check them, because we can have each `Valve` do that themselves. This is a matter of preference, but the point is that each component should validate its own state, and you don't need two components validating each other's state.

Now that we have our test components, we can write the actual test:

```python
from hwtest.controller import Controller

class ValveBoardTest(Controller):
    def __init__(self, valve_board: ValveBoard):
        super().__init__()  # Remember to call the base class __init__
        self.board = valve_board
        for valve in valve_board.valves:
            # You must register each component that needs check() called
            self.register_component(valve)

    def test(self):
        # Make sure all valves are off
        for valve in self.board.valves:
            valve.off()

        yield  # This will run check() for each registered component

        # Turn each valve on and run checks
        for valve in self.board.valves:
            valve.on()
            yield
            valve.off()
            yield
```

Let's go over the important parts:

- **Initialization:** Remember to call the base class `__init__` method.
- **Registering components:** Each component that needs `check()` to be called should be registered with the test controller. The test controller will call the `check()` methods for these automatically. We register each valve, because that's what we want to check. We didn't register the board itself in this case because we know it doesn't have anything to check of its own. It would be OK to register it however. In more complicated tests, it's a good idea to give each component its own `register(controller)` method. That way the board can register its valve sub-componenets, and the test controller doesn't need to know what they are.
- **Testing:** Each controller must implement a `test()` method. Furthermore, this must by a Python generator. I.e., it has one or more `yield` statements (a generator may also have a `return` statement to exit early, however it may not return a value). Each time `yeild` is invoked, the controller will run  the `check()` methods for all registered components. Because the components themselves track their own internal state, and validate it during a `check()` call, this is how the test passes or fails. If all components successfully validate internal state, then the test passes. Otherwise it fails.

We now have all the pieces we can put together:

```python
def main():
    rs422 = RS422()
    board = ValveBoard(10, rs422)
    test = ValveBoardTest(board)
    fail_count = test.run()  # This is how you run the test
```

The code here should be straightforward except for the final line. The rest just creates objects previously defined.

The final line shows how to run the tests. Note that we don't directly call `test.test()`. Instead, we run `test.run()`, which will call `test.test()` for us, and additionally call `check()` on every component for each `yield`. It returns the number of failures detected.

That concludes the basic example of how to write a test using the `hwtest` framework. Note that there are other examples in the `examples/` folder of the included code.

Next we'll get into logging and telemetry.

Logging
-------

By default `hwtest` will log to stdout. This is good for debugging, but not for production purposes. Of course, you can just redirect or `tee` the output to a file.

The logging system is easy to extend, however. You can do this if you want to log to a file directly, or to a database, or just change the format of logging. The logger interface is extremely simple:

```python
class Logger:
    def log(self, event: LogEvent) -> None:
        ...
```

To create a new logger, you just implement this interface. There are different log events, which all subclasses of the `LogEvent` base class. Each log event can have its own schema. However, the logger doesn't usually need to know about each event type or its schema. That's because each log event implements an `items()` method, which returns a `dict` with the event attributes. Events also have `keys()` and `values()` methods. This allows the logger itself to be extremely simple. E.g., the stdout logger looks like this:

```python
class StdoutLogger(Logger):
    def log(self, event: LogEvent):
        print(",".join(str(f) for f in event.values()))
```

The main event types are pass and fail events. Here's an example of how those look:

```
1672872734.5210328,PASS,valve-1,4.5,4.9,5.5
1672872735.5215826,PASS,valve-1,4.5,5.0,5.5
1672872736.5278578,FAIL,valve-1,-inf,0.6,0.5
```

The fields are as follows:

1. Timestamp of the event
2. Event type (PASS or FAIL)
3. Component name
4. Check lower bound (can be -inf)
5. Telemetry value
6. Check upper bound (can be inf)

The logging system is extremely extensible because of its simplicity. You can create a logger that ignores pass events and only logs failures, or one that changes the order of fields around, or logs to a database, or spreadsheet, etc.

You can also add new event types. Just subclass `LogEvent`, set `type_tag` to something unique, and implement the `keys()` method. You don't need to implement `values()` or `items()` because these are automatically derived from `keys()`. The `keys()` method should always call `super().keys()`, which returns a tuple, and then append any additional keys. For example, here's how the `Telemetry` event is implemented:

```python
class Telemetry(LogEvent):
    type_tag: str = "TELE"
    device: str

    def keys(self) -> Tuple[str]:
        return super().keys() + (
            "device",
        )
```

You probably also want to add a constructor to make it easier to create event objects.

Note: The key names must match the attributes, or the default `items()` and `values()` methods won't work.

Telemetry
---------

Telemetry is just an extension of the logging interface, as alluded to above. In order to log telemetry, each device should create a new `LogEvent` type specific to it. This event should subclass `Telemetry` (which itself is a subclass of `LogEvent`) and set the `device` attribute to a unique name. Here's an example from the `network.py` example in the `examples/` folder:

```python
class NetworkTelemetry(Telemetry):
    device: str = "network"
    incremental_bytes: int
    cumulative_bytes: int

    def __init__(self, incremental_bytes, cumulative_bytes) -> None:
        self.timestamp = time.time()
        self.incremental_bytes = incremental_bytes
        self.cumulative_bytes = cumulative_bytes

    def keys(self) -> Tuple[str]:
        return super().keys() + (
            "incremental_bytes",
            "cumulative_bytes",
        )
```

You can then log this event like any other. However, you probably want to log telemetry to a different logger than all the pass / fail logs. This will make it easier to visualize the data later. E.g., each device could have its own logger which logs its telemetry to a CSV file. Then you can open it in Excel to visualize it.

`hwtest` includes an InfluxDB logger just for telemetry. This logger is more ideal than a CSV file because it's simpler to visualize the data later. All you have to do is create an `InfluxDbLogger` object with the name of the bucket you want to log to. Then you can call `log` with whatever `Telemetry` subclasses you like. See the `influxdb.py` code in the `examples/` folder for some sample code.

Background Logging
------------------

While your test may have some delays in it (see the Timing section below for more details on this), you often want to log telemetry from hardware at the highest frequency possible, without any gaps. `hwtest` includes a `SubprocessDriver`, which can do this for you. It requires that your driver implements the `Driver` interface:

```python
class Driver:
    def read(self, **kwargs) -> Any:
        ...

    def write(self, **kwargs) -> Any:
        ...
```

In general, this interface shouldn't cause any restrictions since the keyword arguments give you all the flexability you should need to do different things. The `SubprocessDriver` however, currently requires that it can call `read()` with a fixed set of keyword arguments, and also that `read()` returns a subclass of `ctypes.Structure`. This is because the data needs to be stored in shared memory. `SubprocessDriver` also calls `write()` in the same thread / process as the test, which may be a problem for some drivers that need to synchronize read / write access, or that can only have a single port open to the hardware. You can extend `SubprocessDriver` in such a case to queue write commands, and run them in the subprocess.

Take a look at `examples/background.py` for a concrete example on how to use this. That example logs telemetry in the background at 50 Hz, while the test itself has multiple pauses in it.

Timing
------

When we wrote an example test above, we did a simple `yield` when we wanted to do checks. In many realistic situations, you want to wait some amount of time before doing checks, in order to let the telemetry settle. It's easy to wait a fixed amount of time before doing checks, by yielding the number of seconds to wait. Let's show an example of this by changing the valve board test.

```python
class ValveBoardTest(Controller):
    ...

    def test(self):
        ...

        # Turn each valve on and run checks
        for valve in self.board.valves:
            valve.on()
            yield 0.1
            valve.off()
            yield 0.1
```

Because we're now doing `yield 0.1` instead of `yield`, the test controller will wait 0.1 seconds (100 ms) before doing checks.

This isn't a special case, but actually just the default of a more general system. After each `yield`, the test controller will perform what's called a controller action. The default action is `WaitAndCheck`, which takes an argument for the number of seconds to wait before performing checks. The base `Controller` class has two fields, `default_action_class` and `default_action_args`. When you `yield` without an argument, it applies the action type in `default_action_class` with the arguments `default_action_args` (which can be either a single value or a tuple). Since the value of `default_action_class` is `WaitAndCheck`, and the value of `default_action_args` is `0`, when you `yield` without an argument it's the equivalent of `yield WaitAndCheck(0)`. When you `yield 0.1`, it's equivalent to `yield WaitAndCheck(0.1)`.

You can set `default_action_class` and `default_action_args` if you prefer different defaults. You can also just yield controller action objects directly. E.g., there's also an action `CheckAndWait` which does the checks first, then waits before continuing the test. If you wanted to run use that, you could do `yield CheckAndWait(1)`. Another useful action that's included is `CheckAfterTrue`. This takes a function, and will wait until the function returns `True`, then run checks. You can use this to wait until some telemetry reads a certain value before proceeding (it includes a timeout, and you can supply a function to call if the timeout is exceeded).

Putting It All Together
-----------------------

Now that you have a high-level view of what `hwtest` provides and how to use it, let's wrap up with a summary of how to go about writing a new test.

1. Start with the drivers. Implement them to use the `hwtest.driver.Driver` interface. If you're going to want to log high-frequency telemetry in a background process, then make the read result a `ctypes.Structure`.
2. Implement subclasses of `Telemetry` for whatever telemetry you want to log. This is likely very similar to the read results from your drivers.
3. Implement components. These are software abstractions for the hardware components. The important thing is that the component classes should keep track of internal state (e.g., valve on or off), and have a `check()` method that validates that state against telemetry.
4. Implement test controllers. Remember to register all your components so checks are performed.
5. Adjust logging. Once your test is running, you should get pass / fail logs. You should also be logging telemetry somewhere.

Take a look at the `examples/` folder if you have trouble getting started or using anything. Most features are covered there.

Status of `hwtest`
-------------------

`hwtest` is a work in progress. What follows is a list of areas that could use more time to be completed:

- There are unit tests with high coverage for much of the basic functionality. However, more advanced functionality currently lacks tests. Notably, some of the controller actions, InfluxDB, and `SubprocessDriver` code is lacking tests. Luckily the tests include a code coverage report, so it's easy to see where tests should be added.
- `SubprocessDriver.write()` runs in the same process / thread as the test, which may not work properly for drivers that need read / write synchronization or can only have a single open port to the hardware. This should be easy to fix by adding a multiprocess queue for commands, and perform them in the subprocess.
- Further, `SubprocessDriver` takes the wrapper driver and logger as arguments, which it passes to `Process(args=...)`. I'm not sure if this will work for every possible driver or logger, because the subprocess needs to inherit open file descriptors / network sockets / etc. for it to work properly. If it's ever a problem, it can be solved by passing factory functions instead, and have the subprocess create these objects itself.
- `InfluxDbLogger` is doing synchronous writes, which is inefficient. It should be easy to change to async or batched modes, but I didn't have time to try and test that.
- There may be other inefficiencies. This initial version of `hwtest` is meant to be functional, not as efficient as possible. Since efficiency can matter a lot for hardware tests, it may be desireable to look for optimizations.
