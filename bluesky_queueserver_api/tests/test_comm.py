import asyncio
import re

import pytest
from bluesky_queueserver import generate_zmq_keys

from bluesky_queueserver_api._defaults import default_http_server_uri, default_user_group
from bluesky_queueserver_api.comm_async import ReManagerComm_HTTP_Async, ReManagerComm_ZMQ_Async
from bluesky_queueserver_api.comm_base import ReManagerAPI_Base
from bluesky_queueserver_api.comm_threads import ReManagerComm_HTTP_Threads, ReManagerComm_ZMQ_Threads

from .common import fastapi_server  # noqa: F401
from .common import (  # noqa: F401
    API_KEY_FOR_TESTS,
    re_manager,
    re_manager_cmd,
    set_qserver_zmq_address,
    set_qserver_zmq_encoding,
    set_qserver_zmq_public_key,
)

_plan1 = {"name": "count", "args": [["det1", "det2"]], "item_type": "plan"}
_user = "Test User"
_user_group = default_user_group


def test_ReManagerAPI_Base_01():
    RM = ReManagerAPI_Base()
    assert RM.request_fail_exceptions_enabled is True

    RM.request_fail_exceptions_enabled = False
    assert RM.request_fail_exceptions_enabled is False


# fmt: off
@pytest.mark.parametrize("request_fail_exceptions", [True, False])
@pytest.mark.parametrize("response, success, msg", [
    (None, False, "Request failed: None"),
    (10, False, "Request failed: 10"),
    ([], True, ""),
    ([1, 2, 3], True, ""),
    ({}, True, ""),
    ({"success": True}, True, ""),
    ({"success": False}, False, "Request failed: (no error message)"),
    ({"success": False, "msg": "Error occurred"}, False, "Request failed: Error occurred"),
])
# fmt: on
def test_ReManagerAPI_Base_02(request_fail_exceptions, response, success, msg):
    RM = ReManagerAPI_Base(request_fail_exceptions=request_fail_exceptions)
    request = {"method": "test"}
    if success or not request_fail_exceptions:
        RM._check_response(request=request, response=response)
    else:
        with pytest.raises(RM.RequestFailedError, match=re.escape(msg)):
            RM._check_response(request=request, response=response)

        try:
            RM._check_response(request=request, response=response)
        except RM.RequestFailedError as ex:
            assert ex.response == response
            assert ex.request == request
        else:
            assert False, "Exception was not raised"


def test_ReManagerComm_ZMQ_01():
    """
    ReManagerComm_ZMQ_Threads and ReManagerComm_ZMQ_Async: basic test.
    Create an object, send a request and catch timeout error (the server is not running)
    """

    params = {"item": _plan1, "user": _user, "user_group": _user_group}

    RM = ReManagerComm_ZMQ_Threads()
    with pytest.raises(RM.RequestTimeoutError, match="timeout occurred"):
        RM.send_request(method="queue_item_add", params=params)
    RM.close()

    async def testing():
        RM = ReManagerComm_ZMQ_Async()
        with pytest.raises(RM.RequestTimeoutError, match="timeout occurred"):
            await RM.send_request(method="queue_item_add", params=params)
        await RM.close()

    asyncio.run(testing())


def test_ReManagerComm_ZMQ_02(monkeypatch, re_manager_cmd):  # noqa: F811
    """
    ReManagerComm_ZMQ_Threads, ReManagerComm_ZMQ_Async: Test if the setting
    ``zmq_server_address`` and ``server_public_address`` work as expected.
    """
    zmq_manager_addr = r"tcp://*:60650"
    zmq_server_addr = r"tcp://localhost:60650"
    params = {"item": _plan1, "user": _user, "user_group": _user_group}

    public_key, private_key = generate_zmq_keys()

    # Configure communication functions built into the test system
    set_qserver_zmq_public_key(monkeypatch, server_public_key=public_key)
    set_qserver_zmq_address(monkeypatch, zmq_server_address=zmq_server_addr)
    # Configure and start RE Manager
    monkeypatch.setenv("QSERVER_ZMQ_PRIVATE_KEY", private_key)
    re_manager_cmd(["--zmq-addr", zmq_manager_addr])

    RM = ReManagerComm_ZMQ_Threads(zmq_control_addr=zmq_server_addr, zmq_public_key=public_key)
    result = RM.send_request(method="queue_item_add", params=params)
    assert result["success"] is True
    RM.close()

    async def testing():
        RM = ReManagerComm_ZMQ_Async(zmq_control_addr=zmq_server_addr, zmq_public_key=public_key)
        result = await RM.send_request(method="queue_item_add", params=params)
        assert result["success"] is True
        await RM.close()

    asyncio.run(testing())


