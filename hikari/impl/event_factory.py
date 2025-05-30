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
"""Implementation for a singleton bot event factory."""

from __future__ import annotations

__all__: typing.Sequence[str] = ("EventFactoryImpl",)

import types
import typing

from hikari import applications as application_models
from hikari import auto_mod as auto_mod_models
from hikari import channels as channel_models
from hikari import colors
from hikari import emojis as emojis_models
from hikari import snowflakes
from hikari import undefined
from hikari import users as user_models
from hikari.api import event_factory
from hikari.events import application_events
from hikari.events import auto_mod_events
from hikari.events import channel_events
from hikari.events import guild_events
from hikari.events import interaction_events
from hikari.events import lifetime_events
from hikari.events import member_events
from hikari.events import message_events
from hikari.events import monetization_events
from hikari.events import poll_events
from hikari.events import reaction_events
from hikari.events import role_events
from hikari.events import scheduled_events
from hikari.events import shard_events
from hikari.events import stage_events
from hikari.events import typing_events
from hikari.events import user_events
from hikari.events import voice_events
from hikari.interactions import base_interactions
from hikari.internal import collections
from hikari.internal import data_binding
from hikari.internal import time
from hikari.internal import typing_extensions

if typing.TYPE_CHECKING:
    import datetime

    from hikari import guilds as guild_models
    from hikari import invites as invite_models
    from hikari import messages as messages_models
    from hikari import presences as presences_models
    from hikari import stickers as sticker_models
    from hikari import traits
    from hikari import voices as voices_models
    from hikari.api import shard as gateway_shard

_INTERACTION_EVENTS_MAP: dict[base_interactions.InteractionType, type[interaction_events.InteractionCreateEvent]] = {
    base_interactions.InteractionType.APPLICATION_COMMAND: interaction_events.CommandInteractionCreateEvent,
    base_interactions.InteractionType.AUTOCOMPLETE: interaction_events.AutocompleteInteractionCreateEvent,
    base_interactions.InteractionType.MESSAGE_COMPONENT: interaction_events.ComponentInteractionCreateEvent,
    base_interactions.InteractionType.MODAL_SUBMIT: interaction_events.ModalInteractionCreateEvent,
}


