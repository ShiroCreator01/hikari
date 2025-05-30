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
"""Events that fire if messages are sent/updated/deleted."""

from __future__ import annotations

__all__: typing.Sequence[str] = (
    "DMMessageCreateEvent",
    "DMMessageDeleteEvent",
    "DMMessageUpdateEvent",
    "GuildBulkMessageDeleteEvent",
    "GuildMessageCreateEvent",
    "GuildMessageDeleteEvent",
    "GuildMessageUpdateEvent",
    "MessageCreateEvent",
    "MessageDeleteEvent",
    "MessageEvent",
    "MessageUpdateEvent",
)

import abc
import typing

import attrs

from hikari import channels
from hikari import intents
from hikari import snowflakes
from hikari import traits
from hikari import undefined
from hikari.events import base_events
from hikari.events import shard_events
from hikari.internal import attrs_extensions
from hikari.internal import typing_extensions

if typing.TYPE_CHECKING:
    from hikari import embeds as embeds_
    from hikari import guilds
    from hikari import messages
    from hikari import users
    from hikari.api import shard as shard_


@base_events.requires_intents(intents.Intents.DM_MESSAGES, intents.Intents.GUILD_MESSAGES)
class MessageEvent(shard_events.ShardEvent, abc.ABC):
    """Any event that concerns manipulation of messages."""

    __slots__: typing.Sequence[str] = ()

    @property
    @abc.abstractmethod
    def channel_id(self) -> snowflakes.Snowflake:
        """ID of the channel that this event concerns."""

    @property
    @abc.abstractmethod
    def message_id(self) -> snowflakes.Snowflake:
        """ID of the message that this event concerns."""


@base_events.requires_intents(intents.Intents.DM_MESSAGES, intents.Intents.GUILD_MESSAGES)
class MessageCreateEvent(MessageEvent, abc.ABC):
    """Event that is fired when a message is created."""

    __slots__: typing.Sequence[str] = ()

    @property
    @typing_extensions.override
    def app(self) -> traits.RESTAware:
        # <<inherited docstring from Event>>.
        return self.message.app

    @property
    def author(self) -> users.User:
        """User that sent the message."""
        return self.message.author

    @property
    def author_id(self) -> snowflakes.Snowflake:
        """ID of the author of the message this event concerns."""
        return self.author.id

    @property
    @typing_extensions.override
    def channel_id(self) -> snowflakes.Snowflake:
        # <<inherited docstring from MessageEvent>>
        return self.message.channel_id

    @property
    def content(self) -> str | None:
        """Content of the message.

        The content of the message, if present. This will be [`None`][]
        if no content is present (e.g. if only an embed was sent).
        """
        return self.message.content

    @property
    def embeds(self) -> typing.Sequence[embeds_.Embed]:
        """Sequence of embeds in the message."""
        return self.message.embeds

    @property
    def is_bot(self) -> bool:
        """Return [`True`][] if the message is from a bot."""
        return self.message.author.is_bot

    @property
    def is_human(self) -> bool:
        """Return [`True`][] if the message was created by a human."""
        # Not second-guessing some weird edge case will occur in the future with this,
        # so I am being safe rather than sorry.
        return not self.message.author.is_bot and self.message.webhook_id is None

    @property
    def is_webhook(self) -> bool:
        """Return [`True`][] if the message was created by a webhook."""
        return self.message.webhook_id is not None

    @property
    @abc.abstractmethod
    def message(self) -> messages.Message:
        """Message that was sent in the event."""

    @property
    @typing_extensions.override
    def message_id(self) -> snowflakes.Snowflake:
        """ID of the message that this event concerns."""
        return self.message.id