# fmt: off
@pytest.mark.parametrize("zmq_encoding", ["json", "msgpack"])
# fmt: on
def test_ReManagerComm_ZMQ_03(monkeypatch, re_manager_cmd, zmq_encoding):  # noqa: F811
    """
    ReManagerComm_ZMQ_Threads, ReManagerComm_ZMQ_Async: Test if the setting
    ``zmq_encoding`` works as expected.
    """
    params = {"item": _plan1, "user": _user, "user_group": _user_group}

    public_key, private_key = generate_zmq_keys()

    set_qserver_zmq_encoding(monkeypatch, encoding=zmq_encoding)
    re_manager_cmd([f"--zmq-encoding={zmq_encoding}"])

    RM = ReManagerComm_ZMQ_Threads(zmq_encoding=zmq_encoding)
    result = RM.send_request(method="queue_item_add", params=params)
    assert result["success"] is True
    RM.close()

    async def testing():
        RM = ReManagerComm_ZMQ_Async(zmq_encoding=zmq_encoding)
        result = await RM.send_request(method="queue_item_add", params=params)
        assert result["success"] is True
        await RM.close()

    asyncio.run(testing())


def test_ReManagerComm_HTTP_01():
    """
    ReManagerComm_HTTP_Thread and ReManagerComm_HTTP_Async: basic test.
    Create an object, send a request and catch HTTPRequestError (the server is not running)
    """

    params = {"item": _plan1}

    RM = ReManagerComm_HTTP_Threads()
    with pytest.raises(RM.HTTPRequestError, match=re.escape("HTTP request error: [Errno 111] Connection refused")):
        RM.send_request(method="queue_item_add", params=params)
    RM.close()

    async def testing():
        RM = ReManagerComm_HTTP_Async()
        with pytest.raises(
            RM.HTTPRequestError, match=re.escape("HTTP request error: All connection attempts failed")
        ):
            await RM.send_request(method="queue_item_add", params=params)
        await RM.close()

    asyncio.run(testing())


# fmt: off
@pytest.mark.parametrize("server_uri, success", [
    (None, True),
    (default_http_server_uri, True),
    ("http://localhost:60660", False),
])
# fmt: on
def test_ReManagerComm_HTTP_02(re_manager, fastapi_server, server_uri, success):  # noqa: F811
    """
    ReManagerComm_HTTP_Thread and ReManagerComm_HTTP_Async:
    Test if parameter for setting HTTP server URI works as expected
    """
    params = {"item": _plan1}

    RM = ReManagerComm_HTTP_Threads(http_server_uri=server_uri)
    RM.set_authorization_key(api_key=API_KEY_FOR_TESTS)
    if success:
        result = RM.send_request(method="queue_item_add", params=params)
        assert result["success"] is True
    else:
        with pytest.raises(RM.HTTPRequestError):
            RM.send_request(method="queue_item_add", params=params)
    RM.close()

    async def testing():
        RM = ReManagerComm_HTTP_Async(http_server_uri=server_uri)
        RM.set_authorization_key(api_key=API_KEY_FOR_TESTS)
        if success:
            result = await RM.send_request(method="queue_item_add", params=params)
            assert result["success"] is True
        else:
            with pytest.raises(RM.HTTPRequestError):
                await RM.send_request(method="queue_item_add", params=params)
        await RM.close()

    asyncio.run(testing())


