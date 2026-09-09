"""Inspect real Security.framework ACLs without reading or writing Keychain items."""

from __future__ import annotations

import ctypes
import sys
from ctypes import byref, c_long, c_uint32, c_ulong, c_void_p

import pytest

pytestmark = pytest.mark.skipif(sys.platform != "darwin", reason="Security.framework")


@pytest.fixture
def darwin():
    from pipefy_auth import wrapping_key_darwin

    return wrapping_key_darwin


def _bind(library, name, arguments, result):
    function = getattr(library, name)
    function.argtypes = arguments
    function.restype = result
    return function


def _application_data(darwin, application):
    copy_data = _bind(
        darwin._sec,
        "SecTrustedApplicationCopyData",
        [c_void_p, ctypes.POINTER(c_void_p)],
        ctypes.c_int32,
    )
    data = c_void_p()
    assert copy_data(application, byref(data)) == 0
    try:
        return ctypes.string_at(
            darwin.CFDataGetBytePtr(data), darwin.CFDataGetLength(data)
        )
    finally:
        darwin.CFRelease(data)


def test_creator_access_restricts_readers_and_preserves_acl_owner(darwin):
    pointer = ctypes.POINTER(c_void_p)
    copy_matching = _bind(
        darwin._sec, "SecAccessCopyMatchingACLList", [c_void_p, c_void_p], c_void_p
    )
    copy_contents = _bind(
        darwin._sec,
        "SecACLCopyContents",
        [c_void_p, pointer, pointer, ctypes.POINTER(c_uint32)],
        ctypes.c_int32,
    )
    count = _bind(darwin._found, "CFArrayGetCount", [c_void_p], c_long)
    get = _bind(darwin._found, "CFArrayGetValueAtIndex", [c_void_p, c_long], c_void_p)
    release = _bind(darwin._found, "CFRelease", [c_void_p], None)
    create_application = _bind(
        darwin._sec,
        "SecTrustedApplicationCreateFromPath",
        [ctypes.c_char_p, pointer],
        ctypes.c_int32,
    )
    creator = c_void_p()
    assert create_application(None, byref(creator)) == 0
    try:
        creator_data = _application_data(darwin, creator)
    finally:
        release(creator)
    access = darwin._creator_access()
    try:
        for authorization in (
            "kSecACLAuthorizationDecrypt",
            "kSecACLAuthorizationChangeACL",
        ):
            acls = copy_matching(access, darwin._k(authorization))
            try:
                assert count(acls) > 0
                for index in range(count(acls)):
                    apps, description, prompt = c_void_p(), c_void_p(), c_uint32()
                    assert (
                        copy_contents(
                            get(acls, index),
                            byref(apps),
                            byref(description),
                            byref(prompt),
                        )
                        == 0
                    )
                    try:
                        if authorization == "kSecACLAuthorizationDecrypt":
                            assert apps.value is not None, (
                                "decrypt must not trust every application"
                            )
                            assert count(apps) == 1
                            assert (
                                _application_data(darwin, get(apps, 0)) == creator_data
                            )
                        else:
                            assert apps.value is not None
                            assert count(apps) == 0, (
                                "changing the ACL must still require consent"
                            )
                    finally:
                        if apps:
                            release(apps)
                        if description:
                            release(description)
            finally:
                release(acls)
    finally:
        release(access)


@pytest.mark.parametrize("value", [True, False])
def test_cf_boolean_uses_boolean_type_required_by_security_queries(darwin, value):
    get_type = _bind(darwin._found, "CFGetTypeID", [c_void_p], c_ulong)
    boolean_type = _bind(darwin._found, "CFBooleanGetTypeID", [], c_ulong)
    release = _bind(darwin._found, "CFRelease", [c_void_p], None)
    converted = darwin._cf(value)
    try:
        assert get_type(converted) == boolean_type()
    finally:
        release(converted)