@attrs_extensions.with_copy
@attrs.define(kw_only=True, weakref_slot=False)
@base_events.requires_intents(intents.Intents.GUILD_MESSAGES)
class GuildMessageCreateEvent(MessageCreateEvent):
    """Event that is fired when a message is created within a guild.

    This contains the full message in the internal
    [`message`][hikari.events.message_events.GuildMessageCreateEvent.message] attribute.
    """

    message: messages.Message = attrs.field()
    # <<inherited docstring from MessageCreateEvent>>

    shard: shard_.GatewayShard = attrs.field(metadata={attrs_extensions.SKIP_DEEP_COPY: True})
    # <<inherited docstring from ShardEvent>>

    @property
    @typing_extensions.override
    def author(self) -> users.User:
        """User object of the user that sent the message."""
        return self.message.author

    @property
    def member(self) -> guilds.Member | None:
        """Member object of the user that sent the message."""
        return self.message.member

    @property
    def guild_id(self) -> snowflakes.Snowflake:
        """ID of the guild that this event occurred in."""
        guild_id = self.message.guild_id
        # Always present on guild events
        assert isinstance(guild_id, snowflakes.Snowflake), "no guild_id attribute set"
        return guild_id

    def get_channel(self) -> channels.TextableGuildChannel | None:
        """Channel that the message was sent in, if known.

        Returns
        -------
        typing.Optional[hikari.channels.TextableGuildChannel]
            The channel that the message was sent in, if known and cached,
            otherwise, [`None`][].
        """
        if not isinstance(self.app, traits.CacheAware):
            return None

        channel = self.app.cache.get_guild_channel(self.channel_id)
        assert channel is None or isinstance(channel, channels.TextableGuildChannel), (
            f"Cached channel ID is not a TextableGuildChannel, but a {type(channel).__name__}!"
        )
        return channel

    def get_guild(self) -> guilds.GatewayGuild | None:
        """Get the cached guild that this event occurred in, if known.

        !!! note
            This will require the [`hikari.intents.Intents.GUILDS`][] intent to be specified on start-up
            in order to be known.

        Returns
        -------
        typing.Optional[hikari.guilds.GatewayGuild]
            The guild that this event occurred in, if cached. Otherwise,
            [`None`][] instead.
        """
        if not isinstance(self.app, traits.CacheAware):
            return None

        return self.app.cache.get_guild(self.guild_id)

    def get_member(self) -> guilds.Member | None:
        """Get the member that sent this message from the cache if available.

        Returns
        -------
        typing.Optional[hikari.guilds.Member]
            Cached object of the member that sent the message if found.
        """
        if isinstance(self.app, traits.CacheAware):
            return self.app.cache.get_member(self.guild_id, self.message.author.id)

        return None


@attrs_extensions.with_copy
@attrs.define(kw_only=True, weakref_slot=False)
@base_events.requires_intents(intents.Intents.DM_MESSAGES)
class DMMessageCreateEvent(MessageCreateEvent):
    """Event that is fired when a message is created within a DM.

    This contains the full message in the internal
    [`message`][hikari.events.message_events.GuildMessageCreateEvent.message] attribute.
    """

    message: messages.Message = attrs.field()
    # <<inherited docstring from MessageCreateEvent>>

    shard: shard_.GatewayShard = attrs.field(metadata={attrs_extensions.SKIP_DEEP_COPY: True})
    # <<inherited docstring from ShardEvent>>


