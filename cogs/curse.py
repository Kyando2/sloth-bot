import discord
from discord.ext import commands
from mysqldb import *

server_id = 459195345419763713
class CurseMember(commands.Cog):
    
    def __init__(self, client):
        self.client = client
        
    
    @commands.Cog.listener()
    async def on_ready(self):
        print('CurseMember cog is online!')
    
    
    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        cursed_member = await self.get_cursed_member(member.id)
        if not cursed_member:
            return
        voice = member.voice
        voice_client = member.guild.voice_client
        if not after.channel:
            if voice_client.channel == before.channel:
                await voice_client.disconnect()

        if after.channel:
            if voice_client and after.channel:
                #print(voice_client.channel)
                await voice_client.move_to(after.channel)

            else:
                voicechannel = discord.utils.get(member.guild.channels, id=voice.channel.id)
                vc = await voicechannel.connect()
                await self.play_earrape(member.id, vc)

    async def play_earrape(self, mid, vc):
        guild = self.client.get_guild(server_id)
        member = discord.utils.get(guild.members, id=mid)
        voice = member.voice
        if voice:
            voicechannel = discord.utils.get(guild.channels, id=voice.channel.id)
            if member in voicechannel.members:
                print('It is')
                try:
                    vc.play(discord.FFmpegPCMAudio(f"earrape.mp3"), after=lambda e: self.client.loop.create_task(self.play_earrape(mid, vc)))
                    print('ok!')
                except Exception:
                    print('not ok!')

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def curse(self, ctx, member: discord.Member = None):
        await ctx.message.delete()
        if not member:
            return await ctx.send("**Inform a member to curse!**", delete_after=3)


        if member.voice:
            await self.is_connected(ctx)
            voicechannel = discord.utils.get(member.guild.channels, id=member.voice.channel.id)
            vc = await voicechannel.connect()
            await self.play_earrape(member.id, vc)

        await self.delete_cursed_member()
        await self.insert_cursed_member(member.id)
        await ctx.send(f"**{member} has been cursed!**", delete_after=3)

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def uncurse(self, ctx):
        await ctx.message.delete()

        await self.is_connected(ctx)
        curse = await self.delete_cursed_member()
        if curse:
            await ctx.send(f"**The curse has been undone!**", delete_after=3)
        else:
            await ctx.send(f"**No one had been cursed!**", delete_after=3)

    async def is_connected(self, ctx):
        voice_client = discord.utils.get(ctx.bot.voice_clients, guild=ctx.guild)
        if voice_client and voice_client.is_connected():
            await voice_client.disconnect()

    async def insert_cursed_member(self, user_id: int):
        mycursor, db = await the_data_base()
        await mycursor.execute("INSERT INTO CursedMember (user_id) VALUES (%s)", (user_id))
        await db.commit()
        await mycursor.close()

    
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def create_table_cursed_member(self, ctx):
        await ctx.message.delete()
        mycursor, db = await the_data_base()
        await mycursor.execute("CREATE TABLE CursedMember (user_id bigint)")
        await db.commit()
        await mycursor.close()
        return await ctx.send("**Table CursedMember was created!**", delete_after=3)
    
    
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def drop_table_cursed_member(self, ctx):
        await ctx.message.delete()
        mycursor, db = await the_data_base()
        await mycursor.execute("DROP TABLE CursedMember")
        await db.commit()
        await mycursor.close()
        return await ctx.send("**Table CursedMember was dropped!**", delete_after=3)
        
        
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def reset_table_cursed_member(self, ctx):
        await ctx.message.delete()
        mycursor, db = await the_data_base()
        await mycursor.execute("DROP TABLE CursedMember")
        await db.commit()
        await mycursor.execute("CREATE TABLE CursedMember (user_id bigint)")
        await db.commit()
        await mycursor.close()
        return await ctx.send("**Table CursedMember was reseted!**", delete_after=3)
    
    
    async def get_cursed_member(self, user_id: int):
        mycursor, db = await the_data_base()
        await mycursor.execute(f"SELECT * FROM CursedMember WHERE user_id = {user_id}")
        cm = await mycursor.fetchall()
        return cm

    async def delete_cursed_member(self):
        mycursor, db = await the_data_base()
        await mycursor.execute(f"SELECT * FROM CursedMember")
        cm = await mycursor.fetchall()
        if cm:
            cm = cm[0]
            await mycursor.execute(f"DELETE FROM CursedMember WHERE user_id = {cm[0]}")
            await db.commit()
            await mycursor.close()
            return True
        await mycursor.close()
    
    
def setup(client):
    client.add_cog(CurseMember(client))