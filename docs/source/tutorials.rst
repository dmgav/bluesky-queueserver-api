.. _tutorials_queue_server_api:

=========
Tutorials
=========

The following tutorials are available:

- :ref:`tutorial_opening_closing_re_worker_environment`
- :ref:`tutorial_adding_items_to_the_queue`


.. _tutorial_opening_closing_re_worker_environment:

Opening and Closing RE Worker Environment
-----------------------------------------

The tutorial illustrates how to open and close the RE Worker environment using
**bluesky-queueserver-api** package. For more details on the used API please refer to
`the respective tutorial <https://blueskyproject.io/bluesky-queueserver/tutorials.html#tutorial-opening-closing-re-worker-environment>`_
in **bluesky-queueserver** package documentation.

.. code-block:: python

    In [1]: from bluesky_queueserver_api.zmq import REManagerAPI

    In [2]: RM = REManagerAPI()

By default, ``REManagerAPI`` object connects to the RE Manager
running on the ``localhost`` with the default port. The host name and the port can
be customized by passing parameters the respective parameters to ``REManagerAPI``
constructor. Note, that the constructor parameters are different for the 0MQ and REST
API versions.

Requests are sent to RE Manager by calling the respective methods of the ``REManagerAPI``.
Let's open the RE Worker environment:

.. code-block:: python

    In [3]: RM.environment_open()
    Out[3]: {'success': True, 'msg': ''}

If the API calls are successful, the methods are returning a dictionary with parameters.
Here, the ``'success': True`` indicates that the request was successfully accepted by
the RE Manager.

In practice, it may take some time for the environment to be opened. The API package
include a number of ``wait_for_...`` methods that can be used to wait for status
parameters to reach the desired values. For example, to wait for the completion of
many operation, such as opening the environment, we can use ``wait_for_idle()`` method:

.. code-block:: python

    In [4]: RM.wait_for_idle(timeout=60)

The function exits (returns *None*) if RE Manager state is *idle* within the specified
timeout. Otherwise it raises ``WaitTimeoutError`` exception. All ``wait_for_...`` methods
accept ``monitor`` parameter (see documentation for ``WaitMonitor`` class). Monitor
object may be used to cancel wait before timeout expires. In this case ``WaitCancelError``
is raised.

RE Manager status is changed to *IDLE* whether the environment was successfully opened
or the operation failed. To verify that the environment the environment exists, we can check
the status of RE Manager:

.. code-block:: python

    In [5]: RM.status()
    Out[5]:
    {'msg': 'RE Manager v0.0.20',
    ...
    'worker_environment_exists': True,
    'worker_environment_state': 'idle',
    ...
    'lock': {'environment': False, 'queue': False}}

If API request is not accepted by the RE Manager, the respective method raises
``RequestFailedError``. The exception object contains full copies of the request
and response parameters that may be used for error processing. For example,
if the environment is already opened, an attempt to open it again raises
the following exception:

.. code-block:: python

    In [6]: RM.environment_open()
    ---------------------------------------------------------------------------
    RequestFailedError                        Traceback (most recent call last)
    Cell In[6], line 1
    ----> 1 RE.environment_open()

    File ~/Projects/bluesky-queueserver-api/bluesky_queueserver_api/api_threads.py:411, in API_Threads_Mixin.environment_open(self, lock_key)
        409 self._clear_status_timestamp()
        410 request_params = self._prepare_environment_control(lock_key=lock_key)
    --> 411 return self.send_request(method="environment_open", params=request_params)

    File ~/Projects/bluesky-queueserver-api/bluesky_queueserver_api/comm_threads.py:52, in ReManagerComm_ZMQ_Threads.send_request(self, method, params)
        50 except Exception:
        51     self._process_comm_exception(method=method, params=params)
    ---> 52 self._check_response(request={"method": method, "params": params}, response=response)
        54 return response

    File ~/Projects/bluesky-queueserver-api/bluesky_queueserver_api/comm_base.py:169, in ReManagerAPI_Base._check_response(self, request, response)
        167 is_mapping = isinstance(response, Mapping)
        168 if not any([is_iterable, is_mapping]) or (is_mapping and not response.get("success", True)):
    --> 169     raise self.RequestFailedError(request, response)

    RequestFailedError: Request failed: RE Worker environment already exists.

To close the environment, use the ``environment_close()`` method:

.. code-block:: python

    In [8]: RM.environment_close()
    Out[8]: {'success': True, 'msg': ''}

    In [9]: RM.status()
    Out[9]:
    {'msg': 'RE Manager v0.0.20',
    ...
    'worker_environment_exists': False,
    'worker_environment_state': 'closed',
    ...
    'lock': {'environment': False, 'queue': False}}