@base_events.requires_intents(intents.Intents.DM_MESSAGES, intents.Intents.GUILD_MESSAGES)
class MessageUpdateEvent(MessageEvent, abc.ABC):
    """Event that is fired when a message is updated.

    !!! note
        Less information will be available here than in the creation event
        due to Discord limitations.
    """

    __slots__: typing.Sequence[str] = ()

    @property
    @typing_extensions.override
    def app(self) -> traits.RESTAware:
        # <<inherited docstring from Event>>.
        return self.message.app

    @property
    def author(self) -> undefined.UndefinedOr[users.User]:
        """User that sent the message.

        This will be [`hikari.undefined.UNDEFINED`][] in some cases such as when Discord
        updates a message with an embed URL preview.
        """
        return self.message.author

    @property
    def author_id(self) -> undefined.UndefinedOr[snowflakes.Snowflake]:
        """ID of the author that triggered this event.

        This will be [`hikari.undefined.UNDEFINED`][] in some cases such as when Discord
        updates a message with an embed URL preview.
        """
        author = self.message.author
        return author.id if author is not undefined.UNDEFINED else undefined.UNDEFINED

    @property
    @typing_extensions.override
    def channel_id(self) -> snowflakes.Snowflake:
        # <<inherited docstring from MessageEvent>>.
        return self.message.channel_id

    @property
    def content(self) -> undefined.UndefinedNoneOr[str]:
        """Content of the message.

        The content of the message, if present. This may be [`None`][]
        if no content is present (e.g. if only an embed was sent).

        If not part of the update, then this will be
        [`hikari.undefined.UNDEFINED`][] instead.
        """
        return self.message.content

    @property
    def embeds(self) -> undefined.UndefinedOr[typing.Sequence[embeds_.Embed]]:
        """Sequence of embeds in the message.

        If the embeds were not changed in this event, then this may instead be
        [`hikari.undefined.UNDEFINED`][].
        """
        return self.message.embeds

    @property
    def is_bot(self) -> undefined.UndefinedOr[bool]:
        """Whether the message is from a bot.

        If the author is not known, due to the update event being caused
        by Discord adding an embed preview to accompany a URL, then this
        will return [`hikari.undefined.UNDEFINED`][] instead.
        """
        if (author := self.message.author) is not undefined.UNDEFINED:
            return author.is_bot

        return undefined.UNDEFINED

    @property
    def is_human(self) -> undefined.UndefinedOr[bool]:
        """Whether the message was created by a human.

        If the author is not known, due to the update event being caused
        by Discord adding an embed preview to accompany a URL, then this
        may return [`hikari.undefined.UNDEFINED`][] instead.
        """
        # Not second-guessing some weird edge case will occur in the future with this,
        # so I am being safe rather than sorry.
        if (webhook_id := self.message.webhook_id) is not undefined.UNDEFINED:
            return webhook_id is None

        if (author := self.message.author) is not undefined.UNDEFINED:
            return not author.is_bot

        return undefined.UNDEFINED

    @property
    def is_webhook(self) -> undefined.UndefinedOr[bool]:
        """Whether the message was created by a webhook.

        If the author is not known, due to the update event being caused
        by Discord adding an embed preview to accompany a URL, then this
        may return [`hikari.undefined.UNDEFINED`][] instead.
        """
        if (webhook_id := self.message.webhook_id) is not undefined.UNDEFINED:
            return webhook_id is not None

        return undefined.UNDEFINED

    @property
    @abc.abstractmethod
    def message(self) -> messages.PartialMessage:
        """Partial message that was sent in the event."""

    @property
    @typing_extensions.override
    def message_id(self) -> snowflakes.Snowflake:
        """ID of the message that this event concerns."""
        return self.message.id


@attrs_extensions.with_copy
@attrs.define(kw_only=True, weakref_slot=False)
@base_events.requires_intents(intents.Intents.GUILD_MESSAGES)
class GuildMessageUpdateEvent(MessageUpdateEvent):
    """Event that is fired when a message is updated in a guild.

    !!! note
        Less information will be available here than in the creation event
        due to Discord limitations.
    """

    old_message: messages.PartialMessage | None = attrs.field()
    """The old message object.

    This will be [`None`][] if the message missing from the cache.
    """

    message: messages.PartialMessage = attrs.field()
    # <<inherited docstring from MessageUpdateEvent>>

    shard: shard_.GatewayShard = attrs.field(metadata={attrs_extensions.SKIP_DEEP_COPY: True})
    # <<inherited docstring from ShardEvent>>

    @property
    def member(self) -> undefined.UndefinedNoneOr[guilds.Member]:
        """Member that sent the message if provided by the event.

        If the message is not in a guild, this will be [`None`][].

        This will also be [`hikari.undefined.UNDEFINED`][] in some cases such as when Discord
        updates a message with an embed URL preview.
        """
        return self.message.member

    def get_member(self) -> guilds.Member | None:
        """Get the member that sent this message from the cache if available.

        Returns
        -------
        typing.Optional[hikari.guilds.Member]
            Cached object of the member that sent the message if found.
        """
        if self.message.author is not undefined.UNDEFINED and isinstance(self.app, traits.CacheAware):
            return self.app.cache.get_member(self.guild_id, self.message.author.id)

        return None

    @property
    def guild_id(self) -> snowflakes.Snowflake:
        """ID of the guild that this event occurred in."""
        guild_id = self.message.guild_id
        # Always present on guild events
        assert isinstance(guild_id, snowflakes.Snowflake), f"expected guild_id, got {guild_id}"
        return guild_id

    def get_channel(self) -> channels.TextableGuildChannel | None:
        """Channel that the message was sent in, if known.

        Returns
        -------
        typing.Optional[hikari.channels.TextableGuildChannel]
            The channel that the message was sent in, if known and cached,
            otherwise, [`None`][].
        """
        if not isinstance(self.app, traits.CacheAware):
            return None

        channel = self.app.cache.get_guild_channel(self.channel_id)
        assert channel is None or isinstance(channel, channels.TextableGuildChannel), (
            f"Cached channel ID is not a TextableGuildChannel, but a {type(channel).__name__}!"
        )
        return channel

    def get_guild(self) -> guilds.GatewayGuild | None:
        """Get the cached guild that this event occurred in, if known.

        !!! note
            This will require the [`hikari.intents.Intents.GUILDS`][] intent to be specified on start-up
            in order to be known.

        Returns
        -------
        typing.Optional[hikari.guilds.GatewayGuild]
            The guild that this event occurred in, if cached. Otherwise,
            [`None`][] instead.
        """
        if not isinstance(self.app, traits.CacheAware):
            return None

        return self.app.cache.get_guild(self.guild_id)


