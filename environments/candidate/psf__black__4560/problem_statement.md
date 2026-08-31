# psf/black#4560

## Problem statement

Verbatim text of the GitHub issue(s) this pull request closed. Nothing below this heading was written for this project.

### Issue #3251 — https://github.com/psf/black/issues/3251

<!--
Please make sure that the bug is not already fixed either in newer versions or the
current development version. To confirm this, you have three options:

1. Update Black's version if a newer release exists: `pip install -U black`
2. Use the online formatter at <https://black.vercel.app/?version=main>, which will use
   the latest main branch.
3. Or run _Black_ on your machine:
   - create a new virtualenv (make sure it's the same Python version);
   - clone this repository;
   - run `pip install -e .[d]`;
   - run `pip install -r test_requirements.txt`
   - make sure it's sane by running `python -m pytest`; and
   - run `black` like you did last time.
-->

**Describe the bug**

BlackDTestCase.test_cors_preflight test failure:

<details>
  <summary>show/hide</summary>

```
______________________ BlackDTestCase.test_cors_preflight ______________________

self = <tests.test_blackd.BlackDTestCase testMethod=test_cors_preflight>

    async def get_application(self) -> web.Application:
>       return blackd.make_app()

tests/test_blackd.py:46:
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
test-env/lib/python3.10/site-packages/blackd/__init__.py:76: in make_app
    executor = ProcessPoolExecutor()
/usr/lib/python3.10/concurrent/futures/process.py:657: in __init__
    self._call_queue = _SafeQueue(
/usr/lib/python3.10/concurrent/futures/process.py:168: in __init__
    super().__init__(max_size, ctx=ctx)
/usr/lib/python3.10/multiprocessing/queues.py:42: in __init__
    self._reader, self._writer = connection.Pipe(duplex=False)
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

duplex = False

    def Pipe(duplex=True):
        '''
        Returns pair of connection objects at either end of a pipe
        '''
        if duplex:
            s1, s2 = socket.socketpair()
            s1.setblocking(True)
            s2.setblocking(True)
            c1 = Connection(s1.detach())
            c2 = Connection(s2.detach())
        else:
>           fd1, fd2 = os.pipe()
E           OSError: [Errno 24] Too many open files

/usr/lib/python3.10/multiprocessing/connection.py:532: OSError
=========================== short test summary info ============================
FAILED tests/test_blackd.py::BlackDTestCase::test_cors_preflight - OSError: [...
================== 1 failed, 286 passed, 3 skipped in 11.32s ===================
```
</details>

**To Reproduce**

<!--
Minimal steps to reproduce the behavior with source code and Black's configuration.
-->

https://github.com/archlinux/svntogit-community/blob/8ef0305f6c9b28df533696a7e54d08269dc75aa8/trunk/PKGBUILD#L33-L35

```
python -m venv --system-site-packages test-env
test-env/bin/python -m installer dist/*.whl
PATH="$PWD/test-env/bin:$PATH" test-env/bin/python -m pytest
```

The package build process also hangs after the above output.

**Expected behavior**

<!-- A clear and concise description of what you expected to happen. -->

Test passes and we all live happily ever after.

**Environment**

<!-- Please complete the following information: -->

- Black's version: 22.8.0
- OS and Python version: <!-- e.g. [Linux/Python 3.7.4rc1] --> Arch Linux/Python 3.10.6

**Additional context**

<!-- Add any other context about the problem here. -->

Can provide dependency versions if that would help.

### Issue #4504 — https://github.com/psf/black/issues/4504

**Describe the bug**

When running the test suite on a machine with high nproc (i.e. large number of CPUs/cores — we have 80 on arm64 and 256 on sparc), the test suite suddenly runs out of fds in middle of testing `tests/test_blackd.py`. The remaining blackd tests fail, then pytest hangs when it's supposed to exit.

**To Reproduce**

1. Errr, get a system with high `nproc`… (perhaps some mocking will work?)
2. `tox -e py312-ci` (xdist in non-CI jobs works around the problem)

**Expected behavior**

Test suite passing.

**Environment**

- Black's version: 53a219056d1ab092ee2d4e5181c55c2e58c4756c
- OS and Python version: Gentoo Linux arm64, 3.12.7

**Additional context**

To not shadow the issue, here's a minimal log:

```pytb
$ python -m pytest tests/test_blackd.py --maxfail=2
========================================================= test session starts =========================================================
platform linux -- Python 3.12.7, pytest-8.3.3, pluggy-1.5.0
rootdir: /home/mgorny/black
configfile: pyproject.toml
plugins: xdist-3.6.1, cov-5.0.0
collected 20 items                                                                                                                    

tests/test_blackd.py ........FF

============================================================== FAILURES ===============================================================
_________________________________________ BlackDTestCase.test_blackd_request_needs_formatting _________________________________________

self = <tests.test_blackd.BlackDTestCase testMethod=test_blackd_request_needs_formatting>

    async def test_blackd_request_needs_formatting(self) -> None:
        response = await self.client.post("/", data=b"print('hello world')")
>       self.assertEqual(response.status, 200)
E       AssertionError: 500 != 200

tests/test_blackd.py:38: AssertionError
---------------------------------------------------------- Captured log call ----------------------------------------------------------
ERROR    root:__init__.py:163 Exception during handling a request
Traceback (most recent call last):
  File "/home/mgorny/black/src/blackd/__init__.py", line 124, in handle
    formatted_str = await loop.run_in_executor(
                          ^^^^^^^^^^^^^^^^^^^^^
  File "/usr/lib/python3.12/asyncio/base_events.py", line 863, in run_in_executor
    executor.submit(func, *args), loop=self)
    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/lib/python3.12/concurrent/futures/process.py", line 831, in submit
    self._start_executor_manager_thread()
  File "/usr/lib/python3.12/concurrent/futures/process.py", line 770, in _start_executor_manager_thread
    self._launch_processes()
  File "/usr/lib/python3.12/concurrent/futures/process.py", line 797, in _launch_processes
    self._spawn_process()
  File "/usr/lib/python3.12/concurrent/futures/process.py", line 807, in _spawn_process
    p.start()
  File "/usr/lib/python3.12/multiprocessing/process.py", line 121, in start
    self._popen = self._Popen(self)
                  ^^^^^^^^^^^^^^^^^
  File "/usr/lib/python3.12/multiprocessing/context.py", line 282, in _Popen
    return Popen(process_obj)
           ^^^^^^^^^^^^^^^^^^
  File "/usr/lib/python3.12/multiprocessing/popen_fork.py", line 19, in __init__
    self._launch(process_obj)
  File "/usr/lib/python3.12/multiprocessing/popen_fork.py", line 65, in _launch
    child_r, parent_w = os.pipe()
                        ^^^^^^^^^
OSError: [Errno 24] Too many open files
WARNING  asyncio:base_events.py:1981 Executing <Task pending name='Task-120' coro=<RequestHandler.start() running at /home/mgorny/black/.tox/py312/lib/python3.12/site-packages/aiohttp/web_protocol.py:534> wait_for=<Future pending cb=[Task.task_wakeup()] created at /usr/lib/python3.12/asyncio/base_events.py:449> created at /home/mgorny/black/.tox/py312/lib/python3.12/site-packages/aiohttp/web_protocol.py:319> took 0.168 seconds
____________________________________________ BlackDTestCase.test_blackd_request_no_change _____________________________________________

self = <tests.test_blackd.BlackDTestCase testMethod=test_blackd_request_no_change>

    async def get_application(self) -> web.Application:
>       return blackd.make_app()

tests/test_blackd.py:34: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
src/blackd/__init__.py:92: in make_app
    executor = ProcessPoolExecutor()
/usr/lib/python3.12/concurrent/futures/process.py:754: in __init__
    self._call_queue = _SafeQueue(
/usr/lib/python3.12/concurrent/futures/process.py:175: in __init__
    super().__init__(max_size, ctx=ctx)
/usr/lib/python3.12/multiprocessing/queues.py:43: in __init__
    self._rlock = ctx.Lock()
/usr/lib/python3.12/multiprocessing/context.py:68: in Lock
    return Lock(ctx=self.get_context())
/usr/lib/python3.12/multiprocessing/synchronize.py:169: in __init__
    SemLock.__init__(self, SEMAPHORE, 1, 1, ctx=ctx)
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

self = <Lock(owner=unknown)>, kind = 1, value = 1, maxvalue = 1

    def __init__(self, kind, value, maxvalue, *, ctx):
        if ctx is None:
            ctx = context._default_context.get_context()
        self._is_fork_ctx = ctx.get_start_method() == 'fork'
        unlink_now = sys.platform == 'win32' or self._is_fork_ctx
        for i in range(100):
            try:
>               sl = self._semlock = _multiprocessing.SemLock(
                    kind, value, maxvalue, self._make_name(),
                    unlink_now)
E                   OSError: [Errno 24] Too many open files

/usr/lib/python3.12/multiprocessing/synchronize.py:57: OSError
======================================================= short test summary info =======================================================
FAILED tests/test_blackd.py::BlackDTestCase::test_blackd_request_needs_formatting - AssertionError: 500 != 200
FAILED tests/test_blackd.py::BlackDTestCase::test_blackd_request_no_change - OSError: [Errno 24] Too many open files
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!! stopping after 2 failures !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
===================================================== 2 failed, 8 passed in 1.82s =====================================================
^CException ignored in atexit callback: <function _exit_function at 0xffff9a292c00>
Traceback (most recent call last):
  File "/usr/lib/python3.12/multiprocessing/util.py", line 360, in _exit_function
    p.join()
  File "/usr/lib/python3.12/multiprocessing/process.py", line 149, in join
    res = self._popen.wait(timeout)
          ^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/lib/python3.12/multiprocessing/popen_fork.py", line 43, in wait
    return self.poll(os.WNOHANG if timeout == 0.0 else 0)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/lib/python3.12/multiprocessing/popen_fork.py", line 27, in poll
    pid, sts = os.waitpid(self.pid, flag)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^
KeyboardInterrupt: 
```

(note I had to ^C it, as it was hanging)

My initial guess was that `ProcessPoolExecutor` is not cleaned up when `main()` finishes, but hacking a `.shutdown()` in doesn't seem to help. Adding `max_workers=` does (with values up to 29 here).

The setup here is using the default `ulimit -n 1024`.

## Reference (not part of the problem statement)

Solution-adjacent metadata. Withhold this section from any agent under evaluation; it names the fixing pull request and its commits.

- Repository: `psf/black`
- Pull request: https://github.com/psf/black/pull/4560
- Pull request title: Cache executor to avoid hitting open file limits
- Merged at: 2025-01-25T17:28:06Z
- Parent commit (bug present): `c0b92f3888a004b95e4626d8007a4b259b8f444f`
- Fix commit (bug absent): `99dbf3006b30dd77a0f650b25d9b1c8071f25e1e`
- Changed source paths: src/blackd/__init__.py