The unresponsive environment may be closed by calling the ``environment_destroy()`` method.
The method kills the Worker process and should be used as a last resort:

.. code-block:: python

    In [10]: RM.environment_open()
    Out[10]: {'success': True, 'msg': ''}

    # Wait until the environment is opened

    In [11]: RM.environment_destroy()
    Out[11]: {'success': True, 'msg': ''}

The full script that opens the environment and closes the environment:

.. code-block:: python

    from bluesky_queueserver_api.zmq import REManagerAPI

    RM = REManagerAPI()

    try:
        RM.environment_open()

        RM.wait_for_idle()
        status = RM.status()
        if not status["worker_environment_exists"]:
            raise RuntimeError("Failed to open the Worker environment")
        print("Environment was opened successfully")

        RM.environment_close()
        RM.wait_for_idle()

    except RM.RequestFailedError as ex:
        print(f"{ex}\n{ex.request = }\n{ex.response =}")
    except RM.WaitTimeoutError as ex:
        print(f"Timeout: {ex}")
    except Exception as ex:
        print(f"Error: {ex}")

    RM.close()

The script may easily be converted to async version by awaiting on all API calls:

.. code-block:: python

    import asyncio
    from bluesky_queueserver_api.zmq.aio import REManagerAPI

    async def main():

        RM = REManagerAPI()

        try:
            await RM.environment_open()

            await RM.wait_for_idle()
            status = await RM.status()
            if not status["worker_environment_exists"]:
                raise RuntimeError("Failed to open the Worker environment")
            print("Environment was opened successfully")

            await RM.environment_close()
            await RM.wait_for_idle()

        except RM.RequestFailedError as ex:
            print(f"{ex}\n{ex.request = }\n{ex.response =}")
        except RM.WaitTimeoutError as ex:
            print(f"Timeout: {ex}")
        except Exception as ex:
            print(f"Error: {ex}")

        await RM.close()

    asyncio.run(main())


.. _tutorial_adding_items_to_the_queue:

Adding Items to the Queue
-------------------------

The tutorial illustrates how to add items to the queue. Only the plans in included in the
list of allowed plans can be added to the queue and only the devices in the list of allowed
devices can be used in the plans. The package provides ``plans_allowed()`` and ``devices_allowed()``
methods to load the lists from the RE Manager.

.. code-block:: python

    In [1]: from bluesky_queueserver_api.zmq import REManagerAPI

    In [2]: RM = REManagerAPI()

    In [3]: p = RM.plans_allowed()

    In [4]: list(p.keys())
    Out[4]: ['success', 'msg', 'plans_allowed_uid', 'plans_allowed']

    In [5]: type(p["plans_allowed"])
    Out[5]: dict

    In [6]: len(p["plans_allowed"])
    Out[6]: 32

    In [7]: list(p["plans_allowed"].keys())
    Out[7]:
    ['adaptive_scan',
    'count',
    'count_bundle_test',
    'fly',
    'grid_scan',
    'inner_product_scan',
    'list_grid_scan',
    'list_scan',
    'log_scan',
    'marked_up_count',
    'move_then_count',
    'plan_test_progress_bars',
    'ramp_plan',
    'rel_adaptive_scan',
    'rel_grid_scan',
    'rel_list_grid_scan',
    'rel_list_scan',
    'rel_log_scan',
    'rel_scan',
    'rel_spiral',
    'rel_spiral_fermat',
    'rel_spiral_square',
    'relative_inner_product_scan',
    'scan',
    'scan_nd',
    'sim_multirun_plan_nested',
    'spiral',
    'spiral_fermat',
    'spiral_square',
    'tune_centroid',
    'tweak',
    'x2x_scan']

    In [8]: p["plans_allowed_uid"]
    Out[8]: '2e291051-24df-497e-ad47-be0697daaafc'

The ``plan_allowed_uid`` parameter is UID of the current list that is changed each time the list
is updated. The UID is also part of RE Manager status. The list of allowed plans is cached locally
by REManagerAPI object and is updated automatically when the UID changes. The other lists as
well as the plan queue and the plan history are also cached locally. The RE Manager status contains
UIDs of all lists. The UIDs are used to check if the local cache is up-to-date each time
the respective list is requested. The following UIDs are part of RE Manager status:

