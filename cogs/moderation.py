import discord
from discord.ext import commands
import asyncio
from mysqldb2 import the_data_base3
from datetime import datetime
import time

mod_log_id = 562195805272932372
muted_role_id = 537763763982434304
general_channel = 562019539135627276
last_deleted_message = []
suspect_channel_id = 732691690514546709

class Moderation(commands.Cog):
    '''
    Moderation related commands.
    '''

    def __init__(self, client):
        self.client = client

    @commands.Cog.listener()
    async def on_ready(self):
        print('Moderation cog is ready!')

    @commands.Cog.listener()
    async def on_member_join(self, member):
        if member.bot:
            return

        # User timestamp
        the_time = member.created_at
        timestamp = datetime.timestamp(the_time)
        # Actual timestamp
        time_now = datetime.timestamp(datetime.utcnow())
        account_age = round((time_now - timestamp)/86400)
        if account_age <= 2:
            suspect_channel = discord.utils.get(member.guild.channels, id=suspect_channel_id)
            await suspect_channel.send(f"🔴 Alert! Possible fake account: {member.mention} joined the server. Account was just created.\nAccount age: {account_age} day(s)!")


        if await self.get_muted_roles(member.id):
            muted_role = discord.utils.get(member.guild.roles, id=muted_role_id)
            await member.add_roles(muted_role)
            general = discord.utils.get(member.guild.channels, id=general_channel)
            await general.send(f"**Stop right there, {member.mention}! ✋ You were muted, left and rejoined the server, but that won't work!**")
    
    @commands.Cog.listener()
    async def on_message_delete(self, message):
        if message.author.bot:
            return
        last_deleted_message.clear()
        last_deleted_message.append(message)

    @commands.command()
    async def snipe(self, ctx):
        '''
        Snipes the last deleted message.
        '''
        message = last_deleted_message
        if message:
            message = message[0]
            embed = discord.Embed(title="Snipped", description=f"**>>** {message.content}", color=message.author.color, timestamp=message.created_at)
            embed.set_author(name=message.author,url=message.author.avatar_url, icon_url=message.author.avatar_url)
            await ctx.send(embed=embed)
        else:
            await ctx.send("**I couldn't snipe any messages!**")

    # Purge command
    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def purge(self, ctx, amount=0):
        '''
        (MOD) Purges messages.
        :param amount: The amount of messages to purge.
        '''
        await ctx.channel.purge(limit=amount + 1)

    # Warns a member
    @commands.command()
    @commands.has_permissions(kick_members=True)
    async def warn(self, ctx, member: discord.Member = None, *, reason=None):
        '''
        (MOD) Warns a member.
        :param member: The @ or ID of the user to warn.
        :param reason: The reason for warning the user. (Optional)
        '''
        await ctx.message.delete()
        if not member:
            await ctx.send("Please, specify a member!", delete_after=3)
        else:
            # General embed
            general_embed = discord.Embed(description=f'**Reason:** {reason}', colour=discord.Colour.dark_gold())
            general_embed.set_author(name=f'{member} has been warned', icon_url=member.avatar_url)
            await ctx.send(embed=general_embed)
            # Moderation log embed
            moderation_log = discord.utils.get(ctx.guild.channels, id=mod_log_id)
            embed = discord.Embed(title='__**Warning**__', colour=discord.Colour.dark_gold(),
                                  timestamp=ctx.message.created_at)
            embed.add_field(name='User info:', value=f'```Name: {member.display_name}\nId: {member.id}```',
                            inline=False)
            embed.add_field(name='Reason:', value=f'```{reason}```')
            embed.set_author(name=member)
            embed.set_thumbnail(url=member.avatar_url)
            embed.set_footer(text=f"Warned by {ctx.author}", icon_url=ctx.author.avatar_url)
            await moderation_log.send(embed=embed)
            current_ts = time.time()
            await self.insert_user_warn(member.id, reason, current_ts, ctx.author.id)
            user_warns = await self.get_user_warns(member.id)
            if len(user_warns) >= 3:
                await self.mute(ctx, member, reason)

    @commands.command()
    @commands.has_permissions(kick_members=True)
    async def mute(self, ctx, member: discord.Member = None, *, reason = None):
        '''
        (MOD) Mutes a member.
        :param member: The @ or the ID of the user to mute.
        :param reason: The reason for the mute.
        '''
        try:
            await ctx.message.delete()
        except:
            pass

        role = discord.utils.get(ctx.guild.roles, id=muted_role_id)
        if not member:
            return await ctx.send("**Please, specify a member!**", delete_after=3)
        if role not in member.roles:
            await member.add_roles(role)
            for mr in member.roles:
                if mr.id != role.id:
                    try:
                        await member.remove_roles(mr)
                        await self.insert_in_muted(member.id, mr.id)
                    except Exception:
                        pass
            # General embed
            general_embed = discord.Embed(description=f'**Reason:** {reason}', colour=discord.Colour.dark_grey(), timestamp=ctx.message.created_at)
            general_embed.set_author(name=f'{member} has been muted', icon_url=member.avatar_url)
            await ctx.send(embed=general_embed)
            # Moderation log embed
            moderation_log = discord.utils.get(ctx.guild.channels, id=mod_log_id)
            embed = discord.Embed(title='__**Mute**__', colour=discord.Colour.dark_grey(),
                                  timestamp=ctx.message.created_at)
            embed.add_field(name='User info:', value=f'```Name: {member.display_name}\nId: {member.id}```',
                            inline=False)
            embed.add_field(name='Reason:', value=f'```{reason}```')

            embed.set_author(name=member)
            embed.set_thumbnail(url=member.avatar_url)
            embed.set_footer(text=f"Muted by {ctx.author}", icon_url=ctx.author.avatar_url)
            await moderation_log.send(embed=embed)
        
        else:
            await ctx.send(f'**{member} is already muted!**', delete_after=5)

    # Unmutes a member
    @commands.command()
    @commands.has_permissions(kick_members=True)
    async def unmute(self, ctx, member: discord.Member = None):
        '''
        (MOD) Unmutes a member.
        :param member: The @ or the ID of the user to unmute.
        '''
        await ctx.message.delete()
        role = discord.utils.get(ctx.guild.roles, id=muted_role_id)
        if not member:
            return await ctx.send("**Please, specify a member!**", delete_after=3)
        if role in member.roles:
            user_roles = await self.get_muted_roles(member.id)
            if user_roles:
                for mrole in user_roles:
                    the_role = discord.utils.get(member.guild.roles, id=mrole[1])
                    try:
                        await member.add_roles(the_role)
                        await self.remove_role_from_system(member.id, the_role.id)
                    except Exception:
                        pass
            await member.remove_roles(role)
            # General embed
            general_embed = discord.Embed(colour=discord.Colour.light_grey(),
                                          timestamp=ctx.message.created_at)
            general_embed.set_author(name=f'{member} has been unmuted', icon_url=member.avatar_url)
            await ctx.send(embed=general_embed)
            # Moderation log embed
            moderation_log = discord.utils.get(ctx.guild.channels, id=mod_log_id)
            embed = discord.Embed(title='__**Unmute**__', colour=discord.Colour.light_grey(),
                                  timestamp=ctx.message.created_at)
            embed.add_field(name='User info:', value=f'```Name: {member.display_name}\nId: {member.id}```',
                            inline=False)
            embed.set_author(name=member)
            embed.set_thumbnail(url=member.avatar_url)
            embed.set_footer(text=f"Unmuted by {ctx.author}", icon_url=ctx.author.avatar_url)
            await moderation_log.send(embed=embed)

        else:
            await ctx.send(f'**{member} is not even muted!**', delete_after=5)

    # Mutes a member temporarily
    @commands.command()
    @commands.has_permissions(kick_members=True)
    async def tempmute(self, ctx, member: discord.Member = None, minutes: int = 5, *, reason =  None):
        '''
        (MOD) Mutes a member for a determined amount of time.
        :param member: The @ or the ID of the user to tempmute.
        :param minutes: The amount of minutes that the user will be muted.
        :param reason: The reason for the tempmute.
        '''
        await ctx.message.delete()
        if minutes == 0:
            return await ctx.send('**Inform a valid parameter!**', delete_after=3)

        role = discord.utils.get(ctx.guild.roles, id=muted_role_id)
        seconds = minutes * 60
        if not member:
            return await ctx.send("**Please, specify a member!**", delete_after=3)
        if role not in member.roles:
            await member.add_roles(role)
            for mr in member.roles:
                if mr.id != role.id:
                    try:
                        await member.remove_roles(mr)
                        await self.insert_in_muted(member.id, mr.id)
                    except Exception:
                        pass
            
            # General embed
            general_embed = discord.Embed(description=f'**Reason:** {reason}', colour=discord.Colour.lighter_grey(),
                                          timestamp=ctx.message.created_at)
            general_embed.set_author(name=f'{member} has been tempmuted', icon_url=member.avatar_url)
            await ctx.send(embed=general_embed)
            # Moderation log embed
            moderation_log = discord.utils.get(ctx.guild.channels, id=mod_log_id)
            embed = discord.Embed(title='__**Tempmute**__', colour=discord.Colour.lighter_grey(),
                                  timestamp=ctx.message.created_at)
            embed.add_field(name='User info:', value=f'```Name: {member.display_name}\nId: {member.id}```',
                            inline=False)
            embed.add_field(name='Reason:', value=f'```{reason}```')
            embed.set_author(name=member)
            embed.set_thumbnail(url=member.avatar_url)
            embed.set_footer(text=f"Tempmuted by {ctx.author}", icon_url=ctx.author.avatar_url)
            await moderation_log.send(embed=embed)
            # After a while
            await asyncio.sleep(seconds)
            if role in member.roles:
                user_roles = await self.get_muted_roles(member.id)
                if user_roles:
                    for mrole in user_roles:
                        the_role = discord.utils.get(member.guild.roles, id=mrole[1])
                        try:
                            await member.add_roles(the_role)
                            await self.remove_role_from_system(member.id, the_role.id)
                        except Exception:
                            pass
                await member.remove_roles(role)
            general_embed = discord.Embed(colour=discord.Colour.lighter_grey(),
                                          timestamp=ctx.message.created_at)
            general_embed.set_author(name=f'{member} is no longer tempmuted', icon_url=member.avatar_url)
            await ctx.send(embed=general_embed)
        else:
            await ctx.send(f'**{member} is not even muted!**', delete_after=5)
    @commands.command()
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx, member: discord.Member = None, *, reason=None):
        '''
        (MOD) Kicks a member from the server.
        :param member: The @ or ID of the user to kick.
        :param reason: The reason for kicking the user. (Optional)
        '''
        await ctx.message.delete()
        if not member:
            await ctx.send('**Please, specify a member!**', delete_after=3)
        else:
            try:
                await member.kick(reason=reason)
            except Exception:
                await ctx.send('**You cannot do that!**', delete_after=3)
            else:
                # General embed
                general_embed = discord.Embed(description=f'**Reason:** {reason}', colour=discord.Colour.magenta())
                general_embed.set_author(name=f'{member} has been kicked', icon_url=member.avatar_url)
                await ctx.send(embed=general_embed)
                # Moderation log embed
                moderation_log = discord.utils.get(ctx.guild.channels, id=mod_log_id)
                embed = discord.Embed(title='__**Kick**__', colour=discord.Colour.magenta(),
                                      timestamp=ctx.message.created_at)
                embed.add_field(name='User info:', value=f'```Name: {member.display_name}\nId: {member.id}```',
                                inline=False)
                embed.add_field(name='Reason:', value=f'```{reason}```')
                embed.set_author(name=member)
                embed.set_thumbnail(url=member.avatar_url)
                embed.set_footer(text=f"Kicked by {ctx.author}", icon_url=ctx.author.avatar_url)
                await moderation_log.send(embed=embed)

    # Bans a member
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def ban(self, ctx, member: discord.Member = None, *, reason=None):
        '''
        (ADM) Bans a member from the server.
        :param member: The @ or ID of the user to ban.
        :param reason: The reason for banning the user. (Optional)
        '''
        await ctx.message.delete()
        if not member:
            await ctx.send('**Please, specify a member!**', delete_after=3)
        else:
            try:
                await member.ban(delete_message_days=7, reason=reason)
            except Exception:
                await ctx.send('**You cannot do that!**', delete_after=3)
            else:
                # General embed
                general_embed = discord.Embed(description=f'**Reason:** {reason}', colour=discord.Colour.dark_red())
                general_embed.set_author(name=f'{member} has been banned', icon_url=member.avatar_url)
                await ctx.send(embed=general_embed)
                # Moderation log embed
                moderation_log = discord.utils.get(ctx.guild.channels, id=mod_log_id)
                embed = discord.Embed(title='__**Banishment**__', colour=discord.Colour.dark_red(),
                                      timestamp=ctx.message.created_at)
                embed.add_field(name='User info:', value=f'```Name: {member.display_name}\nId: {member.id}```',
                                inline=False)
                embed.add_field(name='Reason:', value=f'```{reason}```')
                embed.set_author(name=member)
                embed.set_thumbnail(url=member.avatar_url)
                embed.set_footer(text=f"Banned by {ctx.author}", icon_url=ctx.author.avatar_url)
                await moderation_log.send(embed=embed)

    # Unbans a member
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def unban(self, ctx, *, member=None):
        '''
        (ADM) Unbans a member from the server.
        :param member: The full nickname and # of the user to unban.
        '''
        await ctx.message.delete()
        if not member:
            return await ctx.send('**Please, inform a member!**', delete_after=3)

        banned_users = await ctx.guild.bans()
        try:
            member_name, member_discriminator = str(member).split('#')
        except ValueError:
            return await ctx.send('**Wrong parameter!**', delete_after=3)

        for ban_entry in banned_users:
            user = ban_entry.user

            if (user.name, user.discriminator) == (member_name, member_discriminator):
                await ctx.guild.unban(user)
                # General embed
                general_embed = discord.Embed(colour=discord.Colour.red())
                general_embed.set_author(name=f'{user} has been unbanned', icon_url=user.avatar_url)
                await ctx.send(embed=general_embed)
                # Moderation log embed
                moderation_log = discord.utils.get(ctx.guild.channels, id=mod_log_id)
                embed = discord.Embed(title='__**Unbanishment**__', colour=discord.Colour.red(),
                                      timestamp=ctx.message.created_at)
                embed.add_field(name='User info:', value=f'```Name: {user.display_name}\nId: {user.id}```',
                                inline=False)
                embed.set_author(name=user)
                embed.set_thumbnail(url=user.avatar_url)
                embed.set_footer(text=f"Unbanned by {ctx.author}", icon_url=ctx.author.avatar_url)
                await moderation_log.send(embed=embed)
                return
        else:
            await ctx.send('**Member not found!**', delete_after=3)

    # Bans a member
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def softban(self, ctx, member: discord.Member = None, *, reason=None):
        '''
        (ADM) Bans and unbans a member from the server; deleting their messages from the last 7 seven days.
        :param member: The @ or ID of the user to softban.
        :param reason: The reason for softbanning the user. (Optional)
        '''
        await ctx.message.delete()
        if not member:
            await ctx.send('**Please, specify a member!**', delete_after=3)
        else:
            try:
                await member.ban(delete_message_days=7, reason=reason)
                await member.unban(reason=reason)
            except Exception:
                await ctx.send('**You cannot do that!**', delete_after=3)
            else:
                # General embed
                general_embed = discord.Embed(description=f'**Reason:** {reason}', colour=discord.Colour.dark_purple())
                general_embed.set_author(name=f'{member} has been softbanned', icon_url=member.avatar_url)
                await ctx.send(embed=general_embed)
                # Moderation log embed
                moderation_log = discord.utils.get(ctx.guild.channels, id=mod_log_id)
                embed = discord.Embed(title='__**SoftBanishment**__', colour=discord.Colour.dark_purple(),
                                      timestamp=ctx.message.created_at)
                embed.add_field(name='User info:', value=f'```Name: {member.display_name}\nId: {member.id}```',
                                inline=False)
                embed.add_field(name='Reason:', value=f'```{reason}```')
                embed.set_author(name=member)
                embed.set_thumbnail(url=member.avatar_url)
                embed.set_footer(text=f"SoftBanned by {ctx.author}", icon_url=ctx.author.avatar_url)
                await moderation_log.send(embed=embed)

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def hackban(self, ctx, user_id: int = None, *, reason=None):
        '''
        (ADM) Bans a user that is currently not in the server.
        Only accepts user IDs.
        :param user_id: Member ID
        :param reason: The reason for hackbanning the user. (Optional)
        '''
        await ctx.message.delete()
        if not user_id:
            return await ctx.send("**Inform the user id!**", delete_after=3)
        member = discord.Object(id=user_id)
        if not member:
            return await ctx.send("**Invalid user id!**", delete_after=3)
        try:
            await ctx.guild.ban(member, reason=reason)
            # General embed
            general_embed = discord.Embed(description=f'**Reason:** {reason}', colour=discord.Colour.dark_teal(),
                                          timestamp=ctx.message.created_at)
            general_embed.set_author(name=f'{self.client.get_user(user_id)} has been hackbanned')
            await ctx.send(embed=general_embed)

            # Moderation log embed
            moderation_log = discord.utils.get(ctx.guild.channels, id=mod_log_id)
            embed = discord.Embed(title='__**HackBanishment**__', colour=discord.Colour.dark_teal(),
                                  timestamp=ctx.message.created_at)
            embed.add_field(name='User info:', value=f'```Name: {self.client.get_user(user_id)}\nId: {member.id}```',
                            inline=False)
            embed.add_field(name='Reason:', value=f'```{reason}```')

            embed.set_author(name=self.client.get_user(user_id))
            embed.set_footer(text=f"HackBanned by {ctx.author}", icon_url=ctx.author.avatar_url)
            await moderation_log.send(embed=embed)
        except discord.errors.NotFound:
            return await ctx.send("**Invalid user id!**", delete_after=3)

    async def insert_in_muted(self, user_id: int, role_id: int):
        mycursor, db = await the_data_base3()
        await mycursor.execute(f"INSERT INTO mutedmember (user_id, role_id) VALUES (%s, %s)", (user_id, role_id))
        await db.commit()
        await mycursor.close()

    async def get_muted_roles(self, user_id: int):
        mycursor, db = await the_data_base3()
        await mycursor.execute(f"SELECT * FROM mutedmember WHERE user_id = {user_id}")
        user_roles = await mycursor.fetchall()
        await mycursor.close()
        return user_roles

    async def remove_role_from_system(self, user_id: int, role_id: int):
        mycursor, db = await the_data_base3()
        await mycursor.execute(f"DELETE FROM mutedmember WHERE user_id = {user_id} and role_id = {role_id}")
        await db.commit()
        await mycursor.close()


    @commands.command(hidden=True)
    @commands.has_permissions(administrator=True)
    async def reset_table_mutedmember(self, ctx):
        '''
        (ADM) Resets the MutedMember table.
        '''
        if not self.check_table_mutedmember_exists():
            return await ctx.send("**Table __MutedMember__ doesn't exist yet**")

        await ctx.message.delete()
        mycursor, db = await the_data_base3()
        await mycursor.execute("DELETE FROM mutedmember")
        #await mycursor.execute("CREATE TABLE mutedmember (user_id bigint, role_id bigint)")
        await db.commit()
        await mycursor.close()
        return await ctx.send("**Table __mutedmember__ reset!**", delete_after=3)

    @commands.command(hidden=True)
    @commands.has_permissions(administrator=True)
    async def create_table_warns(self, ctx):
        '''
        (ADM) Creates the UserWarns table
        '''
        if await self.check_table_warns_exists():
            return await ctx.send("**Table __UserWarns__ already exists!**")
        
        await ctx.message.delete()
        mycursor, db = await the_data_base3()
        await mycursor.execute("CREATE TABLE UserWarns (user_id bigint, warn_reason VARCHAR(100), warn_timestamp bigint, warn_id bigint auto_increment, perpetrator bigint)")
        await db.commit()
        await mycursor.close()
        return await ctx.send("**Table __UserWarns__ created!**", delete_after=3)


    @commands.command(hidden=True)
    @commands.has_permissions(administrator=True)
    async def drop_table_warns(self, ctx):
        '''
        (ADM) Creates the UserWarns table
        '''
        if not await self.check_table_warns_exists():
            return await ctx.send("**Table __UserWarns__ doesn't exist!**")
        await ctx.message.delete()
        mycursor, db = await the_data_base3()
        await mycursor.execute("DROP TABLE UserWarns")
        await db.commit()
        await mycursor.close()
        return await ctx.send("**Table __UserWarns__ created!**", delete_after=3)

    @commands.command(hidden=True)
    @commands.has_permissions(administrator=True)
    async def reset_table_warns(self, ctx):
        '''
        (ADM) Creates the UserWarns table
        '''
        if not await self.check_table_warns_exists():
            return await ctx.send("**Table __UserWarns__ doesn't exist yet!**")

        await ctx.message.delete()
        mycursor, db = await the_data_base3()
        await mycursor.execute("DELETE FROM UserWarns")
        await db.commit()
        await mycursor.close()
        return await ctx.send("**Table __UserWarns__ created!**", delete_after=3)

    async def check_table_warns_exists(self):
        '''
        Checks if the UserWarns table exists
        '''
        mycursor, db = await the_data_base3()
        await mycursor.execute(f"SHOW TABLE STATUS LIKE 'UserWarns'")
        table_info = await mycursor.fetchall()
        await mycursor.close()
        if len(table_info) == 0:
            return False

        else:
            return True

    async def check_table_mutedmember_exists(self):
        '''
        Checks if the MutedMember table exists
        '''
        mycursor, db = await the_data_base3()
        await mycursor.execute(f"SHOW TABLE STATUS LIKE 'MutedMember'")
        table_info = await mycursor.fetchall()
        await mycursor.close()
        if len(table_info) == 0:
            return False

        else:
            return True

    async def insert_user_warn(self, user_id: int, reason, timestamp: int, perpetrator: int):
        '''
        Insert a warning into the system.
        '''
        mycursor, db = await the_data_base3()
        await mycursor.execute(f"INSERT INTO UserWarns (user_id, warn_reason, warn_timestamp, perpetrator) VALUES (%s, %s, %s, %s)", (user_id, reason, timestamp, perpetrator))
        await db.commit()
        await mycursor.close()

    async def get_user_warn_by_warn_id(self, warn_id: int):
        '''
        Gets a specific warning by ID.
        '''
        mycursor, db = await the_data_base3()
        await mycursor.execute(f"SELECT * FROM UserWarns WHERE warn_id = {warn_id}")
        user_warns = await mycursor.fetchall()
        return user_warns

    async def get_user_warns(self, user_id: int):
        '''
        Gets all warnings from a user.
        '''
        mycursor, db = await the_data_base3()
        await mycursor.execute(f"SELECT * FROM UserWarns WHERE user_id = {user_id}")
        user_warns = await mycursor.fetchall()
        await mycursor.close()
        return user_warns

    async def remove_user_warning(self, warn_id: int):
        '''
        Removes a specifc warning by ID.
        '''
        mycursor, db = await the_data_base3()
        await mycursor.execute(f"DELETE FROM UserWarns WHERE warn_id = {warn_id}")
        await db.commit()
        await mycursor.close()

    async def remove_user_warnings(self, user_id: int):
        '''
        Deletes all warnings from a user by their ID.
        '''
        mycursor, db = await the_data_base3()
        await mycursor.execute(f"DELETE FROM UserWarns WHERE user_id = {user_id}")
        await db.commit()
        await mycursor.close()
    

    @commands.command()
    @commands.has_permissions(kick_members=True)
    async def remove_warning(self, ctx, warn_id: int = None):
        '''
        (ADM) Removes a specific warn by ID.
        :param warn_id: The warn ID.
        '''
        if not warn_id:
            return await ctx.send("**Inform the warn ID!**")

        user_warns = await self.get_user_warn_by_warn_id(warn_id)
        if user_warns:
            await self.remove_user_warning(warn_id)
            member = discord.utils.get(ctx.guild.members, id=user_warns[0])
            await ctx.send(f"**Removed warn with ID `{warn_id}` for {member}**")
        else:
            await ctx.send(f"**Warn with ID `{warn_id}` was not found!**")

    @commands.command()
    @commands.has_permissions(kick_members=True)
    async def remove_warnings(self, ctx, member: discord.Member = None):
        '''
        (MOD) Removes all warnings for a specific user.
        :param member: The member to get the warns from.
        '''
        if not member:
            return await ctx.send("**Inform a member!**")
        
        user_warns = await self.get_user_warns(member.id)
        if not user_warns:
            return await ctx.send(f"**{member.mention} doesn't have any existent warnings!**")

        await self.remove_user_warnings(member.id)
        return await ctx.send(f"**Removed all warnings for {member.mention}!**")
        
        
    @commands.command()
    @commands.has_permissions(kick_members=True)
    async def show_warnings(self, ctx, member: discord.Member = None):
        '''
        Shows all warnings for a specific user.
        :param member: The member to show the warnings from.
        '''
        if not member:
            return await ctx.send("**Inform a member!**")
        
        user_warns = await self.get_user_warns(member.id)
        if not user_warns:
            return await ctx.send(f"**{member.mention} doesn't have any existent warnings!**")
        
        embed = discord.Embed(
            title=f"Warnings for {member}",
            color=member.color,
            url=member.avatar_url,
            timestamp=ctx.message.created_at)
        
        embed.set_thumbnail(url=member.avatar_url)
        embed.set_footer(text=f"Requested by: {ctx.author}", icon_url=ctx.author.avatar_url)
        
        for warn in user_warns:
            warn_date = datetime.fromtimestamp(warn[2]).strftime('%d/%m/%Y at %H:%M:%S')
            perpetrator = discord.utils.get(ctx.guild.members, id=user_warns[4])
            embed.add_field(
                name=f"Warn ID: {warn[3]}", 
                value=f"**Warned on {warn_date} by {perpetrator}\n**Reason:** {warn[1]}", 
                inline=True)

        await ctx.send(embed=embed)

def setup(client):
    client.add_cog(Moderation(client))