def test_ReManagerComm_HTTP_03():
    """
    ReManagerComm_HTTP_Thread and ReManagerComm_HTTP_Async: Attempt to call
    unknown method, which does not exist in the table and can not be converted to
    endpoint name.
    """

    RM = ReManagerComm_HTTP_Threads()
    with pytest.raises(RM.RequestParameterError, match=re.escape("Unknown method 'unknown_method'")):
        RM.send_request(method="unknown_method")
    RM.close()

    async def testing():
        RM = ReManagerComm_HTTP_Async()
        with pytest.raises(RM.RequestParameterError, match=re.escape("Unknown method 'unknown_method'")):
            await RM.send_request(method="unknown_method")
        await RM.close()

    asyncio.run(testing())


@pytest.mark.parametrize("protocol", ["ZMQ", "HTTP"])
def test_ReManagerComm_ALL_01(re_manager, fastapi_server, protocol):  # noqa: F811
    """
    ReManagerComm_ZMQ_Threads and ReManagerComm_ZMQ_Async,
    ReManagerComm_HTTP_Threads and ReManagerComm_HTTP_Async:
    Send a request: successful (accepted by the server), rejected and
    raising an exception, rejected not raising an exception.
    """

    if protocol == "ZMQ":
        params = {"item": _plan1, "user": _user, "user_group": _user_group}
        params_invalid = {"user": _user, "user_group": _user_group}
        RM_threads_class = ReManagerComm_ZMQ_Threads
        RM_async_class = ReManagerComm_ZMQ_Async
    elif protocol == "HTTP":
        params = {"item": _plan1}
        params_invalid = {"user": _user}
        RM_threads_class = ReManagerComm_HTTP_Threads
        RM_async_class = ReManagerComm_HTTP_Async
    else:
        assert False, f"Unknown protocol {protocol!r}"

    RM = RM_threads_class()
    if protocol == "HTTP":
        RM.set_authorization_key(api_key=API_KEY_FOR_TESTS)
    result = RM.send_request(method="queue_item_add", params=params)
    assert result["success"] is True
    RM.close()

    RM = RM_threads_class()
    if protocol == "HTTP":
        RM.set_authorization_key(api_key=API_KEY_FOR_TESTS)
    # Test that the exception is raised
    with pytest.raises(RM.RequestFailedError, match="request contains no item info"):
        RM.send_request(method="queue_item_add", params=params_invalid)
    # Test that the exception has the copy of request
    try:
        RM.send_request(method="queue_item_add", params=params_invalid)
    except RM.RequestFailedError as ex:
        assert ex.response["success"] is False
        assert "request contains no item info" in ex.response["msg"]
    else:
        assert False
    RM.close()

    # Do not raise the exceptions if the request fails (rejected by the server)
    RM = RM_threads_class(request_fail_exceptions=False)
    if protocol == "HTTP":
        RM.set_authorization_key(api_key=API_KEY_FOR_TESTS)
    result = RM.send_request(method="queue_item_add", params=params_invalid)
    assert result["success"] is False
    assert "request contains no item info" in result["msg"]
    RM.close()

    # Repeat the same test for 'async' version
    async def testing():
        RM = RM_async_class()
        if protocol == "HTTP":
            RM.set_authorization_key(api_key=API_KEY_FOR_TESTS)
        result = await RM.send_request(method="queue_item_add", params=params)
        assert result["success"] is True
        await RM.close()

        RM = RM_async_class()
        if protocol == "HTTP":
            RM.set_authorization_key(api_key=API_KEY_FOR_TESTS)
        # Test that the exception is raised
        with pytest.raises(RM.RequestFailedError, match="request contains no item info"):
            await RM.send_request(method="queue_item_add", params=params_invalid)
        # Test that the exception has the copy of request
        try:
            await RM.send_request(method="queue_item_add", params=params_invalid)
        except RM.RequestFailedError as ex:
            assert ex.response["success"] is False
            assert "request contains no item info" in ex.response["msg"]
        else:
            assert False
        await RM.close()

        # Do not raise the exceptions if the request fails (rejected by the server)
        RM = RM_async_class(request_fail_exceptions=False)
        if protocol == "HTTP":
            RM.set_authorization_key(api_key=API_KEY_FOR_TESTS)
        result = await RM.send_request(method="queue_item_add", params=params_invalid)
        assert result["success"] is False
        assert "request contains no item info" in result["msg"]
        await RM.close()

    asyncio.run(testing())