.. code-block:: python

    In [9]: RM.status()
    Out[9]:
    {'msg': 'RE Manager v0.0.20',
    ...
    'run_list_uid': '0d518078-7bb8-43d0-963f-2ebc09edd2de',
    'plan_queue_uid': '1eec3dcd-d0b1-4e6a-92e7-7738eb0a71d0',
    'plan_history_uid': '1a47f909-6805-447f-9899-a38037dd1fa1',
    'devices_existing_uid': 'a82e5a72-2ad4-4eed-996f-63d798d021ca',
    'plans_existing_uid': '6b02808d-526a-4289-807f-bdb867f4a3b5',
    'devices_allowed_uid': '82942752-5324-486b-92d2-9e129f5d034b',
    'plans_allowed_uid': '2e291051-24df-497e-ad47-be0697daaafc',
    'task_results_uid': '90337219-9ad6-4d1d-a716-9cc5b5118b96',
    'lock_info_uid': 'a37062cb-3b44-46c1-885d-3030c84291d3',
    ...
    'lock': {'environment': False, 'queue': False}}

The methods ``item_add()`` and ``item_add_batch()`` are used to add items to the queue.
The methods accept an item (or a list of items for the batch method) of ``BItem``,
``BPlan`` or ``BInst`` types. The methods also accept be plain dictionaries of parameters
used by raw API, but using the user-friendly convenience classes is recommended.
``BPlan`` and ``BInst`` are subclasses of ``BItem``, which may be used for both plans
and instructions.

The queue and the history may already contain items. To clear the queue and the history
use the ``queue_clear()`` and ``history_clear()`` methods:

.. code-block:: python

    In [10]: RM.queue_clear()
    Out[10]: {'success': True, 'msg': ''}

    In [11]: RM.history_clear()
    Out[11]: {'success': True, 'msg': ''}

    In [12]: RM.status()
    Out[12]:
    {'msg': 'RE Manager v0.0.20',
    'items_in_queue': 0,
    'items_in_history': 0,
    ...
    'lock': {'environment': False, 'queue': False}}

Now, let's add a plan and an instruction to the queue:

.. code-block:: python

    In [13]: from bluesky_queueserver_api import BPlan, BInst

    In [14]: plan = BPlan("count", ['det1', 'det2'], delay=1, num=10)

    In [15]: plan
    Out[15]: {'item_type': 'plan', 'name': 'count', 'args': [['det1', 'det2']], 'kwargs': {'delay': 1, 'num': 10}}

    In [16]: RM.item_add(plan)
    Out[16]:
    {'success': True,
    'msg': '',
    'qsize': 1,
    'item': {'item_type': 'plan',
    'name': 'count',
    'args': [['det1', 'det2']],
    'kwargs': {'delay': 1, 'num': 10},
    'user': 'Queue Server API User',
    'user_group': 'primary',
    'item_uid': 'e08d1c25-2cf6-41a2-83d1-39887bf58d24'}}

Note, that ``user`` and ``user_group`` are sent as part of 0MQ API request. The default values
may be changed by setting ``RM.user`` and ``RM.user_group`` properties. The values can also
be sent with each API request (parameters ``user`` and ``user_group`` of ``item_add()`` method).
When using REST API, the values of ``user`` and ``user_group`` are determined by the HTTP server
based on the login information of the current user.

The ``BInst`` helper class is used to add instructions to the queue. Only one ``queue_stop``
instruction, which stops execution of the queue, is currently supported:

.. code-block:: python

    In [17]: RM.item_add(BInst("queue_stop"))
    Out[17]:
    {'success': True,
    'msg': '',
    'qsize': 2,
    'item': {'item_type': 'instruction',
    'name': 'queue_stop',
    'user': 'Queue Server API User',
    'user_group': 'primary',
    'item_uid': '583192b1-efa5-4c77-ae30-1ebf37341c41'}}

The queue may be downloaded using the ``queue_get()`` method:

.. code-block:: python

    In [18]: RM.queue_get()
    Out[18]:
    {'success': True,
    'msg': '',
    'items': [{'item_type': 'plan',
    'name': 'count',
    'args': [['det1', 'det2']],
    'kwargs': {'delay': 1, 'num': 10},
    'user': 'Queue Server API User',
    'user_group': 'primary',
    'item_uid': 'e08d1c25-2cf6-41a2-83d1-39887bf58d24'},
    {'item_type': 'instruction',
    'name': 'queue_stop',
    'user': 'Queue Server API User',
    'user_group': 'primary',
    'item_uid': '583192b1-efa5-4c77-ae30-1ebf37341c41'}],
    'running_item': {},
    'plan_queue_uid': '4b7ed0d5-895e-4a65-805f-647398e6fae6'}