@attrs_extensions.with_copy
@attrs.define(kw_only=True, weakref_slot=False)
@base_events.requires_intents(intents.Intents.DM_MESSAGES)
class DMMessageUpdateEvent(MessageUpdateEvent):
    """Event that is fired when a message is updated in a DM.

    !!! note
        Less information will be available here than in the creation event
        due to Discord limitations.
    """

    old_message: messages.PartialMessage | None = attrs.field()
    """The old message object.

    This will be [`None`][] if the message missing from the cache.
    """

    message: messages.PartialMessage = attrs.field()
    # <<inherited docstring from MessageUpdateEvent>>

    shard: shard_.GatewayShard = attrs.field(metadata={attrs_extensions.SKIP_DEEP_COPY: True})
    # <<inherited docstring from ShardEvent>>


@base_events.requires_intents(intents.Intents.GUILD_MESSAGES, intents.Intents.DM_MESSAGES)
class MessageDeleteEvent(MessageEvent, abc.ABC):
    """Special event that is triggered when a message gets deleted.

    !!! note
        Due to Discord limitations, most message information is unavailable
        during deletion events.
    """

    __slots__: typing.Sequence[str] = ()

    @property
    @abc.abstractmethod
    @typing_extensions.override
    def message_id(self) -> snowflakes.Snowflake:
        """ID of the message that was deleted."""

    @property
    @abc.abstractmethod
    def old_message(self) -> messages.Message | None:
        """Object of the message that was deleted.

        Will be [`None`][] if the message was not found in the cache.
        """


@attrs_extensions.with_copy
@attrs.define(kw_only=True, weakref_slot=False)
@base_events.requires_intents(intents.Intents.GUILD_MESSAGES)
class GuildMessageDeleteEvent(MessageDeleteEvent):
    """Event that is triggered if a message is deleted in a guild.

    !!! note
        Due to Discord limitations, most message information is unavailable
        during deletion events.
    """

    app: traits.RESTAware = attrs.field(metadata={attrs_extensions.SKIP_DEEP_COPY: True})
    # <<inherited docstring from Event>>

    channel_id: snowflakes.Snowflake = attrs.field()
    # <<inherited docstring from MessageEvent>>

    guild_id: snowflakes.Snowflake = attrs.field()
    """ID of the guild that this event occurred in."""

    message_id: snowflakes.Snowflake = attrs.field()
    # <<inherited docstring from MessageDeleteEvent>>

    old_message: messages.Message | None = attrs.field()
    # <<inherited docstring from MessageDeleteEvent>>

    shard: shard_.GatewayShard = attrs.field(metadata={attrs_extensions.SKIP_DEEP_COPY: True})
    # <<inherited docstring from ShardEvent>>

    def get_channel(self) -> channels.TextableGuildChannel | None:
        """Get the cached channel the message were sent in, if known.

        Returns
        -------
        typing.Optional[hikari.channels.TextableGuildChannel]
            The channel the messages were sent in, or [`None`][] if not
            known/cached.
        """
        if not isinstance(self.app, traits.CacheAware):
            return None

        channel = self.app.cache.get_guild_channel(self.channel_id)
        assert channel is None or isinstance(channel, channels.TextableGuildChannel), (
            f"Cached channel ID is not a TextableGuildChannel, but a {type(channel).__name__}!"
        )
        return channel

    def get_guild(self) -> guilds.GatewayGuild | None:
        """Get the cached guild this event corresponds to, if known.

        !!! note
            You will need [`hikari.intents.Intents.GUILDS`][] enabled to receive this
            information.

        Returns
        -------
        hikari.guilds.GatewayGuild
            The gateway guild that this event corresponds to, if known and
            cached.
        """
        if not isinstance(self.app, traits.CacheAware):
            return None

        return self.app.cache.get_guild(self.guild_id)