class EventFactoryImpl(event_factory.EventFactory):
    """Implementation for a single-application bot event factory."""

    __slots__: typing.Sequence[str] = ("_app",)

    def __init__(self, app: traits.RESTAware) -> None:
        self._app = app

    ######################
    # APPLICATION EVENTS #
    ######################

    @typing_extensions.override
    def deserialize_application_command_permission_update_event(
        self, shard: gateway_shard.GatewayShard, payload: data_binding.JSONObject
    ) -> application_events.ApplicationCommandPermissionsUpdateEvent:
        permissions = self._app.entity_factory.deserialize_guild_command_permissions(payload)
        return application_events.ApplicationCommandPermissionsUpdateEvent(
            app=self._app, shard=shard, permissions=permissions
        )

    ##################
    # CHANNEL EVENTS #
    ##################

    @typing_extensions.override
    def deserialize_guild_channel_create_event(
        self, shard: gateway_shard.GatewayShard, payload: data_binding.JSONObject
    ) -> channel_events.GuildChannelCreateEvent:
        channel = self._app.entity_factory.deserialize_channel(payload)
        assert isinstance(channel, channel_models.PermissibleGuildChannel), (
            "CHANNEL_CREATE events for threads and DMS are undocumented behaviour"
        )
        return channel_events.GuildChannelCreateEvent(shard=shard, channel=channel)

    @typing_extensions.override
    def deserialize_guild_channel_update_event(
        self,
        shard: gateway_shard.GatewayShard,
        payload: data_binding.JSONObject,
        *,
        old_channel: channel_models.PermissibleGuildChannel | None = None,
    ) -> channel_events.GuildChannelUpdateEvent:
        channel = self._app.entity_factory.deserialize_channel(payload)
        assert isinstance(channel, channel_models.PermissibleGuildChannel), (
            "CHANNEL_UPDATE events for threads and DMS are undocumented behaviour"
        )
        return channel_events.GuildChannelUpdateEvent(shard=shard, channel=channel, old_channel=old_channel)

    @typing_extensions.override
    def deserialize_guild_channel_delete_event(
        self, shard: gateway_shard.GatewayShard, payload: data_binding.JSONObject
    ) -> channel_events.GuildChannelDeleteEvent:
        channel = self._app.entity_factory.deserialize_channel(payload)
        assert isinstance(channel, channel_models.PermissibleGuildChannel), (
            "CHANNEL_DELETE events for threads and DMS are undocumented behaviour"
        )
        return channel_events.GuildChannelDeleteEvent(shard=shard, channel=channel)

    @typing_extensions.override
    def deserialize_channel_pins_update_event(
        self, shard: gateway_shard.GatewayShard, payload: data_binding.JSONObject
    ) -> channel_events.PinsUpdateEvent:
        channel_id = snowflakes.Snowflake(payload["channel_id"])

        # Turns out this can be None or not present. Only set it if it is actually available.
        if (raw := payload.get("last_pin_timestamp")) is not None:
            last_pin_timestamp: datetime.datetime | None = time.iso8601_datetime_string_to_datetime(raw)
        else:
            last_pin_timestamp = None

        if "guild_id" in payload:
            return channel_events.GuildPinsUpdateEvent(
                app=self._app,
                shard=shard,
                channel_id=channel_id,
                guild_id=snowflakes.Snowflake(payload["guild_id"]),
                last_pin_timestamp=last_pin_timestamp,
            )

        return channel_events.DMPinsUpdateEvent(
            app=self._app, shard=shard, channel_id=channel_id, last_pin_timestamp=last_pin_timestamp
        )

    @typing_extensions.override
    def deserialize_guild_thread_create_event(
        self, shard: gateway_shard.GatewayShard, payload: data_binding.JSONObject
    ) -> channel_events.GuildThreadCreateEvent:
        channel = self._app.entity_factory.deserialize_guild_thread(payload)
        return channel_events.GuildThreadCreateEvent(shard=shard, thread=channel)

    @typing_extensions.override
    def deserialize_guild_thread_access_event(
        self, shard: gateway_shard.GatewayShard, payload: data_binding.JSONObject
    ) -> channel_events.GuildThreadAccessEvent:
        channel = self._app.entity_factory.deserialize_guild_thread(payload)
        return channel_events.GuildThreadAccessEvent(shard=shard, thread=channel)

    @typing_extensions.override
    def deserialize_guild_thread_update_event(
        self,
        shard: gateway_shard.GatewayShard,
        payload: data_binding.JSONObject,
        *,
        old_thread: channel_models.GuildThreadChannel | None = None,
    ) -> channel_events.GuildThreadUpdateEvent:
        channel = self._app.entity_factory.deserialize_guild_thread(payload)
        return channel_events.GuildThreadUpdateEvent(shard=shard, thread=channel, old_thread=old_thread)

    @typing_extensions.override
    def deserialize_guild_thread_delete_event(
        self, shard: gateway_shard.GatewayShard, payload: data_binding.JSONObject
    ) -> channel_events.GuildThreadDeleteEvent:
        return channel_events.GuildThreadDeleteEvent(
            app=self._app,
            shard=shard,
            thread_id=snowflakes.Snowflake(payload["id"]),
            guild_id=snowflakes.Snowflake(payload["guild_id"]),
            parent_id=snowflakes.Snowflake(payload["parent_id"]),
            type=channel_models.ChannelType(payload["type"]),
        )

    @typing_extensions.override
    def deserialize_thread_members_update_event(
        self, shard: gateway_shard.GatewayShard, payload: data_binding.JSONObject
    ) -> channel_events.ThreadMembersUpdateEvent:
        guild_id = snowflakes.Snowflake(payload["guild_id"])

        added_members: dict[snowflakes.Snowflake, channel_models.ThreadMember] = {}
        guild_members: dict[snowflakes.Snowflake, guild_models.Member] = {}
        guild_presences: dict[snowflakes.Snowflake, presences_models.MemberPresence] = {}
        if raw_added_members := payload.get("added_members"):
            for member_payload in raw_added_members:
                member = self._app.entity_factory.deserialize_thread_member(member_payload)
                added_members[member.user_id] = member
                if guild_member_payload := member_payload.get("member"):
                    guild_members[member.user_id] = self._app.entity_factory.deserialize_member(
                        guild_member_payload, guild_id=guild_id
                    )

                if presence_payload := member_payload.get("presence"):
                    guild_presences[member.user_id] = self._app.entity_factory.deserialize_member_presence(
                        presence_payload, guild_id=guild_id
                    )

        if raw_removed_members := payload.get("removed_member_ids"):
            removed_member_ids = [snowflakes.Snowflake(m) for m in raw_removed_members]

        else:
            removed_member_ids = []

        return channel_events.ThreadMembersUpdateEvent(
            app=self._app,
            shard=shard,
            thread_id=snowflakes.Snowflake(payload["id"]),
            guild_id=guild_id,
            added_members=added_members,
            removed_member_ids=removed_member_ids,
            approximate_member_count=payload["member_count"],
            guild_members=guild_members,
            guild_presences=guild_presences,
        )

    @typing_extensions.override
    def deserialize_thread_list_sync_event(
        self, shard: gateway_shard.GatewayShard, payload: data_binding.JSONObject
    ) -> channel_events.ThreadListSyncEvent:
        guild_id = snowflakes.Snowflake(payload["guild_id"])
        channel_ids: list[snowflakes.Snowflake] | None = None
        if raw_channel_ids := payload.get("channel_ids"):
            channel_ids = [snowflakes.Snowflake(x) for x in raw_channel_ids]

        members = {m.thread_id: m for m in map(self._app.entity_factory.deserialize_thread_member, payload["members"])}
        threads: dict[snowflakes.Snowflake, channel_models.GuildThreadChannel] = {}
        for thread_payload in payload["threads"]:
            thread_id = snowflakes.Snowflake(thread_payload["id"])
            thread = self._app.entity_factory.deserialize_guild_thread(
                thread_payload, guild_id=guild_id, member=members.get(thread_id)
            )
            threads[thread.id] = thread

        return channel_events.ThreadListSyncEvent(
            app=self._app, shard=shard, guild_id=guild_id, channel_ids=channel_ids, threads=threads
        )

    @typing_extensions.override
    def deserialize_webhook_update_event(
        self, shard: gateway_shard.GatewayShard, payload: data_binding.JSONObject
    ) -> channel_events.WebhookUpdateEvent:
        guild_id = snowflakes.Snowflake(payload["guild_id"])
        channel_id = snowflakes.Snowflake(payload["channel_id"])
        return channel_events.WebhookUpdateEvent(app=self._app, shard=shard, channel_id=channel_id, guild_id=guild_id)

    @typing_extensions.override
    def deserialize_invite_create_event(
        self, shard: gateway_shard.GatewayShard, payload: data_binding.JSONObject
    ) -> channel_events.InviteCreateEvent:
        invite = self._app.entity_factory.deserialize_invite_with_metadata(payload)
        return channel_events.InviteCreateEvent(shard=shard, invite=invite)

    @typing_extensions.override
    def deserialize_invite_delete_event(
        self,
        shard: gateway_shard.GatewayShard,
        payload: data_binding.JSONObject,
        *,
        old_invite: invite_models.InviteWithMetadata | None = None,
    ) -> channel_events.InviteDeleteEvent:
        return channel_events.InviteDeleteEvent(
            app=self._app,
            shard=shard,
            code=payload["code"],
            channel_id=snowflakes.Snowflake(payload["channel_id"]),
            guild_id=snowflakes.Snowflake(payload["guild_id"]),
            old_invite=old_invite,
        )

    #################
    # TYPING EVENTS #
    ##################

    @typing_extensions.override
    def deserialize_typing_start_event(
        self, shard: gateway_shard.GatewayShard, payload: data_binding.JSONObject
    ) -> typing_events.TypingEvent:
        channel_id = snowflakes.Snowflake(payload["channel_id"])
        # Turns out that this endpoint uses seconds rather than milliseconds.
        timestamp = time.unix_epoch_to_datetime(payload["timestamp"], is_millis=False)

        if "guild_id" in payload:
            guild_id = snowflakes.Snowflake(payload["guild_id"])
            member = self._app.entity_factory.deserialize_member(payload["member"], guild_id=guild_id)
            return typing_events.GuildTypingEvent(
                shard=shard, channel_id=channel_id, guild_id=guild_id, timestamp=timestamp, member=member
            )

        user_id = snowflakes.Snowflake(payload["user_id"])
        return typing_events.DMTypingEvent(
            app=self._app, shard=shard, channel_id=channel_id, user_id=user_id, timestamp=timestamp
        )

    ################
    # GUILD EVENTS #
    ################

    @typing_extensions.override
    def deserialize_guild_available_event(
        self, shard: gateway_shard.GatewayShard, payload: data_binding.JSONObject
    ) -> guild_events.GuildAvailableEvent:
        guild_information = self._app.entity_factory.deserialize_gateway_guild(payload, user_id=shard.get_user_id())
        return guild_events.GuildAvailableEvent(
            shard=shard,
            guild=guild_information.guild(),
            emojis=guild_information.emojis(),
            roles=guild_information.roles(),
            channels=guild_information.channels(),
            members=guild_information.members(),
            presences=guild_information.presences(),
            stickers=guild_information.stickers(),
            threads=guild_information.threads(),
            voice_states=guild_information.voice_states(),
        )

    @typing_extensions.override
    def deserialize_guild_join_event(
        self, shard: gateway_shard.GatewayShard, payload: data_binding.JSONObject
    ) -> guild_events.GuildJoinEvent:
        guild_information = self._app.entity_factory.deserialize_gateway_guild(payload, user_id=shard.get_user_id())
        return guild_events.GuildJoinEvent(
            shard=shard,
            guild=guild_information.guild(),
            emojis=guild_information.emojis(),
            roles=guild_information.roles(),
            channels=guild_information.channels(),
            members=guild_information.members(),
            presences=guild_information.presences(),
            stickers=guild_information.stickers(),
            threads=guild_information.threads(),
            voice_states=guild_information.voice_states(),
        )

    @typing_extensions.override
    def deserialize_guild_update_event(
        self,
        shard: gateway_shard.GatewayShard,
        payload: data_binding.JSONObject,
        *,
        old_guild: guild_models.GatewayGuild | None = None,
    ) -> guild_events.GuildUpdateEvent:
        guild_information = self._app.entity_factory.deserialize_gateway_guild(payload, user_id=shard.get_user_id())
        return guild_events.GuildUpdateEvent(
            shard=shard,
            guild=guild_information.guild(),
            emojis=guild_information.emojis(),
            roles=guild_information.roles(),
            stickers=guild_information.stickers(),
            old_guild=old_guild,
        )

    @typing_extensions.override
    def deserialize_guild_leave_event(
        self,
        shard: gateway_shard.GatewayShard,
        payload: data_binding.JSONObject,
        *,
        old_guild: guild_models.GatewayGuild | None = None,
    ) -> guild_events.GuildLeaveEvent:
        return guild_events.GuildLeaveEvent(
            app=self._app, shard=shard, guild_id=snowflakes.Snowflake(payload["id"]), old_guild=old_guild
        )

    @typing_extensions.override
    def deserialize_guild_unavailable_event(
        self, shard: gateway_shard.GatewayShard, payload: data_binding.JSONObject
    ) -> guild_events.GuildUnavailableEvent:
        return guild_events.GuildUnavailableEvent(
            app=self._app, shard=shard, guild_id=snowflakes.Snowflake(payload["id"])
        )

    @typing_extensions.override
    def deserialize_guild_ban_add_event(
        self, shard: gateway_shard.GatewayShard, payload: data_binding.JSONObject
    ) -> guild_events.BanCreateEvent:
        return guild_events.BanCreateEvent(
            shard=shard,
            guild_id=snowflakes.Snowflake(payload["guild_id"]),
            user=self._app.entity_factory.deserialize_user(payload["user"]),
        )

    @typing_extensions.override
    def deserialize_guild_ban_remove_event(
        self, shard: gateway_shard.GatewayShard, payload: data_binding.JSONObject
    ) -> guild_events.BanDeleteEvent:
        return guild_events.BanDeleteEvent(
            shard=shard,
            guild_id=snowflakes.Snowflake(payload["guild_id"]),
            user=self._app.entity_factory.deserialize_user(payload["user"]),
        )

    @typing_extensions.override
    def deserialize_guild_emojis_update_event(
        self,
        shard: gateway_shard.GatewayShard,
        payload: data_binding.JSONObject,
        *,
        old_emojis: typing.Sequence[emojis_models.KnownCustomEmoji] | None = None,
    ) -> guild_events.EmojisUpdateEvent:
        guild_id = snowflakes.Snowflake(payload["guild_id"])
        emojis = [
            self._app.entity_factory.deserialize_known_custom_emoji(emoji, guild_id=guild_id)
            for emoji in payload["emojis"]
        ]
        return guild_events.EmojisUpdateEvent(
            app=self._app, shard=shard, guild_id=guild_id, emojis=emojis, old_emojis=old_emojis
        )

    @typing_extensions.override
    def deserialize_guild_stickers_update_event(
        self,
        shard: gateway_shard.GatewayShard,
        payload: data_binding.JSONObject,
        *,
        old_stickers: typing.Sequence[sticker_models.GuildSticker] | None = None,
    ) -> guild_events.StickersUpdateEvent:
        guild_id = snowflakes.Snowflake(payload["guild_id"])
        stickers = [self._app.entity_factory.deserialize_guild_sticker(sticker) for sticker in payload["stickers"]]
        return guild_events.StickersUpdateEvent(
            app=self._app, shard=shard, guild_id=guild_id, stickers=stickers, old_stickers=old_stickers
        )

    @typing_extensions.override
    def deserialize_integration_create_event(
        self, shard: gateway_shard.GatewayShard, payload: data_binding.JSONObject
    ) -> guild_events.IntegrationCreateEvent:
        return guild_events.IntegrationCreateEvent(
            app=self._app, shard=shard, integration=self._app.entity_factory.deserialize_integration(payload)
        )

    @typing_extensions.override
    def deserialize_integration_delete_event(
        self, shard: gateway_shard.GatewayShard, payload: data_binding.JSONObject
    ) -> guild_events.IntegrationDeleteEvent:
        application_id: snowflakes.Snowflake | None = None
        if (raw_application_id := payload.get("application_id")) is not None:
            application_id = snowflakes.Snowflake(raw_application_id)

        return guild_events.IntegrationDeleteEvent(
            id=snowflakes.Snowflake(payload["id"]),
            app=self._app,
            shard=shard,
            guild_id=snowflakes.Snowflake(payload["guild_id"]),
            application_id=application_id,
        )

    @typing_extensions.override
    def deserialize_integration_update_event(
        self, shard: gateway_shard.GatewayShard, payload: data_binding.JSONObject
    ) -> guild_events.IntegrationUpdateEvent:
        return guild_events.IntegrationUpdateEvent(
            app=self._app, shard=shard, integration=self._app.entity_factory.deserialize_integration(payload)
        )

    @typing_extensions.override
    def deserialize_presence_update_event(
        self,
        shard: gateway_shard.GatewayShard,
        payload: data_binding.JSONObject,
        *,
        old_presence: presences_models.MemberPresence | None = None,
    ) -> guild_events.PresenceUpdateEvent:
        presence = self._app.entity_factory.deserialize_member_presence(payload)

        user_payload = payload["user"]
        user: user_models.PartialUser | None = None
        # Here we're told that the only guaranteed field is "id", so if we only get 1 field in the user payload then
        # then we've only got an ID and there's no reason to form a user object.
        if len(user_payload) > 1:
            # PartialUser
            discriminator = user_payload.get("discriminator", undefined.UNDEFINED)
            flags: undefined.UndefinedOr[user_models.UserFlag] = undefined.UNDEFINED
            if "public_flags" in user_payload:
                flags = user_models.UserFlag(user_payload["public_flags"])

            accent_color: undefined.UndefinedNoneOr[colors.Color] = undefined.UNDEFINED
            if "accent_color" in user_payload:
                raw_accent_color = user_payload["accent_color"]
                accent_color = colors.Color(raw_accent_color) if raw_accent_color is not None else raw_accent_color

            user = user_models.PartialUserImpl(
                app=self._app,
                id=snowflakes.Snowflake(user_payload["id"]),
                discriminator=discriminator,
                username=user_payload.get("username", undefined.UNDEFINED),
                global_name=user_payload.get("global_name", undefined.UNDEFINED),
                avatar_decoration=None,
                avatar_hash=user_payload.get("avatar", undefined.UNDEFINED),
                banner_hash=user_payload.get("banner", undefined.UNDEFINED),
                accent_color=accent_color,
                is_bot=user_payload.get("bot", undefined.UNDEFINED),
                is_system=user_payload.get("system", undefined.UNDEFINED),
                flags=flags,
            )
        return guild_events.PresenceUpdateEvent(shard=shard, presence=presence, user=user, old_presence=old_presence)

    @typing_extensions.override
    def deserialize_audit_log_entry_create_event(
        self, shard: gateway_shard.GatewayShard, payload: data_binding.JSONObject
    ) -> guild_events.AuditLogEntryCreateEvent:
        return guild_events.AuditLogEntryCreateEvent(
            shard=shard, entry=self._app.entity_factory.deserialize_audit_log_entry(payload)
        )

    ######################
    # INTERACTION EVENTS #
    ######################

    @typing_extensions.override
    def deserialize_interaction_create_event(
        self, shard: gateway_shard.GatewayShard, payload: data_binding.JSONObject
    ) -> interaction_events.InteractionCreateEvent:
        interaction = self._app.entity_factory.deserialize_interaction(payload)

        return _INTERACTION_EVENTS_MAP[interaction.type](shard=shard, interaction=interaction)

    #################
    # MEMBER EVENTS #
    #################

    @typing_extensions.override
    def deserialize_guild_member_add_event(
        self, shard: gateway_shard.GatewayShard, payload: data_binding.JSONObject
    ) -> member_events.MemberCreateEvent:
        member = self._app.entity_factory.deserialize_member(payload)
        return member_events.MemberCreateEvent(shard=shard, member=member)

    @typing_extensions.override
    def deserialize_guild_member_update_event(
        self,
        shard: gateway_shard.GatewayShard,
        payload: data_binding.JSONObject,
        *,
        old_member: guild_models.Member | None = None,
    ) -> member_events.MemberUpdateEvent:
        member = self._app.entity_factory.deserialize_member(payload)
        return member_events.MemberUpdateEvent(shard=shard, member=member, old_member=old_member)

    @typing_extensions.override
    def deserialize_guild_member_remove_event(
        self,
        shard: gateway_shard.GatewayShard,
        payload: data_binding.JSONObject,
        *,
        old_member: guild_models.Member | None = None,
    ) -> member_events.MemberDeleteEvent:
        guild_id = snowflakes.Snowflake(payload["guild_id"])
        user = self._app.entity_factory.deserialize_user(payload["user"])
        return member_events.MemberDeleteEvent(shard=shard, guild_id=guild_id, user=user, old_member=old_member)

    ###############
    # ROLE EVENTS #
    ###############

    @typing_extensions.override
    def deserialize_guild_role_create_event(
        self, shard: gateway_shard.GatewayShard, payload: data_binding.JSONObject
    ) -> role_events.RoleCreateEvent:
        role = self._app.entity_factory.deserialize_role(
            payload["role"], guild_id=snowflakes.Snowflake(payload["guild_id"])
        )
        return role_events.RoleCreateEvent(shard=shard, role=role)

    @typing_extensions.override
    def deserialize_guild_role_update_event(
        self,
        shard: gateway_shard.GatewayShard,
        payload: data_binding.JSONObject,
        *,
        old_role: guild_models.Role | None = None,
    ) -> role_events.RoleUpdateEvent:
        role = self._app.entity_factory.deserialize_role(
            payload["role"], guild_id=snowflakes.Snowflake(payload["guild_id"])
        )
        return role_events.RoleUpdateEvent(shard=shard, role=role, old_role=old_role)

    @typing_extensions.override
    def deserialize_guild_role_delete_event(
        self,
        shard: gateway_shard.GatewayShard,
        payload: data_binding.JSONObject,
        *,
        old_role: guild_models.Role | None = None,
    ) -> role_events.RoleDeleteEvent:
        return role_events.RoleDeleteEvent(
            app=self._app,
            shard=shard,
            guild_id=snowflakes.Snowflake(payload["guild_id"]),
            role_id=snowflakes.Snowflake(payload["role_id"]),
            old_role=old_role,
        )

    ##########################
    # SCHEDULED EVENT EVENTS #
    ##########################

    @typing_extensions.override
    def deserialize_scheduled_event_create_event(
        self, shard: gateway_shard.GatewayShard, payload: data_binding.JSONObject
    ) -> scheduled_events.ScheduledEventCreateEvent:
        return scheduled_events.ScheduledEventCreateEvent(
            shard=shard, event=self._app.entity_factory.deserialize_scheduled_event(payload)
        )

    @typing_extensions.override
    def deserialize_scheduled_event_update_event(
        self, shard: gateway_shard.GatewayShard, payload: data_binding.JSONObject
    ) -> scheduled_events.ScheduledEventUpdateEvent:
        return scheduled_events.ScheduledEventUpdateEvent(
            shard=shard, event=self._app.entity_factory.deserialize_scheduled_event(payload)
        )

    @typing_extensions.override
    def deserialize_scheduled_event_delete_event(
        self, shard: gateway_shard.GatewayShard, payload: data_binding.JSONObject
    ) -> scheduled_events.ScheduledEventDeleteEvent:
        return scheduled_events.ScheduledEventDeleteEvent(
            shard=shard, event=self._app.entity_factory.deserialize_scheduled_event(payload)
        )

    @typing_extensions.override
    def deserialize_scheduled_event_user_add_event(
        self, shard: gateway_shard.GatewayShard, payload: data_binding.JSONObject
    ) -> scheduled_events.ScheduledEventUserAddEvent:
        return scheduled_events.ScheduledEventUserAddEvent(
            app=self._app,
            shard=shard,
            event_id=snowflakes.Snowflake(payload["guild_scheduled_event_id"]),
            user_id=snowflakes.Snowflake(payload["user_id"]),
            guild_id=snowflakes.Snowflake(payload["guild_id"]),
        )

    @typing_extensions.override
    def deserialize_scheduled_event_user_remove_event(
        self, shard: gateway_shard.GatewayShard, payload: data_binding.JSONObject
    ) -> scheduled_events.ScheduledEventUserRemoveEvent:
        return scheduled_events.ScheduledEventUserRemoveEvent(
            app=self._app,
            shard=shard,
            event_id=snowflakes.Snowflake(payload["guild_scheduled_event_id"]),
            user_id=snowflakes.Snowflake(payload["user_id"]),
            guild_id=snowflakes.Snowflake(payload["guild_id"]),
        )

    ###################
    # LIFETIME EVENTS #
    ###################

    @typing_extensions.override
    def deserialize_starting_event(self) -> lifetime_events.StartingEvent:
        return lifetime_events.StartingEvent(app=self._app)

    @typing_extensions.override
    def deserialize_started_event(self) -> lifetime_events.StartedEvent:
        return lifetime_events.StartedEvent(app=self._app)

    @typing_extensions.override
    def deserialize_stopping_event(self) -> lifetime_events.StoppingEvent:
        return lifetime_events.StoppingEvent(app=self._app)

    @typing_extensions.override
    def deserialize_stopped_event(self) -> lifetime_events.StoppedEvent:
        return lifetime_events.StoppedEvent(app=self._app)

    ##################
    # MESSAGE EVENTS #
    ##################

    @typing_extensions.override
    def deserialize_message_create_event(
        self, shard: gateway_shard.GatewayShard, payload: data_binding.JSONObject
    ) -> message_events.MessageCreateEvent:
        message = self._app.entity_factory.deserialize_message(payload)

        if message.guild_id is None:
            return message_events.DMMessageCreateEvent(shard=shard, message=message)

        return message_events.GuildMessageCreateEvent(shard=shard, message=message)

    @typing_extensions.override
    def deserialize_message_update_event(
        self,
        shard: gateway_shard.GatewayShard,
        payload: data_binding.JSONObject,
        *,
        old_message: messages_models.PartialMessage | None = None,
    ) -> message_events.MessageUpdateEvent:
        message = self._app.entity_factory.deserialize_partial_message(payload)

        if message.guild_id is None:
            return message_events.DMMessageUpdateEvent(shard=shard, message=message, old_message=old_message)

        return message_events.GuildMessageUpdateEvent(shard=shard, message=message, old_message=old_message)

    @typing_extensions.override
    def deserialize_message_delete_event(
        self,
        shard: gateway_shard.GatewayShard,
        payload: data_binding.JSONObject,
        *,
        old_message: messages_models.Message | None = None,
    ) -> message_events.MessageDeleteEvent:
        channel_id = snowflakes.Snowflake(payload["channel_id"])
        message_id = snowflakes.Snowflake(payload["id"])

        if "guild_id" in payload:
            return message_events.GuildMessageDeleteEvent(
                app=self._app,
                shard=shard,
                channel_id=channel_id,
                message_id=message_id,
                guild_id=snowflakes.Snowflake(payload["guild_id"]),
                old_message=old_message,
            )

        return message_events.DMMessageDeleteEvent(
            app=self._app, shard=shard, channel_id=channel_id, message_id=message_id, old_message=old_message
        )

    @typing_extensions.override
    def deserialize_guild_message_delete_bulk_event(
        self,
        shard: gateway_shard.GatewayShard,
        payload: data_binding.JSONObject,
        *,
        old_messages: typing.Mapping[snowflakes.Snowflake, messages_models.Message] | None = None,
    ) -> message_events.GuildBulkMessageDeleteEvent:
        return message_events.GuildBulkMessageDeleteEvent(
            app=self._app,
            shard=shard,
            channel_id=snowflakes.Snowflake(payload["channel_id"]),
            guild_id=snowflakes.Snowflake(payload["guild_id"]),
            message_ids=collections.SnowflakeSet(*(snowflakes.Snowflake(message_id) for message_id in payload["ids"])),
            old_messages=old_messages or {},
        )

    ###################
    # REACTION EVENTS #
    ###################

    @typing_extensions.override
    def deserialize_message_reaction_add_event(
        self, shard: gateway_shard.GatewayShard, payload: data_binding.JSONObject
    ) -> reaction_events.ReactionAddEvent:
        channel_id = snowflakes.Snowflake(payload["channel_id"])
        message_id = snowflakes.Snowflake(payload["message_id"])

        emoji_payload = payload["emoji"]
        raw_emoji_id = emoji_payload.get("id")
        emoji_id = snowflakes.Snowflake(raw_emoji_id) if raw_emoji_id else None
        is_animated = bool(emoji_payload.get("animated", False))
        emoji_name = emojis_models.UnicodeEmoji(emoji_payload["name"]) if not emoji_id else emoji_payload["name"]

        if "member" in payload:
            guild_id = snowflakes.Snowflake(payload["guild_id"])
            member = self._app.entity_factory.deserialize_member(payload["member"], guild_id=guild_id)
            return reaction_events.GuildReactionAddEvent(
                shard=shard,
                member=member,
                channel_id=channel_id,
                message_id=message_id,
                emoji_id=emoji_id,
                emoji_name=emoji_name,
                is_animated=is_animated,
            )

        user_id = snowflakes.Snowflake(payload["user_id"])
        return reaction_events.DMReactionAddEvent(
            app=self._app,
            shard=shard,
            channel_id=channel_id,
            message_id=message_id,
            user_id=user_id,
            emoji_id=emoji_id,
            emoji_name=emoji_name,
            is_animated=is_animated,
        )

    def _split_reaction_emoji(
        self, emoji_payload: data_binding.JSONObject, /
    ) -> tuple[snowflakes.Snowflake | None, str | emojis_models.UnicodeEmoji | None]:
        if (emoji_id := emoji_payload.get("id")) is not None:
            return snowflakes.Snowflake(emoji_id), emoji_payload["name"]

        return None, emojis_models.UnicodeEmoji(emoji_payload["name"])

    @typing_extensions.override
    def deserialize_message_reaction_remove_event(
        self, shard: gateway_shard.GatewayShard, payload: data_binding.JSONObject
    ) -> reaction_events.ReactionDeleteEvent:
        channel_id = snowflakes.Snowflake(payload["channel_id"])
        message_id = snowflakes.Snowflake(payload["message_id"])
        user_id = snowflakes.Snowflake(payload["user_id"])
        emoji_id, emoji_name = self._split_reaction_emoji(payload["emoji"])

        if "guild_id" in payload:
            return reaction_events.GuildReactionDeleteEvent(
                app=self._app,
                shard=shard,
                user_id=user_id,
                guild_id=snowflakes.Snowflake(payload["guild_id"]),
                channel_id=channel_id,
                message_id=message_id,
                emoji_id=emoji_id,
                emoji_name=emoji_name,
            )

        return reaction_events.DMReactionDeleteEvent(
            app=self._app,
            shard=shard,
            user_id=user_id,
            channel_id=channel_id,
            message_id=message_id,
            emoji_id=emoji_id,
            emoji_name=emoji_name,
        )

    @typing_extensions.override
    def deserialize_message_reaction_remove_all_event(
        self, shard: gateway_shard.GatewayShard, payload: data_binding.JSONObject
    ) -> reaction_events.ReactionDeleteAllEvent:
        channel_id = snowflakes.Snowflake(payload["channel_id"])
        message_id = snowflakes.Snowflake(payload["message_id"])

        if "guild_id" in payload:
            return reaction_events.GuildReactionDeleteAllEvent(
                app=self._app,
                shard=shard,
                guild_id=snowflakes.Snowflake(payload["guild_id"]),
                channel_id=channel_id,
                message_id=message_id,
            )

        return reaction_events.DMReactionDeleteAllEvent(
            app=self._app, shard=shard, channel_id=channel_id, message_id=message_id
        )

    @typing_extensions.override
    def deserialize_message_reaction_remove_emoji_event(
        self, shard: gateway_shard.GatewayShard, payload: data_binding.JSONObject
    ) -> reaction_events.ReactionDeleteEmojiEvent:
        channel_id = snowflakes.Snowflake(payload["channel_id"])
        message_id = snowflakes.Snowflake(payload["message_id"])
        emoji_id, emoji_name = self._split_reaction_emoji(payload["emoji"])

        if "guild_id" in payload:
            return reaction_events.GuildReactionDeleteEmojiEvent(
                app=self._app,
                shard=shard,
                emoji_id=emoji_id,
                emoji_name=emoji_name,
                guild_id=snowflakes.Snowflake(payload["guild_id"]),
                channel_id=channel_id,
                message_id=message_id,
            )

        return reaction_events.DMReactionDeleteEmojiEvent(
            app=self._app,
            shard=shard,
            emoji_id=emoji_id,
            emoji_name=emoji_name,
            channel_id=channel_id,
            message_id=message_id,
        )

    ################
    # SHARD EVENTS #
    ################

    @typing_extensions.override
    def deserialize_shard_payload_event(
        self, shard: gateway_shard.GatewayShard, payload: data_binding.JSONObject, *, name: str
    ) -> shard_events.ShardPayloadEvent:
        payload = types.MappingProxyType(payload)
        return shard_events.ShardPayloadEvent(app=self._app, shard=shard, payload=payload, name=name)

    @typing_extensions.override
    def deserialize_ready_event(
        self, shard: gateway_shard.GatewayShard, payload: data_binding.JSONObject
    ) -> shard_events.ShardReadyEvent:
        return shard_events.ShardReadyEvent(
            shard=shard,
            actual_gateway_version=int(payload["v"]),
            resume_gateway_url=payload["resume_gateway_url"],
            session_id=payload["session_id"],
            my_user=self._app.entity_factory.deserialize_my_user(payload["user"]),
            unavailable_guilds=[snowflakes.Snowflake(guild["id"]) for guild in payload["guilds"]],
            application_id=snowflakes.Snowflake(payload["application"]["id"]),
            application_flags=application_models.ApplicationFlags(int(payload["application"]["flags"])),
        )

    @typing_extensions.override
    def deserialize_connected_event(self, shard: gateway_shard.GatewayShard) -> shard_events.ShardConnectedEvent:
        return shard_events.ShardConnectedEvent(app=self._app, shard=shard)

    @typing_extensions.override
    def deserialize_disconnected_event(self, shard: gateway_shard.GatewayShard) -> shard_events.ShardDisconnectedEvent:
        return shard_events.ShardDisconnectedEvent(app=self._app, shard=shard)

    @typing_extensions.override
    def deserialize_resumed_event(self, shard: gateway_shard.GatewayShard) -> shard_events.ShardResumedEvent:
        return shard_events.ShardResumedEvent(app=self._app, shard=shard)

    @typing_extensions.override
    def deserialize_guild_member_chunk_event(
        self, shard: gateway_shard.GatewayShard, payload: data_binding.JSONObject
    ) -> shard_events.MemberChunkEvent:
        guild_id = snowflakes.Snowflake(payload["guild_id"])
        index = int(payload["chunk_index"])
        count = int(payload["chunk_count"])
        members = {
            snowflakes.Snowflake(m["user"]["id"]): self._app.entity_factory.deserialize_member(m, guild_id=guild_id)
            for m in payload["members"]
        }
        # Note, these IDs may be returned as ints or strings based on whether they're over a certain value.
        not_found = [snowflakes.Snowflake(sn) for sn in payload["not_found"]] if "not_found" in payload else []

        if presence_payloads := payload.get("presences"):
            presences = {
                snowflakes.Snowflake(p["user"]["id"]): self._app.entity_factory.deserialize_member_presence(
                    p, guild_id=guild_id
                )
                for p in presence_payloads
            }
        else:
            presences = {}

        return shard_events.MemberChunkEvent(
            app=self._app,
            shard=shard,
            guild_id=guild_id,
            members=members,
            chunk_index=index,
            chunk_count=count,
            not_found=not_found,
            presences=presences,
            nonce=payload.get("nonce"),
        )

    ###############
    # USER EVENTS #
    ###############

    @typing_extensions.override
    def deserialize_own_user_update_event(
        self,
        shard: gateway_shard.GatewayShard,
        payload: data_binding.JSONObject,
        *,
        old_user: user_models.OwnUser | None = None,
    ) -> user_events.OwnUserUpdateEvent:
        return user_events.OwnUserUpdateEvent(
            shard=shard, user=self._app.entity_factory.deserialize_my_user(payload), old_user=old_user
        )

    ################
    # VOICE EVENTS #
    ################

    @typing_extensions.override
    def deserialize_voice_state_update_event(
        self,
        shard: gateway_shard.GatewayShard,
        payload: data_binding.JSONObject,
        *,
        old_state: voices_models.VoiceState | None = None,
    ) -> voice_events.VoiceStateUpdateEvent:
        state = self._app.entity_factory.deserialize_voice_state(payload)
        return voice_events.VoiceStateUpdateEvent(shard=shard, state=state, old_state=old_state)

    @typing_extensions.override
    def deserialize_voice_server_update_event(
        self, shard: gateway_shard.GatewayShard, payload: data_binding.JSONObject
    ) -> voice_events.VoiceServerUpdateEvent:
        token = payload["token"]
        guild_id = snowflakes.Snowflake(payload["guild_id"])
        raw_endpoint = payload["endpoint"]
        return voice_events.VoiceServerUpdateEvent(
            app=self._app, shard=shard, guild_id=guild_id, token=token, raw_endpoint=raw_endpoint
        )

    ################
    # MONETIZATION #
    ################

    @typing_extensions.override
    def deserialize_entitlement_create_event(
        self, shard: gateway_shard.GatewayShard, payload: data_binding.JSONObject
    ) -> monetization_events.EntitlementCreateEvent:
        return monetization_events.EntitlementCreateEvent(
            app=self._app, shard=shard, entitlement=self._app.entity_factory.deserialize_entitlement(payload)
        )

    @typing_extensions.override
    def deserialize_entitlement_update_event(
        self, shard: gateway_shard.GatewayShard, payload: data_binding.JSONObject
    ) -> monetization_events.EntitlementUpdateEvent:
        return monetization_events.EntitlementUpdateEvent(
            app=self._app, shard=shard, entitlement=self._app.entity_factory.deserialize_entitlement(payload)
        )

    @typing_extensions.override
    def deserialize_entitlement_delete_event(
        self, shard: gateway_shard.GatewayShard, payload: data_binding.JSONObject
    ) -> monetization_events.EntitlementDeleteEvent:
        return monetization_events.EntitlementDeleteEvent(
            app=self._app, shard=shard, entitlement=self._app.entity_factory.deserialize_entitlement(payload)
        )

    #########################
    # STAGE INSTANCE EVENTS #
    #########################

    @typing_extensions.override
    def deserialize_stage_instance_create_event(
        self, shard: gateway_shard.GatewayShard, payload: data_binding.JSONObject
    ) -> stage_events.StageInstanceCreateEvent:
        return stage_events.StageInstanceCreateEvent(
            shard=shard, stage_instance=self._app.entity_factory.deserialize_stage_instance(payload)
        )

    @typing_extensions.override
    def deserialize_stage_instance_update_event(
        self, shard: gateway_shard.GatewayShard, payload: data_binding.JSONObject
    ) -> stage_events.StageInstanceUpdateEvent:
        return stage_events.StageInstanceUpdateEvent(
            shard=shard, stage_instance=self._app.entity_factory.deserialize_stage_instance(payload)
        )

    @typing_extensions.override
    def deserialize_stage_instance_delete_event(
        self, shard: gateway_shard.GatewayShard, payload: data_binding.JSONObject
    ) -> stage_events.StageInstanceDeleteEvent:
        return stage_events.StageInstanceDeleteEvent(
            shard=shard, stage_instance=self._app.entity_factory.deserialize_stage_instance(payload)
        )

    ################
    #  POLL EVENTS #
    ################

    @typing_extensions.override
    def deserialize_poll_vote_create_event(
        self, shard: gateway_shard.GatewayShard, payload: data_binding.JSONObject
    ) -> poll_events.PollVoteCreateEvent:
        return poll_events.PollVoteCreateEvent(
            app=self._app,
            shard=shard,
            user_id=snowflakes.Snowflake(payload["user_id"]),
            channel_id=snowflakes.Snowflake(payload["channel_id"]),
            message_id=snowflakes.Snowflake(payload["message_id"]),
            guild_id=snowflakes.Snowflake(payload["guild_id"]) if "guild_id" in payload else None,
            answer_id=payload["answer_id"],
        )

    @typing_extensions.override
    def deserialize_poll_vote_delete_event(
        self, shard: gateway_shard.GatewayShard, payload: data_binding.JSONObject
    ) -> poll_events.PollVoteDeleteEvent:
        return poll_events.PollVoteDeleteEvent(
            app=self._app,
            shard=shard,
            user_id=snowflakes.Snowflake(payload["user_id"]),
            channel_id=snowflakes.Snowflake(payload["channel_id"]),
            message_id=snowflakes.Snowflake(payload["message_id"]),
            guild_id=snowflakes.Snowflake(payload["guild_id"]) if "guild_id" in payload else None,
            answer_id=payload["answer_id"],
        )

    @typing_extensions.override
    def deserialize_auto_mod_rule_create_event(
        self, shard: gateway_shard.GatewayShard, payload: data_binding.JSONObject
    ) -> auto_mod_events.AutoModRuleCreateEvent:
        return auto_mod_events.AutoModRuleCreateEvent(
            shard=shard, rule=self._app.entity_factory.deserialize_auto_mod_rule(payload)
        )

    @typing_extensions.override
    def deserialize_auto_mod_rule_update_event(
        self, shard: gateway_shard.GatewayShard, payload: data_binding.JSONObject
    ) -> auto_mod_events.AutoModRuleUpdateEvent:
        return auto_mod_events.AutoModRuleUpdateEvent(
            shard=shard, rule=self._app.entity_factory.deserialize_auto_mod_rule(payload)
        )

    @typing_extensions.override
    def deserialize_auto_mod_rule_delete_event(
        self, shard: gateway_shard.GatewayShard, payload: data_binding.JSONObject
    ) -> auto_mod_events.AutoModRuleDeleteEvent:
        return auto_mod_events.AutoModRuleDeleteEvent(
            shard=shard, rule=self._app.entity_factory.deserialize_auto_mod_rule(payload)
        )

    @typing_extensions.override
    def deserialize_auto_mod_action_execution_event(
        self, shard: gateway_shard.GatewayShard, payload: data_binding.JSONObject
    ) -> auto_mod_events.AutoModActionExecutionEvent:
        channel_id = payload.get("channel_id")
        message_id = payload.get("message_id")
        alert_message_id = payload.get("alert_system_message_id")
        return auto_mod_events.AutoModActionExecutionEvent(
            app=self._app,
            shard=shard,
            guild_id=snowflakes.Snowflake(payload["guild_id"]),
            action=self._app.entity_factory.deserialize_auto_mod_action(payload["action"]),
            rule_id=snowflakes.Snowflake(payload["rule_id"]),
            rule_trigger_type=auto_mod_models.AutoModTriggerType(payload["rule_trigger_type"]),
            user_id=snowflakes.Snowflake(payload["user_id"]),
            channel_id=snowflakes.Snowflake(channel_id) if channel_id else None,
            message_id=snowflakes.Snowflake(message_id) if message_id else None,
            alert_system_message_id=snowflakes.Snowflake(alert_message_id) if alert_message_id is not None else None,
            content=payload.get("content") or None,
            matched_keyword=payload["matched_keyword"],
            matched_content=payload.get("matched_content") or None,
        )