By default, the ``item_add()`` method adds items to the end of the queue. The method also
accepts multiple optional parameters to control where the item is inserted: ``pos``,
``before_uid`` and ``after_uid``. The ``pos`` parameter may be set to ``"front"``, ``"back"``
string values or an integer. The integer value represents the position of the inserted item
in the queue (0 - inserted to front of the queue, 1 - after the first item, etc.). Negative
integer is used to specify positions counted from the back of the queue (-1 - insert to
the back of the queue, -2 - insert before the last item, etc.). Let's add a plan to psition
-2:

.. code-block:: python

    In [31]: RM.item_add(BPlan("count", ['det2'], delay=1, num=10), pos=-2)
    Out[31]:
    {'success': True,
    'msg': '',
    'qsize': 3,
    'item': {'item_type': 'plan',
    'name': 'count',
    'args': [['det2']],
    'kwargs': {'delay': 1, 'num': 10},
    'user': 'Queue Server API User',
    'user_group': 'primary',
    'item_uid': 'a0b95d71-ca25-4571-9f75-5d07ca376efa'}}

    In [32]: RM.queue_get()
    Out[32]:
    {'success': True,
    'msg': '',
    'items': [{'item_type': 'plan',
    'name': 'count',
    'args': [['det1', 'det2']],
    'kwargs': {'delay': 1, 'num': 10},
    'user': 'Queue Server API User',
    'user_group': 'primary',
    'item_uid': 'e08d1c25-2cf6-41a2-83d1-39887bf58d24'},
    {'item_type': 'plan',
    'name': 'count',
    'args': [['det2']],
    'kwargs': {'delay': 1, 'num': 10},
    'user': 'Queue Server API User',
    'user_group': 'primary',
    'item_uid': 'a0b95d71-ca25-4571-9f75-5d07ca376efa'},
    {'item_type': 'instruction',
    'name': 'queue_stop',
    'user': 'Queue Server API User',
    'user_group': 'primary',
    'item_uid': '583192b1-efa5-4c77-ae30-1ebf37341c41'}],
    'running_item': {},
    'plan_queue_uid': '54932469-68fc-47b4-955e-8a4e45917997'}

The parameters ``before_uid`` and ``after_uid`` are used to insert the item before or after
an existing reference item with the specified item UID. The reference item **must** exist in
the queue, otherwise the API request fails. Using reference items to insert new elements
is more robust and strongly recommended when modifying a running queue. Let's insert another
item before the second item (with item UID ``'a0b95d71-ca25-4571-9f75-5d07ca376efa'``):

.. code-block:: python

    In [33]: RM.item_add(BPlan("count", ['det1'], delay=1, num=10), before_uid='a0b95d71-ca25-4571-9f75-5d07ca376efa')
    Out[33]:
    {'success': True,
    'msg': '',
    'qsize': 4,
    'item': {'item_type': 'plan',
    'name': 'count',
    'args': [['det1']],
    'kwargs': {'delay': 1, 'num': 10},
    'user': 'Queue Server API User',
    'user_group': 'primary',
    'item_uid': 'e51ef3cc-0888-4cab-8149-25fce1abe22a'}}

    In [34]: RM.queue_get()
    Out[34]:
    {'success': True,
    'msg': '',
    'items': [{'item_type': 'plan',
    'name': 'count',
    'args': [['det1', 'det2']],
    'kwargs': {'delay': 1, 'num': 10},
    'user': 'Queue Server API User',
    'user_group': 'primary',
    'item_uid': 'e08d1c25-2cf6-41a2-83d1-39887bf58d24'},
    {'item_type': 'plan',
    'name': 'count',
    'args': [['det1']],
    'kwargs': {'delay': 1, 'num': 10},
    'user': 'Queue Server API User',
    'user_group': 'primary',
    'item_uid': 'e51ef3cc-0888-4cab-8149-25fce1abe22a'},
    {'item_type': 'plan',
    'name': 'count',
    'args': [['det2']],
    'kwargs': {'delay': 1, 'num': 10},
    'user': 'Queue Server API User',
    'user_group': 'primary',
    'item_uid': 'a0b95d71-ca25-4571-9f75-5d07ca376efa'},
    {'item_type': 'instruction',
    'name': 'queue_stop',
    'user': 'Queue Server API User',
    'user_group': 'primary',
    'item_uid': '583192b1-efa5-4c77-ae30-1ebf37341c41'}],
    'running_item': {},
    'plan_queue_uid': '4bf5e248-a647-44bc-ab08-3a751e5f528f'}