@attrs_extensions.with_copy
@attrs.define(kw_only=True, weakref_slot=False)
@base_events.requires_intents(intents.Intents.DM_MESSAGES)
class DMMessageDeleteEvent(MessageDeleteEvent):
    """Event that is triggered if a message is deleted in a DM.

    !!! note
        Due to Discord limitations, most message information is unavailable
        during deletion events.
    """

    app: traits.RESTAware = attrs.field(metadata={attrs_extensions.SKIP_DEEP_COPY: True})
    # <<inherited docstring from Event>>

    channel_id: snowflakes.Snowflake = attrs.field()
    # <<inherited docstring from MessageEvent>>

    message_id: snowflakes.Snowflake = attrs.field()
    # <<inherited docstring from MessageDeleteEvent>>

    old_message: messages.Message | None = attrs.field()
    # <<inherited docstring from MessageDeleteEvent>>

    shard: shard_.GatewayShard = attrs.field(metadata={attrs_extensions.SKIP_DEEP_COPY: True})
    # <<inherited docstring from ShardEvent>>


@attrs_extensions.with_copy
@attrs.define(kw_only=True, weakref_slot=False)
@base_events.requires_intents(intents.Intents.GUILD_MESSAGES)
class GuildBulkMessageDeleteEvent(shard_events.ShardEvent):
    """Event that is triggered when a bulk deletion is triggered in a guild.

    !!! note
        Due to Discord limitations, most message information is unavailable
        during deletion events.
    """

    app: traits.RESTAware = attrs.field(metadata={attrs_extensions.SKIP_DEEP_COPY: True})
    # <<inherited docstring from Event>>

    channel_id: snowflakes.Snowflake = attrs.field()
    """ID of the channel that this event concerns."""

    guild_id: snowflakes.Snowflake = attrs.field()
    """ID of the guild that this event occurred in."""

    message_ids: typing.AbstractSet[snowflakes.Snowflake] = attrs.field()
    """Set of message IDs that were bulk deleted."""

    old_messages: typing.Mapping[snowflakes.Snowflake, messages.Message] = attrs.field()
    """Mapping of a snowflake to the deleted message object.

    If the message was not found in the cache it will be missing from the mapping.
    """

    shard: shard_.GatewayShard = attrs.field(metadata={attrs_extensions.SKIP_DEEP_COPY: True})
    # <<inherited docstring from ShardEvent>>

    def get_channel(self) -> channels.TextableGuildChannel | None:
        """Get the cached channel the messages were sent in, if known.

        Returns
        -------
        typing.Optional[hikari.channels.TextableGuildChannel]
            The channel the messages were sent in, or [`None`][] if not
            known/cached.
        """
        if not isinstance(self.app, traits.CacheAware):
            return None

        channel = self.app.cache.get_guild_channel(self.channel_id)
        assert channel is None or isinstance(channel, channels.TextableGuildChannel), (
            f"Cached channel ID is not a TextableGuildChannel, but a {type(channel).__name__}!"
        )
        return channel

    def get_guild(self) -> guilds.GatewayGuild | None:
        """Get the cached guild this event corresponds to, if known.

        !!! note
            You will need [`hikari.intents.Intents.GUILDS`][] enabled to receive this
            information.

        Returns
        -------
        hikari.guilds.GatewayGuild
            The gateway guild that this event corresponds to, if known and
            cached.
        """
        if not isinstance(self.app, traits.CacheAware):
            return None

        return self.app.cache.get_guild(self.guild_id)
