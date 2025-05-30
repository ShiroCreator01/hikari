# Copyright (c) 2020 Nekokatt
# Copyright (c) 2021-present davfsa
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
"""Events that fire when voice state changes."""

from __future__ import annotations

__all__: typing.Sequence[str] = ("VoiceEvent", "VoiceServerUpdateEvent", "VoiceStateUpdateEvent")

import abc
import typing

import attrs

from hikari import intents
from hikari.events import base_events
from hikari.events import shard_events
from hikari.internal import attrs_extensions
from hikari.internal import typing_extensions

if typing.TYPE_CHECKING:
    from hikari import snowflakes
    from hikari import traits
    from hikari import voices
    from hikari.api import shard as gateway_shard


class VoiceEvent(shard_events.ShardEvent, abc.ABC):
    """Base for any voice-related event."""

    __slots__: typing.Sequence[str] = ()

    @property
    @abc.abstractmethod
    def guild_id(self) -> snowflakes.Snowflake:
        """ID of the guild this event is for."""


@base_events.requires_intents(intents.Intents.GUILD_VOICE_STATES)
@attrs_extensions.with_copy
@attrs.define(kw_only=True, weakref_slot=False)
class VoiceStateUpdateEvent(VoiceEvent):
    """Event fired when a user changes their voice state.

    Sent when a user joins, leaves or moves voice channel(s).

    This is also fired for the application user, and is used when preparing
    to connect to the voice gateway to stream audio or video content.
    """

    shard: gateway_shard.GatewayShard = attrs.field(metadata={attrs_extensions.SKIP_DEEP_COPY: True})
    # <<inherited docstring>>.

    old_state: voices.VoiceState | None = attrs.field(repr=True)
    """The old voice state.

    This will be [`None`][] if the voice state missing from the cache.
    """

    state: voices.VoiceState = attrs.field(repr=True)
    """Voice state that this update contained."""

    @property
    @typing_extensions.override
    def app(self) -> traits.RESTAware:
        # <<inherited docstring from Event>>.
        return self.state.app

    @property
    @typing_extensions.override
    def guild_id(self) -> snowflakes.Snowflake:
        # <<inherited docstring from VoiceEvent>>
        return self.state.guild_id


@attrs_extensions.with_copy
@attrs.define(kw_only=True, weakref_slot=False)
class VoiceServerUpdateEvent(VoiceEvent):
    """Event fired when a voice server is changed.

    Sent when initially connecting to voice and when the current voice instance
    falls over to a new server.
    """

    app: traits.RESTAware = attrs.field(metadata={attrs_extensions.SKIP_DEEP_COPY: True})
    # <<inherited docstring from Event>>.

    shard: gateway_shard.GatewayShard = attrs.field(metadata={attrs_extensions.SKIP_DEEP_COPY: True})
    # <<inherited docstring from ShardEvent>>.

    guild_id: snowflakes.Snowflake = attrs.field(repr=True)
    # <<inherited docstring from VoiceEvent>>

    token: str = attrs.field(repr=False)
    """Token that should be used to authenticate with the voice gateway."""

    raw_endpoint: str | None = attrs.field(repr=True)
    """Raw endpoint URI that Discord sent.

    If this is [`None`][], it means that the server has been deallocated
    and you have to disconnect. You will later receive a new event specifying
    what endpoint to connect to.

    !!! warning
        This will not contain the scheme to use. Use the
        [`endpoint`][hikari.events.voice_events.VoiceServerUpdateEvent.endpoint]
        property to get a representation that has this prepended.
    """

    @property
    def endpoint(self) -> str | None:
        """URI for this voice server host, with the correct scheme prepended.

        If this is [`None`][], it means that the server has been deallocated
        and you have to disconnect. You will later receive a new event specifying
        what endpoint to connect to.
        """
        if self.raw_endpoint is None:
            return None

        return f"wss://{self.raw_endpoint}"
